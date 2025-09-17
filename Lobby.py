# Lobby.py

import pygame
from pygame_networking import Server
import sys

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
PORT = 3333
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
BLUE = (50, 100, 200)
GREEN = (50, 200, 100)
ACTIVE_COLOR = (100, 150, 255)

server = Server()

class Lobby:
    """
    Handles the game lobby, including creating a session (server)
    and joining a session (client).
    """

    def __init__(self, username="Player"):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Texas Hold'em - Lobby")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 30)
        self.small_font = pygame.font.SysFont("monospace", 20)

        # State management
        self.state = "main_menu"  # main_menu, create_session, join_session_ip_input, waiting_in_lobby, game_starting
        self.running = True
        self.username = username  # Username from a potential login screen

        # UI elements
        self.create_button = pygame.Rect(300, 200, 200, 50)
        self.join_button = pygame.Rect(300, 300, 200, 50)
        self.start_button = pygame.Rect(300, 500, 200, 50)

        # Network related
        self.server = None
        self.client = None
        self.is_host = False
        self.connected_players = {}  # Store client info: {client_id: {"name": name, "ip": ip}}

        # IP address input box for "Join Session"
        self.ip_input_box = pygame.Rect(250, 300, 300, 40)
        self.ip_input_text = ''
        self.ip_input_active = False

    def run(self):
        """The main loop for the lobby."""
        while self.running:
            self.handle_events()
            self.update_network()
            self.draw()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def handle_events(self):
        """Handles user input and window events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                if self.server:
                    self.server.shutdown()
                if self.client:
                    self.client.disconnect()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if self.state == "main_menu":
                    if self.create_button.collidepoint(event.pos):
                        self.start_as_server()
                    elif self.join_button.collidepoint(event.pos):
                        self.state = "join_session_ip_input"
                elif self.state == "create_session":
                    # The "Start Game" button is clickable only if other players have joined
                    if len(self.connected_players) > 0 and self.start_button.collidepoint(event.pos):
                        self.start_game()
                elif self.state == "join_session_ip_input":
                    self.ip_input_active = self.ip_input_box.collidepoint(event.pos)

            if event.type == pygame.KEYDOWN and self.state == "join_session_ip_input":
                if self.ip_input_active:
                    if event.key == pygame.K_RETURN:
                        self.start_as_client(self.ip_input_text)
                    elif event.key == pygame.K_BACKSPACE:
                        self.ip_input_text = self.ip_input_text[:-1]
                    else:
                        self.ip_input_text += event.unicode

    def start_as_server(self):
        """Starts the game as a server (host)."""
        try:
            # Bind to '0.0.0.0' to listen on all available network interfaces
            self.server = server.serve(("10.36.115.178", PORT))  # Allow up to 10 clients
            self.is_host = True
            self.state = "create_session"
            print(f"Server started, listening on port {PORT}")
        except Exception as e:
            print(f"Failed to start server: {e}")
            self.state = "main_menu"

    def start_as_client(self, server_ip):
        """Starts the game as a client (guest)."""
        try:
            self.client = server.connect((server_ip, PORT))
            # On successful connection, send username
            username = "Player" + str(pygame.time.get_ticks())[:4]  # A temporary unique name
            self.client.send_message({"action": "set_name", "name": username})
            self.state = "waiting_in_lobby"
            print(f"Connected to server {server_ip}:{PORT}")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            self.state = "join_session_ip_input"

    def start_game(self):
        """Called by the host to notify everyone to start the game."""
        if self.is_host:
            self.server.send_message_to_all({"action": "start_game"})
            self.server.close_lobby()  # Stop accepting new connections
            print("Game starting! Lobby is now closed to new players.")
            self.state = "game_starting"
            self.load_game()

    def update_network(self):
        """Handles all network events, sending and receiving data."""
        # If this instance is a server
        if self.server:
            self.server.update()
            # Handle new player connections
            client_id, _ = self.server.get_client_connected()
            if client_id:
                client_ip = self.server.get_client_address(client_id)[0]
                self.connected_players[client_id] = {"name": "Reading...", "ip": client_ip}
                print(f"Player {client_id} connected from {client_ip}.")

            # Handle player disconnections
            client_id, _ = self.server.get_client_disconnected()
            if client_id and client_id in self.connected_players:
                print(f"Player {self.connected_players[client_id]['name']} has disconnected.")
                del self.connected_players[client_id]

            # Process messages from clients
            client_id, message = self.server.get_message()
            if client_id and message and message.get("action") == "set_name":
                self.connected_players[client_id]["name"] = message["name"]
                print(f"Player {client_id} set username to: {message['name']}")

        # If this instance is a client
        if self.client:
            self.client.update()
            # Process messages from the server
            message = self.client.get_message()
            if message and message.get("action") == "start_game":
                print("Received 'start game' signal from the host.")
                self.state = "game_starting"
                self.load_game()

    def load_game(self):
        """
        Placeholder function to load the main game file.
        You should import your game.py here and start the main game loop,
        passing the network object (server or client) to it.
        """
        print("Loading game.py...")
        # Example:
        # import game
        # if self.is_host:
        #     game.run_game(network_object=self.server, is_host=True)
        # else:
        #     game.run_game(network_object=self.client, is_host=False)

        # For this demo, we'll just exit the lobby
        self.running = False

    def draw(self):
        """Draws all UI elements based on the current state."""
        self.screen.fill(WHITE)

        if self.state == "main_menu":
            self.draw_main_menu()
        elif self.state == "create_session":
            self.draw_host_lobby()
        elif self.state == "join_session_ip_input":
            self.draw_join_ip_input()
        elif self.state == "waiting_in_lobby":
            self.draw_client_waiting()
        elif self.state == "game_starting":
            self.draw_text("Game is starting...", self.font, BLACK, 400, 300)

        pygame.display.flip()

    def draw_main_menu(self):
        self.draw_text("Texas Hold'em", self.font, BLACK, 400, 100)
        pygame.draw.rect(self.screen, GRAY, self.create_button)
        self.draw_text("Create Session", self.font, BLACK, self.create_button.centerx, self.create_button.centery)
        pygame.draw.rect(self.screen, GRAY, self.join_button)
        self.draw_text("Join Session", self.font, BLACK, self.join_button.centerx, self.join_button.centery)

    def draw_host_lobby(self):
        self.draw_text("Game Lobby (Host)", self.font, BLACK, 400, 50)
        self.draw_text("Tell players to connect to your IP.", self.small_font, BLUE, 400, 100)
        self.draw_text("(Find your IPv4 Address in Network Settings)", self.small_font, BLUE, 400, 130)
        self.draw_text(f"Port: {PORT}", self.small_font, BLUE, 400, 160)

        # Display list of connected players
        y_offset = 220
        self.draw_text("Connected Players:", self.small_font, BLACK, 400, y_offset)
        y_offset += 40
        for i, player_data in enumerate(self.connected_players.values()):
            player_text = f"Player {i + 1}: {player_data['name']} (IP: {player_data['ip']})"
            self.draw_text(player_text, self.small_font, BLACK, 400, y_offset)
            y_offset += 40

        # Show the "Start Game" button if at least one other player has joined
        if len(self.connected_players) > 0:
            pygame.draw.rect(self.screen, GREEN, self.start_button)
            self.draw_text("Start Game", self.font, BLACK, self.start_button.centerx, self.start_button.centery)

    def draw_join_ip_input(self):
        self.draw_text("Join Session", self.font, BLACK, 400, 100)
        self.draw_text("Enter Host's IP Address:", self.small_font, BLACK, 400, 250)

        # Draw the IP input box
        color = ACTIVE_COLOR if self.ip_input_active else BLACK
        pygame.draw.rect(self.screen, color, self.ip_input_box, 2)
        input_surface = self.small_font.render(self.ip_input_text, True, BLACK)
        self.screen.blit(input_surface, (self.ip_input_box.x + 10, self.ip_input_box.y + 5))

        self.draw_text(f"Port: {PORT} (Fixed)", self.small_font, GRAY, 400, 360)
        self.draw_text("Press Enter to Join", self.small_font, BLACK, 400, 420)

    def draw_client_waiting(self):
        self.draw_text("Connected to Lobby", self.font, BLACK, 400, 250)
        self.draw_text("Waiting for the host to start the game...", self.small_font, GRAY, 400, 320)

    def draw_text(self, text, font, color, x, y):
        """A helper function to draw centered text on the screen."""
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(x, y))
        self.screen.blit(text_surface, text_rect)


# --- Program Entry Point ---
if __name__ == "__main__":
    lobby = Lobby()
    lobby.run()
