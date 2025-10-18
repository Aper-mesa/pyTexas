import time

import imgui
import pygame as g

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
    steam.set_rich_presence("status", "在菜单中")
    steam.set_rich_presence("steam_player_group", "")
    steam.set_rich_presence("steam_player_group_size", "")
    steam.set_rich_presence("steam_display", "")


class Lobby:
    def __init__(self, screen, impl, current_player: player.Player, max_members: int = 9, auto_join_id: int = None):
        print("Lobby init")
        self._received_room = None

        self.screen = screen
        self.clock = g.time.Clock()
        self.impl = impl
        self.running = True

        self.current_player = current_player
        self.max_members = max_members

        self.my_steamid = steam.get_my_steam_id()
        self.my_name = steam.get_my_persona_name()
        dbg(f"self.my_steamid={self.my_steamid}, self.my_name={self.my_name}")

        self.lobby_id = 0
        self.member_names = []
        self._friend_ids = []
        self._start_payload = None
        self._start_seen_ts = 0

        self._callbacks = []
        self._install_callbacks()

        self.status_message = f"你好 {self.my_name} ({self.my_steamid})"
        self.member_list_display = []

        self.is_host = False
        self.minBet_str = "1"
        self.initBet_str = "50"

        self.create_btn_enabled = True
        self.invite_btn_enabled = False
        self.leave_btn_enabled = False
        self.host_controls_visible = False

        self._load_friends_list()

        # --- 关键修改：检查是否有 auto_join_id，如果有则自动加入 ---
        if auto_join_id:
            dbg(f"Auto-joining lobby {auto_join_id} from main process...")
            steam.join_lobby(auto_join_id)
            self._set_status(f"收到邀请，正在加入 Lobby {auto_join_id} ...")
        else:
            # 原有的启动参数检查逻辑，只在没有自动加入时执行
            try:
                val = steam.get_launch_query_param("connect")
                if val:
                    s = val.decode('utf-8', 'ignore').strip()
                    dbg(f"launch connect param='{s}'")
                    for prefix in ("lobby:", "connect=", "steam://joinlobby/"):
                        if s.startswith(prefix): s = s[len(prefix):]
                    lobby_id = int(s)
                    steam.join_lobby(lobby_id)
                    self._set_status(f"启动参数 Join -> 加入 Lobby {lobby_id} ...")
                    dbg(f"JoinLobby via launch param: {lobby_id}")
            except Exception as e:
                dbg(f"parse launch connect failed: {e}")

        dbg(f"overlay enabled? {bool(steam.is_overlay_enabled())}")
        _after_leave_lobby()
        self._set_status(f"你好 {self.my_name} ({self.my_steamid})")
        dbg("Initial Rich Presence cleared on lobby entry.")

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

    # ---------- Steam Callbacks ----------
    def _install_callbacks(self):
        def on_lobby_created(data):
            dbg(f"on_lobby_created: result={data['m_eResult']}, lobby={data['m_ulSteamIDLobby']}")
            if data['m_eResult'] == 1:  # k_EResultOK
                self.lobby_id = data['m_ulSteamIDLobby']
                self._set_status(f"已创建Lobby：{self.lobby_id}")

                # --- 房主专属逻辑 ---
                self.is_host = True
                self.host_controls_visible = True

                # --- 调用公共设置函数 ---
                _on_joined_lobby_common(self)

            else:
                self._set_status(f"创建失败，EResult={data['m_eResult']}")

        def _on_joined_lobby_common(self):
            """无论是创建还是加入Lobby成功后，都应执行的通用逻辑"""
            self.leave_btn_enabled = True
            self.create_btn_enabled = False
            self.invite_btn_enabled = True

            self._push_my_member_data()
            self._refresh_members_list()
            self._refresh_member_names()
            self._after_enter_lobby()

            if self.is_host:
                ok_joinable = steam.set_lobby_joinable(self.lobby_id, True)
                dbg(f"SetLobbyJoinable(true) -> {ok_joinable}")

                steam.set_lobby_data(self.lobby_id, "name", self.my_name)
                steam.set_lobby_data(self.lobby_id, "ver", "1")
                steam.set_lobby_data(self.lobby_id, "mode", "poker")
                dbg("Lobby metadata set by host.")

        def on_lobby_enter(data):
            self.lobby_id = data['m_ulSteamIDLobby']
            dbg(f"on_lobby_enter: lobby={data['m_ulSteamIDLobby']}, locked={data['m_bLocked']}, enter_resp={data['m_EChatRoomEnterResponse']}")
            self._set_status(f"已进入Lobby：{self.lobby_id}")

            # --- 客户端专属逻辑 ---
            if not getattr(self, "is_host", False):
                self.is_host = False
                self.host_controls_visible = False

            # --- 调用公共设置函数 ---
            _on_joined_lobby_common(self)

        def on_lobby_chat_update(data):
            if data['m_ulSteamIDLobby'] == self.lobby_id:
                self._refresh_member_names()
            dbg(f"on_lobby_chat_update: lobby={data['m_ulSteamIDLobby']}, user_changed={data['m_ulSteamIDUserChanged']}, state_change={data['m_rgfChatMemberStateChange']}")

        def on_lobby_data_update(data):
            self._refresh_member_names()
            self._refresh_members_list()

            if data['m_ulSteamIDLobby'] != self.lobby_id:
                return

            if data['m_ulSteamIDMember'] not in (0, self.lobby_id):
                return

            raw = steam.get_lobby_data(self.lobby_id, "start")
            s = (raw or b"").strip()

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
            invited_lobby_id = data['m_ulSteamIDLobby']
            dbg(f"on_lobby_invite: from={data['m_ulSteamIDUser']}, lobby={invited_lobby_id}, gameid={data['m_ulGameID']}")

            # 检查是否已经在同一个lobby中
            if self.lobby_id and self.lobby_id == invited_lobby_id:
                dbg(f"已经在Lobby {invited_lobby_id} 中，忽略重复邀请")
                self._set_status(f"你已经在这个大厅中了")
                return

            self._set_status(f"收到邀请，正在加入Lobby {invited_lobby_id} ...")

        def on_game_lobby_join_requested(data):
            requested_lobby_id = data['m_steamIDLobby']
            dbg(f"on_game_lobby_join_requested: friend={data['m_steamIDFriend']}, lobby={requested_lobby_id}")

            # 检查是否已经在同一个lobby中
            if self.lobby_id and self.lobby_id == requested_lobby_id:
                dbg(f"已经在Lobby {requested_lobby_id} 中，忽略重复加入请求")
                self._set_status(f"你已经在这个大厅中了")
                return

            steam.join_lobby(requested_lobby_id)
            self._set_status(f"好友请求加入，进入Lobby {requested_lobby_id} ...")

        def on_game_rich_presence_join_requested(data):
            connect = bytes(data['m_rgchConnect']).split(b'\x00', 1)[0].decode('utf-8', 'ignore')
            dbg(f"on_game_rich_presence_join_requested: friend={data['m_steamIDFriend']}, connect='{connect}'")
            s = connect.strip()
            for prefix in ("lobby:", "connect=", "steam://joinlobby/"):
                if s.startswith(prefix):
                    s = s[len(prefix):]
            try:
                requested_lobby_id = int(s)

                # 检查是否已经在同一个lobby中
                if self.lobby_id and self.lobby_id == requested_lobby_id:
                    dbg(f"已经在Lobby {requested_lobby_id} 中，忽略RichPresence重复加入")
                    self._set_status(f"你已经在这个大厅中了")
                    return

                steam.join_lobby(requested_lobby_id)
                self._set_status(f"RichPresence Join -> 加入 Lobby {requested_lobby_id} ...")
                dbg(f"JoinLobby via RP connect: {requested_lobby_id}")
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
        payload = f"{username},{steam_id},{money}"
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

            s = raw.decode("utf-8", "ignore") if raw else ""
            if not len(s.split(",", 3)) == 3: continue
            name, steam_id, money = s.split(",", 3)
            p = player.Player(steam_id, name, money)
            p.money = int(money)

            res.append(p)
        return res

    def _refresh_members_list(self):
        players = self._collect_players()
        items = [f"{p.username} | {p.steam_id} | ¥{p.money}" for p in players]
        # 修改：更新 UI 状态变量
        self.member_list_display = items

    def _set_status(self, msg: str):
        self.status_message = msg

    def _after_enter_lobby(self):
        steam.set_rich_presence("connect", str(self.lobby_id))
        steam.set_rich_presence("status", "In Lobby")
        steam.set_rich_presence("steam_player_group", str(self.lobby_id))
        steam.set_rich_presence("steam_player_group_size", str(steam.get_num_lobby_members(self.lobby_id)))
        steam.set_rich_presence("steam_display", "#Status_Hosting")

    def _load_friends_list(self):
        k_EFriendFlagImmediate = 4
        cnt = steam.get_friend_count(k_EFriendFlagImmediate)
        items, ids = [], []
        for i in range(max(0, cnt)):
            fid = steam.get_friend_by_index(i, k_EFriendFlagImmediate)
            name = steam.get_friend_persona_name(fid)
            display = name or b"Unknown"
            items.append(display)
            ids.append(fid)
        self._friend_ids = ids

    def _refresh_member_names(self):
        if not self.lobby_id:
            self.member_list_display = []
            return
        count = steam.get_num_lobby_members(self.lobby_id)
        names = []
        for i in range(int(count)):
            sid = steam.get_lobby_member_by_index(self.lobby_id, i)
            pname = steam.get_friend_persona_name(sid)
            display = (pname or b"")
            if not display:
                p = steam.get_lobby_member_data(self.lobby_id, sid, "player_name")
                display = (p or b"Unknown").decode("utf-8", "ignore")
            names.append(display)
        self.member_names = names
        self.member_list_display = names
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
            # 修改：更新 UI 状态变量
            self.invite_btn_enabled = False
            self.is_host = False
            self.create_btn_enabled = True
            self.leave_btn_enabled = False
            self.host_controls_visible = False

            _after_leave_lobby()
            self._set_status("已离开Lobby")
            self.lobby_id = 0
            # 修改：更新 UI 状态变量
            self.member_list_display = []

    def draw_ui(self):
        """使用 ImGui 绘制大厅界面"""
        w, h = self.screen.get_size()

        # 使用一个全屏、固定的窗口作为背景
        imgui.set_next_window_position(0, 0)
        imgui.set_next_window_size(w, h)
        imgui.begin(
            "LobbyWindow",
            flags=imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_COLLAPSE
        )

        # 1. 标题
        # (可以根据需要调整字体大小)
        imgui.text("Lobby")
        imgui.separator()

        # 2. 顶部按钮
        # 按钮宽度 (大致模仿 _relayout)
        btn_w = int(w * 0.14)

        # 根据 UI 状态变量设置按钮是否禁用
        if self.create_btn_enabled and imgui.button("create lobby", width=btn_w):
            self.create_public_lobby()

        imgui.same_line()
        if self.invite_btn_enabled and imgui.button("invite friends", width=btn_w):
            self.invite_friends_via_overlay()

        imgui.same_line()
        if self.leave_btn_enabled and imgui.button("leave lobby", width=btn_w):
            self.leave_lobby()

        imgui.spacing()

        # 3. 成员列表
        # (大致模仿 _relayout 尺寸)
        list_w = int(w * 0.62)
        list_h = int(h * 0.60)
        imgui.begin_child("member_list_frame", width=list_w, height=list_h, border=True)
        if not self.member_list_display:
            imgui.text("Lobby 为空")
        else:
            for item_str in self.member_list_display:
                imgui.text(item_str)
        imgui.end_child()

        # 4. 状态标签
        imgui.text(self.status_message)

        # 5. 房主控制 (仅在 self.host_controls_visible 为 True 时绘制)
        if self.host_controls_visible:
            # (大致模仿 _relayout 布局)
            bottom_y = h - 60  # ImGui 坐标系可能略有不同，调整y值
            group_w = 480
            group_x = (w - group_w) // 2

            imgui.set_cursor_pos((group_x, bottom_y))

            imgui.push_item_width(120)
            # ImGui InputText 返回 (changed, value) 元组
            # 使用 INPUT_TEXT_CHARS_DECIMAL 标志只允许输入数字
            changed, self.minBet_str = imgui.input_text(
                "minBet", self.minBet_str, 6, flags=imgui.INPUT_TEXT_CHARS_DECIMAL
            )
            imgui.pop_item_width()

            imgui.same_line(spacing=20)
            imgui.push_item_width(120)
            changed, self.initBet_str = imgui.input_text(
                "initBet", self.initBet_str, 6, flags=imgui.INPUT_TEXT_CHARS_DECIMAL
            )
            imgui.pop_item_width()

            imgui.same_line(spacing=20)
            if imgui.button("Start Game", width=200):
                # --- 这是原 handle_events 中的开始游戏逻辑 ---
                try:
                    minBet_int = int(self.minBet_str.strip() or "1")
                    initBet_int = int(self.initBet_str.strip() or "50")
                except ValueError:
                    self._set_status("错误: minBet 和 initBet 必须是数字")
                else:
                    players_list = self._collect_players()
                    room = Room([players_list, minBet_int, initBet_int])

                    ts = int(time.time())
                    payload = f"{minBet_int},{initBet_int},{ts}"
                    steam.set_lobby_data(self.lobby_id, "start", payload)
                    steam.set_lobby_joinable(self.lobby_id, False)

                    # 设置此项，run() 循环将在下一帧检测到并切换状态
                    self._received_room = room
                    self._start_payload = (minBet_int, initBet_int, ts)

                    dbg("[Lobby] 房主已创建并广播 Room，准备进入游戏")

        imgui.end()  # 结束 "LobbyWindow"

    def run(self):
        while self.running:
            steam.run_callbacks()
            for event in g.event.get():
                if event.type == g.QUIT:
                    self.running = False
                    return "STATE_QUIT", None
                self.impl.process_event(event)

            # --- ImGui 新一帧 ---
            self.impl.process_inputs()
            imgui.new_frame()

            # --- 绘制 UI ---
            self.draw_ui()

            # --- 渲染 ---
            # 1. 清屏
            self.screen.fill((0, 0, 0))
            # 2. 渲染 ImGui
            imgui.render()
            self.impl.render(imgui.get_draw_data())
            # 3. 更新 Pygame 显示
            g.display.flip()

            # --- 状态切换检查 (来自原始 run() 方法) ---
            if self._received_room:
                dbg("[Lobby] 检测到 Room 对象，启动游戏")
                room = self._received_room
                self._received_room = None  # 清空以避免重复进入
                return "STATE_GAME", room

            if self._start_payload:
                minBet, initBet, ts = self._start_payload
                # 如果还没有 Room 对象（例如房主自己），用旧方式创建
                if not self._received_room:
                    players = self._collect_players()
                    room = Room([players, minBet, initBet])
                    self._start_payload = None  # 清空以避免重复进入
                    return "STATE_GAME", room

            # --- 帧率控制 ---
            self.clock.tick(60)
        return None
