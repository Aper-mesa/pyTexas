import socket

import pygame as g
import sys
from pygame_networking import Server

# --- Constants ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
COLOR_INACTIVE = g.Color('lightskyblue3')
COLOR_ACTIVE = g.Color('dodgerblue2')

server = Server()

class Lobby:
    """A class to manage the registration screen UI and logic."""

    def __init__(self, screen):
        self.screen = screen
        self.clock = g.time.Clock()
        self.font = g.font.Font(None, 32)  # Use the default font

        self.create_session_button = g.Rect(250, 150, 300, 50)
        self.join_session_button = g.Rect(250, 250, 300, 50)

        # --- State Variables ---
        self.running = True

    def handle_events(self):
        """Process all events from the event queue."""
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False

            # --- Mouse Click Events ---
            if event.type == g.MOUSEBUTTONDOWN:
                # Check if the user clicked the confirm button
                if self.join_session_button.collidepoint(event.pos):
                    self.joinSession()
                elif self.create_session_button.collidepoint(event.pos):
                    self.createSession()

    def draw(self):
        """Draw all elements to the screen."""
        # Fill the background with white
        self.screen.fill(WHITE)

        # --- Draw Confirm Button ---
        g.draw.rect(self.screen, GRAY, self.create_session_button)
        create_session_text = self.font.render("Create Session", True, BLACK)
        # Center the text inside the button
        create_session_text_rect = create_session_text.get_rect(center=self.create_session_button.center)
        self.screen.blit(create_session_text, create_session_text_rect)

        g.draw.rect(self.screen, GRAY, self.join_session_button)
        join_session_text = self.font.render("Join Session", True, BLACK)
        join_session_text_rect = join_session_text.get_rect(center=self.join_session_button.center)
        self.screen.blit(join_session_text, join_session_text_rect)

        # Update the full display surface to the screen
        g.display.flip()

    def createSession(self):
        server.serve((self.get_local_ip(), 3333))

    def get_local_ip(self):
        """
        A reliable way to get the local IP address of the machine.
        """
        s = None
        try:
            # Create a UDP socket (no actual connection is made)
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            # Connect to a public DNS server
            # This doesn't send any data, it just finds the right local interface
            s.connect(("8.8.8.8", 80))
            # Get the socket's own address
            ip_address = s.getsockname()[0]
        except Exception as e:
            print(f"Could not get IP address: {e}")
            # Fallback: get IP from hostname (less reliable)
            try:
                ip_address = socket.gethostbyname(socket.gethostname())
            except Exception:
                ip_address = "127.0.0.1"  # If all else fails
        finally:
            if s:
                s.close()
        print(f"Host IP address: {ip_address}")
        return ip_address

    def run(self):
        """The main loop of the registration screen."""
        while self.running:
            next_state, data = self.handle_events()
            if next_state:
                return next_state, data

            self.draw()
            self.clock.tick(60)  # FPS

        return "STATE_QUIT", None