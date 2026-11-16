#version 330

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _121;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _129;

layout(location = 0) out vec4 fragColor;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;

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

vec4 apply_fog(vec4 inColor, float sphericalVertexDistance_1, float cylindricalVertexDistance_1, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd, vec4 fogColor)
{
    float param = sphericalVertexDistance_1;
    float param_1 = cylindricalVertexDistance_1;
    float param_2 = environmentalStart;
    float param_3 = environmantalEnd;
    float param_4 = renderDistanceStart;
    float param_5 = renderDistanceEnd;
    float fogValue = total_fog_value(param, param_1, param_2, param_3, param_4, param_5);
    return vec4(mix(inColor.xyz, fogColor.xyz, vec3(fogValue * fogColor.w)), inColor.w);
}

void main()
{
    vec4 param = _121.ColorModulator;
    float param_1 = sphericalVertexDistance;
    float param_2 = cylindricalVertexDistance;
    float param_3 = 0.0;
    float param_4 = _129.FogSkyEnd;
    float param_5 = _129.FogSkyEnd;
    float param_6 = _129.FogSkyEnd;
    vec4 param_7 = _129.FogColor;
    fragColor = apply_fog(param, param_1, param_2, param_3, param_4, param_5, param_6, param_7);
}

