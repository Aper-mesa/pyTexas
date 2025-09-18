# main.py
import pygame
import sys
import Login
import Lobby


def game():
    """Main controller for the application."""
    pygame.init()

    # --- Create the one and only window ---
    screen_width = 800
    screen_height = 600
    screen = pygame.display.set_mode((screen_width, screen_height))

    # --- State Management ---
    # Start the application in the "MENU" state
    current_state = "STATE_LOGIN"

    while True:  # The main loop that controls state transitions
        if current_state == "STATE_LOGIN":
            # Call the menu function. It will run its own loop and return the next state.
            next_state = Login(screen)
            current_state = next_state  # Update the state

        elif current_state == "GAME":
            # Call the game function.
            next_state = game_screen(screen)
            current_state = next_state  # Update the state

        elif current_state == "QUIT":
            # If any screen returns "QUIT", break the main loop
            break

    # --- Clean up and exit ---
    print("Exiting application.")
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    game()