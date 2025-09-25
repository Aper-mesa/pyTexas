import os

import pygame as g

import player
import tools

os.environ["SDL_IME_SHOW_UI"] = "1"

# --- Constants ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (200, 200, 200)
COLOR_INACTIVE = g.Color('lightskyblue3')
COLOR_ACTIVE = g.Color('dodgerblue2')


class Login:
    def __init__(self, screen):
        self.screen = screen
        self.clock = g.time.Clock()

        font_path = tools.resource_path('msyh.ttc')
        self.font = g.font.Font(font_path, 24)

        # --- UI Elements ---
        self.username_box = g.Rect(300, 150, 200, 32)
        self.password_box = g.Rect(300, 250, 200, 32)
        self.confirm_button = g.Rect(350, 350, 100, 50)

        # --- State ---
        self.username_text = ''
        self.password_text = ''
        self.username_editing_text = ''
        self.password_editing_text = ''

        self.username_active = False
        self.password_active = False
        self.running = True

        self.currentPlayer = None

    def handle_events(self):
        for event in g.event.get():
            if event.type == g.QUIT:
                self.running = False
                return "STATE_QUIT", None

            # --- 鼠标点击事件 ---
            if event.type == g.MOUSEBUTTONDOWN:
                if self.username_box.collidepoint(event.pos):
                    self.username_active = True
                    self.password_active = False
                    g.key.set_text_input_rect(self.username_box)
                elif self.password_box.collidepoint(event.pos):
                    self.username_active = False
                    self.password_active = True
                    g.key.set_text_input_rect(self.password_box)
                elif self.confirm_button.collidepoint(event.pos):
                    if self.register():
                        return 'STATE_LOBBY', self.username_text
                else:  # 点击其他地方
                    self.username_active = False
                    self.password_active = False

                # 开关文本输入模式
                if self.username_active or self.password_active:
                    g.key.start_text_input()
                else:
                    g.key.stop_text_input()

            # --- 4. 核心改动：处理 TEXTEDITING (拼音) ---
            elif event.type == g.TEXTEDITING:
                if self.username_active:
                    self.username_editing_text = event.text
                elif self.password_active:
                    # 密码框不显示拼音，保护隐私
                    self.password_editing_text = ''

                    # --- 5. 核心改动：处理 TEXTINPUT (最终汉字) ---
            elif event.type == g.TEXTINPUT:
                if self.username_active:
                    self.username_editing_text = ''  # 清空拼音
                    self.username_text += event.text
                elif self.password_active:
                    self.password_editing_text = ''  # 清空拼音
                    self.password_text += event.text

            # --- 6. 核心改动：KEYDOWN 只处理功能键 ---
            elif event.type == g.KEYDOWN:
                if event.key == g.K_BACKSPACE:
                    if self.username_active:
                        if self.username_editing_text:  # 优先删除拼音
                            self.username_editing_text = ''
                        else:
                            self.username_text = self.username_text[:-1]
                    elif self.password_active:
                        self.password_text = self.password_text[:-1]

        return None, None

    def draw(self):
        self.screen.fill(WHITE)
        # --- 标签 ---
        username_label = self.font.render("Username:", True, BLACK)
        self.screen.blit(username_label, (self.username_box.x - 120, self.username_box.y + 5))
        password_label = self.font.render("Password:", True, BLACK)
        self.screen.blit(password_label, (self.password_box.x - 120, self.password_box.y + 5))

        # --- 用户名输入框 (带拼音显示) ---
        username_color = COLOR_ACTIVE if self.username_active else COLOR_INACTIVE
        g.draw.rect(self.screen, username_color, self.username_box, 2)
        # 先渲染已确定的文本
        username_surface = self.font.render(self.username_text, True, BLACK)
        self.screen.blit(username_surface, (self.username_box.x + 5, self.username_box.y + 5))
        # 7. 渲染正在输入的、带下划线的拼音
        editing_surface = self.font.render(self.username_editing_text, True, BLACK)
        # 将拼音渲染在已确定文本的后面
        self.screen.blit(editing_surface,
                         (self.username_box.x + 5 + username_surface.get_width(), self.username_box.y + 5))

        # --- 密码输入框 ---
        password_color = COLOR_ACTIVE if self.password_active else COLOR_INACTIVE
        g.draw.rect(self.screen, password_color, self.password_box, 2)
        password_surface = self.font.render('*' * len(self.password_text), True, BLACK)
        self.screen.blit(password_surface, (self.password_box.x + 5, self.password_box.y + 5))

        # --- 按钮 ---
        g.draw.rect(self.screen, GRAY, self.confirm_button)
        confirm_text = self.font.render("Confirm", True, BLACK)
        self.screen.blit(confirm_text, confirm_text.get_rect(center=self.confirm_button.center))

        g.display.flip()

    def register(self):
        ip = '127.0.0.1'
        p = player.Player.create(username=self.username_text, password=self.password_text, ip=ip)
        if p:
            player.Player.storeData(p)
            self.currentPlayer = p
            return True
        else:
            print("Password is incorrect, retry password or create a new account")
            return False

    def run(self):
        while self.running:
            next_state, data = self.handle_events()
            if next_state:
                g.key.stop_text_input()
                return next_state, data
            self.draw()
            self.clock.tick(60)
        g.key.stop_text_input()
        return "STATE_QUIT", None
