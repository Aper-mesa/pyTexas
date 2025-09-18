# main.py
import pygame
import sys
from Login import Login
from Lobby import Lobby


def game():
    """Main controller for the application."""
    pygame.init()

    # --- Create the one and only window ---
    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))

    # --- State Management ---
    current_state = "STATE_LOGIN"

    while True:  # The main loop that controls state transitions
        if current_state == "STATE_LOGIN":
            login  = Login(screen)
            next_state, data = login.run()
            current_state = next_state  # Update the state

        elif current_state == "STATE_LOBBY":
            lobby = Lobby(screen)
            next_state, data = lobby.run()
            current_state = next_state  # Update the state

        elif current_state == "STATE_QUIT":
            # If any screen returns "QUIT", break the main loop
            break

    # --- Clean up and exit ---
    print("Exiting application.")
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    game()