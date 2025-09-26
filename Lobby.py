import re
import threading

import pygame as g
from pygame_networking import Server

import player

import pygame_gui as gui


class Lobby:
    def __init__(self, screen, manager, localPlayer):
        self.server = Server()
        self.tick = 0
        self.players = []
        self.localPlayer = localPlayer
        self.screen = screen
        self.clock = g.time.Clock()

        self.manager = manager

        self.ip_text = ''
        self.ip_active = False
        self.minBetText = '1'
        self.initBetText = '50'
        self.minBetActive = False
        self.initBetActive = False
        self.running = True
        self.lobby_state = "main"

        self.ui_btn_create = gui.elements.UIButton(
            relative_rect=g.Rect(250, 150, 300, 50),
            text="lang.create_session",
            manager=self.manager
        )
        self.ui_btn_join = gui.elements.UIButton(
            relative_rect=g.Rect(250, 250, 300, 50),
            text="lang.join_session",
            manager=self.manager
        )
        self.ui_ip_entry = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(250, 350, 300, 50),
            manager=self.manager
        )
        self.ui_btn_store_ip = gui.elements.UIButton(
            relative_rect=g.Rect(250, 450, 100, 50),
            text="lang.save_ip",
            manager=self.manager
        )

        # ---- Hosting 界面控件 ----
        self.ui_label_host_running = gui.elements.UILabel(
            relative_rect=g.Rect(150, 150, 400, 32),
            text="lang.server_running",
            manager=self.manager
        )
        self.ui_label_ip_info = gui.elements.UILabel(
            relative_rect=g.Rect(150, 200, 500, 32),
            text="lang.your_ip",
            manager=self.manager
        )
        self.ui_label_wait = gui.elements.UILabel(
            relative_rect=g.Rect(150, 250, 500, 32),
            text="lang.wait_join",
            manager=self.manager
        )
        self.ui_btn_start = gui.elements.UIButton(
            relative_rect=g.Rect(250, 300, 300, 50),
            text="lang.start",
            manager=self.manager
        )

        self.ui_label_minbet = gui.elements.UILabel(
            relative_rect=g.Rect(180, 400, 100, 30),
            text="lang.min_bet",
            manager=self.manager
        )
        self.ui_entry_minbet = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(300, 400, 100, 30),
            manager=self.manager
        )
        self.ui_entry_minbet.set_text(self.minBetText)

        self.ui_label_initbet = gui.elements.UILabel(
            relative_rect=g.Rect(180, 450, 100, 30),
            text="lang.init_bet",
            manager=self.manager
        )
        self.ui_entry_initbet = gui.elements.UITextEntryLine(
            relative_rect=g.Rect(300, 450, 100, 30),
            manager=self.manager
        )
        self.ui_entry_initbet.set_text(self.initBetText)

        self.ui_label_joining = gui.elements.UILabel(
            relative_rect=g.Rect(250, 150, 400, 32),
            text="lang.wait_host",
            manager=self.manager
        )

        self._set_state_visibility("main")

    def _set_state_visibility(self, state: str):
        self.lobby_state = state

        def show(elems):
            for e in elems: e.show()

        def hide(elems):
            for e in elems: e.hide()

        main_elems = [
            self.ui_btn_create, self.ui_btn_join, self.ui_ip_entry, self.ui_btn_store_ip
        ]
        hosting_elems = [
            self.ui_label_host_running, self.ui_label_ip_info, self.ui_label_wait,
            self.ui_btn_start, self.ui_label_minbet, self.ui_entry_minbet,
            self.ui_label_initbet, self.ui_entry_initbet
        ]
        joining_elems = [self.ui_label_joining]

        if state == "main":
            show(main_elems);
            hide(hosting_elems);
            hide(joining_elems)
        elif state == "hosting":
            hide(main_elems);
            show(hosting_elems);
            hide(joining_elems)
        elif state == "joining":
            hide(main_elems);
            hide(hosting_elems);
            show(joining_elems)

        self.ui_label_ip_info.set_text(self.ip_text)

    def handle_events(self):
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT", None

            if event.type == gui.UI_TEXT_ENTRY_CHANGED:
                if event.ui_element == self.ui_ip_entry:
                    self.ip_text = self.ui_ip_entry.get_text()
                elif event.ui_element == self.ui_entry_minbet:
                    self.minBetText = self.ui_entry_minbet.get_text()
                elif event.ui_element == self.ui_entry_initbet:
                    self.initBetText = self.ui_entry_initbet.get_text()

            if event.type == gui.UI_BUTTON_PRESSED:
                if event.ui_element == self.ui_btn_join and self.lobby_state == "main":
                    self.joinSession()
                elif event.ui_element == self.ui_btn_create and self.lobby_state == "main":
                    self.createSession()
                elif event.ui_element == self.ui_btn_store_ip and self.lobby_state == "main":
                    self.storeIP()
                elif event.ui_element == self.ui_btn_start and self.lobby_state == "hosting":
                    return self.newGame()

            self.manager.process_events(event)

        return None, None

    def draw(self):
        self.screen.fill(g.Color("white"))
        if self.lobby_state == "hosting":
            self.ui_label_ip_info.set_text(self.ip_text)

        time_delta = self.clock.tick(60) / 1000.0
        self.manager.update(time_delta)
        self.manager.draw_ui(self.screen)
        g.display.flip()

    def _start_server(self):
        try:
            # 若房主输入了新的IP地址加入，则更新存储的用户IP
            if self.localPlayer.getIP != self.ip_text:
                self.localPlayer.setIP(self.ip_text)
            self.server.serve((self.ip_text, 3333))
        except Exception as e:
            print(f"Error starting server thread: {e}")

    def createSession(self):
        # 房主不输入IP地址就默认调用用户数据中存储的地址
        if self.ip_text == '' and self.localPlayer.getIP != '127.0.0.1':
            self.ip_text = self.localPlayer.getIP()
            self.ui_ip_entry.set_text(self.ip_text)
        # 若房主的IP地址未初始化，则要求房主手动输入IP地址
        elif self.ip_text == '' and self.localPlayer.getIP == '127.0.0.1':
            print('Input a valid IP to host')
            return
        # 上面两个如果都没执行说明房主手动输入了IP
        server_thread = threading.Thread(target=self._start_server, daemon=True)
        server_thread.start()
        # 房主先把自己放进数组
        self.players.append(
            player.PlayerInGame(self.localPlayer.username, self.localPlayer.ip, self.localPlayer.money))
        self._set_state_visibility("hosting")

    def joinSession(self):
        if self.ip_text == '':
            print('Input IP address to join')
            return
        self.server.connect((self.ip_text, 3333))
        if self.server.connected:
            # 客户端进房间以后把自己的用户信息发送给服务器
            self.server.sync(self.localPlayer.ip, self.localPlayer.getOnlineData())
            self._set_state_visibility('joining')

    def newGame(self):
        print("New game started.")
        return 'STATE_GAME', [self.players, self.minBetText, self.initBetText, self.server]

    def run(self):
        while self.running:
            next_state, data = self.handle_events()
            if next_state:
                g.key.stop_text_input()
                return next_state, data

            # 服务器逻辑
            if self.lobby_state == 'hosting':
                # 0.5秒执行一次
                if self.tick < 30:
                    self.tick += 1
                else:
                    data = str(self.server.connections)
                    ip_addresses = re.findall(r"raddr=\('([\d.]+)',", data)
                    self.createUsers(ip_addresses)
                    self.tick = 0

            self.draw()
            # 游戏帧率，60帧
            self.clock.tick(60)

        return "STATE_QUIT", None

    def createUsers(self, ip_addresses):
        existing_ips = {p.ip for p in self.players}

        for ip in ip_addresses:
            try:
                if ip not in existing_ips:
                    player_data_string = self.server.get(ip)
                    data_parts = player_data_string.split(',')
                    username = data_parts[0]
                    money = data_parts[2]

                    new_player = player.PlayerInGame(
                        username=username,
                        ip=ip,
                        money=money
                    )
                    self.players.append(new_player)
                    for p in self.players:
                        print(p.username)
                        print(p.ip)
                        print(p.money)
                    existing_ips.add(ip)

            except (IndexError, TypeError) as e:
                print(f"处理IP {ip} 时出错: {e}")

    def storeIP(self):
        self.localPlayer.setIP(self.ip_text)
