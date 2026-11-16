#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _22;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _29;

layout(location = 0) in vec3 Position;
out vec4 vertexColor;
layout(location = 1) in vec4 Color;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;

void main()
{
    gl_Position = (_22.ProjMat * _29.ModelViewMat) * vec4(Position, 1.0);
    vertexColor = Color;
    texCoord0 = UV0;
}

