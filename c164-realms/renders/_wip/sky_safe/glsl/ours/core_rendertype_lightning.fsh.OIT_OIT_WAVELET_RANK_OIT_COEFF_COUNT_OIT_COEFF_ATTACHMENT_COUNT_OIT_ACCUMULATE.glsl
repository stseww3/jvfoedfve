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
} _159;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _326;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _712;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _721;

uniform sampler2D DepthBoundsSampler;
uniform sampler2D Coeff0;
uniform sampler2D Coeff1;

in vec3 c164_ray;
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

bool c164_open_air(float environmentalStart, float environmentalEnd)
{
    return ((environmentalEnd > 192.0) && (environmentalEnd < 1000000015047466219876688855040.0)) && (environmentalStart > (-4.0));
}

vec3 c164_direction()
{
    float l = length(c164_ray);
    vec3 _143 = vec3(0.0);
    if (l > 9.9999999747524270787835121154785e-07)
    {
        _143 = c164_ray / vec3(l);
    }
    else
    {
        _143 = vec3(0.0, 0.0, 1.0);
    }
    return _143;
}

float c164_height()
{
    return (float(_159.CameraBlockPos.y) - _159.CameraOffset.y) - 172.0;
}

float c164_depth(float _distance, float rise)
{
    float height = max(c164_height(), 0.0);
    float _181 = 0.0;
    if (rise < 0.0)
    {
        _181 = min(_distance, height / max(-rise, 9.9999997473787516355514526367188e-06));
    }
    else
    {
        _181 = _distance;
    }
    float reach = _181;
    float a = (reach * rise) / 12.0;
    float start = exp((-height) / 12.0);
    float mist = 0.0;
    if (abs(a) < 0.001000000047497451305389404296875)
    {
        mist = (reach * start) * (1.0 - (0.5 * a));
    }
    else
    {
        mist = ((start - exp((-max(height + (reach * rise), 0.0)) / 12.0)) * 12.0) / rise;
    }
    return (_distance / 1600.0) + (mist / 587.0);
}

float c164_fogged(float _distance, float rise)
{
    float param = _distance;
    float param_1 = rise;
    return 1.0 - exp(-c164_depth(param, param_1));
}

float c164_levelled()
{
    float far = clamp((length(c164_ray.xz) - 60.0) / 90.0, 0.0, 1.0);
    float low = clamp((12.0 - (c164_height() + c164_ray.y)) / 4.0, 0.0, 1.0);
    return far * low;
}

float total_fog_value(float sphericalVertexDistance_1, float cylindricalVertexDistance_1, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd)
{
    float param = cylindricalVertexDistance_1;
    float param_1 = renderDistanceStart;
    float param_2 = renderDistanceEnd;
    float edge = linear_fog_value(param, param_1, param_2);
    float param_3 = environmentalStart;
    float param_4 = environmantalEnd;
    if (c164_open_air(param_3, param_4))
    {
        float param_5 = sphericalVertexDistance_1;
        float param_6 = c164_direction().y;
        return 1.0 - ((1.0 - c164_fogged(param_5, param_6)) * (1.0 - max(edge, c164_levelled())));
    }
    float param_7 = sphericalVertexDistance_1;
    float param_8 = environmentalStart;
    float param_9 = environmantalEnd;
    return max(linear_fog_value(param_7, param_8, param_9), edge);
}

float deviceToLinearDepth(inout float deviceDepth)
{
    deviceDepth = (deviceDepth - 0.5) * 2.0;
    return _326.ProjMat[3].z / (deviceDepth + _326.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float _378 = deviceToLinearDepth(param);
    float fragmentLinearDepth = _378;
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
    int _461 = 0;
    if (shouldSampleA)
    {
        _461 = treeIndexB - 1;
    }
    else
    {
        _461 = treeIndexB;
    }
    int treeIndexA = _461;
    treeIndexB += 8;
    treeIndexA += 8;
    float sampleB = averageAbsorbance;
    float sampleA = shouldSampleA ? averageAbsorbance : 0.0;
    float _564 = 0.0;
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
                _564 = differenceCoefficientB;
            }
            else
            {
                _564 = coefficients[parentIndexA];
            }
            float differenceCoefficientA = _564;
            int isRightHalfA = treeIndexA & 1;
            int waveletSignA = 1 - (isRightHalfA << 1);
            sampleA -= ((waveletHeightScale * differenceCoefficientA) * float(waveletSignA));
            treeIndexA = parentIndexA;
        }
    }
    float _594 = 0.0;
    if (depthMeasuredInBins >= 8.0)
    {
        _594 = 1.0;
    }
    else
    {
        _594 = fract(depthMeasuredInBins);
    }
    float lerpAlpha = _594;
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
    float param_2 = _721.FogEnvironmentalStart;
    float param_3 = _721.FogEnvironmentalEnd;
    float param_4 = _721.FogRenderDistanceStart;
    float param_5 = _721.FogRenderDistanceEnd;
    vec4 color = (vertexColor * _712.ColorModulator) * (1.0 - total_fog_value(param, param_1, param_2, param_3, param_4, param_5));
    vec4 param_6 = color;
    vec4 _745 = calculateFinalColor(param_6);
    fragColor = _745;
}

