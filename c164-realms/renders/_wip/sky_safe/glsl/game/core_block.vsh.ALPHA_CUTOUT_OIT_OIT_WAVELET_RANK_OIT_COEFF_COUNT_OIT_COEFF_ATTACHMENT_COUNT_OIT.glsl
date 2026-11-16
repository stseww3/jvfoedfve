#version 330

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _50;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _64;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _100;

layout(location = 0) in vec3 Position;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
layout(location = 1) in vec4 Color;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;
layout(location = 3) in ivec2 UV2;

float fog_spherical_distance(vec3 pos)
{
    return length(pos);
}

float fog_cylindrical_distance(vec3 pos)
{
    float distXZ = length(pos.xz);
    float distY = abs(pos.y);
    return max(distXZ, distY);
}

void main()
{
    vec3 pos = Position + _50.ModelOffset;
    gl_Position = (_64.ProjMat * _50.ModelViewMat) * vec4(pos, 1.0);
    vec3 param = pos;
    sphericalVertexDistance = fog_spherical_distance(param);
    vec3 param_1 = pos;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    vertexColor = Color;
    texCoord0 = UV0;
}

