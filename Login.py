# -*- coding: utf-8 -*-
import pygame as g
import pygame_gui as gui
import ctypes
from ctypes import c_uint64, c_char_p
import player
import steam_bootstrap as steam  # ← 全局初始化在 main 里做过

os_env_set = False
import os

os.environ["SDL_IME_SHOW_UI"] = "1"

# 绑定我们只需要的两个函数（使用 steam_bootstrap.DLL）
_DLL = None


def _bind_steam_funcs():
    global _DLL, ISteamUser_GetSteamID, ISteamFriends_GetPersonaName
    if _DLL is not None:
        return
    _DLL = steam.DLL
    if _DLL is None:
        raise RuntimeError("Steam 未初始化。请确保在 main.py 中调用 steam.init().")

    ISteamUser_GetSteamID = _DLL.SteamAPI_ISteamUser_GetSteamID
    ISteamUser_GetSteamID.restype = c_uint64
    ISteamUser_GetSteamID.argtypes = [ctypes.c_void_p]

    ISteamFriends_GetPersonaName = _DLL.SteamAPI_ISteamFriends_GetPersonaName
    ISteamFriends_GetPersonaName.restype = c_char_p
    ISteamFriends_GetPersonaName.argtypes = [ctypes.c_void_p]


class Login:
    def __init__(self, screen, manager):
        _bind_steam_funcs()

        # Steam handles （由 steam_bootstrap.init() 提供）
        user, friends, mm, apps, utils = steam.get_handles()

        self.screen = screen
        self.manager = manager
        self.clock = g.time.Clock()
        self.running = True
        self.currentPlayer = None

        self.confirm_button = gui.elements.UIButton(
            relative_rect=g.Rect(0, 0, 0, 0),
            text="enter_lobby",
            manager=self.manager,
            object_id="#login_btn_big"  # 用于稍微放大按钮字体
        )

        # 语言按钮固定左上角
        self.language_button = gui.elements.UIButton(
            relative_rect=g.Rect(10, 10, 90, 36),  # 稍微加高
            text="英语",
            manager=self.manager,
            object_id="#login_lang"
        )

        self.info_label = gui.elements.UILabel(
            relative_rect=g.Rect(0, 0, 0, 0),
            text="正在获取 Steam 用户信息...",
            manager=self.manager,
            object_id="#login_info_mid"  # 字体略放大
        )

        # 获取当前 Steam 用户
        sid = ISteamUser_GetSteamID(user)
        name = (ISteamFriends_GetPersonaName(friends) or b"Unknown").decode("utf-8", "ignore")

        # 创建 Player 实例
        self.currentPlayer = player.Player.create(sid, name)
        self.info_label.set_text(f"{name} (SteamID: {sid})")

        # 首次布局
        self._w, self._h = self.screen.get_size()
        self._relayout()

    # -------------------- 布局 --------------------
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
        btn_h = max(44, int(h * 0.08))  # 比原来 40 稍微大一圈
        btn_y = info_y + int(h * 0.12)

        self.info_label.set_relative_position((cx - info_w // 2, info_y))
        self.info_label.set_dimensions((info_w, info_h))

        self.confirm_button.set_relative_position((cx - btn_w // 2, btn_y))
        self.confirm_button.set_dimensions((btn_w, btn_h))

        self.language_button.set_relative_position((10, 10))
        self.language_button.set_dimensions((max(90, int(w * 0.10)), max(36, int(h * 0.06))))

        self._w, self._h = w, h

    # -------------------- 事件逻辑 --------------------
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
