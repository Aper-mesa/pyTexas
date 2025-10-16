cdef extern from "steam_api.h":
    bint SteamAPI_Init()
    void SteamAPI_Shutdown()
    void SteamAPI_RunCallbacks()
    void SteamAPI_RegisterCallback(void * pCallback, int iCallback)
    void SteamAPI_UnregisterCallback(void * pCallback)

cdef extern from "steam_api_common.h":
    ctypedef enum ELobbyType "ELobbyType":
        k_ELobbyTypePublic "k_ELobbyTypePublic"
    ctypedef enum EResult "EResult":
        k_EResultOK "k_EResultOK"
    ctypedef enum EChatRoomEnterResponse "EChatRoomEnterResponse":
        k_EChatRoomEnterResponseSuccess "k_EChatRoomEnterResponseSuccess"

cdef extern from "steamclientpublic.h":
    cdef cppclass CSteamID "CSteamID":
        CSteamID(unsigned long long ulSteamID) except +
        unsigned long long ConvertToUint64() nogil

cdef extern from "isteamfriends.h":
    ctypedef struct GameLobbyJoinRequested_t "GameLobbyJoinRequested_t":
        CSteamID m_steamIDLobby
        CSteamID m_steamIDFriend
    ctypedef struct GameRichPresenceJoinRequested_t "GameRichPresenceJoinRequested_t":
        CSteamID m_steamIDFriend
        char m_rgchConnect[256]
    ctypedef struct GameOverlayActivated_t "GameOverlayActivated_t":
        bint m_bActive;
    cdef cppclass ISteamFriends:
        const char * GetPersonaName()
        void ActivateGameOverlayInviteDialog(CSteamID steamIDLobby)
        bint SetRichPresence(const char * pchKey, const char * pchValue)
        void ClearRichPresence()
        int GetFriendCount(int iFriendFlags)
        CSteamID GetFriendByIndex(int iFriend, int iFriendFlags)
        const char *GetFriendPersonaName(CSteamID steamIDFriend)
    ISteamFriends * SteamFriends()

cdef extern from "isteammatchmaking.h":
    ctypedef unsigned long long SteamAPICall_t "SteamAPICall_t"
    ctypedef struct LobbyCreated_t "LobbyCreated_t":
        EResult m_eResult
        unsigned long long m_ulSteamIDLobby
    ctypedef struct LobbyEnter_t "LobbyEnter_t":
        unsigned long long m_ulSteamIDLobby
        unsigned int m_rgfChatPermissions
        bint m_bLocked
        unsigned int m_EChatRoomEnterResponse
    ctypedef struct LobbyChatUpdate_t "LobbyChatUpdate_t":
        unsigned long long m_ulSteamIDLobby
        unsigned long long m_ulSteamIDUserChanged
        unsigned long long m_ulSteamIDMakingChange
        unsigned int m_rgfChatMemberStateChange
    ctypedef struct LobbyDataUpdate_t "LobbyDataUpdate_t":
        unsigned long long m_ulSteamIDLobby
        unsigned long long m_ulSteamIDMember
        bint m_bSuccess
    ctypedef struct LobbyInvite_t "LobbyInvite_t":
        unsigned long long m_ulSteamIDUser
        unsigned long long m_ulSteamIDLobby
        unsigned long long m_ulGameID
    cdef cppclass ISteamMatchmaking:
        SteamAPICall_t CreateLobby(ELobbyType eLobbyType, int cMaxMembers)
        SteamAPICall_t JoinLobby(CSteamID steamIDLobby)
        void LeaveLobby(CSteamID steamIDLobby)
        bint SetLobbyData(CSteamID steamIDLobby, const char * pchKey, const char * pchValue)
        const char * GetLobbyData(CSteamID steamIDLobby, const char * pchKey)
        int GetNumLobbyMembers(CSteamID steamIDLobby)
        CSteamID GetLobbyMemberByIndex(CSteamID steamIDLobby, int iMember)
        void SetLobbyMemberData(CSteamID steamIDLobby, const char * pchKey, const char * pchValue)
        const char *GetLobbyMemberData(CSteamID steamIDLobby, CSteamID steamIDUser, const char *pchKey)
        bint SetLobbyJoinable(CSteamID steamIDLobby, bint bLobbyJoinable)
    ISteamMatchmaking * SteamMatchmaking()

cdef extern from "isteamuser.h":
    cdef cppclass ISteamUser:
        CSteamID GetSteamID()
    ISteamUser * SteamUser()

cdef extern from "isteamapps.h":
    cdef cppclass ISteamApps:
        const char *GetLaunchQueryParam(const char *pchKey)
    ISteamApps * SteamApps()

cdef extern from "isteamutils.h":
    cdef cppclass ISteamUtils:
        bint IsOverlayEnabled()
    ISteamUtils * SteamUtils()

cdef extern from "steam_callback_helpers.h":
    void * new_lobby_created_handler(SteamCallback obj)
    void del_lobby_created_handler(void * handler)
    void * new_join_requested_handler(SteamCallback obj)
    void del_join_requested_handler(void * handler)
    void * new_lobby_enter_handler(SteamCallback obj)
    void del_lobby_enter_handler(void * handler)
    void * new_lobby_chat_update_handler(SteamCallback obj)
    void del_lobby_chat_update_handler(void * handler)
    void * new_lobby_data_update_handler(SteamCallback obj)
    void del_lobby_data_update_handler(void * handler)
    void * new_lobby_invite_handler(SteamCallback obj)
    void del_lobby_invite_handler(void * handler)
    void * new_game_rich_presence_join_requested_handler(SteamCallback obj)
    void del_game_rich_presence_join_requested_handler(void * handler)
    void * new_game_overlay_activated_handler(SteamCallback obj)
    void del_game_overlay_activated_handler(void * handler)

cdef public class SteamCallback[object SteamCallback, type SteamCallback_Type]:
    cdef:
        void * _handler
        object _py_callback
        int _callback_id

    def __cinit__(self, int callback_id, object py_callback):
        self.callback_id = callback_id
        self._py_callback = py_callback
        self._handler = NULL

        if callback_id == 513:
            self._handler = new_lobby_created_handler(self)
        elif callback_id == 333:
            self._handler = new_join_requested_handler(self)
        elif callback_id == 504:
            self._handler = new_lobby_enter_handler(self)
        elif callback_id == 506:
            self._handler = new_lobby_chat_update_handler(self)
        elif callback_id == 505:
            self._handler = new_lobby_data_update_handler(self)
        elif callback_id == 503:
            self._handler = new_lobby_invite_handler(self)
        elif callback_id == 337:
            self._handler = new_game_rich_presence_join_requested_handler(self)
        elif callback_id == 331:
            self._handler = new_game_overlay_activated_handler(self)
        else:
            raise TypeError(f"Callback ID {callback_id} is not supported yet.")

    cdef public api void on_lobby_created(self, LobbyCreated_t * data):
        py_data = {
            'm_eResult': data.m_eResult,
            'm_ulSteamIDLobby': data.m_ulSteamIDLobby,
        }
        self._py_callback(py_data)

    cdef public api void on_lobby_enter(self, LobbyEnter_t * data):
        self._py_callback({'m_ulSteamIDLobby': data.m_ulSteamIDLobby, 'm_bLocked': data.m_bLocked,
                           'm_EChatRoomEnterResponse': data.m_EChatRoomEnterResponse})

    cdef public api void on_lobby_chat_update(self, LobbyChatUpdate_t * data):
        self._py_callback(
            {'m_ulSteamIDLobby': data.m_ulSteamIDLobby, 'm_ulSteamIDUserChanged': data.m_ulSteamIDUserChanged,
             'm_ulSteamIDMakingChange': data.m_ulSteamIDMakingChange,
             'm_rgfChatMemberStateChange': data.m_rgfChatMemberStateChange})

    cdef public api void on_lobby_data_update(self, LobbyDataUpdate_t * data):
        self._py_callback({'m_ulSteamIDLobby': data.m_ulSteamIDLobby, 'm_ulSteamIDMember': data.m_ulSteamIDMember,
                           'm_bSuccess': data.m_bSuccess})

    cdef public api void on_lobby_invite(self, LobbyInvite_t * data):
        self._py_callback({'m_ulSteamIDUser': data.m_ulSteamIDUser, 'm_ulSteamIDLobby': data.m_ulSteamIDLobby,
                           'm_ulGameID': data.m_ulGameID})

    cdef public api void on_join_requested(self, GameLobbyJoinRequested_t * data):
        py_data = {
            'm_steamIDLobby': data.m_steamIDLobby.ConvertToUint64(),
            'm_steamIDFriend': data.m_steamIDFriend.ConvertToUint64()
        }
        self._py_callback(py_data)

    cdef public api void on_game_rich_presence_join_requested(self, GameRichPresenceJoinRequested_t * data):
        connect_str = data.m_rgchConnect
        self._py_callback({'m_steamIDFriend': data.m_steamIDFriend.ConvertToUint64(), 'm_rgchConnect': connect_str})

    cdef public api void on_game_overlay_activated(self, GameOverlayActivated_t * data):
        self._py_callback({'m_bActive': data.m_bActive})

    def __dealloc__(self):
        if self._handler != NULL:
            if self.callback_id == 513:
                del_lobby_created_handler(self._handler)
            elif self.callback_id == 333:
                del_join_requested_handler(self._handler)
            elif self.callback_id == 504:
                del_lobby_enter_handler(self._handler)
            elif self.callback_id == 506:
                del_lobby_chat_update_handler(self._handler)
            elif self.callback_id == 505:
                del_lobby_data_update_handler(self._handler)
            elif self.callback_id == 503:
                del_lobby_invite_handler(self._handler)
            elif self.callback_id == 337:
                del_game_rich_presence_join_requested_handler(self._handler)
            elif self.callback_id == 331:
                del_game_overlay_activated_handler(self._handler)
            self._handler = NULL

cdef ISteamFriends * g_friends = NULL
cdef ISteamMatchmaking * g_matchmaking = NULL
cdef ISteamUser * g_user = NULL
cdef ISteamApps * g_apps = NULL
cdef ISteamUtils * g_utils = NULL

def init():
    global g_friends, g_matchmaking, g_user, g_apps, g_utils
    if not SteamAPI_Init():
        raise RuntimeError("SteamAPI_Init() failed.")
    g_friends = SteamFriends()
    g_matchmaking = SteamMatchmaking()
    g_user = SteamUser()
    g_apps = SteamApps()
    g_utils = SteamUtils()
    if not (g_friends and g_matchmaking and g_user and g_apps and g_utils):
        raise RuntimeError("Failed to get Steam interfaces.")
    print("steam_wrapper: Steamworks API initialized successfully.")

def shutdown():
    SteamAPI_Shutdown()

def run_callbacks():
    SteamAPI_RunCallbacks()

# --- User ---
def get_my_steam_id():
    if g_user:
        return g_user.GetSteamID().ConvertToUint64()
    return 0

# --- Apps ---
def get_launch_query_param(key):
    if not g_apps: return ""
    return g_apps.GetLaunchQueryParam(key.encode('utf-8'))

# --- Utils ---
def is_overlay_enabled():
    if not g_utils: return False
    return g_utils.IsOverlayEnabled()

# --- Friends ---
def get_my_persona_name():
    if g_friends:
        return g_friends.GetPersonaName().decode('utf-8', 'ignore')
    return ""

def activate_game_overlay_invite_dialog(unsigned long long lobby_id_int):
    if g_friends:
        g_friends.ActivateGameOverlayInviteDialog(CSteamID(lobby_id_int))

def set_rich_presence(key, value):
    if g_friends:
        g_friends.SetRichPresence(key.encode('utf-8'), value.encode('utf-8'))

def clear_rich_presence():
    if g_friends:
        g_friends.ClearRichPresence()

def get_friend_count(int iFriendFlags):
    if not g_friends: return 0
    return g_friends.GetFriendCount(iFriendFlags)

def get_friend_by_index(int iFriend, int iFriendFlags):
    if g_friends:
        return g_friends.GetFriendByIndex(iFriend, iFriendFlags).ConvertToUint64()
    return None

def get_friend_persona_name(unsigned long long steamIDFriend):
    if g_friends:
        return g_friends.GetFriendPersonaName(CSteamID(steamIDFriend)).decode('utf-8')
    return ""

# --- Matchmaking ---
def create_lobby(lobby_type, max_members):
    if g_matchmaking:
        return g_matchmaking.CreateLobby(<ELobbyType> lobby_type, max_members)
    return 0

def join_lobby(unsigned long long lobby_id_int):
    if g_matchmaking:
        return g_matchmaking.JoinLobby(CSteamID(lobby_id_int))
    return 0

def leave_lobby(unsigned long long lobby_id_int):
    if g_matchmaking:
        g_matchmaking.LeaveLobby(CSteamID(lobby_id_int))

def get_lobby_data(unsigned long long lobby_id_int, key):
    cdef const char * value_bytes = NULL
    if g_matchmaking:
        value_bytes = g_matchmaking.GetLobbyData(CSteamID(lobby_id_int), key.encode('utf-8'))
        return value_bytes.decode('utf-8', 'ignore')
    return ""

def set_lobby_data(unsigned long long lobby_id_int, key, value):
    if g_matchmaking:
        g_matchmaking.SetLobbyData(CSteamID(lobby_id_int), key.encode('utf-8'), value.encode('utf-8'))

def get_lobby_member_by_index(unsigned long long lobby_id_int, int iMember):
    if g_matchmaking:
        return g_matchmaking.GetLobbyMemberByIndex(CSteamID(lobby_id_int), iMember).ConvertToUint64()
    return 0

def get_num_lobby_members(unsigned long long lobby_id_int):
    if not g_matchmaking: return 0
    return g_matchmaking.GetNumLobbyMembers(CSteamID(lobby_id_int))

def get_lobby_member_data(unsigned long long lobby_id_int, unsigned long long steam_id_int, key):
    if g_matchmaking:
        return g_matchmaking.GetLobbyMemberData(CSteamID(lobby_id_int), CSteamID(steam_id_int), key.encode('utf-8'))
    return None

def set_lobby_member_data(unsigned long long lobby_id_int, key, value):
    if not g_matchmaking: return
    g_matchmaking.SetLobbyMemberData(CSteamID(lobby_id_int), key.encode('utf-8'), value.encode('utf-8'))

def set_lobby_joinable(unsigned long long lobby_id_int, bint bLobbyJoinable):
    if not g_matchmaking: return None
    return g_matchmaking.SetLobbyJoinable(CSteamID(lobby_id_int), bLobbyJoinable)
