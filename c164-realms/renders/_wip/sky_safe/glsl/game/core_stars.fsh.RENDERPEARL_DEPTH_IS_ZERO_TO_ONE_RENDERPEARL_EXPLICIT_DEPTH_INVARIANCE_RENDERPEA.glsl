#version 330

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _16;

layout(location = 0) out vec4 fragColor;

void main()
{
    fragColor = _16.ColorModulator;
}

