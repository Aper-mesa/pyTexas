import pygame as g
import socket
import threading
from pygame_networking import Server

# --- Constants ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
COLOR_INACTIVE = g.Color('lightskyblue3')
COLOR_ACTIVE = g.Color('dodgerblue2')

server = Server()

class Lobby:
    def __init__(self, screen):
        self.players = []
        self.screen = screen
        self.clock = g.time.Clock()
        self.font = g.font.Font(None, 32)

        # --- UI Elements ---
        self.create_session_button = g.Rect(250, 150, 300, 50)
        self.join_session_button = g.Rect(250, 250, 300, 50)
        self.ip_box = g.Rect(250, 350, 300, 50)
        self.ip_text = ''
        self.ip_active = False

        self.startButton = g.Rect(250, 350, 300, 50)

        # --- State Variables ---
        self.running = True
        # MODIFICATION: A new state to show after creating a session
        self.lobby_state = "main"  # "main" or "hosting"

    def handle_events(self):
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT", None

            if self.lobby_state == "main":  # Only handle buttons in the main state
                if event.type == g.MOUSEBUTTONDOWN:
                    if self.join_session_button.collidepoint(event.pos):
                        self.joinSession()
                    elif self.create_session_button.collidepoint(event.pos):
                        self.createSession()
                    elif self.ip_box.collidepoint(event.pos):
                        self.ip_active = True
                    else:
                        self.ip_active = False
            elif self.lobby_state == 'hosting':
                if event.type == g.MOUSEBUTTONDOWN:
                    if self.startButton.collidepoint(event.pos):
                        self.newGame()

                if event.type == g.KEYDOWN:
                    if self.ip_active:
                        if event.key == g.K_BACKSPACE:
                            self.ip_text = self.ip_text[:-1]
                        else:
                            self.ip_text += event.unicode
        return None, None

    def draw_main_lobby(self):
        """Draws the initial lobby screen with buttons."""
        g.draw.rect(self.screen, GRAY, self.create_session_button)
        create_text = self.font.render("Create Session", True, BLACK)
        self.screen.blit(create_text, create_text.get_rect(center=self.create_session_button.center))

        g.draw.rect(self.screen, GRAY, self.join_session_button)
        join_text = self.font.render("Join Session", True, BLACK)
        self.screen.blit(join_text, join_text.get_rect(center=self.join_session_button.center))

        ip_color = COLOR_ACTIVE if self.ip_active else COLOR_INACTIVE
        g.draw.rect(self.screen, ip_color, self.ip_box, 2)
        ip_surface = self.font.render(self.ip_text, True, BLACK)
        self.screen.blit(ip_surface, (self.ip_box.x + 5, self.ip_box.y + 5))

    def draw_hosting_lobby(self):
        """Draws the screen after the host has created a session."""
        host_ip_text = self.font.render(f"Server is running!", True, BLACK)
        ip_info_text = self.font.render(f"Your IP is: {self.get_local_ip()}", True, BLACK)
        wait_text = self.font.render("Waiting for players to join...", True, GRAY)

        g.draw.rect(self.screen, GRAY, self.startButton)
        start_text = self.font.render('Start', True, BLACK)
        text_rect = start_text.get_rect(center=self.startButton.center)
        self.screen.blit(start_text, text_rect)

        self.screen.blit(host_ip_text, (250, 150))
        self.screen.blit(ip_info_text, (250, 200))
        self.screen.blit(wait_text, (250, 300))

    def draw(self):
        self.screen.fill(WHITE)
        if self.lobby_state == "main":
            self.draw_main_lobby()
        elif self.lobby_state == "hosting":
            self.draw_hosting_lobby()
        g.display.flip()

    def _start_server(self):
        """
        This function will run in a separate thread.
        It contains the blocking 'serve' call.
        """
        try:
            # The blocking call is now safely inside a thread
            server.serve((self.get_local_ip(), 3333))
            print("Server thread has started.")
        except Exception as e:
            print(f"Error starting server thread: {e}")

    def createSession(self):
        """Creates the server and starts it in a new thread."""

        # MODIFICATION: Create a new thread for the server.
        # target=_start_server is the function the thread will run.
        # daemon=True means the thread will exit when the main program exits.
        server_thread = threading.Thread(target=self._start_server, daemon=True)
        server_thread.start()

        print("Create Session button clicked, server thread starting in background...")
        self.lobby_state = "hosting"  # Change the screen state

    def get_local_ip(self):
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip_address = s.getsockname()[0]
        except Exception:
            ip_address = "127.0.0.1"
        finally:
            if s:
                s.close()
        return ip_address

    def joinSession(self):
        """
        MODIFICATION: Correctly uses a Client object to connect.
        """
        try:
            # The port needs to be an integer, not a string.
            server.connect((self.ip_text, 3333))
            print(f"Attempting to join session at {self.ip_text}:3333")
            # Here you would transition to a "waiting in lobby" state
        except Exception as e:
            print(f"Failed to join session: {e}")

    def newGame(self):
        print("New game started.")
        return 'STATE_GAME', self.players

    def run(self):
        while self.running:
            next_state, data = self.handle_events()
            if next_state:
                return next_state, data

            # You can also update networking info here, e.g., check for new players
            # if self.server:
            #     client_id, msg = self.server.get_message()
            #     if client_id:
            #         print(f"Received from {client_id}: {msg}")

            self.draw()
            self.clock.tick(60)

        return "STATE_QUIT", None