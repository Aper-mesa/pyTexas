import json
import os
import sys

import imgui
import pygame
from imgui.integrations.pygame import PygameRenderer

import steam_wrapper as steam
import tools
from Lobby import Lobby
from Login import Login
from round import PlayScreen
import player


def main():
    running_dir = tools.resource_path('.')
    os.chdir(running_dir)
    steam.init()

    if not os.path.exists('data'): os.mkdir('data')
    sid = steam.get_my_steam_id()
    if os.path.exists(f"data/{sid}.json"):
        data = json.load(open(f"data/{sid}.json"))
        current_player = player.Player(data['steam_id'], data['username'], data['money'])
    else:
        current_player = player.Player(steam.get_my_steam_id(), steam.get_my_persona_name())

    pygame.mixer.pre_init(44100, -16, 2, 512)
    os.environ["SDL_RENDER_SCALE_QUALITY"] = "0"  # 0=最近邻(默认), 1=线性, 2=best
    pygame.init()
    pygame.display.set_caption("pyTexas")

    try:
        bgm_path = tools.resource_path(os.path.join('resources/sounds', 'bgm.mp3'))
        pygame.mixer.music.load(bgm_path)
        pygame.mixer.music.set_volume(0.5)  # 可调音量 0.0~1.0
        pygame.mixer.music.play(-1)  # -1 表示无限循环
    except Exception as e:
        print(f"WARNING: Failed to load/play BGM: {e}")

    screen_width = 1600
    screen_height = 900
    flags = pygame.OPENGL | pygame.DOUBLEBUF
    screen = pygame.display.set_mode((screen_width, screen_height), flags)

    imgui.create_context()
    impl = PygameRenderer()

    io = imgui.get_io()
    io.display_size = screen_width, screen_height

    current_state = "STATE_LOGIN"

    data = None

    while True:
        steam.run_callbacks()
        if current_state == "STATE_LOGIN":
            login = Login(screen, impl)
            next_state = login.run()
            _cleanup_scene(screen)
            current_state = next_state
        elif current_state == "STATE_LOBBY":
            lobby = Lobby(screen, impl, current_player)
            next_state, data = lobby.run()
            _cleanup_scene(screen)
            current_state = next_state
        elif current_state == 'STATE_GAME':
            game = PlayScreen(screen, impl, data, current_player)
            _cleanup_scene(screen)
            # current_state = next_state
        elif current_state == "STATE_QUIT":
            print('exit game because of quit state')
            break

    print("Exiting application.")
    impl.shutdown()
    pygame.quit()
    sys.exit()


def _cleanup_scene(screen):
    screen.fill((0, 0, 0))
    pygame.display.flip()
    pygame.event.clear()


if __name__ == "__main__":
    main()
