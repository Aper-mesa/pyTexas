# -*- coding: utf-8 -*-
"""
Lobby.py — Steamworks(Flat C, ctypes) 版本
功能：
  ✓ 创建公开Lobby
  ✓ 覆盖层邀请好友加入
  ✓ 接收好友在Steam里右键“加入游戏”
  ✓ 游戏内好友列表 -> 一键加入好友所在Lobby
  ✓ 显示Lobby成员username列表
  ✗ 删除通过ID加入（无输入框、无按钮）
"""
import ctypes
import time
from ctypes import c_bool, c_void_p, c_char_p, c_int32, c_uint64, c_uint32, c_uint8, c_uint16
from pathlib import Path

import pygame as g
import pygame_gui as gui

import player

def dbg(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

# ================= Steam flat C bindings =================
_DLL = ctypes.WinDLL(str(Path(__file__).resolve().parent / "steam_api64.dll"))

# Core
SteamAPI_Init = getattr(_DLL, "SteamAPI_InitSafe", None) or _DLL.SteamAPI_Init
SteamAPI_Init.restype = c_bool
SteamAPI_Shutdown = _DLL.SteamAPI_Shutdown
SteamAPI_RunCallbacks = _DLL.SteamAPI_RunCallbacks

SteamInternal_CreateInterface = _DLL.SteamInternal_CreateInterface
SteamInternal_CreateInterface.restype = c_void_p
SteamInternal_CreateInterface.argtypes = [c_char_p]

SteamAPI_GetHSteamUser = _DLL.SteamAPI_GetHSteamUser
SteamAPI_GetHSteamUser.restype = c_int32
SteamAPI_GetHSteamPipe = _DLL.SteamAPI_GetHSteamPipe
SteamAPI_GetHSteamPipe.restype = c_int32

# ISteamClient -> sub-interfaces
GetISteamUser = _DLL.SteamAPI_ISteamClient_GetISteamUser
GetISteamUser.restype = c_void_p
GetISteamUser.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

GetISteamFriends = _DLL.SteamAPI_ISteamClient_GetISteamFriends
GetISteamFriends.restype = c_void_p
GetISteamFriends.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

GetISteamMatchmaking = _DLL.SteamAPI_ISteamClient_GetISteamMatchmaking
GetISteamMatchmaking.restype = c_void_p
GetISteamMatchmaking.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

# ISteamUser
ISteamUser_GetSteamID = _DLL.SteamAPI_ISteamUser_GetSteamID
ISteamUser_GetSteamID.restype = c_uint64
ISteamUser_GetSteamID.argtypes = [c_void_p]

# ISteamFriends（常用）
ISteamFriends_GetPersonaName = _DLL.SteamAPI_ISteamFriends_GetPersonaName
ISteamFriends_GetPersonaName.restype = c_char_p
ISteamFriends_GetPersonaName.argtypes = [c_void_p]

ISteamFriends_GetFriendCount = _DLL.SteamAPI_ISteamFriends_GetFriendCount
ISteamFriends_GetFriendCount.restype = c_int32
ISteamFriends_GetFriendCount.argtypes = [c_void_p, c_int32]  # flags

ISteamFriends_GetFriendByIndex = _DLL.SteamAPI_ISteamFriends_GetFriendByIndex
ISteamFriends_GetFriendByIndex.restype = c_uint64
ISteamFriends_GetFriendByIndex.argtypes = [c_void_p, c_int32, c_int32]

ISteamFriends_GetFriendPersonaName = _DLL.SteamAPI_ISteamFriends_GetFriendPersonaName
ISteamFriends_GetFriendPersonaName.restype = c_char_p
ISteamFriends_GetFriendPersonaName.argtypes = [c_void_p, c_uint64]

ISteamFriends_ActivateGameOverlayInviteDialog = _DLL.SteamAPI_ISteamFriends_ActivateGameOverlayInviteDialog
ISteamFriends_ActivateGameOverlayInviteDialog.restype = None
ISteamFriends_ActivateGameOverlayInviteDialog.argtypes = [c_void_p, c_uint64]

ISteamFriends_SetRichPresence = _DLL.SteamAPI_ISteamFriends_SetRichPresence
ISteamFriends_SetRichPresence.restype = c_bool
ISteamFriends_SetRichPresence.argtypes = [c_void_p, c_char_p, c_char_p]

ISteamFriends_ClearRichPresence = _DLL.SteamAPI_ISteamFriends_ClearRichPresence
ISteamFriends_ClearRichPresence.restype = None
ISteamFriends_ClearRichPresence.argtypes = [c_void_p]

# 获取好友的游戏信息（含LobbyID）
class FriendGameInfo_t(ctypes.Structure):
    _fields_ = [("m_gameID", c_uint64), ("m_unGameIP", c_uint32),
                ("m_usGamePort", c_uint16), ("m_usQueryPort", c_uint16),
                ("m_steamIDLobby", c_uint64)]
ISteamFriends_GetFriendGamePlayed = _DLL.SteamAPI_ISteamFriends_GetFriendGamePlayed
ISteamFriends_GetFriendGamePlayed.restype = c_bool
ISteamFriends_GetFriendGamePlayed.argtypes = [c_void_p, c_uint64, ctypes.POINTER(FriendGameInfo_t)]

# ISteamMatchmaking
ELobbyType_Private, ELobbyType_FriendsOnly, ELobbyType_Public, ELobbyType_Invisible = 0, 1, 2, 3

ISteamMatchmaking_SetLobbyJoinable = _DLL.SteamAPI_ISteamMatchmaking_SetLobbyJoinable
ISteamMatchmaking_SetLobbyJoinable.restype = c_bool
ISteamMatchmaking_SetLobbyJoinable.argtypes = [c_void_p, c_uint64, c_bool]

ISteamMatchmaking_SetLobbyData = _DLL.SteamAPI_ISteamMatchmaking_SetLobbyData
ISteamMatchmaking_SetLobbyData.restype = c_bool
ISteamMatchmaking_SetLobbyData.argtypes = [c_void_p, c_uint64, c_char_p, c_char_p]

ISteamMatchmaking_SetLobbyMemberData = _DLL.SteamAPI_ISteamMatchmaking_SetLobbyMemberData
ISteamMatchmaking_SetLobbyMemberData.restype = None
ISteamMatchmaking_SetLobbyMemberData.argtypes = [c_void_p, c_uint64, c_char_p, c_char_p]

ISteamMatchmaking_CreateLobby = _DLL.SteamAPI_ISteamMatchmaking_CreateLobby
ISteamMatchmaking_CreateLobby.restype = c_uint64  # SteamAPICall_t
ISteamMatchmaking_CreateLobby.argtypes = [c_void_p, c_int32, c_int32]

ISteamMatchmaking_JoinLobby = _DLL.SteamAPI_ISteamMatchmaking_JoinLobby
ISteamMatchmaking_JoinLobby.restype = c_uint64  # SteamAPICall_t
ISteamMatchmaking_JoinLobby.argtypes = [c_void_p, c_uint64]

ISteamMatchmaking_LeaveLobby = _DLL.SteamAPI_ISteamMatchmaking_LeaveLobby
ISteamMatchmaking_LeaveLobby.restype = None
ISteamMatchmaking_LeaveLobby.argtypes = [c_void_p, c_uint64]

ISteamMatchmaking_GetNumLobbyMembers = _DLL.SteamAPI_ISteamMatchmaking_GetNumLobbyMembers
ISteamMatchmaking_GetNumLobbyMembers.restype = c_int32
ISteamMatchmaking_GetNumLobbyMembers.argtypes = [c_void_p, c_uint64]

ISteamMatchmaking_GetLobbyMemberByIndex = _DLL.SteamAPI_ISteamMatchmaking_GetLobbyMemberByIndex
ISteamMatchmaking_GetLobbyMemberByIndex.restype = c_uint64
ISteamMatchmaking_GetLobbyMemberByIndex.argtypes = [c_void_p, c_uint64, c_int32]

# 为了非好友成员名，读取 member data "player_name"
ISteamMatchmaking_GetLobbyMemberData = _DLL.SteamAPI_ISteamMatchmaking_GetLobbyMemberData
ISteamMatchmaking_GetLobbyMemberData.restype = c_char_p
ISteamMatchmaking_GetLobbyMemberData.argtypes = [c_void_p, c_uint64, c_uint64, c_char_p]

# callbacks 基础
SteamAPI_RegisterCallback = _DLL.SteamAPI_RegisterCallback
SteamAPI_UnregisterCallback = _DLL.SteamAPI_UnregisterCallback
SteamAPI_RegisterCallback.restype = None
SteamAPI_RegisterCallback.argtypes = [c_void_p, c_int32]
SteamAPI_UnregisterCallback.restype = None
SteamAPI_UnregisterCallback.argtypes = [c_void_p]

class _CallbackBase(ctypes.Structure):
    _fields_ = [("vtable", c_void_p), ("m_iCallback", c_int32)]

CALLBACK_RUN = ctypes.CFUNCTYPE(None, c_void_p, c_void_p)
CALLBACK_RUNARGS = ctypes.CFUNCTYPE(None, c_void_p, c_void_p, c_bool, c_uint64)
CALLBACK_GETSIZE = ctypes.CFUNCTYPE(ctypes.c_int)

class _CallbackVTable(ctypes.Structure):
    _fields_ = [("Run", CALLBACK_RUN), ("RunArgs", CALLBACK_RUNARGS), ("GetCallbackSizeBytes", CALLBACK_GETSIZE)]

# 回调ID（见 steam_api.json）
CBID_LobbyCreated            = 513
CBID_LobbyEnter              = 504
CBID_LobbyChatUpdate         = 506
CBID_LobbyDataUpdate         = 505
CBID_LobbyInvite             = 503  # 收到别人邀请你
CBID_GameLobbyJoinRequested  = 333  # 别人在好友界面“加入你”

# 回调结构
class LobbyCreated_t(ctypes.Structure):
    _fields_ = [("m_eResult", c_int32), ("m_ulSteamIDLobby", c_uint64)]

class LobbyEnter_t(ctypes.Structure):
    _fields_ = [("m_ulSteamIDLobby", c_uint64),
                ("m_rgfChatPermissions", c_uint32),
                ("m_bLocked", c_uint8),
                ("m_EChatRoomEnterResponse", c_uint32)]

class LobbyChatUpdate_t(ctypes.Structure):
    _fields_ = [("m_ulSteamIDLobby", c_uint64),
                ("m_ulSteamIDUserChanged", c_uint64),
                ("m_ulSteamIDMakingChange", c_uint64),
                ("m_rgfChatMemberStateChange", c_uint32)]

class LobbyDataUpdate_t(ctypes.Structure):
    _fields_ = [("m_ulSteamIDLobby", c_uint64),
                ("m_ulSteamIDMember", c_uint64),
                ("m_bSuccess", c_uint8)]

class LobbyInvite_t(ctypes.Structure):
    _fields_ = [("m_ulSteamIDUser", c_uint64), ("m_ulSteamIDLobby", c_uint64), ("m_ulGameID", c_uint64)]

class GameLobbyJoinRequested_t(ctypes.Structure):
    _fields_ = [("m_steamIDLobby", c_uint64), ("m_steamIDFriend", c_uint64)]


def _steam_init_handles():
    """Init + 获取各接口实例"""
    SteamAPI_Init()
    steam_client = c_void_p(SteamInternal_CreateInterface(b"SteamClient023"))
    hUser = SteamAPI_GetHSteamUser()
    hPipe = SteamAPI_GetHSteamPipe()
    user = c_void_p(GetISteamUser(steam_client, hUser, hPipe, b"SteamUser023"))
    friends = c_void_p(GetISteamFriends(steam_client, hUser, hPipe, b"SteamFriends018"))
    mm = c_void_p(GetISteamMatchmaking(steam_client, hUser, hPipe, b"SteamMatchMaking009"))
    dbg("SteamAPI_Init ok")
    dbg(f"handles: user={user.value} friends={friends.value} mm={mm.value}")
    return user, friends, mm


# ================= GUI Lobby State =================
class Lobby:
    """
    入口：
        lobby = Lobby(screen, manager, current_player)
        state = lobby.run()
    """
    def __init__(self, screen, manager, current_player: player.Player, max_members: int = 9):
        self.screen = screen
        self.clock = g.time.Clock()
        self.manager = manager
        self.running = True

        self.current_player = current_player
        self.max_members = max_members

        # Steam
        self.user, self.friends, self.mm = _steam_init_handles()
        self.my_steamid = ISteamUser_GetSteamID(self.user)
        self.my_name = (ISteamFriends_GetPersonaName(self.friends) or b"Unknown").decode("utf-8", "ignore")
        dbg(f"self.my_steamid={self.my_steamid}, self.my_name={self.my_name}")

        # Lobby runtime
        self.lobby_id = 0
        self.member_names = []
        self._friend_ids = []

        # ---------- UI ----------
        w, h = self.screen.get_size()
        cx = w // 2

        self.title_label = gui.elements.UILabel(
            relative_rect=g.Rect(cx - 140, 24, 280, 36),
            text="Lobby",
            manager=self.manager,
        )

        self.create_btn = gui.elements.UIButton(
            relative_rect=g.Rect(cx - 240, 70, 160, 38),
            text="创建公开大厅",
            manager=self.manager,
        )

        self.invite_btn = gui.elements.UIButton(
            relative_rect=g.Rect(cx - 60, 70, 160, 38),
            text="邀请好友加入",
            manager=self.manager,
        )

        self.leave_btn = gui.elements.UIButton(
            relative_rect=g.Rect(cx + 120, 70, 120, 38),
            text="离开大厅",
            manager=self.manager,
        )

        # 左侧：好友列表 + 跟随加入
        self.friends_list = gui.elements.UISelectionList(
            relative_rect=g.Rect(30, 130, 260, 320),
            item_list=[],
            manager=self.manager,
        )
        self.join_friend_btn = gui.elements.UIButton(
            relative_rect=g.Rect(30, 460, 260, 30),
            text="加入所选好友的房间",
            manager=self.manager,
        )

        # 右侧：成员列表
        self.members_list = gui.elements.UISelectionList(
            relative_rect=g.Rect(cx - 120, 130, 520, 360),
            item_list=[],
            manager=self.manager,
        )

        # 状态栏
        self.status_label = gui.elements.UILabel(
            relative_rect=g.Rect(cx - 260, 500, 520, 28),
            text=f"你好 {self.my_name} ({self.my_steamid})",
            manager=self.manager,
        )

        # 初始化
        self._install_callbacks()
        self._load_friends_list()

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
            if ev.m_eResult == 1:  # k_EResultOK
                self.lobby_id = ev.m_ulSteamIDLobby
                self._set_status(f"已创建Lobby：{self.lobby_id}，等待进入...")
            else:
                self._set_status(f"创建失败，EResult={ev.m_eResult}")
            dbg(f"on_lobby_created: result={ev.m_eResult}, lobby={ev.m_ulSteamIDLobby}")

        def on_lobby_enter(ev: LobbyEnter_t):
            self.lobby_id = ev.m_ulSteamIDLobby
            self._set_status(f"已进入Lobby：{self.lobby_id}")
            self._after_enter_lobby()
            self._refresh_member_names()
            ok_joinable = ISteamMatchmaking_SetLobbyJoinable(self.mm, self.lobby_id, True)
            dbg(f"SetLobbyJoinable(true) -> {ok_joinable}")

            # 让好友“最近的大厅/同游戏好友列表”更容易发现
            ISteamMatchmaking_SetLobbyData(self.mm, self.lobby_id, b"name", self.my_name.encode("utf-8"))
            ISteamMatchmaking_SetLobbyData(self.mm, self.lobby_id, b"ver", b"1")
            ISteamMatchmaking_SetLobbyData(self.mm, self.lobby_id, b"mode", b"poker")

            # 写入成员名，给非好友也能看到
            ISteamMatchmaking_SetLobbyMemberData(self.mm, self.lobby_id, b"player_name", self.my_name.encode("utf-8"))
            dbg("Lobby data & member data set")

            dbg(f"on_lobby_enter: lobby={ev.m_ulSteamIDLobby}, locked={ev.m_bLocked}, enter_resp={ev.m_EChatRoomEnterResponse}")

        def on_lobby_chat_update(ev: LobbyChatUpdate_t):
            if ev.m_ulSteamIDLobby == self.lobby_id:
                self._refresh_member_names()
            dbg(f"on_lobby_chat_update: lobby={ev.m_ulSteamIDLobby}, user_changed={ev.m_ulSteamIDUserChanged}, state_change={ev.m_rgfChatMemberStateChange}")

        def on_lobby_data_update(ev: LobbyDataUpdate_t):
            if ev.m_ulSteamIDLobby == self.lobby_id:
                self._refresh_member_names()
            dbg(f"on_lobby_data_update: lobby={ev.m_ulSteamIDLobby}, member={ev.m_ulSteamIDMember}, success={ev.m_bSuccess}")

        def on_lobby_invite(ev: LobbyInvite_t):
            # 收到别人邀请你 -> 自动加入（也可弹确认UI）
            ISteamMatchmaking_JoinLobby(self.mm, c_uint64(ev.m_ulSteamIDLobby))
            self._set_status(f"收到邀请，正在加入Lobby {ev.m_ulSteamIDLobby} ...")
            dbg(f"on_lobby_invite: from={ev.m_ulSteamIDUser}, lobby={ev.m_ulSteamIDLobby}, gameid={ev.m_ulGameID}")

        def on_game_lobby_join_requested(ev: GameLobbyJoinRequested_t):
            # 别人在好友列表右键“加入游戏” -> 你将被请求进入该Lobby
            ISteamMatchmaking_JoinLobby(self.mm, c_uint64(ev.m_steamIDLobby))
            self._set_status(f"好友请求加入，进入Lobby {ev.m_steamIDLobby} ...")
            dbg(f"on_game_lobby_join_requested: friend={ev.m_steamIDFriend}, lobby={ev.m_steamIDLobby}")

        self._cb_keep = []
        for cls_, func, cbid in [
            (LobbyCreated_t, on_lobby_created, CBID_LobbyCreated),
            (LobbyEnter_t, on_lobby_enter, CBID_LobbyEnter),
            (LobbyChatUpdate_t, on_lobby_chat_update, CBID_LobbyChatUpdate),
            (LobbyDataUpdate_t, on_lobby_data_update, CBID_LobbyDataUpdate),
            (LobbyInvite_t, on_lobby_invite, CBID_LobbyInvite),
            (GameLobbyJoinRequested_t, on_game_lobby_join_requested, CBID_GameLobbyJoinRequested),
        ]:
            vtbl, base = _mk_vtable(cls_, func, cbid)
            self._cb_keep.append((vtbl, base))
            SteamAPI_RegisterCallback(ctypes.byref(base), cbid)

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
        dbg(f"SetRichPresence connect={self.lobby_id}")

    def _after_leave_lobby(self):
        ISteamFriends_ClearRichPresence(self.friends)

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
        self.friends_list.set_item_list(items)

    def _refresh_member_names(self):
        if not self.lobby_id:
            self.members_list.set_item_list([])
            return
        count = ISteamMatchmaking_GetNumLobbyMembers(self.mm, self.lobby_id)
        names = []
        for i in range(int(count)):
            sid = ISteamMatchmaking_GetLobbyMemberByIndex(self.mm, self.lobby_id, i)
            # 优先用 Friends API 取昵称（大多可用）
            pname = ISteamFriends_GetFriendPersonaName(self.friends, sid)
            display = (pname or b"").decode("utf-8", "ignore").strip()
            if not display:
                # 退化到 Lobby Member Data 的 "player_name"
                p = ISteamMatchmaking_GetLobbyMemberData(self.mm, self.lobby_id, sid, b"player_name")
                display = (p or b"Unknown").decode("utf-8", "ignore")
            names.append(display)
        self.member_names = names
        self.members_list.set_item_list(names)
        dbg(f"members[{len(self.member_names)}]: {self.member_names}")

    # ---------- Actions ----------
    def create_public_lobby(self):
        ISteamMatchmaking_CreateLobby(self.mm, ELobbyType_Public, self.max_members)
        call = ISteamMatchmaking_CreateLobby(self.mm, ELobbyType_Public, self.max_members)
        dbg(f"CreateLobby called -> SteamAPICall_t={call}")
        self._set_status("正在创建公开Lobby...")

    def invite_friends_via_overlay(self):
        if self.lobby_id:
            ISteamFriends_ActivateGameOverlayInviteDialog(self.friends, c_uint64(self.lobby_id))
            self._set_status("已打开Steam邀请弹窗")
        else:
            self._set_status("请先创建或加入一个Lobby")
        dbg(f"invite overlay open, lobby={self.lobby_id}")

    def join_selected_friend_lobby(self):
        sel = self.friends_list.get_single_selection()
        if sel is None:
            self._set_status("先从好友列表选择一个好友")
            return
        idx = self.friends_list.item_list.index(sel)
        fid = self._friend_ids[idx]
        info = FriendGameInfo_t()
        if ISteamFriends_GetFriendGamePlayed(self.friends, fid, ctypes.byref(info)):
            lobby = info.m_steamIDLobby
            if lobby:
                ISteamMatchmaking_JoinLobby(self.mm, c_uint64(lobby))
                self._set_status(f"跟随加入好友的Lobby {lobby} ...")
            else:
                self._set_status("该好友当前不在可加入的Lobby")
        else:
            self._set_status("该好友未在游戏中或不可加入")
        dbg(f"join_selected_friend_lobby: pick_idx={idx}, friend_id={fid}")
        ok = ISteamFriends_GetFriendGamePlayed(self.friends, fid, ctypes.byref(info))
        dbg(f"GetFriendGamePlayed ok={ok}, lobby={info.m_steamIDLobby}, gameid={info.m_gameID}")

    def leave_lobby(self):
        if self.lobby_id:
            ISteamMatchmaking_LeaveLobby(self.mm, self.lobby_id)
            self._after_leave_lobby()
            self._set_status("已离开Lobby")
            self.lobby_id = 0
            self.members_list.set_item_list([])

    # ---------- Loop ----------
    def handle_events(self):
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT"

            self.manager.process_events(event)

            if event.type == gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.create_btn:
                    self.create_public_lobby()
                elif event.ui_element == self.invite_btn:
                    self.invite_friends_via_overlay()
                elif event.ui_element == self.join_friend_btn:
                    self.join_selected_friend_lobby()
                elif event.ui_element == self.leave_btn:
                    self.leave_lobby()

        return None

    def draw(self):
        self.screen.fill((245, 245, 245))
        dt = self.clock.tick(60) / 1000.0

        # 一定要跑回调
        SteamAPI_RunCallbacks()

        self.manager.update(dt)
        self.manager.draw_ui(self.screen)
        g.display.flip()

    def run(self):
        try:
            while self.running:
                nxt = self.handle_events()
                if nxt:
                    return nxt
                self.draw()
        finally:
            self._uninstall_callbacks()
            SteamAPI_Shutdown()
        return "STATE_QUIT"
