import os
import pygame as g
import pygame_gui as gui
import player

os.environ["SDL_IME_SHOW_UI"] = "1"   # 开启IME候选框显示（需要SDL/系统支持）

class Login:
    def __init__(self, screen):
        self.screen = screen
        g.display.set_caption('pyTexas Login')
        self.clock = g.time.Clock()
        self.running = True
        self.currentPlayer = None

        self.manager = gui.UIManager((self.screen.get_size()), starting_language='zh', theme_path='theme.json')  # 如需中文字体，可加载主题或自定义字体

        w, h = self.screen.get_size()
        center_x = w // 2

        self.title_label = gui.elements.UILabel(
            relative_rect=g.Rect(center_x - 120, 60, 240, 40),
            text='pyTexas Login',
            manager=self.manager
        )

        self.username_label = gui.elements.UILabel(
            relative_rect=g.Rect(center_x - 180, 140, 120, 32),
            text='Username',
            manager=self.manager
        )
        self.username_entry = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(center_x - 40, 140, 240, 32),
            manager=self.manager
        )

        self.password_label = gui.elements.UILabel(
            relative_rect=g.Rect(center_x - 180, 200, 120, 32),
            text='Password',
            manager=self.manager
        )
        self.password_entry = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(center_x - 40, 200, 240, 32),
            manager=self.manager
        )
        self.password_entry.set_text_hidden(True)  # 密码模式

        self.confirm_button = gui.elements.UIButton(
            relative_rect=g.Rect(center_x - 60, 270, 120, 44),
            text='Confirm',
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
                    return 'STATE_LOBBY', self.username_entry.get_text()

            self.manager.process_events(event)

            if event.type == gui.UI_BUTTON_PRESSED and event.ui_element == self.confirm_button:
                if self.register():
                    return 'STATE_LOBBY', self.username_entry.get_text()

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
            self.info_label.set_text("Username/Password 不能为空")
            return False

        ip = '127.0.0.1'
        try:
            p = player.Player.create(username=username_text, password=password_text, ip=ip)
            if p:
                player.Player.storeData(p)
                self.currentPlayer = p
                self.info_label.set_text("Login success!")
                return True
            else:
                self.info_label.set_text("Password incorrect. Retry or create new account.")
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
