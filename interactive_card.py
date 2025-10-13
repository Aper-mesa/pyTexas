# --- START OF FILE interactive_card.py ---

import moderngl
import numpy as np
import pygame


class InteractiveCard:
    def __init__(self, ctx: moderngl.Context, screen_size: tuple):
        self.ctx = ctx
        self.screen_width, self.screen_height = screen_size

        # --- 着色器代码 ---
        self.vertex_shader_source = """
        #version 330
        uniform float u_bounce_time;
        uniform float u_bounce_amplitude;
        uniform float u_bounce_damping;
        uniform float u_bounce_frequency;
        uniform vec2 u_resolution;
        uniform vec2 u_mouse_pos;
        uniform float u_hover_intensity;
        in vec2 in_vert;
        void main() {
            vec2 final_vert = in_vert;
            if (u_bounce_time >= 0.0) {
                float decay = exp(-u_bounce_damping * u_bounce_time);
                float oscillation = cos(u_bounce_frequency * u_bounce_time);
                float scale = 1.0 + u_bounce_amplitude * decay * oscillation;
                final_vert *= scale;
            }
            gl_Position = vec4(final_vert, 0.0, 1.0);
            if (u_hover_intensity <= 0.0) {
                return;
            }
            vec2 vertex_screen_pos = vec2((gl_Position.x + 1.0) * 0.5 * u_resolution.x, (1.0 - gl_Position.y) * 0.5 * u_resolution.y);
            vec2 screen_center = u_resolution * 0.5;
            float mid_dist = length(vertex_screen_pos - screen_center) / length(u_resolution);
            vec2 mouse_offset = vertex_screen_pos - u_mouse_pos;
            float screen_scale = 200.0;
            float magnitude_multiplier = 1.5;
            float scale = magnitude_multiplier * (-0.03 - 0.3 * max(0.0, 0.3 - mid_dist)) * u_hover_intensity * (pow(length(mouse_offset / screen_scale), 2.0)) / (2.0 - mid_dist);
            gl_Position.w += scale;
        }
        """
        self.fragment_shader_source = """
        #version 330
        out vec4 f_color;
        void main() {
            f_color = vec4(0.9, 0.9, 0.95, 1.0);
        }
        """

        # --- 程序和 Uniforms ---
        self.prog = self.ctx.program(vertex_shader=self.vertex_shader_source,
                                     fragment_shader=self.fragment_shader_source)
        self.u_resolution = self.prog['u_resolution']
        self.u_mouse_pos = self.prog['u_mouse_pos']
        self.u_bounce_time = self.prog['u_bounce_time']
        self.u_bounce_amplitude = self.prog['u_bounce_amplitude']
        self.u_bounce_damping = self.prog['u_bounce_damping']
        self.u_bounce_frequency = self.prog['u_bounce_frequency']
        self.u_hover_intensity = self.prog['u_hover_intensity']

        # --- 几何体和 VAO ---
        self.vbo = None
        self.vao = None
        self.card_rect = None
        self.handle_resize(screen_size)  # 初始化几何体

        # --- 动画状态变量 ---
        self.was_hovering = False
        self.bounce_time = -1.0
        self.BOUNCE_DURATION = 0.5
        self.hover_intensity = 0.0
        self.HOVER_TRANSITION_SPEED = 17.0

        # 设置动画物理参数
        self.u_bounce_amplitude.value = 0.05
        self.u_bounce_damping.value = 15.0
        self.u_bounce_frequency.value = 40.0

    def handle_resize(self, screen_size: tuple):
        self.screen_width, self.screen_height = screen_size
        card_width, card_height = 200, 300
        self.card_rect = pygame.Rect((self.screen_width - card_width) / 2, (self.screen_height - card_height) / 2,
                                     card_width, card_height)

        x1 = (self.card_rect.left / self.screen_width) * 2 - 1
        y1 = 1 - (self.card_rect.top / self.screen_height) * 2
        x2 = (self.card_rect.right / self.screen_width) * 2 - 1
        y2 = 1 - (self.card_rect.bottom / self.screen_height) * 2

        quad_vertices = np.array([x1, y1, x2, y1, x1, y2, x2, y2], dtype='f4')

        if self.vbo:
            self.vbo.release()
        if self.vao:
            self.vao.release()

        self.vbo = self.ctx.buffer(quad_vertices)
        self.vao = self.ctx.simple_vertex_array(self.prog, self.vbo, 'in_vert')

    def update(self, delta_time: float):
        mouse_pos = pygame.mouse.get_pos()
        is_hovering = self.card_rect.collidepoint(mouse_pos)

        # 弹跳动画触发逻辑
        if is_hovering and not self.was_hovering:
            self.bounce_time = 0.0
        if 0.0 <= self.bounce_time < self.BOUNCE_DURATION:
            self.bounce_time += delta_time
        else:
            self.bounce_time = -1.0
        self.was_hovering = is_hovering

        # 平滑过渡逻辑
        if is_hovering:
            self.hover_intensity += self.HOVER_TRANSITION_SPEED * delta_time
        else:
            self.hover_intensity -= self.HOVER_TRANSITION_SPEED * delta_time
        self.hover_intensity = max(0.0, min(1.0, self.hover_intensity))

        # 更新 uniforms
        self.u_resolution.value = (float(self.screen_width), float(self.screen_height))
        self.u_mouse_pos.value = mouse_pos
        self.u_bounce_time.value = self.bounce_time
        self.u_hover_intensity.value = self.hover_intensity

    def render(self):
        self.vao.render(moderngl.TRIANGLE_STRIP)