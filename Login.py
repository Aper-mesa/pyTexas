import pygame as g
import sys
import player

# --- Constants ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
COLOR_INACTIVE = g.Color('lightskyblue3')
COLOR_ACTIVE = g.Color('dodgerblue2')


class Login:
    """A class to manage the registration screen UI and logic."""

    def __init__(self):
        # Initialize g
        g.init()
        self.screen = g.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        g.display.set_caption("Registration")
        self.clock = g.time.Clock()
        self.font = g.font.Font(None, 32)  # Use the default font

        # --- UI Elements ---
        # Define rectangles for the input boxes
        self.username_box = g.Rect(300, 150, 200, 32)
        self.password_box = g.Rect(300, 250, 200, 32)

        # Define rectangle for the confirm button
        self.confirm_button = g.Rect(350, 350, 100, 50)

        # --- State Variables ---
        self.username_text = ''
        self.password_text = ''
        self.username_active = False
        self.password_active = False
        self.running = True

    def handle_events(self):
        """Process all events from the event queue."""
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False

            # --- Mouse Click Events ---
            if event.type == g.MOUSEBUTTONDOWN:
                # Check if the user clicked on the username input box
                if self.username_box.collidepoint(event.pos):
                    self.username_active = True
                    self.password_active = False
                # Check if the user clicked on the password input box
                elif self.password_box.collidepoint(event.pos):
                    self.username_active = False
                    self.password_active = True
                # Check if the user clicked the confirm button
                elif self.confirm_button.collidepoint(event.pos):
                    # Action for the button: print to console
                    print(f"Registration confirmed! Username: '{self.username_text}'")
                    self.register()
                else:
                    # Deactivate both boxes if clicked elsewhere
                    self.username_active = False
                    self.password_active = False

            # --- Keyboard Input Events ---
            if event.type == g.KEYDOWN:
                if self.username_active:
                    if event.key == g.K_BACKSPACE:
                        self.username_text = self.username_text[:-1]
                    else:
                        self.username_text += event.unicode
                elif self.password_active:
                    if event.key == g.K_BACKSPACE:
                        self.password_text = self.password_text[:-1]
                    else:
                        self.password_text += event.unicode

    def draw(self):
        """Draw all elements to the screen."""
        # Fill the background with white
        self.screen.fill(WHITE)

        # --- Draw Labels ---
        username_label = self.font.render("Username:", True, BLACK)
        self.screen.blit(username_label, (self.username_box.x - 120, self.username_box.y + 5))

        password_label = self.font.render("Password:", True, BLACK)
        self.screen.blit(password_label, (self.password_box.x - 120, self.password_box.y + 5))

        # --- Draw Input Boxes ---
        # Change the color of the box when it is active
        username_color = COLOR_ACTIVE if self.username_active else COLOR_INACTIVE
        password_color = COLOR_ACTIVE if self.password_active else COLOR_INACTIVE

        # Draw the username box and render the text inside it
        g.draw.rect(self.screen, username_color, self.username_box, 2)
        username_surface = self.font.render(self.username_text, True, BLACK)
        self.screen.blit(username_surface, (self.username_box.x + 5, self.username_box.y + 5))

        # Draw the password box and render the text as asterisks for privacy
        g.draw.rect(self.screen, password_color, self.password_box, 2)
        password_surface = self.font.render('*' * len(self.password_text), True, BLACK)
        self.screen.blit(password_surface, (self.password_box.x + 5, self.password_box.y + 5))

        # --- Draw Confirm Button ---
        g.draw.rect(self.screen, GRAY, self.confirm_button)
        confirm_text = self.font.render("Confirm", True, BLACK)
        # Center the text inside the button
        text_rect = confirm_text.get_rect(center=self.confirm_button.center)
        self.screen.blit(confirm_text, text_rect)

        # Update the full display surface to the screen
        g.display.flip()

    def register(self):
        """Register the username and password."""
        p = player.Player.create(username=self.username_text, password=self.password_text)
        if p:
            player.Player.storeData(p)
        else:
            print("Password is incorrect, retry password or create a new account")

    def run(self):
        """The main loop of the registration screen."""
        while self.running:
            self.handle_events()
            self.draw()
            self.clock.tick(60)  # FPS

        g.quit()
        sys.exit()

# --- Main Execution ---
if __name__ == "__main__":
    reg_screen = Login()
    reg_screen.run()