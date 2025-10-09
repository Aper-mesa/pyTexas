import os
import sys

import i18n
import pygame
import pygame_gui as gui

import steam_bootstrap as steam
import tools
from Lobby import Lobby
from Login import Login
from round import Room, PlayScreen


def main():
    running_dir = tools.resource_path('.')
    os.chdir(running_dir)
    steam.init()

    pygame.mixer.pre_init(44100, -16, 2, 512)
    os.environ["SDL_RENDER_SCALE_QUALITY"] = "0"  # 0=最近邻(默认), 1=线性, 2=best
    pygame.init()
    pygame.display.set_caption("pyTexas 0.5.10.9.1")

    try:
        bgm_path = tools.resource_path(os.path.join('sounds', 'bgm.mp3'))
        pygame.mixer.music.load(bgm_path)
        pygame.mixer.music.set_volume(0.5)  # 可调音量 0.0~1.0
        pygame.mixer.music.play(-1)  # -1 表示无限循环
    except Exception as e:
        print(f"WARNING: Failed to load/play BGM: {e}")

    i18n.set('load_path', ['languages'])
    i18n.set('filename_format', 'lang.{locale}.{format}')
    i18n.set('locale', 'zh')
    i18n.set('fallback', 'en')

    screen_width = 1200
    screen_height = 900
    flags = pygame.SCALED
    screen = pygame.display.set_mode((screen_width, screen_height), flags)

    current_state = "STATE_LOGIN"

    loginInstance = None
    data = None

    manager = gui.UIManager((screen.get_size()), starting_language='zh',
                            theme_path=tools.resource_path('themes/theme.json'),
                            translation_directory_paths=[tools.resource_path('languages')])

    while True:
        steam.run_callbacks()
        if current_state == "STATE_LOGIN":
            login = Login(screen, manager)
            loginInstance = login
            next_state = login.run()
            _cleanup_scene(login, screen)
            current_state = next_state
        elif current_state == "STATE_LOBBY":
            if loginInstance:
                if loginInstance.currentPlayer:
                    lobby = Lobby(screen, manager, loginInstance.currentPlayer)
                    next_state, data = lobby.run()
                    _cleanup_scene(lobby, screen)
                    current_state = next_state
        elif current_state == 'STATE_GAME':
            room = Room(screen, data)
            game = PlayScreen(screen, manager, room, loginInstance.currentPlayer)
            _cleanup_scene(game, screen)
            # current_state = next_state
        elif current_state == "STATE_QUIT":
            print('exit game because of quit state')
            break

    print("Exiting application.")
    pygame.quit()
    sys.exit()


def _cleanup_scene(obj, screen):
    if hasattr(obj, "manager") and obj.manager is not None:
        obj.manager.clear_and_reset()

    screen.fill((0, 0, 0))
    pygame.display.flip()
    pygame.event.clear()


if __name__ == "__main__":
    main()
