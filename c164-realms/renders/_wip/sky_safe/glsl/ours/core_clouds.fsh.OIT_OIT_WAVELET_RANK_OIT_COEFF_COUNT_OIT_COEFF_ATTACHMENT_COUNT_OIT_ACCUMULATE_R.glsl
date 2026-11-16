#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _91;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _491;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _515;

uniform sampler2D DepthBoundsSampler;
uniform sampler2D Coeff0;
uniform sampler2D Coeff1;

in vec4 vertexColor;
in float vertexDistance;
layout(location = 0) out vec4 fragColor;
in vec3 c164_ray;

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

float deviceToLinearDepth(float deviceDepth)
{
    return _91.ProjMat[3].z / (deviceDepth + _91.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float fragmentLinearDepth = deviceToLinearDepth(param);
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
    int _232 = 0;
    if (shouldSampleA)
    {
        _232 = treeIndexB - 1;
    }
    else
    {
        _232 = treeIndexB;
    }
    int treeIndexA = _232;
    treeIndexB += 8;
    treeIndexA += 8;
    float sampleB = averageAbsorbance;
    float sampleA = shouldSampleA ? averageAbsorbance : 0.0;
    float _336 = 0.0;
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
                _336 = differenceCoefficientB;
            }
            else
            {
                _336 = coefficients[parentIndexA];
            }
            float differenceCoefficientA = _336;
            int isRightHalfA = treeIndexA & 1;
            int waveletSignA = 1 - (isRightHalfA << 1);
            sampleA -= ((waveletHeightScale * differenceCoefficientA) * float(waveletSignA));
            treeIndexA = parentIndexA;
        }
    }
    float _366 = 0.0;
    if (depthMeasuredInBins >= 8.0)
    {
        _366 = 1.0;
    }
    else
    {
        _366 = fract(depthMeasuredInBins);
    }
    float lerpAlpha = _366;
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
    gl_FragDepth = gl_FragCoord.z;
    float param = gl_FragCoord.z;
    ivec2 param_1 = ivec2(gl_FragCoord.xy);
    float param_2 = normalizeDepth(param);
    float param_3 = transmittance;
    float sampledTransmittance = sampleTransmittance(param_1, param_2, param_3);
    return vec4(color.xyz * color.w, accumAlpha) * sampledTransmittance;
}

vec4 calculateFinalColor(inout vec4 color)
{
    vec4 param = color;
    vec4 _481 = sampleColorForAccumulation(param);
    color = _481;
    return color;
}

void main()
{
    vec4 color = vertexColor;
    float param = vertexDistance;
    float param_1 = 0.0;
    float param_2 = _491.FogCloudsEnd;
    color.w *= (1.0 - linear_fog_value(param, param_1, param_2));
    vec4 param_3 = color;
    vec4 _509 = calculateFinalColor(param_3);
    fragColor = _509;
}

