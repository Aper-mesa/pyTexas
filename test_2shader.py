import pygame
import moderngl
import numpy as np

# Pygame 和 ModernGL 初始化
pygame.init()
screen_width, screen_height = 800, 600
pygame.display.set_mode((screen_width, screen_height), pygame.OPENGL | pygame.DOUBLEBUF, vsync=1)
ctx = moderngl.create_context()

# --- 着色器代码 (已更新为平滑过渡) ---
vertex_shader_source = """
#version 330

// 动画 Uniforms
uniform float u_bounce_time;
uniform float u_bounce_amplitude;
uniform float u_bounce_damping;
uniform float u_bounce_frequency;

// 其他 Uniforms
uniform vec2 u_resolution;
uniform vec2 u_mouse_pos;
// --- 修改点: 用一个浮点数 intensity 代替了布尔值的 hovering ---
uniform float u_hover_intensity; // (0.0 -> 1.0)

in vec2 in_vert;

void main() {
    vec2 final_vert = in_vert;

    // 阻尼振荡动画逻辑 (不变)
    if (u_bounce_time >= 0.0) {
        float decay = exp(-u_bounce_damping * u_bounce_time);
        float oscillation = cos(u_bounce_frequency * u_bounce_time);
        float scale = 1.0 + u_bounce_amplitude * decay * oscillation;
        final_vert *= scale;
    }

    gl_Position = vec4(final_vert, 0.0, 1.0);

    // --- 修改点: 如果强度为0，则不计算倾斜 ---
    if (u_hover_intensity <= 0.0) {
        return;
    }

    // --- 倾斜效果逻辑 ---
    vec2 vertex_screen_pos = vec2(
        (gl_Position.x + 1.0) * 0.5 * u_resolution.x,
        (1.0 - gl_Position.y) * 0.5 * u_resolution.y
    );
    vec2 screen_center = u_resolution * 0.5;
    float mid_dist = length(vertex_screen_pos - screen_center) / length(u_resolution);
    vec2 mouse_offset = vertex_screen_pos - u_mouse_pos;
    float screen_scale = 200.0;
    float magnitude_multiplier = 1.5;

    // --- 修改点: 将 u_hovering 替换为 u_hover_intensity ---
    // 这使得倾斜效果的强度可以平滑地从 0 变化到 100%
    float scale = magnitude_multiplier * (-0.03 - 0.3 * max(0.0, 0.3 - mid_dist))
                * u_hover_intensity * (pow(length(mouse_offset / screen_scale), 2.0)) / (2.0 - mid_dist);

    gl_Position.w += scale;
}
"""

fragment_shader_source = """
#version 330
out vec4 f_color;
void main() {
    f_color = vec4(0.9, 0.9, 0.95, 1.0);
}
"""

# 创建着色器程序
try:
    prog = ctx.program(vertex_shader=vertex_shader_source, fragment_shader=fragment_shader_source)
except Exception as e:
    print("Shader Error:", e)
    pygame.quit()
    exit()

# 获取 uniform 的位置
u_resolution = prog['u_resolution']
u_mouse_pos = prog['u_mouse_pos']
u_bounce_time = prog['u_bounce_time']
u_bounce_amplitude = prog['u_bounce_amplitude']
u_bounce_damping = prog['u_bounce_damping']
u_bounce_frequency = prog['u_bounce_frequency']
# --- 新增: 获取 hover_intensity 的位置 ---
u_hover_intensity = prog['u_hover_intensity']

# 创建卡牌的几何体
card_width, card_height = 200, 300
card_rect = pygame.Rect((screen_width - card_width) / 2, (screen_height - card_height) / 2, card_width, card_height)
x1, y1 = (card_rect.left / screen_width) * 2 - 1, 1 - (card_rect.top / screen_height) * 2
x2, y2 = (card_rect.right / screen_width) * 2 - 1, 1 - (card_rect.bottom / screen_height) * 2
quad_vertices = np.array([x1, y1, x2, y1, x1, y2, x2, y2], dtype='f4')
vbo = ctx.buffer(quad_vertices)
vao = ctx.simple_vertex_array(prog, vbo, 'in_vert')

# --- 动画相关的变量 ---
clock = pygame.time.Clock()
was_hovering = False
bounce_time = -1.0
BOUNCE_DURATION = 0.5

# --- 新增: 平滑过渡相关的变量 ---
hover_intensity = 0.0  # 当前的悬停强度 (0.0 到 1.0)
HOVER_TRANSITION_SPEED = 15.0  # 过渡速度 (值越大, 过渡越快)

# 设置动画参数
u_bounce_amplitude.value = 0.03  # 初始弹跳幅度 (放大20%)
u_bounce_damping.value = 7.0  # 阻尼/衰减率 (值越大, 停得越快)
u_bounce_frequency.value = 35.0  # 频率 (值越大, 弹得越快)

# 游戏主循环
running = True
while running:
    delta_time = clock.tick(60) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    ctx.clear(0.1, 0.2, 0.3)

    mouse_pos = pygame.mouse.get_pos()
    is_hovering = card_rect.collidepoint(mouse_pos)

    # 弹跳动画触发逻辑 (不变)
    if is_hovering and not was_hovering:
        bounce_time = 0.0
    if 0.0 <= bounce_time < BOUNCE_DURATION:
        bounce_time += delta_time
    else:
        bounce_time = -1.0
    was_hovering = is_hovering

    # --- 新增: 更新 hover_intensity ---
    # 如果鼠标悬停，则增加强度；否则，减少强度
    if is_hovering:
        hover_intensity += HOVER_TRANSITION_SPEED * delta_time
    else:
        hover_intensity -= HOVER_TRANSITION_SPEED * delta_time
    # 使用 clamp 确保值在 0.0 和 1.0 之间
    hover_intensity = max(0.0, min(1.0, hover_intensity))

    # 更新 uniforms
    u_resolution.value = (float(screen_width), float(screen_height))
    u_mouse_pos.value = (float(mouse_pos[0]), float(mouse_pos[1]))
    u_bounce_time.value = bounce_time
    # --- 新增: 发送 hover_intensity 到 GPU ---
    u_hover_intensity.value = hover_intensity

    # 渲染
    vao.render(moderngl.TRIANGLE_STRIP)

    pygame.display.flip()

pygame.quit()
