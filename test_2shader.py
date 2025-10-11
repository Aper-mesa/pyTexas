import pygame
import moderngl
import numpy as np

# Pygame 和 ModernGL 初始化
pygame.init()
screen_width, screen_height = 800, 600
pygame.display.set_mode((screen_width, screen_height), pygame.OPENGL | pygame.DOUBLEBUF, vsync=1)
ctx = moderngl.create_context()

# --- 着色器代码 (已更新为阻尼振荡动画) ---
vertex_shader_source = """
#version 330

// --- 动画 Uniforms ---
uniform float u_bounce_time;      // 动画计时器 (从 0 开始增加)
uniform float u_bounce_amplitude; // 初始弹跳幅度
uniform float u_bounce_damping;   // 阻尼系数 (衰减速度)
uniform float u_bounce_frequency; // 振荡频率 (弹跳速度)

// 其他 Uniforms
uniform vec2 u_resolution;
uniform vec2 u_mouse_pos;
uniform float u_hovering;

in vec2 in_vert;

void main() {
    vec2 final_vert = in_vert;

    // --- 新增: 阻尼振荡动画逻辑 ---
    // 检查计时器是否大于0，表示动画正在播放
    if (u_bounce_time >= 0.0) {
        // 1. 指数衰减 (e^-dt): 决定了振荡的包络线，使其幅度随时间减小
        float decay = exp(-u_bounce_damping * u_bounce_time);

        // 2. 余弦振荡 (cos(wt)): 决定了来回弹跳的运动
        // 我们用余弦因为 cos(0) = 1, 这意味着在动画开始时(t=0), 振幅最大
        float oscillation = cos(u_bounce_frequency * u_bounce_time);

        // 3. 组合计算最终缩放比例
        // 最终效果 = 初始幅度 * 衰减 * 振荡
        float scale = 1.0 + u_bounce_amplitude * decay * oscillation;
        final_vert *= scale;
    }

    // 基础的顶点位置 (使用经过弹跳缩放的顶点)
    gl_Position = vec4(final_vert, 0.0, 1.0);

    // 如果没有悬停，则不需要计算倾斜效果
    if (u_hovering <= 0.0) {
        return;
    }

    // --- 倾斜效果逻辑 (与之前相同) ---
    vec2 vertex_screen_pos = vec2(
        (gl_Position.x + 1.0) * 0.5 * u_resolution.x,
        (1.0 - gl_Position.y) * 0.5 * u_resolution.y
    );
    vec2 screen_center = u_resolution * 0.5;
    float mid_dist = length(vertex_screen_pos - screen_center) / length(u_resolution);
    vec2 mouse_offset = vertex_screen_pos - u_mouse_pos;
    float screen_scale = 200.0;
    float magnitude_multiplier = 1.5;
    float scale = magnitude_multiplier * (-0.03 - 0.3 * max(0.0, 0.3 - mid_dist))
                * u_hovering * (pow(length(mouse_offset / screen_scale), 2.0)) / (2.0 - mid_dist);
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
u_hovering = prog['u_hovering']

# --- 新增: 获取所有动画 uniform 的位置 ---
u_bounce_time = prog['u_bounce_time']
u_bounce_amplitude = prog['u_bounce_amplitude']
u_bounce_damping = prog['u_bounce_damping']
u_bounce_frequency = prog['u_bounce_frequency']

# 创建卡牌的几何体
card_width, card_height = 200, 300
card_rect = pygame.Rect((screen_width - card_width) / 2, (screen_height - card_height) / 2, card_width, card_height)
x1, y1 = (card_rect.left / screen_width) * 2 - 1, 1 - (card_rect.top / screen_height) * 2
x2, y2 = (card_rect.right / screen_width) * 2 - 1, 1 - (card_rect.bottom / screen_height) * 2
quad_vertices = np.array([x1, y1, x2, y1, x1, y2, x2, y2], dtype='f4')
vbo = ctx.buffer(quad_vertices)
vao = ctx.simple_vertex_array(prog, vbo, 'in_vert')

# --- 新增: 动画相关的变量 ---
clock = pygame.time.Clock()
was_hovering = False
bounce_time = -1.0  # 动画计时器。-1.0 表示不激活。激活时从 0 开始计时。
BOUNCE_DURATION = 0.5  # 动画总时长(秒)

# --- 新增: 设置动画参数 (你可以调整这些值来改变动画感觉) ---
u_bounce_amplitude.value = 0.03  # 初始弹跳幅度 (放大20%)
u_bounce_damping.value = 5.0  # 阻尼/衰减率 (值越大, 停得越快)
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

    # --- 新增: 动画触发和更新逻辑 ---
    # 1. 触发: 当鼠标“刚刚进入”时，重置计时器为 0
    if is_hovering and not was_hovering:
        bounce_time = 0.0

    # 2. 更新: 如果动画正在播放, 增加计时器
    if 0.0 <= bounce_time < BOUNCE_DURATION:
        bounce_time += delta_time
    else:
        # 如果动画结束或从未开始，将其设为无效值
        bounce_time = -1.0

    was_hovering = is_hovering

    # 更新 uniforms
    u_resolution.value = (float(screen_width), float(screen_height))
    u_mouse_pos.value = (float(mouse_pos[0]), float(mouse_pos[1]))
    u_hovering.value = 1.0 if is_hovering else 0.0
    u_bounce_time.value = bounce_time

    # 渲染
    vao.render(moderngl.TRIANGLE_STRIP)

    pygame.display.flip()

pygame.quit()