#version 330

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _59;

in vec4 vertexColor;
in float vertexDistance;
layout(location = 0) out vec4 fragColor;

float linear_fog_value(float vertexDistance_1, float fogStart, float fogEnd)
{
    if (vertexDistance_1 <= fogStart)
    {
        return 0.0;
    }
    else
    {
        if (vertexDistance_1 >= fogEnd)
        {
            return 1.0;
        }
    }
    return (vertexDistance_1 - fogStart) / (fogEnd - fogStart);
}

vec4 calculateFinalColor(vec4 color)
{
    return color;
}

void main()
{
    vec4 color = vertexColor;
    float param = vertexDistance;
    float param_1 = 0.0;
    float param_2 = _59.FogCloudsEnd;
    color.w *= (1.0 - linear_fog_value(param, param_1, param_2));
    vec4 param_3 = color;
    fragColor = calculateFinalColor(param_3);
}

