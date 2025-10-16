#include "steam_wrapper_api.h"
#include "steam_callback_helpers.h"

// --- Generic Handler Macro ---
#define MAKE_HANDLER(name, type) \
class name##Handler { \
public: \
    name##Handler(SteamCallback* py_obj) : m_pyObject(py_obj), m_Callback(this, &name##Handler::OnCallback) {} \
private: \
    SteamCallback* m_pyObject; \
    CCallback<name##Handler, type> m_Callback; \
    void OnCallback(type* pParam) { \
        __pyx_f_13steam_wrapper_13SteamCallback_on_##name(m_pyObject, pParam); \
    } \
}; \
void* new_##name##_handler(SteamCallback* obj) { return new name##Handler(obj); } \
void del_##name##_handler(void* handler) { delete static_cast<name##Handler*>(handler); }

// --- Create Handlers for each callback type ---
MAKE_HANDLER(lobby_created, LobbyCreated_t)
MAKE_HANDLER(lobby_enter, LobbyEnter_t)
MAKE_HANDLER(lobby_chat_update, LobbyChatUpdate_t)
MAKE_HANDLER(lobby_data_update, LobbyDataUpdate_t)
MAKE_HANDLER(lobby_invite, LobbyInvite_t)
MAKE_HANDLER(join_requested, GameLobbyJoinRequested_t)
MAKE_HANDLER(game_rich_presence_join_requested, GameRichPresenceJoinRequested_t)
MAKE_HANDLER(game_overlay_activated, GameOverlayActivated_t)