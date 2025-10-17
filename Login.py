import pygame as g
import imgui
import os
import steam_wrapper as steam

from OpenGL.GL import glClear, GL_COLOR_BUFFER_BIT, GL_DEPTH_BUFFER_BIT, glClearColor

os.environ["SDL_IME_SHOW_UI"] = "1"


class Login:
    def __init__(self, screen, renderer):
        self.screen = screen
        self.renderer = renderer
        self.clock = g.time.Clock()
        self.running = True

    def _get_text(self, key):
        return key

    def handle_events(self):
        steam.run_callbacks()

        for event in g.event.get():
            self.renderer.process_event(event)

            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT"

            if event.type == g.VIDEORESIZE:
                io = imgui.get_io()
                io.display_size = event.w, event.h

            if event.type == g.KEYDOWN and event.key == g.K_RETURN:
                return "STATE_LOBBY"

        return None

    def draw_ui(self):
        imgui.new_frame()
        io = imgui.get_io()
        width, height = io.display_size
        imgui.push_style_var(imgui.STYLE_WINDOW_ROUNDING, 80.0)
        imgui.push_style_var(imgui.STYLE_WINDOW_PADDING, (20, 20))

        imgui.set_next_window_position(0,0)
        imgui.set_next_window_size(width, height)
        imgui.begin("Login", False,
                    flags=imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_MOVE | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_BACKGROUND)

        imgui.dummy(0, height / 2 - 200)
        info_text = self._get_text("login_title")
        text_width = imgui.calc_text_size(info_text).x
        imgui.set_cursor_pos_x((width - text_width) / 2)
        imgui.text(info_text)
        imgui.dummy(0, 200)

        button_width, button_height = 400, 140
        imgui.set_cursor_pos_x((width - button_width) / 2)
        imgui.push_style_color(imgui.COLOR_BUTTON, 0.2, 0.6, 0.9, 1.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_HOVERED, 0.3, 0.7, 1.0, 1.0)
        imgui.push_style_color(imgui.COLOR_BUTTON_ACTIVE, 0.1, 0.5, 0.8, 1.0)

        next_state = None
        if imgui.button(self._get_text("enter_lobby"), button_width, button_height):
            next_state = "STATE_LOBBY"

        imgui.pop_style_color(3)
        imgui.end()
        imgui.pop_style_var(2)

        imgui.set_next_window_position(50, 50)
        imgui.set_next_window_size(120, 60)
        imgui.begin("Language", False,
                    flags=imgui.WINDOW_NO_RESIZE | imgui.WINDOW_NO_COLLAPSE | imgui.WINDOW_NO_TITLE_BAR | imgui.WINDOW_NO_BACKGROUND)
        if imgui.button(self._get_text("switch_lang"), 100, 40): pass
        imgui.end()

        return next_state

    def draw(self):
        glClearColor(0, 0, 0, 0)

        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)

        next_state = self.draw_ui()

        imgui.render()
        self.renderer.render(imgui.get_draw_data())
        g.display.flip()

        return next_state

    def run(self):
        while self.running:
            next_state = self.handle_events()
            if next_state:
                return next_state

            next_state = self.draw()
            if next_state:
                return next_state

            self.clock.tick(60)

        return "STATE_QUIT"