#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _36;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _42;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _72;

out vec3 c164_ray;
layout(location = 0) in vec3 Position;
out vec4 vertexColor;
layout(location = 1) in vec4 Color;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;

float fog_spherical_distance(vec3 pos)
{
    c164_ray = pos;
    return length(pos);
}

void main()
{
    gl_Position = (_36.ProjMat * _42.ModelViewMat) * vec4(Position, 1.0);
    vec3 param = Position;
    float _59 = fog_spherical_distance(param);
    vertexColor = Color;
    texCoord0 = UV0;
}

