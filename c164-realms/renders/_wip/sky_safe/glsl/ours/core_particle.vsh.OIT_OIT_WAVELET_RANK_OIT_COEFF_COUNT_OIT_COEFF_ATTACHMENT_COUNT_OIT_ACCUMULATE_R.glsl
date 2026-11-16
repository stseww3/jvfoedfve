#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _82;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _88;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _130;

uniform sampler2D Sampler2;

out vec3 c164_ray;
layout(location = 0) in vec3 Position;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec2 texCoord0;
layout(location = 1) in vec2 UV0;
out vec4 vertexColor;
layout(location = 2) in vec4 Color;
layout(location = 3) in ivec2 UV2;

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

vec4 sample_lightmap(sampler2D lightMap, ivec2 uv)
{
    return textureLod(lightMap, clamp((vec2(uv) / vec2(256.0)) + vec2(0.03125), vec2(0.03125), vec2(0.96875)), 0.0);
}

void main()
{
    gl_Position = (_82.ProjMat * _88.ModelViewMat) * vec4(Position, 1.0);
    vec3 param = Position;
    float _107 = fog_spherical_distance(param);
    sphericalVertexDistance = _107;
    vec3 param_1 = Position;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    texCoord0 = UV0;
    ivec2 param_2 = UV2;
    vertexColor = Color * sample_lightmap(Sampler2, param_2);
}

