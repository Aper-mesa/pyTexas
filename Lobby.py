import time

import pygame as g
import pygame_gui as gui

import net
import player
import steam_wrapper as steam
from round import Room


def dbg(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ======== 全局常量 ========
ELobbyType_Private, ELobbyType_FriendsOnly, ELobbyType_Public, ELobbyType_Invisible = 0, 1, 2, 3
CBID_LobbyCreated = 513
CBID_GameLobbyJoinRequested = 333
CBID_LobbyEnter = 504
CBID_LobbyChatUpdate = 506
CBID_LobbyDataUpdate = 505
CBID_LobbyInvite = 503
CBID_GameRichPresenceJoinRequested = 337
CBID_GameOverlayActivated = 331


def _after_leave_lobby():
    steam.clear_rich_presence()
    steam.set_rich_presence("steam_player_group", "")
    steam.set_rich_presence("steam_player_group_size", "")


class Lobby:
    def __init__(self, screen, manager, current_player: player.Player, max_members: int = 9):
        try:
            self.messenger = net.create_messenger(steam)
            dbg("[Lobby] Steam 网络消息系统初始化成功")
            self.messenger.register_handler(
                net.SteamNetworkMessenger.CHANNEL_ROOM_DATA,
                self._on_room_received
            )
        except Exception as e:
            dbg(f"[Lobby] 网络消息系统初始化失败: {e}")
            self.messenger = None

        self._received_room = None

        self.screen = screen
        self.clock = g.time.Clock()
        self.manager = manager
        self.running = True

        self.current_player = current_player
        self.max_members = max_members

        self.my_steamid = steam.get_my_steam_id()
        self.my_name = steam.get_my_persona_name()
        dbg(f"self.my_steamid={self.my_steamid}, self.my_name={self.my_name}")

        self.lobby_id = 0
        self.member_names = []
        self._friend_ids = []

        self._start_payload = None  # 保存开局参数（min/init 等）
        self._start_seen_ts = 0  # 避免重复触发

        self._callbacks = []
        self._install_callbacks()

        # ---------- UI ----------
        w, h = self.screen.get_size()
        self._w, self._h = w, h  # 记录，供是否需要 relayout 判断

        # 先占位，具体 rect 在 _relayout() 里计算
        self.title_label = gui.elements.UILabel(
            relative_rect=g.Rect(0, 0, 0, 0), text="Lobby", manager=self.manager
        )

        self.create_btn = gui.elements.UIButton(
            relative_rect=g.Rect(0, 0, 0, 0), text="创建公开大厅", manager=self.manager
        )

        self.invite_btn = gui.elements.UIButton(
            relative_rect=g.Rect(0, 0, 0, 0), text="邀请好友加入", manager=self.manager
        )

        self.leave_btn = gui.elements.UIButton(
            relative_rect=g.Rect(0, 0, 0, 0), text="离开大厅", manager=self.manager
        )

        # 右侧：成员列表（现在居中且更宽）
        self.members_list = gui.elements.UISelectionList(
            relative_rect=g.Rect(0, 0, 0, 0), item_list=[], manager=self.manager
        )

        # 状态栏
        self.status_label = gui.elements.UILabel(
            relative_rect=g.Rect(0, 0, 0, 0),
            text=f"你好 {self.my_name} ({self.my_steamid})",
            manager=self.manager,
        )

        # ===== Host controls (bottom centered) =====
        self.is_host = False  # 进入/创建大厅后再置位
        self.minBet = 1
        self.initBet = 50

        bottom_y = self.screen.get_height() - 120
        group_w = 480
        group_x = (self.screen.get_width() - group_w) // 2

        self.ui_min_bet = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(group_x, bottom_y, 120, 36),
            manager=self.manager,
            placeholder_text="minBet"
        )
        self.ui_min_bet.set_text(str(self.minBet))

        self.ui_init_bet = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(group_x + 140, bottom_y, 120, 36),
            manager=self.manager,
            placeholder_text="initBet"
        )
        self.ui_init_bet.set_text(str(self.initBet))

        self.ui_start_btn = gui.elements.UIButton(
            relative_rect=g.Rect(group_x + 280, bottom_y, 200, 36),
            text="开始游戏",
            manager=self.manager
        )

        # 初始隐藏（只有房主显示）
        for el in (self.ui_min_bet, self.ui_init_bet, self.ui_start_btn):
            el.hide()

        # 初始时未在大厅，禁用邀请按钮
        self.invite_btn.disable()

        self.leave_btn.disable()

        # 统一做一次布局
        self._relayout()

        # 初始化
        self._load_friends_list()

        # 冷启动 join：通过 Steam 启动并带 connect 时
        try:
            val = steam.get_launch_query_param("connect")
            if val:
                s = val.decode('utf-8', 'ignore').strip()
                dbg(f"launch connect param='{s}'")
                for prefix in ("lobby:", "connect=", "steam://joinlobby/"):
                    if s.startswith(prefix):
                        s = s[len(prefix):]
                lobby_id = int(s)
                steam.join_lobby(lobby_id)
                self._set_status(f"启动参数 Join -> 加入 Lobby {lobby_id} ...")
                dbg(f"JoinLobby via launch param: {lobby_id}")
        except Exception as e:
            dbg(f"parse launch connect failed: {e}")
        dbg(f"overlay enabled? {bool(steam.is_overlay_enabled())}")

    def _on_room_received(self, sender_steam_id, room_obj):
        """处理接收到的 Room 对象（非房主回调）"""
        dbg(f"[Lobby] 收到来自 {sender_steam_id} 的 Room 对象")

        # 验证发送者是房主
        if not self.lobby_id:
            dbg("[Lobby] 未在 Lobby 中，忽略 Room 数据")
            return

        # 可选：验证发送者是房主
        # 这里简化处理，直接接受
        self._received_room = room_obj
        self._set_status(f"收到游戏房间数据，准备开始...")
        dbg("[Lobby] Room 对象已接收，等待进入游戏")

    def _relayout(self):
        w, h = self.screen.get_size()
        cx = w // 2

        # 尺寸参数（可按喜好微调）
        title_w, title_h = int(w * 0.23), int(h * 0.05)
        btn_w, btn_h = int(w * 0.14), int(h * 0.05)
        gap = int(w * 0.015)

        # 顶部标题
        self.title_label.set_relative_position((cx - title_w // 2, int(h * 0.03)))
        self.title_label.set_dimensions((title_w, title_h))

        # 顶部三按钮水平排布
        total_w = btn_w * 3 + gap * 2
        btn_y = int(h * 0.10)
        start_x = cx - total_w // 2
        self.create_btn.set_relative_position((start_x, btn_y))
        self.create_btn.set_dimensions((btn_w, btn_h))

        self.invite_btn.set_relative_position((start_x + btn_w + gap, btn_y))
        self.invite_btn.set_dimensions((btn_w, btn_h))

        self.leave_btn.set_relative_position((start_x + (btn_w + gap) * 2, btn_y))
        self.leave_btn.set_dimensions((btn_w, btn_h))

        # 成员列表居中，宽约 60% 屏幕，高约 60% 屏幕
        list_w, list_h = int(w * 0.62), int(h * 0.60)
        list_x = cx - list_w // 2
        list_y = int(h * 0.18)
        self.members_list.set_relative_position((list_x, list_y))
        self.members_list.set_dimensions((list_w, list_h))

        # 底部状态栏
        status_w, status_h = int(w * 0.6), int(h * 0.04)
        status_x = cx - status_w // 2
        status_y = list_y + list_h + int(h * 0.02)
        self.status_label.set_relative_position((status_x, status_y))
        self.status_label.set_dimensions((status_w, status_h))

    # ---------- Steam Callbacks ----------
    def _install_callbacks(self):
        def on_lobby_created(data):
            dbg(f"on_lobby_created: result={data['m_eResult']}, lobby={data['m_ulSteamIDLobby']}")
            if data['m_eResult'] == 1:  # k_EResultOK
                self.lobby_id = data['m_ulSteamIDLobby']
                self.invite_btn.enable()
                self._set_status(f"已创建Lobby：{self.lobby_id}，等待进入...")
                # 创建成功视为房主
                self.is_host = True
                self.create_btn.disable()
                for el in (self.ui_min_bet, self.ui_init_bet, self.ui_start_btn):
                    el.show()
                    el.enable()

                # 把自己资料写到 Lobby 成员数据，供别人读取
                self._push_my_member_data()
            else:
                self._set_status(f"创建失败，EResult={data['m_eResult']}")

        def on_lobby_enter(data):
            self.lobby_id = data['m_ulSteamIDLobby']
            dbg(f"on_lobby_enter: lobby={data['m_ulSteamIDLobby']}, locked={data['m_bLocked']}, enter_resp={data['m_EChatRoomEnterResponse']}")
            self._set_status(f"已进入Lobby：{self.lobby_id}")
            self.leave_btn.enable()
            self.create_btn.disable()

            # 不是创建路径进入，则不是房主
            if not getattr(self, "is_host", False):
                self.is_host = False
                for el in (self.ui_min_bet, self.ui_init_bet, self.ui_start_btn):
                    el.hide()

            # 进入后同样写一次自己的成员数据（昵称/ID/金钱）
            self._push_my_member_data()

            # 刷新成员列表（可选）
            self._refresh_members_list()

            self._after_enter_lobby()
            self._refresh_member_names()
            self.invite_btn.enable()

            ok_joinable = steam.set_lobby_joinable(self.lobby_id, True)
            dbg(f"SetLobbyJoinable(true) -> {ok_joinable}")

            steam.set_lobby_data(self.lobby_id, "name", self.my_name)
            steam.set_lobby_data(self.lobby_id, "ver", "1")
            steam.set_lobby_data(self.lobby_id, "mode", "poker")

            steam.set_lobby_member_data(self.lobby_id, "player_name", self.my_name)
            dbg("Lobby data & member data set")

        def on_lobby_chat_update(data):
            if data['m_ulSteamIDLobby'] == self.lobby_id:
                self._refresh_member_names()
            dbg(f"on_lobby_chat_update: lobby={data['m_ulSteamIDLobby']}, user_changed={data['m_ulSteamIDUserChanged']}, state_change={data['m_rgfChatMemberStateChange']}")

        def on_lobby_data_update(data):
            self._refresh_member_names()
            self._refresh_members_list()

            # 只处理当前 lobby
            if data['m_ulSteamIDLobby'] != self.lobby_id:
                return

            # 只有 Lobby 级变化才考虑 start（成员级更新直接忽略）
            if data['m_ulSteamIDMember'] not in (0, self.lobby_id):
                return

            raw = steam.get_lobby_data(self.lobby_id, "start")
            s = (raw or b"").decode("utf-8", "ignore").strip()

            # 如果 s 是空的，说明 "start" 数据还没被房主设置，直接忽略这次更新
            if not s:
                return

            try:
                parts = s.split(",")
                if len(parts) < 2:
                    dbg(f"收到无效的 'start' 数据: {s}")
                    return

                minBet = int(parts[0])
                initBet = int(parts[1])
                ts = int(parts[2]) if len(parts) > 2 else 0

                if ts and ts == self._start_seen_ts:
                    return
                self._start_seen_ts = ts
                self._start_payload = (minBet, initBet, ts)
            except (ValueError, IndexError) as e:
                dbg(f"解析 'start' 数据 '{s}' 时出错: {e}")

        def on_lobby_invite(data):
            dbg(f"on_lobby_invite: from={data['m_ulSteamIDUser']}, lobby={data['m_ulSteamIDLobby']}, gameid={data['m_ulGameID']}")
            steam.join_lobby(data['m_ulSteamIDLobby'])
            self._set_status(f"收到邀请，正在加入Lobby {data['m_ulSteamIDLobby']} ...")

        def on_game_lobby_join_requested(data):
            dbg(f"on_game_lobby_join_requested: friend={data['m_steamIDFriend']}, lobby={data['m_steamIDLobby']}")
            steam.join_lobby(data['m_steamIDLobby'])
            self._set_status(f"好友请求加入，进入Lobby {data['m_steamIDLobby']} ...")

        def on_game_rich_presence_join_requested(data):
            connect = bytes(data['m_rgchConnect']).split(b'\x00', 1)[0].decode('utf-8', 'ignore')
            dbg(f"on_game_rich_presence_join_requested: friend={data['m_steamIDFriend']}, connect='{connect}'")
            s = connect.strip()
            for prefix in ("lobby:", "connect=", "steam://joinlobby/"):
                if s.startswith(prefix):
                    s = s[len(prefix):]
            try:
                lid = int(s)
                steam.join_lobby(lid)
                self._set_status(f"RichPresence Join -> 加入 Lobby {lid} ...")
                dbg(f"JoinLobby via RP connect: {lid}")
            except ValueError:
                dbg(f"RichPresence connect 无法解析为数字 lobby id: '{connect}'")
                self._set_status("收到 Join 请求但 connect 无效")

        self._callbacks.append(steam.SteamCallback(CBID_LobbyCreated, on_lobby_created))
        self._callbacks.append(steam.SteamCallback(CBID_LobbyEnter, on_lobby_enter))
        self._callbacks.append(steam.SteamCallback(CBID_LobbyChatUpdate, on_lobby_chat_update))
        self._callbacks.append(steam.SteamCallback(CBID_LobbyDataUpdate, on_lobby_data_update))
        self._callbacks.append(steam.SteamCallback(CBID_LobbyInvite, on_lobby_invite))
        self._callbacks.append(steam.SteamCallback(CBID_GameLobbyJoinRequested, on_game_lobby_join_requested))
        self._callbacks.append(
            steam.SteamCallback(CBID_GameRichPresenceJoinRequested, on_game_rich_presence_join_requested))

    def _push_my_member_data(self):
        """把当前玩家资料写入 Lobby 成员数据，键 'player'，值 'username,steam_id,money'"""
        if not getattr(self, "lobby_id", None):
            return
        # Player上若没有getOnlineData，就按下面格式拼
        username = getattr(self.current_player, "username", getattr(self.current_player, "persona_name", ""))
        steam_id = str(self.current_player.steam_id)
        money = int(getattr(self.current_player, "money", 0))
        payload = f"{username},{steam_id},{money}".encode("utf-8")
        # 注意：这里使用你项目里已经绑定好的 matchmaking 句柄/函数名
        steam.set_lobby_member_data(self.lobby_id, "player", payload)

    def _collect_players(self):
        """读取 Lobby 全体成员为 Player 实例列表（用 Player.create / 或直接 new Player）"""
        res = []
        if not getattr(self, "lobby_id", None):
            return res

        count = steam.get_num_lobby_members(self.lobby_id)
        for i in range(count):
            steam_id = steam.get_lobby_member_by_index(self.lobby_id, i)
            raw = steam.get_lobby_member_data(self.lobby_id, steam_id, "player")

            s = raw.decode("utf-8", "ignore")
            name, steam_id, money = s.split(",", 3)
            p = player.Player(steam_id, name, money)
            p.money = int(money)

            res.append(p)
        return res

    def _refresh_members_list(self):
        """（可选）如果你有右侧列表，就按需刷新一下显示"""
        try:
            players = self._collect_players()
            items = [f"{p.username} | {p.steam_id} | ¥{p.money}" for p in players]
            self.members_list.set_item_list(items)
        except Exception:
            pass

    # ---------- Helpers ----------
    def _set_status(self, msg: str):
        self.status_label.set_text(msg)

    def _after_enter_lobby(self):
        steam.set_rich_presence("connect", str(self.lobby_id))
        steam.set_rich_presence("status", "In Lobby")
        steam.set_rich_presence("steam_player_group", str(self.lobby_id))
        steam.set_rich_presence("steam_player_group_size", str(steam.get_num_lobby_members(self.lobby_id)))
        dbg(f"SetRichPresence connect={self.lobby_id}")

    def _load_friends_list(self):
        k_EFriendFlagImmediate = 4
        cnt = steam.get_friend_count(k_EFriendFlagImmediate)
        items, ids = [], []
        for i in range(max(0, cnt)):
            fid = steam.get_friend_by_index(i, k_EFriendFlagImmediate)
            name = steam.get_friend_persona_name(fid)
            display = (name or b"Unknown").decode("utf-8", "ignore")
            items.append(display)
            ids.append(fid)
        self._friend_ids = ids

    def _refresh_member_names(self):
        if not self.lobby_id:
            self.members_list.set_item_list([])
            return
        count = steam.get_num_lobby_members(self.lobby_id)
        names = []
        for i in range(int(count)):
            sid = steam.get_lobby_member_by_index(self.lobby_id, i)
            pname = steam.get_friend_persona_name(sid)
            display = (pname or b"").decode("utf-8", "ignore").strip()
            if not display:
                p = steam.get_lobby_member_data(self.lobby_id, sid, "player_name")
                display = (p or b"Unknown").decode("utf-8", "ignore")
            names.append(display)
        self.member_names = names
        self.members_list.set_item_list(names)
        dbg(f"members[{len(self.member_names)}]: {self.member_names}")
        # 刷新成员列表后，同步人数到 Rich Presence
        if self.lobby_id:
            steam.set_rich_presence("steam_player_group_size", str(len(self.member_names)))

    # ---------- Actions ----------
    def create_public_lobby(self):
        call = steam.create_lobby(ELobbyType_Public, self.max_members)
        dbg(f"CreateLobby called -> SteamAPICall_t={call}")
        self._set_status("正在创建公开Lobby...")

    def invite_friends_via_overlay(self):
        if not self.lobby_id:
            self._set_status("请先创建或加入一个Lobby")
            return
        dbg(f"invite overlay open, lobby={self.lobby_id}")
        steam.activate_game_overlay_invite_dialog(self.lobby_id)
        self._set_status("已打开Steam邀请弹窗")

    def leave_lobby(self):
        if self.lobby_id:
            steam.leave_lobby(self.lobby_id)
            self.invite_btn.disable()
            self.is_host = False
            controls = (self.ui_min_bet, self.ui_init_bet, self.ui_start_btn)
            self.create_btn.enable()
            self.leave_btn.disable()
            for el in controls:
                el.disable()
                el.hide()
            _after_leave_lobby()
            self._set_status("已离开Lobby")
            self.lobby_id = 0
            self.members_list.set_item_list([])

    # ---------- Loop ----------
    def handle_events(self):
        steam.run_callbacks()

        # ===== 新增：处理网络消息 =====
        if self.messenger:
            self.messenger.process_messages()

        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT", None

            self.manager.process_events(event)

            if event.type == gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.create_btn:
                    self.create_public_lobby()
                elif event.ui_element == self.invite_btn:
                    self.invite_friends_via_overlay()
                elif event.ui_element == self.leave_btn:
                    self.leave_lobby()
                elif event.ui_element == self.ui_start_btn:
                    # ===== 修改：房主开始游戏逻辑 =====
                    self.minBet = int(self.ui_min_bet.get_text().strip())
                    self.initBet = int(self.ui_init_bet.get_text().strip())

                    # 1) 创建 Room 对象
                    players_list = self._collect_players()
                    room = Room([players_list, self.minBet, self.initBet])

                    # 2) 广播 Room 给所有成员（使用网络消息）
                    if self.messenger:
                        member_ids = []
                        count = steam.get_num_lobby_members(self.lobby_id)
                        for i in range(count):
                            sid = steam.get_lobby_member_by_index(self.lobby_id, i)
                            if sid != self.my_steamid:
                                member_ids.append(sid)

                        # 广播 Room 对象
                        success_count = self.messenger.broadcast_to_lobby(
                            member_ids,
                            room,
                            channel=net.SteamNetworkMessenger.CHANNEL_ROOM_DATA,
                            reliable=True
                        )
                        dbg(f"[Lobby] Room 已广播给 {success_count}/{len(member_ids)} 个成员")

                        # 给一点时间让消息发送出去
                        time.sleep(0.2)

                    # 3) 设置 Lobby 数据标记（兼容旧方式）
                    ts = int(time.time())
                    payload = f"{self.minBet},{self.initBet},{ts}".encode("utf-8")
                    steam.set_lobby_data(self.lobby_id, "start", payload)
                    steam.set_lobby_joinable(self.lobby_id, False)

                    # 4) 房主自己也保存 Room 对象
                    self._received_room = room
                    self._start_payload = (self.minBet, self.initBet, ts)

                    dbg("[Lobby] 房主已创建并广播 Room，准备进入游戏")
                    return None, None

            if event.type == g.VIDEORESIZE:
                # 只有尺寸真变了才 relayout，避免无谓刷新
                new_w, new_h = event.w, event.h
                if (new_w, new_h) != (self._w, self._h):
                    self._w, self._h = new_w, new_h
                    self._relayout()

        return None

    def draw(self):
        self.screen.fill((245, 245, 245))
        dt = self.clock.tick(60) / 1000.0

        # 统一跑回调（或在 main 里跑也可以，二选一）
        steam.run_callbacks()

        self.manager.update(dt)
        self.manager.draw_ui(self.screen)
        g.display.flip()

    def run(self):
        try:
            while self.running:
                steam.run_callbacks()

                # ===== 修改：统一检查是否收到 Room 对象 =====
                if self._received_room:
                    dbg("[Lobby] 检测到 Room 对象，启动游戏")
                    room = self._received_room
                    self._received_room = None  # 清空以避免重复进入
                    return "STATE_GAME", room

                # 旧方式兼容（通过 Lobby 数据）
                if self._start_payload:
                    minBet, initBet, ts = self._start_payload
                    # 如果还没有 Room 对象，用旧方式创建
                    if not hasattr(self, '_received_room') or not self._received_room:
                        players = self._collect_players()
                        room = Room([players, minBet, initBet])
                        return "STATE_GAME", room

                ret = self.handle_events()
                if ret:
                    next_state, data = ret
                    if next_state:
                        return next_state, data
                self.draw()
        finally:
            pass
        return "STATE_QUIT", None
