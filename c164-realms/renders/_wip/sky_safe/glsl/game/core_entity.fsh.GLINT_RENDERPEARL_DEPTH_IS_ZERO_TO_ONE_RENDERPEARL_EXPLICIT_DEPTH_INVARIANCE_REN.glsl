#version 330

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _152;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _184;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _230;

uniform sampler2D GlintSampler;
uniform sampler2D Sampler0;

in vec4 overlayColor;
in vec4 lightMapColor;
in vec2 texCoordGlint;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec2 texCoord0;
in vec4 vertexColor;
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
    vec4 _126 = color;
    vec3 _132 = mix(overlayColor.xyz, _126.xyz, vec3(overlayColor.w));
    color.x = _132.x;
    color.y = _132.y;
    color.z = _132.z;
    color *= lightMapColor;
    vec4 glintColor = texture(GlintSampler, texCoordGlint) * _152.GlintAlpha;
    vec4 _172 = color;
    vec3 _174 = _172.xyz + (glintColor.xyz * glintColor.xyz);
    color.x = _174.x;
    color.y = _174.y;
    color.z = _174.z;
    vec4 fogColor = _184.FogColor;
    vec4 param = color;
    float param_1 = sphericalVertexDistance;
    float param_2 = cylindricalVertexDistance;
    float param_3 = _184.FogEnvironmentalStart;
    float param_4 = _184.FogEnvironmentalEnd;
    float param_5 = _184.FogRenderDistanceStart;
    float param_6 = _184.FogRenderDistanceEnd;
    vec4 param_7 = fogColor;
    return apply_fog(param, param_1, param_2, param_3, param_4, param_5, param_6, param_7);
}

void main()
{
    vec4 color = texture(Sampler0, texCoord0);
    vec4 faceVertexColor = vertexColor;
    color *= (faceVertexColor * _230.ColorModulator);
    color.w = max(color.w, _152.GlintAlpha);
    vec4 param = color;
    vec4 _246 = calculateFinalColor(param);
    fragColor = _246;
}

