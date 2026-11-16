#version 330

const vec2 _317[4] = vec2[](vec2(0.125, 0.375), vec2(-0.125, -0.375), vec2(0.375, -0.125), vec2(-0.375, 0.125));

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _374;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _411;

layout(std140) uniform TerrainUniform
{
    mat4 ModelViewMat;
    ivec2 TextureSize;
} _427;

uniform sampler2D Sampler0;

in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec2 texCoord0;
in vec4 vertexColor;
in float chunkVisibility;
layout(location = 0) out vec4 fragColor;

vec4 sampleNearest(sampler2D source, inout vec2 uv, vec2 pixelSize, vec2 du, vec2 dv, vec2 texelScreenSize)
{
    vec2 uvTexelCoords = uv / pixelSize;
    vec2 texelCenter = round(uvTexelCoords) - vec2(0.5);
    vec2 texelOffset = uvTexelCoords - texelCenter;
    texelOffset = (((texelOffset - vec2(0.5)) * pixelSize) / texelScreenSize) + vec2(0.5);
    texelOffset = clamp(texelOffset, vec2(0.0), vec2(1.0));
    uv = (texelCenter + texelOffset) * pixelSize;
    return textureGrad(source, uv, du, dv);
}

vec4 sampleRGSS(sampler2D source, vec2 uv, vec2 pixelSize)
{
    vec2 du = dFdx(uv);
    vec2 dv = dFdy(uv);
    vec2 texelScreenSize = sqrt((du * du) + (dv * dv));
    float maxTexelSize = max(texelScreenSize.x, texelScreenSize.y);
    float minPixelSize = min(pixelSize.x, pixelSize.y);
    float transitionStart = minPixelSize * 1.0;
    float transitionEnd = minPixelSize * 2.0;
    float blendFactor = smoothstep(transitionStart, transitionEnd, maxTexelSize);
    float duLength = length(du);
    float dvLength = length(dv);
    float minDerivative = min(duLength, dvLength);
    float maxDerivative = max(duLength, dvLength);
    float effectiveDerivative = sqrt(minDerivative * maxDerivative);
    float mipLevelExact = max(0.0, log2(effectiveDerivative / minPixelSize));
    float mipLevelLow = floor(mipLevelExact);
    float mipLevelHigh = mipLevelLow + 1.0;
    float mipBlend = fract(mipLevelExact);
    vec4 rgssColorLow = vec4(0.0);
    vec4 rgssColorHigh = vec4(0.0);
    for (int i = 0; i < 4; i++)
    {
        vec2 sampleUV = uv + (_317[i] * pixelSize);
        rgssColorLow += textureLod(source, sampleUV, mipLevelLow);
        rgssColorHigh += textureLod(source, sampleUV, mipLevelHigh);
    }
    rgssColorLow *= 0.25;
    rgssColorHigh *= 0.25;
    vec4 rgssColor = mix(rgssColorLow, rgssColorHigh, vec4(mipBlend));
    vec2 param = uv;
    vec2 param_1 = pixelSize;
    vec2 param_2 = du;
    vec2 param_3 = dv;
    vec2 param_4 = texelScreenSize;
    vec4 _363 = sampleNearest(source, param, param_1, param_2, param_3, param_4);
    vec4 nearestColor = _363;
    return mix(nearestColor, rgssColor, vec4(blendFactor));
}

vec4 sampleNearest(sampler2D source, vec2 uv, vec2 pixelSize)
{
    vec2 du = dFdx(uv);
    vec2 dv = dFdy(uv);
    vec2 texelScreenSize = sqrt((du * du) + (dv * dv));
    vec2 param = uv;
    vec2 param_1 = pixelSize;
    vec2 param_2 = du;
    vec2 param_3 = dv;
    vec2 param_4 = texelScreenSize;
    vec4 _212 = sampleNearest(source, param, param_1, param_2, param_3, param_4);
    return _212;
}

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

vec4 calculateFinalColor(vec4 color)
{
    vec4 fogColor = _374.FogColor;
    vec4 param = color;
    float param_1 = sphericalVertexDistance;
    float param_2 = cylindricalVertexDistance;
    float param_3 = _374.FogEnvironmentalStart;
    float param_4 = _374.FogEnvironmentalEnd;
    float param_5 = _374.FogRenderDistanceStart;
    float param_6 = _374.FogRenderDistanceEnd;
    vec4 param_7 = fogColor;
    return apply_fog(param, param_1, param_2, param_3, param_4, param_5, param_6, param_7);
}

void main()
{
    vec4 _417 = vec4(0.0);
    if (_411.UseRgss == 1)
    {
        vec2 param = texCoord0;
        vec2 param_1 = vec2(1.0) / vec2(_427.TextureSize);
        _417 = sampleRGSS(Sampler0, param, param_1);
    }
    else
    {
        vec2 param_2 = texCoord0;
        vec2 param_3 = vec2(1.0) / vec2(_427.TextureSize);
        _417 = sampleNearest(Sampler0, param_2, param_3);
    }
    vec4 color = _417 * vertexColor;
    color = mix(_374.FogColor * vec4(1.0, 1.0, 1.0, color.w), color, vec4(chunkVisibility));
    if (color.w < 0.100000001490116119384765625)
    {
        discard;
    }
    vec4 param_4 = color;
    fragColor = calculateFinalColor(param_4);
}

