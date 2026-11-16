#version 330

const vec2 _355[4] = vec2[](vec2(0.125, 0.375), vec2(-0.125, -0.375), vec2(0.375, -0.125), vec2(-0.375, 0.125));

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _415;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _791;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _834;

layout(std140) uniform TerrainUniform
{
    mat4 ModelViewMat;
    ivec2 TextureSize;
} _848;

layout(std140) uniform ChunkSection
{
    ivec3 ChunkPosition;
    float ChunkVisibility;
} _893;

uniform sampler2D DepthBoundsSampler;
uniform sampler2D Coeff0;
uniform sampler2D Coeff1;
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
        vec2 sampleUV = uv + (_355[i] * pixelSize);
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
    vec4 _401 = sampleNearest(source, param, param_1, param_2, param_3, param_4);
    vec4 nearestColor = _401;
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
    vec4 _251 = sampleNearest(source, param, param_1, param_2, param_3, param_4);
    return _251;
}

float deviceToLinearDepth(inout float deviceDepth)
{
    deviceDepth = (deviceDepth - 0.5) * 2.0;
    return _415.ProjMat[3].z / (deviceDepth + _415.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float _466 = deviceToLinearDepth(param);
    float fragmentLinearDepth = _466;
    float range = max(furthestBoundLinearDepth - closestBoundLinearDepth, 9.9999997473787516355514526367188e-05);
    float depthWithinBounds = clamp(fragmentLinearDepth - closestBoundLinearDepth, 0.0, range);
    float depthWithHighPrecision = 0.75 * range;
    if (depthWithHighPrecision <= 10.0)
    {
        return depthWithinBounds / range;
    }
    else
    {
        if (depthWithinBounds <= 10.0)
        {
            return (depthWithinBounds / 10.0) * 0.75;
        }
        else
        {
            return 0.75 + (((depthWithinBounds - 10.0) / (range - 10.0)) * 0.25);
        }
    }
}

float toAbsorbance(float transmittance)
{
    return clamp(-log(max(transmittance, 9.9999997473787516355514526367188e-05)), 0.0, 4.0);
}

float sampleAbsorbance(float coefficients[8], float originalDepth, float currentAbsorbance)
{
    float averageAbsorbance = coefficients[0];
    if (averageAbsorbance == 0.0)
    {
        return 0.0;
    }
    float depthMeasuredInBins = originalDepth * 7.0;
    float depth = depthMeasuredInBins / 8.0;
    float currentAverageAbsorbanceContribution = currentAbsorbance * (1.0 - depth);
    averageAbsorbance -= currentAverageAbsorbanceContribution;
    int treeIndexB = clamp(int(floor(depthMeasuredInBins)), 0, 7);
    bool shouldSampleA = treeIndexB >= 1;
    int _546 = 0;
    if (shouldSampleA)
    {
        _546 = treeIndexB - 1;
    }
    else
    {
        _546 = treeIndexB;
    }
    int treeIndexA = _546;
    treeIndexB += 8;
    treeIndexA += 8;
    float sampleB = averageAbsorbance;
    float sampleA = shouldSampleA ? averageAbsorbance : 0.0;
    float _649 = 0.0;
    for (int waveletLevel = 0; waveletLevel <= 3; waveletLevel++)
    {
        int power = 3 - waveletLevel;
        float waveletWidth = exp2(float(-power));
        float waveletHeightScale = exp2(float(power) * 0.5);
        int parentIndexB = treeIndexB >> 1;
        int isRightHalfB = treeIndexB & 1;
        int waveletSignB = 1 - (isRightHalfB << 1);
        float indexAtParentLevel = float(parentIndexB & ((1 << power) - 1));
        float depthOffsetRelativeToWavelet = depth - (waveletWidth * indexAtParentLevel);
        float currentDifferenceCoefficient = (((float(isRightHalfB) * waveletWidth) + (float(waveletSignB) * depthOffsetRelativeToWavelet)) * waveletHeightScale) * currentAbsorbance;
        float differenceCoefficientB = coefficients[parentIndexB];
        differenceCoefficientB -= currentDifferenceCoefficient;
        sampleB -= ((waveletHeightScale * differenceCoefficientB) * float(waveletSignB));
        treeIndexB = parentIndexB;
        if (shouldSampleA)
        {
            int parentIndexA = treeIndexA >> 1;
            if (parentIndexA == parentIndexB)
            {
                _649 = differenceCoefficientB;
            }
            else
            {
                _649 = coefficients[parentIndexA];
            }
            float differenceCoefficientA = _649;
            int isRightHalfA = treeIndexA & 1;
            int waveletSignA = 1 - (isRightHalfA << 1);
            sampleA -= ((waveletHeightScale * differenceCoefficientA) * float(waveletSignA));
            treeIndexA = parentIndexA;
        }
    }
    float _679 = 0.0;
    if (depthMeasuredInBins >= 8.0)
    {
        _679 = 1.0;
    }
    else
    {
        _679 = fract(depthMeasuredInBins);
    }
    float lerpAlpha = _679;
    return mix(sampleA, sampleB, lerpAlpha);
}

float toTransmittance(float absorbance)
{
    return clamp(exp(-absorbance), 9.9999997473787516355514526367188e-05, 1.0);
}

float sampleTransmittance(ivec2 pos, float depth, float currentTransmittance)
{
    vec4 coeffSamples[2];
    coeffSamples[0] = texelFetch(Coeff0, pos, 0);
    coeffSamples[1] = texelFetch(Coeff1, pos, 0);
    float coefficients[8];
    for (int i = 0; i < 2; i++)
    {
        for (int j = 0; j < 4; j++)
        {
            coefficients[(i * 4) + j] = coeffSamples[i][j];
        }
    }
    float param = currentTransmittance;
    float param_1[8] = coefficients;
    float param_2 = depth;
    float param_3 = toAbsorbance(param);
    float param_4 = sampleAbsorbance(param_1, param_2, param_3);
    return toTransmittance(param_4);
}

vec4 sampleColorForAccumulation(vec4 color)
{
    float transmittance = 1.0 - color.w;
    float accumAlpha = color.w;
    float param = gl_FragCoord.z;
    ivec2 param_1 = ivec2(gl_FragCoord.xy);
    float param_2 = normalizeDepth(param);
    float param_3 = transmittance;
    float sampledTransmittance = sampleTransmittance(param_1, param_2, param_3);
    return vec4(color.xyz * color.w, accumAlpha) * sampledTransmittance;
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

vec4 calculateFinalColor(inout vec4 color)
{
    vec4 param = color;
    color = sampleColorForAccumulation(param);
    vec4 fogColor = vec4(_791.FogColor.xyz * color.w, _791.FogColor.w);
    vec4 param_1 = color;
    float param_2 = sphericalVertexDistance;
    float param_3 = cylindricalVertexDistance;
    float param_4 = _791.FogEnvironmentalStart;
    float param_5 = _791.FogEnvironmentalEnd;
    float param_6 = _791.FogRenderDistanceStart;
    float param_7 = _791.FogRenderDistanceEnd;
    vec4 param_8 = fogColor;
    return apply_fog(param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8);
}

void main()
{
    vec4 _840 = vec4(0.0);
    if (_834.UseRgss == 1)
    {
        vec2 param = texCoord0;
        vec2 param_1 = vec2(1.0) / vec2(_848.TextureSize);
        _840 = sampleRGSS(Sampler0, param, param_1);
    }
    else
    {
        vec2 param_2 = texCoord0;
        vec2 param_3 = vec2(1.0) / vec2(_848.TextureSize);
        _840 = sampleNearest(Sampler0, param_2, param_3);
    }
    vec4 color = _840 * vertexColor;
    color = mix(_791.FogColor * vec4(1.0, 1.0, 1.0, color.w), color, vec4(chunkVisibility));
    vec4 param_4 = color;
    vec4 _888 = calculateFinalColor(param_4);
    fragColor = _888;
}

