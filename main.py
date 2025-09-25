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
            current_state = next_state
        elif current_state == "STATE_LOBBY":
            if loginInstance:
                if loginInstance.currentPlayer:
                    lobby = Lobby(screen, loginInstance.currentPlayer)
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

if __name__ == "__main__":
    main()