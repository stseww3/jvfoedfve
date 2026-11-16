#version 330

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _89;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _101;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _138;

uniform sampler2D DepthBoundsSampler;

in vec4 vertexColor;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
layout(location = 0) out vec4 coeff[2];

float linear_fog_value(float vertexDistance, float fogStart, float fogEnd)
{
    if (vertexDistance <= fogStart)
    {
        return 0.0;
    }
    else
    {
        if (vertexDistance >= fogEnd)
        {
            return 1.0;
        }
    }
    return (vertexDistance - fogStart) / (fogEnd - fogStart);
}

float total_fog_value(float sphericalVertexDistance_1, float cylindricalVertexDistance_1, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd)
{
    float param = sphericalVertexDistance_1;
    float param_1 = environmentalStart;
    float param_2 = environmantalEnd;
    float param_3 = cylindricalVertexDistance_1;
    float param_4 = renderDistanceStart;
    float param_5 = renderDistanceEnd;
    return max(linear_fog_value(param, param_1, param_2), linear_fog_value(param_3, param_4, param_5));
}

void executeAlphaOnlyPhase(float deviceDepth, float alpha)
{
    discard;
}

void main()
{
    float param = sphericalVertexDistance;
    float param_1 = cylindricalVertexDistance;
    float param_2 = _101.FogEnvironmentalStart;
    float param_3 = _101.FogEnvironmentalEnd;
    float param_4 = _101.FogRenderDistanceStart;
    float param_5 = _101.FogRenderDistanceEnd;
    vec4 color = (vertexColor * _89.ColorModulator) * (1.0 - total_fog_value(param, param_1, param_2, param_3, param_4, param_5));
    float param_6 = gl_FragCoord.z;
    float param_7 = color.w;
    executeAlphaOnlyPhase(param_6, param_7);
}

