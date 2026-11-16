#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _101;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _362;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _371;

uniform sampler2D DepthBoundsSampler;

layout(location = 0) out vec4 coeff[2];
in vec4 vertexColor;
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

float toAbsorbance(float transmittance)
{
    return clamp(-log(max(transmittance, 9.9999997473787516355514526367188e-05)), 0.0, 4.0);
}

float deviceToLinearDepth(inout float deviceDepth)
{
    deviceDepth = (deviceDepth - 0.5) * 2.0;
    return _101.ProjMat[3].z / (deviceDepth + _101.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float _157 = deviceToLinearDepth(param);
    float fragmentLinearDepth = _157;
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

void addTransmittance(float transmittance)
{
    float coefficients[8];
    for (int i = 0; i < 8; i++)
    {
        coefficients[i] = 0.0;
    }
    float param = transmittance;
    float absorbance = toAbsorbance(param);
    float param_1 = gl_FragCoord.z;
    float originalDepth = normalizeDepth(param_1);
    float depth = (originalDepth * 7.0) / 8.0;
    float averageAbsorbance = absorbance * (1.0 - depth);
    coefficients[0] = averageAbsorbance;
    int depthBinIndex = int(floor(originalDepth * 7.0));
    int treeIndex = depthBinIndex + 8;
    for (int waveletLevel = 0; waveletLevel <= 3; waveletLevel++)
    {
        int power = 3 - waveletLevel;
        int parentIndex = treeIndex >> 1;
        float indexAtParentLevel = float(parentIndex & ((1 << power) - 1));
        int isRightHalf = treeIndex & 1;
        int waveletSign = 1 - (isRightHalf << 1);
        float waveletWidth = exp2(float(-power));
        float waveletHeightScale = exp2(float(power) * 0.5);
        float depthOffsetRelativeToWavelet = depth - (waveletWidth * indexAtParentLevel);
        float distanceFromWaveletEdge = (float(isRightHalf) * waveletWidth) + (float(waveletSign) * depthOffsetRelativeToWavelet);
        float differenceCoefficient = (distanceFromWaveletEdge * waveletHeightScale) * absorbance;
        coefficients[parentIndex] = differenceCoefficient;
        treeIndex = parentIndex;
    }
    for (int attachmentIndex = 0; attachmentIndex < 2; attachmentIndex++)
    {
        for (int i_1 = 0; i_1 < 4; i_1++)
        {
            coeff[attachmentIndex][i_1] = coefficients[(attachmentIndex * 4) + i_1];
        }
    }
}

void executeAlphaOnlyPhase(float deviceDepth, float alpha)
{
    float param = 1.0 - alpha;
    addTransmittance(param);
}

void main()
{
    float param = sphericalVertexDistance;
    float param_1 = cylindricalVertexDistance;
    float param_2 = _371.FogEnvironmentalStart;
    float param_3 = _371.FogEnvironmentalEnd;
    float param_4 = _371.FogRenderDistanceStart;
    float param_5 = _371.FogRenderDistanceEnd;
    vec4 color = (vertexColor * _362.ColorModulator) * (1.0 - total_fog_value(param, param_1, param_2, param_3, param_4, param_5));
    float param_6 = gl_FragCoord.z;
    float param_7 = color.w;
    executeAlphaOnlyPhase(param_6, param_7);
}

