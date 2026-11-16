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
} _138;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _307;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _558;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _567;

uniform sampler2D DepthBoundsSampler;

in vec3 c164_ray;
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

bool c164_open_air(float environmentalStart, float environmentalEnd)
{
    return ((environmentalEnd > 192.0) && (environmentalEnd < 1000000015047466219876688855040.0)) && (environmentalStart > (-4.0));
}

vec3 c164_direction()
{
    float l = length(c164_ray);
    vec3 _121 = vec3(0.0);
    if (l > 9.9999999747524270787835121154785e-07)
    {
        _121 = c164_ray / vec3(l);
    }
    else
    {
        _121 = vec3(0.0, 0.0, 1.0);
    }
    return _121;
}

float c164_height()
{
    return (float(_138.CameraBlockPos.y) - _138.CameraOffset.y) - 172.0;
}

float c164_depth(float _distance, float rise)
{
    float height = max(c164_height(), 0.0);
    float _161 = 0.0;
    if (rise < 0.0)
    {
        _161 = min(_distance, height / max(-rise, 9.9999997473787516355514526367188e-06));
    }
    else
    {
        _161 = _distance;
    }
    float reach = _161;
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

float toAbsorbance(float transmittance)
{
    return clamp(-log(max(transmittance, 9.9999997473787516355514526367188e-05)), 0.0, 4.0);
}

float deviceToLinearDepth(inout float deviceDepth)
{
    deviceDepth = (deviceDepth - 0.5) * 2.0;
    return _307.ProjMat[3].z / (deviceDepth + _307.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float _355 = deviceToLinearDepth(param);
    float fragmentLinearDepth = _355;
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
    float param_2 = _567.FogEnvironmentalStart;
    float param_3 = _567.FogEnvironmentalEnd;
    float param_4 = _567.FogRenderDistanceStart;
    float param_5 = _567.FogRenderDistanceEnd;
    vec4 color = (vertexColor * _558.ColorModulator) * (1.0 - total_fog_value(param, param_1, param_2, param_3, param_4, param_5));
    float param_6 = gl_FragCoord.z;
    float param_7 = color.w;
    executeAlphaOnlyPhase(param_6, param_7);
}

