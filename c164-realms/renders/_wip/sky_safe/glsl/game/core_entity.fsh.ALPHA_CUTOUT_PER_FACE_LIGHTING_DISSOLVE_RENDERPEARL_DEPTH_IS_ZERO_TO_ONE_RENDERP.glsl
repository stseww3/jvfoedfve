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
} _148;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _227;

uniform sampler2D Sampler0;
uniform sampler2D DissolveMaskSampler;

in vec4 overlayColor;
in vec4 lightMapColor;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec2 texCoord0;
in vec4 vertexPerFaceColorFront;
in vec4 vertexPerFaceColorBack;
layout(location = 0) out vec4 fragColor;

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

vec4 calculateFinalColor(inout vec4 color)
{
    vec4 _125 = color;
    vec3 _131 = mix(overlayColor.xyz, _125.xyz, vec3(overlayColor.w));
    color.x = _131.x;
    color.y = _131.y;
    color.z = _131.z;
    color *= lightMapColor;
    vec4 fogColor = _148.FogColor;
    vec4 param = color;
    float param_1 = sphericalVertexDistance;
    float param_2 = cylindricalVertexDistance;
    float param_3 = _148.FogEnvironmentalStart;
    float param_4 = _148.FogEnvironmentalEnd;
    float param_5 = _148.FogRenderDistanceStart;
    float param_6 = _148.FogRenderDistanceEnd;
    vec4 param_7 = fogColor;
    return apply_fog(param, param_1, param_2, param_3, param_4, param_5, param_6, param_7);
}

void main()
{
    vec4 color = texture(Sampler0, texCoord0);
    if (color.w < 0.100000001490116119384765625)
    {
        discard;
    }
    vec4 faceVertexColor = gl_FrontFacing ? vertexPerFaceColorFront : vertexPerFaceColorBack;
    if (faceVertexColor.w < texture(DissolveMaskSampler, texCoord0).w)
    {
        discard;
    }
    faceVertexColor.w = 1.0;
    color *= (faceVertexColor * _227.ColorModulator);
    vec4 param = color;
    vec4 _237 = calculateFinalColor(param);
    fragColor = _237;
}

