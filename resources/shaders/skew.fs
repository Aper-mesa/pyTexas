#version 330 core
in vec2 v_uv;
out vec4 f_color;

uniform vec2 card_center_ndc;
uniform vec2 card_size_ndc;
uniform float radius;
uniform vec2 tilt;
uniform float skew_strength;
uniform float hover_smooth;
uniform float time;

vec2 uv_to_ndc(vec2 uv) { return uv * 2.0 - 1.0; }

vec2 local_uv_from_ndc(vec2 ndc, vec2 center, vec2 size) {
    vec2 half = size * 0.5;
    vec2 p = (ndc - center) / (half);
    return p * 0.5 + 0.5;
}

float sdRoundRect(vec2 p, vec2 b, float r){
    vec2 q = abs(p) - b + vec2(r);
    return length(max(q, 0.0)) - r;
}

float smoothshadow(float d, float k){
    return 1.0 - smoothstep(0.0, k, d);
}

void main() {
    vec2 frag_ndc = uv_to_ndc(v_uv);
    vec2 local_uv = local_uv_from_ndc(frag_ndc, card_center_ndc, card_size_ndc);

    float k = skew_strength * hover_smooth;
    float sx = tilt.x * k;
    float sy = -tilt.y * k;

    vec2 uv2 = local_uv;
    uv2.x += (local_uv.y - 0.5) * sx;
    uv2.y += (local_uv.x - 0.5) * sy;

    vec2 p = (uv2 - 0.5) * 2.0;
    float d = sdRoundRect(p, vec2(1.0) - vec2(radius), radius);

    vec3 bg = vec3(0.08, 0.09, 0.11) + 0.02 * vec3(
        0.5 + 0.5*sin(time*0.7),
        0.5 + 0.5*sin(time*0.9 + 1.0),
        0.5 + 0.5*sin(time*1.3 + 2.0)
    );

    if (d > 0.0){
        float sh = smoothshadow(d, 0.08) * 0.5;
        f_color = vec4(bg + vec3(0.0)*sh, 1.0);
        return;
    }

    float edge = smoothstep(-0.02, 0.02, -d);
    vec3 base = mix(vec3(0.93), vec3(1.0), edge);
    float sheen = 0.04 * (0.5 + 0.5 * sin(10.0 * (uv2.x + uv2.y) + time*2.0));
    f_color = vec4(base + vec3(sheen) * 0.6, 1.0);
}
