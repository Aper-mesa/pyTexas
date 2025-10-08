import ctypes
import json
import os
from ctypes import c_bool, c_void_p, c_char_p, c_uint64, c_int32
from pathlib import Path

import pygame as g
import pygame_gui as gui

import player

os.environ["SDL_IME_SHOW_UI"] = "1"


def _load_steam_identity():
    lib = ctypes.WinDLL(str(Path(__file__).resolve().parent / "steam_api64.dll"))

    SteamAPI_Init = getattr(lib, "SteamAPI_InitSafe", None) or lib.SteamAPI_Init
    SteamAPI_Init.restype = c_bool

    SteamAPI_Shutdown = lib.SteamAPI_Shutdown
    SteamAPI_Shutdown.restype = None

    SteamInternal_CreateInterface = lib.SteamInternal_CreateInterface
    SteamInternal_CreateInterface.restype = c_void_p
    SteamInternal_CreateInterface.argtypes = [c_char_p]

    SteamAPI_GetHSteamUser = lib.SteamAPI_GetHSteamUser
    SteamAPI_GetHSteamUser.restype = c_int32
    SteamAPI_GetHSteamPipe = lib.SteamAPI_GetHSteamPipe
    SteamAPI_GetHSteamPipe.restype = c_int32

    # 通过 SteamClient 拿到子接口
    GetISteamUser = lib.SteamAPI_ISteamClient_GetISteamUser
    GetISteamUser.restype = c_void_p
    GetISteamUser.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

    GetISteamFriends = lib.SteamAPI_ISteamClient_GetISteamFriends
    GetISteamFriends.restype = c_void_p
    GetISteamFriends.argtypes = [c_void_p, c_int32, c_int32, c_char_p]

    # 具体方法
    ISteamUser_GetSteamID = lib.SteamAPI_ISteamUser_GetSteamID
    ISteamUser_GetSteamID.restype = c_uint64
    ISteamUser_GetSteamID.argtypes = [c_void_p]

    ISteamFriends_GetPersonaName = lib.SteamAPI_ISteamFriends_GetPersonaName
    ISteamFriends_GetPersonaName.restype = c_char_p
    ISteamFriends_GetPersonaName.argtypes = [c_void_p]

    SteamAPI_Init()

    try:
        steam_client = c_void_p(SteamInternal_CreateInterface(b"SteamClient023"))

        hUser = SteamAPI_GetHSteamUser()
        hPipe = SteamAPI_GetHSteamPipe()

        user = GetISteamUser(steam_client, hUser, hPipe, b"SteamUser021")
        friends = GetISteamFriends(steam_client, hUser, hPipe, b"SteamFriends015")

        steam_id = ISteamUser_GetSteamID(user)
        persona = ISteamFriends_GetPersonaName(friends) or b"Unknown"
        persona_name = persona.decode("utf-8", "ignore")
        return str(steam_id), persona_name
    finally:
        SteamAPI_Shutdown()

class Login:
    def __init__(self, screen, manager):
        self.screen = screen
        self.clock = g.time.Clock()
        self.running = True
        self.currentPlayer = None

        self.manager = manager

        w, h = self.screen.get_size()
        center_x = w // 2

        self.password_entry = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(center_x - 40, 200, 240, 32),
            manager=self.manager
        )
        self.password_entry.set_text_hidden(True)  # 密码模式

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

        self.confirm_button = gui.elements.UIButton(
            relative_rect=g.Rect(center_x - 60, 270, 120, 44),
            text='enter_lobby',
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
        self.load_saved_username()

        self.currentPlayer = None
        sid, name = _load_steam_identity()
        self.currentPlayer = player.Player.create_from_steam(sid, name)
        self.info_label.set_text(f"{name} (SteamID: {sid})")

    def load_saved_username(self):
        data_directory = 'data'
        if os.path.exists(data_directory):
            # 获取data目录下的第一个json文件
            for filename in os.listdir(data_directory):
                if filename.endswith('.json'):
                    try:
                        # 读取json文件
                        with open(os.path.join(data_directory, filename), 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            # 如果有username键，设置输入框的值
                            if 'username' in data:
                                print("username: " + data['username'])
                                self.username_entry.set_text(data['username'])
                            break  # 读取第一个文件后退出
                    except Exception as e:
                        self.info_label.set_text(f"Error loading user data: {e}")

    def handle_events(self):
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT"

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
        return None

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
            next_state = self.handle_events()
            if next_state:
                return next_state
            self.draw()
        return "STATE_QUIT"
