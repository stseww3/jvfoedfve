#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _55;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _61;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _106;

out vec3 c164_ray;
layout(location = 0) in vec3 Position;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
layout(location = 1) in vec4 Color;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;
layout(location = 3) in ivec2 UV1;
layout(location = 4) in ivec2 UV2;
layout(location = 5) in vec3 Normal;
out vec4 lightMapColor;

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

void main()
{
    gl_Position = (_55.ProjMat * _61.ModelViewMat) * vec4(Position, 1.0);
    vec3 param = Position;
    float _80 = fog_spherical_distance(param);
    sphericalVertexDistance = _80;
    vec3 param_1 = Position;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    vertexColor = Color;
    texCoord0 = UV0;
    texCoord0 = (_61.TextureMat * vec4(UV0, 0.0, 1.0)).xy;
}

