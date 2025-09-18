import socket

import pygame as g
from pygame_networking import Server

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
COLOR_INACTIVE = g.Color('lightskyblue3')
COLOR_ACTIVE = g.Color('dodgerblue2')

server = Server()


class Lobby:

    def __init__(self, screen):
        self.screen = screen
        self.clock = g.time.Clock()
        self.font = g.font.Font(None, 32)  # Use the default font

        self.create_session_button = g.Rect(250, 150, 300, 50)
        self.join_session_button = g.Rect(250, 250, 300, 50)
        self.ip_box = g.Rect(250, 350, 300, 50)

        self.ip_text = ''
        self.ip_active = False

        self.running = True

    def handle_events(self):
        """Process all events from the event queue."""
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT", None

            if event.type == g.MOUSEBUTTONDOWN:
                if self.join_session_button.collidepoint(event.pos):
                    self.joinSession()
                elif self.create_session_button.collidepoint(event.pos):
                    self.createSession()
                elif self.ip_box.collidepoint(event.pos):
                    self.ip_active = True
                else:
                    self.ip_active = False

            if event.type == g.KEYDOWN:
                if self.ip_active:
                    if event.key == g.K_BACKSPACE:
                        self.ip_text = self.ip_text[:-1]
                    else:
                        self.ip_text += event.unicode
        return None, None

    def draw(self):
        self.screen.fill(WHITE)

        g.draw.rect(self.screen, GRAY, self.create_session_button)
        create_session_text = self.font.render("Create Session", True, BLACK)
        create_session_text_rect = create_session_text.get_rect(center=self.create_session_button.center)
        self.screen.blit(create_session_text, create_session_text_rect)

        g.draw.rect(self.screen, GRAY, self.join_session_button)
        join_session_text = self.font.render("Join Session", True, BLACK)
        join_session_text_rect = join_session_text.get_rect(center=self.join_session_button.center)
        self.screen.blit(join_session_text, join_session_text_rect)

        ip_color = COLOR_ACTIVE if self.ip_active else COLOR_INACTIVE
        g.draw.rect(self.screen, ip_color, self.ip_box, 2)
        ip_surface = self.font.render(self.ip_text, True, BLACK)
        self.screen.blit(ip_surface, (self.ip_box.x + 5, self.ip_box.y + 5))

        # --- Draw Confirm Button ---
        g.draw.rect(self.screen, GRAY, self.join_session_button)
        join_session_text = self.font.render("Join", True, BLACK)
        # Center the text inside the button
        text_rect = join_session_text.get_rect(center=self.join_session_button.center)
        self.screen.blit(join_session_text, text_rect)

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

    def joinSession(self):
        server.connect((self.ip_text, '3333'))
        print("Join Session")

    def run(self):
        """The main loop of the registration screen."""
        while self.running:
            next_state, data = self.handle_events()
            if next_state:
                return next_state, data

            self.draw()
            self.clock.tick(60)  # FPS

        return "STATE_QUIT", None
