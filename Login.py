import pygame as g
import pygame_gui as gui

os_env_set = False
import os

os.environ["SDL_IME_SHOW_UI"] = "1"

class Login:
    def __init__(self, screen, manager):
        self.screen = screen
        self.manager = manager
        self.clock = g.time.Clock()
        self.running = True
        self.currentPlayer = None

        self.confirm_button = gui.elements.UIButton(
            relative_rect=g.Rect(0, 0, 0, 0),
            text="enter_lobby",
            manager=self.manager,
            object_id="#login_btn_big"
        )

        self.language_button = gui.elements.UIButton(
            relative_rect=g.Rect(10, 10, 90, 36),
            text="英语",
            manager=self.manager,
            object_id="#login_lang"
        )

        self.info_label = gui.elements.UILabel(
            relative_rect=g.Rect(0, 0, 0, 0),
            manager=self.manager,
            text="",
            object_id="#login_info_mid"
        )

        self._w, self._h = self.screen.get_size()
        self._relayout()

    def _relayout(self):
        w, h = self.screen.get_size()
        cx = w // 2

        int(w * 0.36)
        int(h * 0.08)
        title_y = int(h * 0.18)

        info_w = int(w * 0.46)
        info_h = int(h * 0.06)
        info_y = title_y + int(h * 0.11)

        btn_w = int(w * 0.20)
        btn_h = max(44, int(h * 0.08))
        btn_y = info_y + int(h * 0.12)

        self.info_label.set_relative_position((cx - info_w // 2, info_y))
        self.info_label.set_dimensions((info_w, info_h))

        self.confirm_button.set_relative_position((cx - btn_w // 2, btn_y))
        self.confirm_button.set_dimensions((btn_w, btn_h))

        self.language_button.set_relative_position((10, 10))
        self.language_button.set_dimensions((max(90, int(w * 0.10)), max(36, int(h * 0.06))))

        self._w, self._h = w, h

    def handle_events(self):
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT"

            if event.type == g.VIDEORESIZE:
                g.display.set_mode((event.w, event.h), g.RESIZABLE)
                if (event.w, event.h) != (self._w, self._h):
                    self._relayout()

            self.manager.process_events(event)

            if event.type == g.KEYDOWN and event.key == g.K_RETURN:
                return "STATE_LOBBY"

            if event.type == gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.confirm_button:
                    return "STATE_LOBBY"
                elif event.ui_element == self.language_button:
                    if self.manager.get_locale() == "zh":
                        self.manager.set_locale("en")
                        self.language_button.set_text("Chinese")
                    else:
                        self.manager.set_locale("zh")
                        self.language_button.set_text("英语")

        return None

    def draw(self):
        self.screen.fill((255, 255, 255))
        dt = self.clock.tick(60) / 1000.0
        self.manager.update(dt)
        self.manager.draw_ui(self.screen)
        g.display.flip()

    def run(self):
        while self.running:
            next_state = self.handle_events()
            if next_state:
                return next_state
            self.draw()
        return "STATE_QUIT"
