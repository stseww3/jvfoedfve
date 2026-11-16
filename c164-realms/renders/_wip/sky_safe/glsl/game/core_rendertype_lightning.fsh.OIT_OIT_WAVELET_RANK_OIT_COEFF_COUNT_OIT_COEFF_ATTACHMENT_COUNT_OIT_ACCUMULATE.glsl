#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _122;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _516;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _525;

uniform sampler2D DepthBoundsSampler;
uniform sampler2D Coeff0;
uniform sampler2D Coeff1;

in vec4 vertexColor;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
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

float deviceToLinearDepth(inout float deviceDepth)
{
    deviceDepth = (deviceDepth - 0.5) * 2.0;
    return _122.ProjMat[3].z / (deviceDepth + _122.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float _180 = deviceToLinearDepth(param);
    float fragmentLinearDepth = _180;
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
    int _263 = 0;
    if (shouldSampleA)
    {
        _263 = treeIndexB - 1;
    }
    else
    {
        _263 = treeIndexB;
    }
    int treeIndexA = _263;
    treeIndexB += 8;
    treeIndexA += 8;
    float sampleB = averageAbsorbance;
    float sampleA = shouldSampleA ? averageAbsorbance : 0.0;
    float _366 = 0.0;
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
                _366 = differenceCoefficientB;
            }
            else
            {
                _366 = coefficients[parentIndexA];
            }
            float differenceCoefficientA = _366;
            int isRightHalfA = treeIndexA & 1;
            int waveletSignA = 1 - (isRightHalfA << 1);
            sampleA -= ((waveletHeightScale * differenceCoefficientA) * float(waveletSignA));
            treeIndexA = parentIndexA;
        }
    }
    float _396 = 0.0;
    if (depthMeasuredInBins >= 8.0)
    {
        _396 = 1.0;
    }
    else
    {
        _396 = fract(depthMeasuredInBins);
    }
    float lerpAlpha = _396;
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

vec4 calculateFinalColor(inout vec4 color)
{
    vec4 param = color;
    color = sampleColorForAccumulation(param);
    return color;
}

void main()
{
    float param = sphericalVertexDistance;
    float param_1 = cylindricalVertexDistance;
    float param_2 = _525.FogEnvironmentalStart;
    float param_3 = _525.FogEnvironmentalEnd;
    float param_4 = _525.FogRenderDistanceStart;
    float param_5 = _525.FogRenderDistanceEnd;
    vec4 color = (vertexColor * _516.ColorModulator) * (1.0 - total_fog_value(param, param_1, param_2, param_3, param_4, param_5));
    vec4 param_6 = color;
    vec4 _549 = calculateFinalColor(param_6);
    fragColor = _549;
}

