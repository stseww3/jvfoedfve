#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _51;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _57;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _87;

layout(location = 0) in vec3 Position;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
layout(location = 1) in vec4 Color;

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
    gl_Position = (_51.ProjMat * _57.ModelViewMat) * vec4(Position, 1.0);
    vec3 param = Position;
    sphericalVertexDistance = fog_spherical_distance(param);
    vec3 param_1 = Position;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    vertexColor = Color;
}

