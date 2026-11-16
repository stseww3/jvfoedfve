#version 330

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _41;

uniform sampler2D Sampler0;

in vec2 texCoord0;
in vec4 vertexColor;
layout(location = 0) out vec4 fragColor;

vec4 calculateFinalColor(vec4 color)
{
    return color;
}

void main()
{
    vec4 texColor = texture(Sampler0, texCoord0).xxxx;
    vec4 color = (texColor * vertexColor) * _41.ColorModulator;
    if (color.w < 0.100000001490116119384765625)
    {
        discard;
    }
    vec4 param = color;
    fragColor = calculateFinalColor(param);
}

