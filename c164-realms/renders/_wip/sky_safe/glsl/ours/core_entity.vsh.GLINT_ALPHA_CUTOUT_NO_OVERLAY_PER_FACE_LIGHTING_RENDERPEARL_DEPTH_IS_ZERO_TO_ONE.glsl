#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _135;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _141;

layout(std140) uniform Lighting
{
    vec3 Light0_Direction;
    vec3 Light1_Direction;
} _167;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _218;

uniform sampler2D Sampler2;

out vec3 c164_ray;
layout(location = 0) in vec3 Position;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
layout(location = 5) in vec3 Normal;
out vec4 vertexPerFaceColorBack;
layout(location = 1) in vec4 Color;
out vec4 vertexPerFaceColorFront;
out vec4 lightMapColor;
layout(location = 4) in ivec2 UV2;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;
out vec2 texCoordGlint;
layout(location = 3) in ivec2 UV1;

float fog_spherical_distance(vec3 pos)
{
    c164_ray = pos;
    return length(pos);
}

float fog_cylindrical_distance(vec3 pos)
{
    float distXZ = length(pos.xz);
    float distY = abs(pos.y);
    return max(distXZ, distY);
}

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

vec4 sample_lightmap(sampler2D lightMap, ivec2 uv)
{
    return textureLod(lightMap, clamp((vec2(uv) / vec2(256.0)) + vec2(0.03125), vec2(0.03125), vec2(0.96875)), 0.0);
}

void main()
{
    gl_Position = (_135.ProjMat * _141.ModelViewMat) * vec4(Position, 1.0);
    vec3 param = Position;
    float _159 = fog_spherical_distance(param);
    sphericalVertexDistance = _159;
    vec3 param_1 = Position;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    vec3 param_2 = _167.Light0_Direction;
    vec3 param_3 = _167.Light1_Direction;
    vec3 param_4 = Normal;
    vec2 light = minecraft_compute_light(param_2, param_3, param_4);
    vec2 param_5 = -light;
    vec4 param_6 = Color;
    vertexPerFaceColorBack = minecraft_mix_light_separate(param_5, param_6);
    vec2 param_7 = light;
    vec4 param_8 = Color;
    vertexPerFaceColorFront = minecraft_mix_light_separate(param_7, param_8);
    ivec2 param_9 = UV2;
    lightMapColor = sample_lightmap(Sampler2, param_9);
    texCoord0 = UV0;
    texCoordGlint = (_141.TextureMat * vec4(UV0, 0.0, 1.0)).xy;
}

