import pygame
import moderngl
import numpy as np

# Pygame 和 ModernGL 初始化
pygame.init()
screen_width, screen_height = 800, 600
pygame.display.set_mode((screen_width, screen_height), pygame.OPENGL | pygame.DOUBLEBUF, vsync=1)
ctx = moderngl.create_context()

# --- 着色器代码 (已修正方向和幅度) ---
vertex_shader_source = """
#version 330

// Uniforms 从 Python 传入
uniform vec2 u_resolution; // 窗口尺寸
uniform vec2 u_mouse_pos;  // 鼠标像素坐标
uniform float u_hovering;  // 是否悬停 (0.0 或 1.0)

// 顶点输入 (裁剪空间, -1.0 to 1.0)
in vec2 in_vert;

void main() {
    // 基础的顶点位置
    gl_Position = vec4(in_vert, 0.0, 1.0);

    // 如果没有悬停，直接返回
    if (u_hovering <= 0.0) {
        return;
    }

    // 将输入的裁剪空间坐标 (-1 to 1) 转换回屏幕像素坐标
    vec2 vertex_screen_pos = vec2(
        (in_vert.x + 1.0) * 0.5 * u_resolution.x,
        (1.0 - in_vert.y) * 0.5 * u_resolution.y // Y轴需要翻转
    );

    // 在屏幕像素坐标系下进行计算
    vec2 screen_center = u_resolution * 0.5;
    float mid_dist = length(vertex_screen_pos - screen_center) / length(u_resolution);
    vec2 mouse_offset = vertex_screen_pos - u_mouse_pos;

    float screen_scale = 200.0;

    // --- 修改点 #2: 加大倾斜幅度 ---
    // 将原始的系数 0.2 提升到 1.0，使效果增强5倍
    float magnitude_multiplier = 1.5;

    float scale = magnitude_multiplier * (-0.03 - 0.3 * max(0.0, 0.3 - mid_dist))
                * u_hovering * (pow(length(mouse_offset / screen_scale), 2.0)) / (2.0 - mid_dist);

    // --- 修改点 #1: 修正倾斜方向 ---
    // 将 "-=" 改为 "+="。因为 scale 是负数，加上一个负数会使 w < 1.0，
    // 这会让顶点在透视除法后变大，产生向外凸出的效果，感觉更自然。
    gl_Position.w += scale;
}
"""

fragment_shader_source = """
#version 330
out vec4 f_color;
void main() {
    // 输出一个纯色
    f_color = vec4(0.9, 0.9, 0.95, 1.0); // 稍微柔和的白色
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

# 创建一个矩形（卡牌）的顶点数据
card_width, card_height = 200, 300
card_rect = pygame.Rect(
    (screen_width - card_width) / 2,
    (screen_height - card_height) / 2,
    card_width,
    card_height
)

# 将屏幕坐标转换为 OpenGL 的裁剪空间坐标 (-1 到 1)
x1 = (card_rect.left / screen_width) * 2 - 1
y1 = 1 - (card_rect.top / screen_height) * 2
x2 = (card_rect.right / screen_width) * 2 - 1
y2 = 1 - (card_rect.bottom / screen_height) * 2

# 四个顶点的坐标
quad_vertices = np.array([
    x1, y1,  # top left
    x2, y1,  # top right
    x1, y2,  # bottom left
    x2, y2,  # bottom right
], dtype='f4')

# 创建 VBO 和 VAO
vbo = ctx.buffer(quad_vertices)
vao = ctx.simple_vertex_array(prog, vbo, 'in_vert')

# 游戏主循环
running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    # 清屏
    ctx.clear(0.1, 0.2, 0.3)

    # 获取鼠标位置
    mouse_pos = pygame.mouse.get_pos()

    # 检查鼠标是否在卡牌区域内
    is_hovering = card_rect.collidepoint(mouse_pos)

    # 更新 uniforms
    u_resolution.value = (float(screen_width), float(screen_height))
    u_mouse_pos.value = (float(mouse_pos[0]), float(mouse_pos[1]))
    u_hovering.value = 1.0 if is_hovering else 0.0

    # 渲染
    vao.render(moderngl.TRIANGLE_STRIP)

    # 刷新屏幕
    pygame.display.flip()

pygame.quit()
