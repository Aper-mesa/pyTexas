#pragma once

#include "steam_wrapper.h"

#include "steam_api.h"

void __pyx_f_13steam_wrapper_13SteamCallback_on_lobby_created(struct SteamCallback *, LobbyCreated_t *);
void __pyx_f_13steam_wrapper_13SteamCallback_on_lobby_enter(struct SteamCallback *, LobbyEnter_t *);
void __pyx_f_13steam_wrapper_13SteamCallback_on_lobby_chat_update(struct SteamCallback *, LobbyChatUpdate_t *);
void __pyx_f_13steam_wrapper_13SteamCallback_on_lobby_data_update(struct SteamCallback *, LobbyDataUpdate_t *);
void __pyx_f_13steam_wrapper_13SteamCallback_on_lobby_invite(struct SteamCallback *, LobbyInvite_t *);
void __pyx_f_13steam_wrapper_13SteamCallback_on_join_requested(struct SteamCallback *, GameLobbyJoinRequested_t *);
void __pyx_f_13steam_wrapper_13SteamCallback_on_game_rich_presence_join_requested(struct SteamCallback *, GameRichPresenceJoinRequested_t *);
void __pyx_f_13steam_wrapper_13SteamCallback_on_game_overlay_activated(struct SteamCallback *, GameOverlayActivated_t *);