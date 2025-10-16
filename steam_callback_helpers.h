#pragma once
struct SteamCallback;
void* new_lobby_created_handler(SteamCallback* obj); void del_lobby_created_handler(void* handler);
void* new_lobby_enter_handler(SteamCallback* obj); void del_lobby_enter_handler(void* handler);
void* new_lobby_chat_update_handler(SteamCallback* obj); void del_lobby_chat_update_handler(void* handler);
void* new_lobby_data_update_handler(SteamCallback* obj); void del_lobby_data_update_handler(void* handler);
void* new_lobby_invite_handler(SteamCallback* obj); void del_lobby_invite_handler(void* handler);
void* new_join_requested_handler(SteamCallback* obj); void del_join_requested_handler(void* handler);
void* new_game_rich_presence_join_requested_handler(SteamCallback* obj); void del_game_rich_presence_join_requested_handler(void* handler);
void* new_game_overlay_activated_handler(SteamCallback* obj); void del_game_overlay_activated_handler(void* handler);