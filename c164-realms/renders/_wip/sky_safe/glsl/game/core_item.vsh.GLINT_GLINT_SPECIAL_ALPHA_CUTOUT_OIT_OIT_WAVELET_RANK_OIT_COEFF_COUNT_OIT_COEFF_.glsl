#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _104;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _110;

layout(std140) uniform Lighting
{
    vec3 Light0_Direction;
    vec3 Light1_Direction;
} _127;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _161;

layout(location = 0) in vec3 Position;
out vec4 vertexColor;
layout(location = 6) in vec3 Normal;
layout(location = 1) in vec4 Color;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;
out vec2 texCoordGlint;
layout(location = 5) in vec2 UV3;
layout(location = 3) in ivec2 UV1;
layout(location = 4) in ivec2 UV2;

vec2 minecraft_compute_light(vec3 lightDir0, vec3 lightDir1, vec3 normal)
{
    return vec2(dot(lightDir0, normal), dot(lightDir1, normal));
}

vec4 minecraft_mix_light_separate(vec2 light, vec4 color)
{
    vec2 lightValue = max(vec2(0.0), light);
    float lightAccum = min(1.0, ((lightValue.x + lightValue.y) * 0.60000002384185791015625) + 0.4000000059604644775390625);
    return vec4(color.xyz * lightAccum, color.w);
}

vec4 minecraft_mix_light(vec3 lightDir0, vec3 lightDir1, vec3 normal, vec4 color)
{
    vec3 param = lightDir0;
    vec3 param_1 = lightDir1;
    vec3 param_2 = normal;
    vec2 light = minecraft_compute_light(param, param_1, param_2);
    vec2 param_3 = light;
    vec4 param_4 = color;
    return minecraft_mix_light_separate(param_3, param_4);
}

void main()
{
    gl_Position = (_104.ProjMat * _110.ModelViewMat) * vec4(Position, 1.0);
    vec3 param = _127.Light0_Direction;
    vec3 param_1 = _127.Light1_Direction;
    vec3 param_2 = Normal;
    vec4 param_3 = Color;
    vertexColor = minecraft_mix_light(param, param_1, param_2, param_3);
    texCoord0 = UV0;
    texCoordGlint = (_110.TextureMat * vec4(UV3, 0.0, 1.0)).xy;
}

