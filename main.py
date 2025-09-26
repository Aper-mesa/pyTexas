### ---------------打包指令---------------
###  pyinstaller --windowed --name "pyTexas" main.py
### ---------------打包指令---------------

import pygame
import sys
from Login import Login
from Lobby import Lobby
from round import Room

def main():
    pygame.init()

    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))

    current_state = "STATE_LOGIN"

    loginInstance = None
    data = None

    while True:
        if current_state == "STATE_LOGIN":
            login  = Login(screen)
            loginInstance = login
            next_state, data = login.run()
            _cleanup_scene(login, screen)
            current_state = next_state
        elif current_state == "STATE_LOBBY":
            if loginInstance:
                if loginInstance.currentPlayer:
                    lobby = Lobby(screen, data,loginInstance.currentPlayer)
                    next_state, data = lobby.run()
                    current_state = next_state
        elif current_state == 'STATE_GAME':
            game = Room(screen, data)
            next_state, data = game.run()
            current_state = next_state
        elif current_state == "STATE_QUIT":
            print('exit game because of quit state')
            break

    print("Exiting application.")
    pygame.quit()
    sys.exit()

def _cleanup_scene(obj, screen):
    # 1) 清掉 pygame_gui 的控件树（若存在）
    if hasattr(obj, "manager") and obj.manager is not None:
        try:
            obj.manager.clear_and_reset()
        except Exception:
            pass
    # 2) 彻底擦屏，避免残影
    screen.fill((0, 0, 0))
    pygame.display.flip()
    # 3) 清空事件队列，防止“残留点击/回车”串到下个界面
    pygame.event.clear()


if __name__ == "__main__":
    main()