import os
import pygame as g
import pygame_gui as gui
import player
import tools

os.environ["SDL_IME_SHOW_UI"] = "1"


class Login:
    def __init__(self, screen, manager):
        self.screen = screen
        g.display.set_caption("login_title")
        self.clock = g.time.Clock()
        self.running = True
        self.currentPlayer = None

        self.manager = manager

        w, h = self.screen.get_size()
        center_x = w // 2

        self.title_label = gui.elements.UILabel(
            relative_rect=g.Rect(center_x - 120, 60, 240, 40),
            text='login_title',
            manager=self.manager
        )

        self.username_label = gui.elements.UILabel(
            relative_rect=g.Rect(center_x - 180, 140, 120, 32),
            text="username",
            manager=self.manager
        )
        self.username_entry = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(center_x - 40, 140, 240, 32),
            manager=self.manager
        )

        self.password_label = gui.elements.UILabel(
            relative_rect=g.Rect(center_x - 180, 200, 120, 32),
            text='password',
            manager=self.manager
        )
        self.password_entry = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(center_x - 40, 200, 240, 32),
            manager=self.manager
        )
        self.password_entry.set_text_hidden(True)  # 密码模式

        self.confirm_button = gui.elements.UIButton(
            relative_rect=g.Rect(center_x - 60, 270, 120, 44),
            text='confirm_button',
            manager=self.manager
        )

        self.language_button = gui.elements.UIButton(
            relative_rect=g.Rect(0, 0, 70, 35),
            text="英语",
            manager=self.manager
        )

        self.info_label = gui.elements.UILabel(
            relative_rect=g.Rect(center_x - 180, 330, 360, 28),
            text='',
            manager=self.manager
        )

    def handle_events(self):
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT", None

            if event.type == g.KEYDOWN and event.key == g.K_TAB:
                if self.password_entry.is_focused:
                    self.password_entry.unfocus()
                    self.username_entry.focus()
                    self.username_entry.set_text(self.username_entry.get_text())
                    continue
                elif self.username_entry.is_focused:
                    self.username_entry.unfocus()
                    self.password_entry.focus()
                    self.password_entry.set_text(self.password_entry.get_text())
                    continue

            if event.type == g.KEYDOWN and event.key == g.K_RETURN:
                if self.register():
                    return 'STATE_LOBBY'

            self.manager.process_events(event)

            if event.type == gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.confirm_button:
                    if self.register():
                        return 'STATE_LOBBY'
                elif event.ui_element == self.language_button:
                    if self.manager.get_locale() == 'zh':
                        self.manager.set_locale('en')
                        self.language_button.set_text('Chinese')
                    else:
                        self.manager.set_locale('zh')
                        self.language_button.set_text('英语')

        return None, None

    def draw(self):
        self.screen.fill((255, 255, 255))
        time_delta = self.clock.tick(60) / 1000.0
        self.manager.update(time_delta)
        self.manager.draw_ui(self.screen)
        g.display.flip()

    def register(self):
        username_text = self.username_entry.get_text()
        password_text = self.password_entry.get_text()

        if not username_text or not password_text:
            self.info_label.set_text("info_empty_username_or_password")
            return False

        ip = '127.0.0.1'
        try:
            p = player.Player.create(username=username_text, password=password_text, ip=ip)
            if p:
                player.Player.storeData(p)
                self.currentPlayer = p
                return True
            else:
                return False
        except Exception as e:
            self.info_label.set_text(f"Error: {e}")
            return False

    # 保留原版接口：运行主循环
    def run(self):
        while self.running:
            next_state, data = self.handle_events()
            if next_state:
                return next_state, data
            self.draw()
        return "STATE_QUIT", None
