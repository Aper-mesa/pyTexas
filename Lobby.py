# -*- coding: utf-8 -*-
import ctypes
import time
from ctypes import c_bool, c_void_p, c_char_p, c_int32, c_uint64, c_uint32, c_uint8, c_uint16
import pygame as g
import pygame_gui as gui

import net
import player
import steam_bootstrap as steam
from round import Room

def dbg(msg: str):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")


# ======== ctypes 结构体（与 DLL 无关，可在导入期定义）========
class FriendGameInfo_t(ctypes.Structure):
    _fields_ = [
        ("m_gameID", c_uint64),
        ("m_unGameIP", c_uint32),
        ("m_usGamePort", c_uint16),
        ("m_usQueryPort", c_uint16),
        ("m_steamIDLobby", c_uint64),
    ]


class LobbyCreated_t(ctypes.Structure):
    _fields_ = [("m_eResult", c_int32), ("m_ulSteamIDLobby", c_uint64)]


class LobbyEnter_t(ctypes.Structure):
    _fields_ = [
        ("m_ulSteamIDLobby", c_uint64),
        ("m_rgfChatPermissions", c_uint32),
        ("m_bLocked", c_uint8),
        ("m_EChatRoomEnterResponse", c_uint32),
    ]


class LobbyChatUpdate_t(ctypes.Structure):
    _fields_ = [
        ("m_ulSteamIDLobby", c_uint64),
        ("m_ulSteamIDUserChanged", c_uint64),
        ("m_ulSteamIDMakingChange", c_uint64),
        ("m_rgfChatMemberStateChange", c_uint32),
    ]


class LobbyDataUpdate_t(ctypes.Structure):
    _fields_ = [
        ("m_ulSteamIDLobby", c_uint64),
        ("m_ulSteamIDMember", c_uint64),
        ("m_bSuccess", c_uint8),
    ]


class LobbyInvite_t(ctypes.Structure):
    _fields_ = [("m_ulSteamIDUser", c_uint64), ("m_ulSteamIDLobby", c_uint64), ("m_ulGameID", c_uint64)]


class GameLobbyJoinRequested_t(ctypes.Structure):
    _fields_ = [("m_steamIDLobby", c_uint64), ("m_steamIDFriend", c_uint64)]


class GameRichPresenceJoinRequested_t(ctypes.Structure):
    _fields_ = [("m_steamIDFriend", c_uint64), ("m_rgchConnect", ctypes.c_char * 256)]


class GameOverlayActivated_t(ctypes.Structure):
    _fields_ = [("m_bActive", c_uint32)]  # 1=打开, 0=关闭


# ======== 全局常量 ========
ELobbyType_Private, ELobbyType_FriendsOnly, ELobbyType_Public, ELobbyType_Invisible = 0, 1, 2, 3
CBID_LobbyCreated = 513
CBID_LobbyEnter = 504
CBID_LobbyChatUpdate = 506
CBID_LobbyDataUpdate = 505
CBID_LobbyInvite = 503
CBID_GameLobbyJoinRequested = 333
CBID_GameRichPresenceJoinRequested = 337
CBID_GameOverlayActivated = 331


# ======== 回调基础类型 ========
class _CallbackBase(ctypes.Structure):
    _fields_ = [("vtable", c_void_p), ("m_iCallback", c_int32)]


CALLBACK_RUN = ctypes.CFUNCTYPE(None, c_void_p, c_void_p)
CALLBACK_RUNARGS = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, c_bool, c_uint64)
CALLBACK_GETSIZE = ctypes.CFUNCTYPE(ctypes.c_int)


class _CallbackVTable(ctypes.Structure):
    _fields_ = [("Run", CALLBACK_RUN), ("RunArgs", CALLBACK_RUNARGS), ("GetCallbackSizeBytes", CALLBACK_GETSIZE)]


# ======== 延迟绑定的 Steam 函数指针（模块导入阶段不取 DLL）========
# （全部在 _bind_steam_functions() 里赋值）
ISteamUser_GetSteamID = None
ISteamFriends_GetPersonaName = None
ISteamFriends_GetFriendCount = None
ISteamFriends_GetFriendByIndex = None
ISteamFriends_GetFriendPersonaName = None
ISteamFriends_ActivateGameOverlayInviteDialog = None
ISteamFriends_SetRichPresence = None
ISteamFriends_ClearRichPresence = None
ISteamFriends_GetFriendGamePlayed = None
ISteamUtils_IsOverlayEnabled = None
ISteamApps_GetLaunchQueryParam = None
ISteamMatchmaking_CreateLobby = None
ISteamMatchmaking_JoinLobby = None
ISteamMatchmaking_LeaveLobby = None
ISteamMatchmaking_GetNumLobbyMembers = None
ISteamMatchmaking_GetLobbyMemberByIndex = None
ISteamMatchmaking_GetLobbyMemberData = None
ISteamMatchmaking_SetLobbyJoinable = None
ISteamMatchmaking_GetLobbyData = None
ISteamMatchmaking_SetLobbyData = None
ISteamMatchmaking_SetLobbyMemberData = None
SteamAPI_RegisterCallback = None
SteamAPI_UnregisterCallback = None


def _bind_steam_functions():
    global ISteamUser_GetSteamID, ISteamFriends_GetPersonaName, ISteamFriends_GetFriendCount
    global ISteamFriends_GetFriendByIndex, ISteamFriends_GetFriendPersonaName
    global ISteamFriends_ActivateGameOverlayInviteDialog, ISteamFriends_SetRichPresence, ISteamFriends_ClearRichPresence
    global ISteamFriends_GetFriendGamePlayed, ISteamUtils_IsOverlayEnabled, ISteamApps_GetLaunchQueryParam
    global ISteamMatchmaking_CreateLobby, ISteamMatchmaking_JoinLobby, ISteamMatchmaking_LeaveLobby
    global ISteamMatchmaking_GetNumLobbyMembers, ISteamMatchmaking_GetLobbyMemberByIndex
    global ISteamMatchmaking_GetLobbyMemberData, ISteamMatchmaking_SetLobbyJoinable
    global ISteamMatchmaking_SetLobbyData, ISteamMatchmaking_SetLobbyMemberData, ISteamMatchmaking_GetLobbyData
    global SteamAPI_RegisterCallback, SteamAPI_UnregisterCallback

    DLL = steam.DLL
    if DLL is None:
        raise RuntimeError("Steam 未初始化。请确保在 main.py 中已调用 steam.init()。")

    # ISteamUser
    fn = DLL.SteamAPI_ISteamUser_GetSteamID
    fn.restype = c_uint64
    fn.argtypes = [c_void_p]
    ISteamUser_GetSteamID = fn

    # ISteamFriends
    fn = DLL.SteamAPI_ISteamFriends_GetPersonaName
    fn.restype = c_char_p
    fn.argtypes = [c_void_p]
    ISteamFriends_GetPersonaName = fn

    fn = DLL.SteamAPI_ISteamFriends_GetFriendCount
    fn.restype = c_int32
    fn.argtypes = [c_void_p, c_int32]
    ISteamFriends_GetFriendCount = fn

    fn = DLL.SteamAPI_ISteamFriends_GetFriendByIndex
    fn.restype = c_uint64
    fn.argtypes = [c_void_p, c_int32, c_int32]
    ISteamFriends_GetFriendByIndex = fn

    fn = DLL.SteamAPI_ISteamFriends_GetFriendPersonaName
    fn.restype = c_char_p
    fn.argtypes = [c_void_p, c_uint64]
    ISteamFriends_GetFriendPersonaName = fn

    fn = DLL.SteamAPI_ISteamFriends_ActivateGameOverlayInviteDialog
    fn.restype = None
    fn.argtypes = [c_void_p, c_uint64]
    ISteamFriends_ActivateGameOverlayInviteDialog = fn

    fn = DLL.SteamAPI_ISteamFriends_SetRichPresence
    fn.restype = c_bool
    fn.argtypes = [c_void_p, c_char_p, c_char_p]
    ISteamFriends_SetRichPresence = fn

    fn = DLL.SteamAPI_ISteamFriends_ClearRichPresence
    fn.restype = None
    fn.argtypes = [c_void_p]
    ISteamFriends_ClearRichPresence = fn

    fn = DLL.SteamAPI_ISteamFriends_GetFriendGamePlayed
    fn.restype = c_bool
    fn.argtypes = [c_void_p, c_uint64, ctypes.POINTER(FriendGameInfo_t)]
    ISteamFriends_GetFriendGamePlayed = fn

    # ISteamUtils
    fn = DLL.SteamAPI_ISteamClient_GetISteamUtils
    fn.restype = c_void_p
    fn.argtypes = [c_void_p, c_int32, c_char_p]
    GetISteamUtils = fn  # 仅用于获取 utils 句柄（已在 bootstrap 做过）

    fn = DLL.SteamAPI_ISteamUtils_IsOverlayEnabled
    fn.restype = c_bool
    fn.argtypes = [c_void_p]
    ISteamUtils_IsOverlayEnabled = fn

    # ISteamApps
    fn = DLL.SteamAPI_ISteamApps_GetLaunchQueryParam
    fn.restype = c_char_p
    fn.argtypes = [c_void_p, c_char_p]
    ISteamApps_GetLaunchQueryParam = fn

    # ISteamMatchmaking
    fn = DLL.SteamAPI_ISteamMatchmaking_CreateLobby
    fn.restype = c_uint64
    fn.argtypes = [c_void_p, c_int32, c_int32]
    ISteamMatchmaking_CreateLobby = fn

    fn = DLL.SteamAPI_ISteamMatchmaking_JoinLobby
    fn.restype = c_uint64
    fn.argtypes = [c_void_p, c_uint64]
    ISteamMatchmaking_JoinLobby = fn

    fn = DLL.SteamAPI_ISteamMatchmaking_LeaveLobby
    fn.restype = None
    fn.argtypes = [c_void_p, c_uint64]
    ISteamMatchmaking_LeaveLobby = fn

    fn = DLL.SteamAPI_ISteamMatchmaking_GetNumLobbyMembers
    fn.restype = c_int32
    fn.argtypes = [c_void_p, c_uint64]
    ISteamMatchmaking_GetNumLobbyMembers = fn

    fn = DLL.SteamAPI_ISteamMatchmaking_GetLobbyMemberByIndex
    fn.restype = c_uint64
    fn.argtypes = [c_void_p, c_uint64, c_int32]
    ISteamMatchmaking_GetLobbyMemberByIndex = fn

    fn = DLL.SteamAPI_ISteamMatchmaking_GetLobbyMemberData
    fn.restype = c_char_p
    fn.argtypes = [c_void_p, c_uint64, c_uint64, c_char_p]
    ISteamMatchmaking_GetLobbyMemberData = fn

    fn = DLL.SteamAPI_ISteamMatchmaking_SetLobbyJoinable
    fn.restype = c_bool
    fn.argtypes = [c_void_p, c_uint64, c_bool]
    ISteamMatchmaking_SetLobbyJoinable = fn

    # 绑定 —— 读取 Lobby 的某个 key
    fn = DLL.SteamAPI_ISteamMatchmaking_GetLobbyData
    fn.restype = c_char_p
    fn.argtypes = [c_void_p, c_uint64, c_char_p]
    ISteamMatchmaking_GetLobbyData = fn

    fn = DLL.SteamAPI_ISteamMatchmaking_SetLobbyData
    fn.restype = c_bool
    fn.argtypes = [c_void_p, c_uint64, c_char_p, c_char_p]
    ISteamMatchmaking_SetLobbyData = fn

    fn = DLL.SteamAPI_ISteamMatchmaking_SetLobbyMemberData
    fn.restype = None
    fn.argtypes = [c_void_p, c_uint64, c_char_p, c_char_p]
    ISteamMatchmaking_SetLobbyMemberData = fn

    # Callbacks
    fn = DLL.SteamAPI_RegisterCallback
    fn.restype = None
    fn.argtypes = [c_void_p, c_int32]
    SteamAPI_RegisterCallback = fn

    fn = DLL.SteamAPI_UnregisterCallback
    fn.restype = None
    fn.argtypes = [c_void_p]
    SteamAPI_UnregisterCallback = fn


# ================= GUI Lobby State =================
class Lobby:
    def __init__(self, screen, manager, current_player: player.Player, max_members: int = 9):
        # 绑定函数（确保 steam.init() 已先在 main 里调用）
        _bind_steam_functions()

        # ===== 新增：初始化网络消息收发器 =====
        try:
            self.messenger = net.create_messenger(steam)
            dbg("[Lobby] Steam 网络消息系统初始化成功")

            # 注册 Room 数据接收处理器（非房主用）
            self.messenger.register_handler(
                net.SteamNetworkMessenger.CHANNEL_ROOM_DATA,
                self._on_room_received
            )
        except Exception as e:
            dbg(f"[Lobby] 网络消息系统初始化失败: {e}")
            self.messenger = None

        # 用于存储接收到的 Room 对象
        self._received_room = None

        # Steam 句柄
        self.user, self.friends, self.mm, self.apps, self.utils = steam.get_handles()

        self.screen = screen
        self.clock = g.time.Clock()
        self.manager = manager
        self.running = True

        self.current_player = current_player
        self.max_members = max_members

        # 自己的信息
        self.my_steamid = ISteamUser_GetSteamID(self.user)
        self.my_name = (ISteamFriends_GetPersonaName(self.friends) or b"Unknown").decode("utf-8", "ignore")
        dbg(f"self.my_steamid={self.my_steamid}, self.my_name={self.my_name}")

        # Lobby runtime
        self.lobby_id = 0
        self.member_names = []
        self._friend_ids = []

        self._start_payload = None  # 保存开局参数（min/init 等）
        self._start_seen_ts = 0  # 避免重复触发

        # ---------- UI ----------
        w, h = self.screen.get_size()
        self._w, self._h = w, h  # 记录，供是否需要 relayout 判断

        # 统一做一个布局函数
        def _rel(v):  # 便捷百分比 -> 像素
            return int(v)

        def _pctx(p):
            return int(self.screen.get_size()[0] * p)

        def _pcty(p):
            return int(self.screen.get_size()[1] * p)

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
        self._install_callbacks()
        self._load_friends_list()

        # 冷启动 join：通过 Steam 启动并带 connect 时
        try:
            val = ISteamApps_GetLaunchQueryParam(self.apps, b"connect")
            if val:
                s = val.decode('utf-8', 'ignore').strip()
                dbg(f"launch connect param='{s}'")
                for prefix in ("lobby:", "connect=", "steam://joinlobby/"):
                    if s.startswith(prefix):
                        s = s[len(prefix):]
                lid = int(s)
                ISteamMatchmaking_JoinLobby(self.mm, c_uint64(lid))
                self._set_status(f"启动参数 Join -> 加入 Lobby {lid} ...")
                dbg(f"JoinLobby via launch param: {lid}")
        except Exception as e:
            dbg(f"parse launch connect failed: {e}")
        dbg(f"overlay enabled? {bool(ISteamUtils_IsOverlayEnabled(self.utils))}")

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
        def _mk_vtable(cb_struct_cls, handler, cb_id):
            def _run(this, pvParam):
                data = cb_struct_cls.from_address(pvParam)
                handler(data)

            def _runargs(this, pvParam, bIOFailure, hSteamAPICall):
                data = cb_struct_cls.from_address(pvParam)
                handler(data)

            def _getsize():
                return ctypes.sizeof(cb_struct_cls)

            vtbl = _CallbackVTable(CALLBACK_RUN(_run), CALLBACK_RUNARGS(_runargs), CALLBACK_GETSIZE(_getsize))
            base = _CallbackBase()
            base.vtable = ctypes.addressof(vtbl)
            base.m_iCallback = cb_id
            return vtbl, base

        def on_lobby_created(ev: LobbyCreated_t):
            dbg(f"on_lobby_created: result={ev.m_eResult}, lobby={ev.m_ulSteamIDLobby}")
            if ev.m_eResult == 1:  # k_EResultOK
                self.lobby_id = ev.m_ulSteamIDLobby
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
                self._set_status(f"创建失败，EResult={ev.m_eResult}")

        def on_lobby_enter(ev: LobbyEnter_t):
            self.lobby_id = ev.m_ulSteamIDLobby
            dbg(f"on_lobby_enter: lobby={ev.m_ulSteamIDLobby}, locked={ev.m_bLocked}, enter_resp={ev.m_EChatRoomEnterResponse}")
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

            ok_joinable = ISteamMatchmaking_SetLobbyJoinable(self.mm, self.lobby_id, True)
            dbg(f"SetLobbyJoinable(true) -> {ok_joinable}")

            ISteamMatchmaking_SetLobbyData(self.mm, self.lobby_id, b"name", self.my_name.encode("utf-8"))
            ISteamMatchmaking_SetLobbyData(self.mm, self.lobby_id, b"ver", b"1")
            ISteamMatchmaking_SetLobbyData(self.mm, self.lobby_id, b"mode", b"poker")

            ISteamMatchmaking_SetLobbyMemberData(self.mm, self.lobby_id, b"player_name", self.my_name.encode("utf-8"))
            dbg("Lobby data & member data set")

        def on_lobby_chat_update(ev: LobbyChatUpdate_t):
            if ev.m_ulSteamIDLobby == self.lobby_id:
                self._refresh_member_names()
            dbg(f"on_lobby_chat_update: lobby={ev.m_ulSteamIDLobby}, user_changed={ev.m_ulSteamIDUserChanged}, state_change={ev.m_rgfChatMemberStateChange}")

        def on_lobby_data_update(ev: LobbyDataUpdate_t):
            self._refresh_member_names()
            self._refresh_members_list()

            # 只处理当前 lobby
            if ev.m_ulSteamIDLobby != self.lobby_id:
                return

            # 只有 Lobby 级变化才考虑 start（成员级更新直接忽略）
            if ev.m_ulSteamIDMember not in (0, self.lobby_id):
                return

            raw = ISteamMatchmaking_GetLobbyData(self.mm, c_uint64(self.lobby_id), b"start")
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

        def on_lobby_invite(ev: LobbyInvite_t):
            dbg(f"on_lobby_invite: from={ev.m_ulSteamIDUser}, lobby={ev.m_ulSteamIDLobby}, gameid={ev.m_ulGameID}")
            ISteamMatchmaking_JoinLobby(self.mm, c_uint64(ev.m_ulSteamIDLobby))
            self._set_status(f"收到邀请，正在加入Lobby {ev.m_ulSteamIDLobby} ...")

        def on_game_lobby_join_requested(ev: GameLobbyJoinRequested_t):
            dbg(f"on_game_lobby_join_requested: friend={ev.m_steamIDFriend}, lobby={ev.m_steamIDLobby}")
            ISteamMatchmaking_JoinLobby(self.mm, c_uint64(ev.m_steamIDLobby))
            self._set_status(f"好友请求加入，进入Lobby {ev.m_steamIDLobby} ...")

        def on_game_rich_presence_join_requested(ev: GameRichPresenceJoinRequested_t):
            connect = bytes(ev.m_rgchConnect).split(b'\x00', 1)[0].decode('utf-8', 'ignore')
            dbg(f"on_game_rich_presence_join_requested: friend={ev.m_steamIDFriend}, connect='{connect}'")
            s = connect.strip()
            for prefix in ("lobby:", "connect=", "steam://joinlobby/"):
                if s.startswith(prefix):
                    s = s[len(prefix):]
            try:
                lid = int(s)
                ISteamMatchmaking_JoinLobby(self.mm, c_uint64(lid))
                self._set_status(f"RichPresence Join -> 加入 Lobby {lid} ...")
                dbg(f"JoinLobby via RP connect: {lid}")
            except ValueError:
                dbg(f"RichPresence connect 无法解析为数字 lobby id: '{connect}'")
                self._set_status("收到 Join 请求但 connect 无效")

        self._cb_keep = []
        for cls_, func, cbid in [
            (LobbyCreated_t, on_lobby_created, CBID_LobbyCreated),
            (LobbyEnter_t, on_lobby_enter, CBID_LobbyEnter),
            (LobbyChatUpdate_t, on_lobby_chat_update, CBID_LobbyChatUpdate),
            (LobbyDataUpdate_t, on_lobby_data_update, CBID_LobbyDataUpdate),
            (LobbyInvite_t, on_lobby_invite, CBID_LobbyInvite),
            (GameLobbyJoinRequested_t, on_game_lobby_join_requested, CBID_GameLobbyJoinRequested),
            (GameRichPresenceJoinRequested_t, on_game_rich_presence_join_requested, CBID_GameRichPresenceJoinRequested),
        ]:
            vtbl, base = self._mk_vtable(cls_, func, cbid)
            self._cb_keep.append((vtbl, base))
            SteamAPI_RegisterCallback(ctypes.byref(base), cbid)

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
        ISteamMatchmaking_SetLobbyMemberData(self.mm, c_uint64(self.lobby_id), b"player", payload)

    def _collect_players(self):
        """读取 Lobby 全体成员为 Player 实例列表（用 Player.create / 或直接 new Player）"""
        res = []
        if not getattr(self, "lobby_id", None):
            return res

        count = ISteamMatchmaking_GetNumLobbyMembers(self.mm, c_uint64(self.lobby_id))
        for i in range(count):
            sid = ISteamMatchmaking_GetLobbyMemberByIndex(self.mm, c_uint64(self.lobby_id), i)
            raw = ISteamMatchmaking_GetLobbyMemberData(self.mm, c_uint64(self.lobby_id), c_uint64(sid), b"player")

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

    @staticmethod
    def _mk_vtable(cb_struct_cls, handler, cb_id):
        def _run(this, pvParam):
            data = cb_struct_cls.from_address(pvParam)
            handler(data)

        def _runargs(this, pvParam, bIOFailure, hSteamAPICall):
            data = cb_struct_cls.from_address(pvParam)
            handler(data)

        def _getsize():
            return ctypes.sizeof(cb_struct_cls)

        vtbl = _CallbackVTable(CALLBACK_RUN(_run), CALLBACK_RUNARGS(_runargs), CALLBACK_GETSIZE(_getsize))
        base = _CallbackBase()
        base.vtable = ctypes.addressof(vtbl)
        base.m_iCallback = cb_id
        return vtbl, base

    def _uninstall_callbacks(self):
        for vtbl, base in getattr(self, "_cb_keep", []):
            SteamAPI_UnregisterCallback(ctypes.byref(base))
        self._cb_keep = []

    # ---------- Helpers ----------
    def _set_status(self, msg: str):
        self.status_label.set_text(msg)

    def _after_enter_lobby(self):
        # 设置Rich Presence，方便好友看到“Join Game”
        ISteamFriends_SetRichPresence(self.friends, b"connect", str(self.lobby_id).encode("utf-8"))
        ISteamFriends_SetRichPresence(self.friends, b"status", b"In Lobby")
        # ✅ 关键：告诉好友列表“我在这个组里”
        ISteamFriends_SetRichPresence(self.friends, b"steam_player_group", str(self.lobby_id).encode("utf-8"))
        ISteamFriends_SetRichPresence(self.friends, b"steam_player_group_size", str(
            max(1, int(ISteamMatchmaking_GetNumLobbyMembers(self.mm, self.lobby_id)))
        ).encode("utf-8"))
        dbg(f"SetRichPresence connect={self.lobby_id}")

    def _after_leave_lobby(self):
        ISteamFriends_ClearRichPresence(self.friends)
        ISteamFriends_SetRichPresence(self.friends, b"steam_player_group", b"")
        ISteamFriends_SetRichPresence(self.friends, b"steam_player_group_size", b"")

    def _load_friends_list(self):
        k_EFriendFlagImmediate = 0x0001
        cnt = ISteamFriends_GetFriendCount(self.friends, k_EFriendFlagImmediate)
        items, ids = [], []
        for i in range(max(0, cnt)):
            fid = ISteamFriends_GetFriendByIndex(self.friends, i, k_EFriendFlagImmediate)
            name = ISteamFriends_GetFriendPersonaName(self.friends, fid)
            display = (name or b"Unknown").decode("utf-8", "ignore")
            items.append(display)
            ids.append(fid)
        self._friend_ids = ids

    def _refresh_member_names(self):
        if not self.lobby_id:
            self.members_list.set_item_list([])
            return
        count = ISteamMatchmaking_GetNumLobbyMembers(self.mm, self.lobby_id)
        names = []
        for i in range(int(count)):
            sid = ISteamMatchmaking_GetLobbyMemberByIndex(self.mm, self.lobby_id, i)
            pname = ISteamFriends_GetFriendPersonaName(self.friends, sid)
            display = (pname or b"").decode("utf-8", "ignore").strip()
            if not display:
                p = ISteamMatchmaking_GetLobbyMemberData(self.mm, self.lobby_id, sid, b"player_name")
                display = (p or b"Unknown").decode("utf-8", "ignore")
            names.append(display)
        self.member_names = names
        self.members_list.set_item_list(names)
        dbg(f"members[{len(self.member_names)}]: {self.member_names}")
        # 刷新成员列表后，同步人数到 Rich Presence
        if self.lobby_id:
            ISteamFriends_SetRichPresence(
                self.friends, b"steam_player_group_size",
                str(len(self.member_names)).encode("utf-8")
            )

    # ---------- Actions ----------
    def create_public_lobby(self):
        call = ISteamMatchmaking_CreateLobby(self.mm, ELobbyType_Public, self.max_members)
        dbg(f"CreateLobby called -> SteamAPICall_t={call}")
        self._set_status("正在创建公开Lobby...")

    def invite_friends_via_overlay(self):
        if not self.lobby_id:
            self._set_status("请先创建或加入一个Lobby")
            return
        dbg(f"invite overlay open, lobby={self.lobby_id}")
        ISteamFriends_ActivateGameOverlayInviteDialog(self.friends, c_uint64(self.lobby_id))
        self._set_status("已打开Steam邀请弹窗")

    def leave_lobby(self):
        if self.lobby_id:
            ISteamMatchmaking_LeaveLobby(self.mm, self.lobby_id)
            self.invite_btn.disable()
            self.is_host = False
            controls = (self.ui_min_bet, self.ui_init_bet, self.ui_start_btn)
            self.create_btn.enable()
            self.leave_btn.disable()
            for el in controls:
                el.disable()
                el.hide()  # 如果你只想“禁用但不隐藏”，把这一行删掉即可
            self._after_leave_lobby()
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
                        count = ISteamMatchmaking_GetNumLobbyMembers(
                            self.mm, c_uint64(self.lobby_id)
                        )
                        for i in range(count):
                            sid = ISteamMatchmaking_GetLobbyMemberByIndex(
                                self.mm, c_uint64(self.lobby_id), i
                            )
                            if sid != self.my_steamid:  # 不发送给自己
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
                    ISteamMatchmaking_SetLobbyData(
                        self.mm, c_uint64(self.lobby_id), b"start", payload
                    )
                    ISteamMatchmaking_SetLobbyJoinable(
                        self.mm, c_uint64(self.lobby_id), False
                    )

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
            self._uninstall_callbacks()
        return "STATE_QUIT", None

    def prepare_room_for_transfer(room):
        """
        准备 Room 对象用于网络传输
        如果 Room 中有不可序列化的对象，在这里处理

        Args:
            room: Room 对象

        Returns:
            可序列化的 Room 对象
        """
        # 如果 Card 类有 Pygame Surface，移除或转换
        # 示例：
        # for card in room.cards:
        #     if hasattr(card, 'image'):
        #         card.image = None  # 临时移除图像

        return room

    def restore_room_after_transfer(room):
        """
        恢复传输后的 Room 对象
        重新初始化不可序列化的部分

        Args:
            room: 接收到的 Room 对象

        Returns:
            完整的 Room 对象
        """
        # 示例：重新加载卡牌图像
        # for card in room.cards:
        #     card.load_image()  # 重新加载图像

        return room