import re
import threading

import pygame as g
from pygame_networking import Server

import player

# --- Constants ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
COLOR_INACTIVE = g.Color('lightskyblue3')
COLOR_ACTIVE = g.Color('dodgerblue2')

server = Server()


class Lobby:
    def __init__(self, screen, player):
        self.tick = 0
        self.players = []
        self.localPlayer = player
        self.screen = screen
        self.clock = g.time.Clock()
        self.font = g.font.Font(None, 32)

        # --- UI Elements ---
        self.create_session_button = g.Rect(250, 150, 300, 50)
        self.join_session_button = g.Rect(250, 250, 300, 50)
        self.ip_box = g.Rect(250, 350, 300, 50)
        self.store_box = g.Rect(250, 450, 100, 50)
        self.ip_text = ''
        self.ip_active = False

        self.startButton = g.Rect(250, 350, 300, 50)

        # --- State Variables ---
        self.running = True
        self.lobby_state = "main"  # "main" or "hosting"

    def handle_events(self):
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT", None

            if event.type == g.KEYDOWN:
                if self.ip_active:
                    if event.key == g.K_BACKSPACE:
                        self.ip_text = self.ip_text[:-1]
                    else:
                        self.ip_text += event.unicode

            if self.lobby_state == "main":  # Only handle buttons in the main state
                if event.type == g.MOUSEBUTTONDOWN:
                    if self.join_session_button.collidepoint(event.pos):
                        self.joinSession()
                    elif self.create_session_button.collidepoint(event.pos):
                        self.createSession()
                    elif self.ip_box.collidepoint(event.pos):
                        self.ip_active = True
                    elif self.store_box.collidepoint(event.pos):
                        self.storeIP()
                    else:
                        self.ip_active = False
            elif self.lobby_state == 'hosting':
                if event.type == g.MOUSEBUTTONDOWN:
                    if self.startButton.collidepoint(event.pos):
                        self.newGame()

        return None, None

    def draw_main_lobby(self):
        """Draws the initial lobby screen with buttons."""
        g.draw.rect(self.screen, GRAY, self.create_session_button)
        create_text = self.font.render("Create Session", True, BLACK)
        self.screen.blit(create_text, create_text.get_rect(center=self.create_session_button.center))

        g.draw.rect(self.screen, GRAY, self.join_session_button)
        join_text = self.font.render("Join Session", True, BLACK)
        self.screen.blit(join_text, join_text.get_rect(center=self.join_session_button.center))

        g.draw.rect(self.screen, GRAY, self.store_box)
        store_text = self.font.render("Store IP", True, BLACK)
        self.screen.blit(store_text, store_text.get_rect(center=self.store_box.center))

        ip_color = COLOR_ACTIVE if self.ip_active else COLOR_INACTIVE
        g.draw.rect(self.screen, ip_color, self.ip_box, 2)
        ip_surface = self.font.render(self.ip_text, True, BLACK)
        self.screen.blit(ip_surface, (self.ip_box.x + 5, self.ip_box.y + 5))

    def draw_hosting_lobby(self):
        """Draws the screen after the host has created a session."""
        host_ip_text = self.font.render(f"Server is running!", True, BLACK)
        ip_info_text = self.font.render(f"Your IP is: {self.ip_text}", True, BLACK)
        wait_text = self.font.render("Waiting for players to join...", True, GRAY)

        g.draw.rect(self.screen, GRAY, self.startButton)
        start_text = self.font.render('Start', True, BLACK)
        text_rect = start_text.get_rect(center=self.startButton.center)
        self.screen.blit(start_text, text_rect)

        self.screen.blit(host_ip_text, (250, 150))
        self.screen.blit(ip_info_text, (250, 200))
        self.screen.blit(wait_text, (250, 300))

    def draw(self):
        self.screen.fill(WHITE)
        if self.lobby_state == "main":
            self.draw_main_lobby()
        elif self.lobby_state == "hosting":
            self.draw_hosting_lobby()
        g.display.flip()

    def _start_server(self):
        try:
            # 若房主输入了新的IP地址加入，则更新存储的用户IP
            if self.localPlayer.getIP != self.ip_text:
                self.localPlayer.setIP(self.ip_text)
            server.serve((self.ip_text, 3333))
        except Exception as e:
            print(f"Error starting server thread: {e}")

    def createSession(self):
        # 房主不输入IP地址就默认调用用户数据中存储的地址
        if self.ip_text == '' and self.localPlayer.getIP != '127.0.0.1':
            self.ip_text = self.localPlayer.getIP()
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
        self.lobby_state = "hosting"

    def joinSession(self):
        if self.ip_text == '':
            print('Input IP address to join')
            return
        server.connect((self.ip_text, 3333))
        if server.connected:
            # 客户端进房间以后把自己的用户信息发送给服务器
            server.sync(self.localPlayer.ip, self.localPlayer.getOnlineData())

    def newGame(self):
        print("New game started.")
        return 'STATE_GAME', self.players

    def run(self):
        while self.running:
            next_state, data = self.handle_events()
            if next_state:
                return next_state, data

            # 服务器逻辑
            if self.lobby_state == 'hosting':
                # 0.5秒执行一次
                if self.tick < 30:
                    self.tick += 1
                else:
                    data = str(server.connections)
                    ip_addresses = re.findall(r"raddr=\('([\d\.]+)',", data)
                    self.createUsers(ip_addresses)
                    self.tick = 0

            self.draw()
            # 游戏帧率，60帧畅玩3A大作
            self.clock.tick(60)

        return "STATE_QUIT", None

    def createUsers(self, ip_addresses):
        existing_ips = {p.ip for p in self.players}

        for ip in ip_addresses:
            try:
                if ip not in existing_ips:
                    player_data_string = server.get(ip)
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
