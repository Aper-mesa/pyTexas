import pygame
import sys
from Login import Login
from Lobby import Lobby
from round import Game

def main():
    pygame.init()

    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))

    current_state = "STATE_LOGIN"

    logginInstance = None

    while True:
        if current_state == "STATE_LOGIN":
            login  = Login(screen)
            logginInstance = login
            next_state, data = login.run()
            current_state = next_state
        elif current_state == "STATE_LOBBY":
            if logginInstance:
                if logginInstance.currentPlayer:
                    lobby = Lobby(screen, logginInstance.currentPlayer)
                    next_state, data = lobby.run()
                    current_state = next_state
        elif current_state == 'STATE_GAME':
            game = Game(screen)
        elif current_state == "STATE_QUIT":
            break

    print("Exiting application.")
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()