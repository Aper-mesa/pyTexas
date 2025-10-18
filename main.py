# main.py (修正版)
import json
import os
import sys
import imgui
import pygame
from imgui.integrations.pygame import PygameRenderer
from OpenGL.GL import glClear, GL_COLOR_BUFFER_BIT, glClearColor

import steam_wrapper as steam
import tools
from Lobby import Lobby
from Login import Login
from round import PlayScreen
import player

# --- 新增：全局变量，用于存储待处理的Lobby加入请求 ---
g_pending_lobby_join_id = None
# --- 新增：全局回调列表，防止回调被垃圾回收 ---
g_steam_callbacks = []


def main():
    global g_pending_lobby_join_id, g_steam_callbacks

    running_dir = tools.resource_path('.')
    os.chdir(running_dir)

    try:
        steam.init()
    except RuntimeError as e:
        # ... (错误处理代码保持不变) ...
        print(e)
        pygame.init()
        screen = pygame.display.set_mode((1280, 720))
        font = pygame.font.Font(None, 36)
        error_text = font.render("SteamAPI_Init() failed. Is Steam running and is steam_appid.txt present?", True,
                                 (255, 0, 0))
        text_rect = error_text.get_rect(center=(1280 / 2, 720 / 2))
        screen.blit(error_text, text_rect)
        pygame.display.flip()
        pygame.time.wait(5000)
        return

    # --- 新增：定义并注册全局的游戏邀请回调函数 ---
    def on_game_lobby_join_requested(data):
        """这个回调函数在任何界面都能被触发"""
        global g_pending_lobby_join_id
        lobby_id = data.get('m_steamIDLobby', 0)
        if lobby_id:
            print(f"[Main] Received a global lobby join request for lobby ID: {lobby_id}")
            g_pending_lobby_join_id = lobby_id

    # 注册回调，CBID_GameLobbyJoinRequested 的 ID 是 333
    callback = steam.SteamCallback(333, on_game_lobby_join_requested)
    g_steam_callbacks.append(callback)

    # ... (加载玩家数据、初始化pygame和混音器的代码保持不变) ...
    if not os.path.exists('data'): os.mkdir('data')
    sid = steam.get_my_steam_id()
    if os.path.exists(f"data/{sid}.json"):
        data = json.load(open(f"data/{sid}.json"))
        current_player = player.Player(data['steam_id'], data['username'], data['money'])
    else:
        current_player = player.Player(steam.get_my_steam_id(), steam.get_my_persona_name())

    pygame.mixer.pre_init(44100, -16, 2, 512)
    os.environ["SDL_RENDER_SCALE_QUALITY"] = "0"
    pygame.init()
    pygame.display.set_caption("pyTexas")
    try:
        bgm_path = tools.resource_path(os.path.join('resources/sounds', 'bgm.mp3'))
        pygame.mixer.music.load(bgm_path)
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play(-1)
    except Exception as e:
        print(f"WARNING: Failed to load/play BGM: {e}")

    screen_width, screen_height = 1600, 900
    flags = pygame.OPENGL | pygame.DOUBLEBUF
    screen = pygame.display.set_mode((screen_width, screen_height), flags)
    imgui.create_context()
    impl = PygameRenderer()
    io = imgui.get_io()
    io.display_size = screen_width, screen_height

    current_state = "STATE_LOGIN"
    data_for_next_state = None

    running = True
    while running:
        if current_state == "STATE_LOGIN":
            login = Login(screen, impl)
            current_state = login.run()

        elif current_state == "STATE_LOBBY":
            # --- 关键修改：将待处理的 lobby_id 传给 Lobby ---
            lobby = Lobby(screen, impl, current_player, auto_join_id=g_pending_lobby_join_id)
            # 使用后立即清空，防止重复加入
            if g_pending_lobby_join_id:
                g_pending_lobby_join_id = None

            next_state, data_for_next_state = lobby.run()
            current_state = next_state

        elif current_state == 'STATE_GAME':
            if data_for_next_state:
                game = PlayScreen(screen, impl, data_for_next_state, current_player)
                current_state = game.run()
            else:
                print("Error: Tried to enter GAME state without room data. Returning to LOBBY.")
                current_state = "STATE_LOBBY"

        elif current_state == "STATE_QUIT":
            running = False

    print("Exiting application.")
    impl.shutdown()
    steam.shutdown()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()