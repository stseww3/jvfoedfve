#version 330

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _174;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _236;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _653;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _1078;

uniform sampler2D DepthBoundsSampler;
uniform sampler2D Coeff0;
uniform sampler2D Coeff1;
uniform sampler2D Sampler0;

in vec3 c164_ray;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec2 texCoord0;
in vec4 vertexColor;
layout(location = 0) out vec4 fragColor;

float deviceToLinearDepth(inout float deviceDepth)
{
    deviceDepth = (deviceDepth - 0.5) * 2.0;
    return _653.ProjMat[3].z / (deviceDepth + _653.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float _702 = deviceToLinearDepth(param);
    float fragmentLinearDepth = _702;
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
    int _784 = 0;
    if (shouldSampleA)
    {
        _784 = treeIndexB - 1;
    }
    else
    {
        _784 = treeIndexB;
    }
    int treeIndexA = _784;
    treeIndexB += 8;
    treeIndexA += 8;
    float sampleB = averageAbsorbance;
    float sampleA = shouldSampleA ? averageAbsorbance : 0.0;
    float _887 = 0.0;
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
                _887 = differenceCoefficientB;
            }
            else
            {
                _887 = coefficients[parentIndexA];
            }
            float differenceCoefficientA = _887;
            int isRightHalfA = treeIndexA & 1;
            int waveletSignA = 1 - (isRightHalfA << 1);
            sampleA -= ((waveletHeightScale * differenceCoefficientA) * float(waveletSignA));
            treeIndexA = parentIndexA;
        }
    }
    float _917 = 0.0;
    if (depthMeasuredInBins >= 8.0)
    {
        _917 = 1.0;
    }
    else
    {
        _917 = fract(depthMeasuredInBins);
    }
    float lerpAlpha = _917;
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

bool c164_open_air(float environmentalStart, float environmentalEnd)
{
    return ((environmentalEnd > 192.0) && (environmentalEnd < 1000000015047466219876688855040.0)) && (environmentalStart > (-4.0));
}

bool c164_open()
{
    float param = _174.FogEnvironmentalStart;
    float param_1 = _174.FogEnvironmentalEnd;
    return c164_open_air(param, param_1);
}

vec3 c164_direction()
{
    float l = length(c164_ray);
    vec3 _195 = vec3(0.0);
    if (l > 9.9999999747524270787835121154785e-07)
    {
        _195 = c164_ray / vec3(l);
    }
    else
    {
        _195 = vec3(0.0, 0.0, 1.0);
    }
    return _195;
}

float c164_height()
{
    return (float(_236.CameraBlockPos.y) - _236.CameraOffset.y) - 172.0;
}

vec3 c164_level(vec3 d)
{
    float l = length(d.xz);
    vec3 _215 = vec3(0.0);
    if (l > 9.9999997473787516355514526367188e-05)
    {
        _215 = vec3(d.x / l, 0.0, d.z / l);
    }
    else
    {
        _215 = vec3(0.0, 0.0, 1.0);
    }
    return _215;
}

vec3 c164_ring(vec3 d)
{
    float stain = 0.3499999940395355224609375 * max(0.0, dot(d, vec3(-1.0, 0.0, 0.0)));
    return mix(mix(vec3(0.2627449929714202880859375, 0.26666700839996337890625, 0.5215690135955810546875), vec3(0.91372501850128173828125, 0.4862749874591827392578125, 0.2980389893054962158203125), vec3(stain)), vec3(0.02745099924504756927490234375, 0.0588239990174770355224609375, 0.16470600664615631103515625), vec3(0.1867119967937469482421875));
}

float c164_fan(vec3 d)
{
    float lift = (3.0 * d.y) / 0.3499999940395355224609375;
    float k = dot(d, vec3(-1.0, 0.0, 0.0)) - lift;
    if (k <= 0.0)
    {
        return 0.0;
    }
    return (0.4199999868869781494140625 * k) / (length(vec2(lift, dot(d, vec3(0.0, 0.0, 1.0)))) + (1.2000000476837158203125 * k));
}

vec3 c164_band(vec3 d)
{
    vec3 param = d;
    vec3 level = c164_level(param);
    float _421 = 0.0;
    if (d.y < 0.0)
    {
        _421 = 1.0;
    }
    else
    {
        _421 = 1.0 - smoothstep(0.0, 0.0350000001490116119384765625, d.y);
    }
    float soft = _421;
    vec3 param_1 = (d.y < 0.0) ? level : d;
    vec3 param_2 = level;
    return mix(c164_ring(param_1), vec3(0.91372501850128173828125, 0.4862749874591827392578125, 0.2980389893054962158203125), vec3(c164_fan(param_2) * soft));
}

float c164_depth(float _distance, float rise)
{
    float height = max(c164_height(), 0.0);
    float _256 = 0.0;
    if (rise < 0.0)
    {
        _256 = min(_distance, height / max(-rise, 9.9999997473787516355514526367188e-06));
    }
    else
    {
        _256 = _distance;
    }
    float reach = _256;
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

vec3 c164_sea(vec3 d)
{
    float reach = max(c164_height(), 0.5) / max(-d.y, 9.9999997473787516355514526367188e-06);
    vec3 param = d;
    float param_1 = reach;
    float param_2 = d.y;
    return mix(vec3(0.337255001068115234375, 0.360783994197845458984375, 0.549019992351531982421875), c164_band(param), vec3(c164_fogged(param_1, param_2)));
}

vec3 c164_behind(vec3 d)
{
    vec3 _476 = vec3(0.0);
    if (d.y < 0.0)
    {
        vec3 param = d;
        _476 = c164_sea(param);
    }
    else
    {
        vec3 param_1 = d;
        _476 = c164_band(param_1);
    }
    return _476;
}

vec4 c164_fog_color()
{
    if (!c164_open())
    {
        return _174.GameFogColor;
    }
    vec3 param = c164_direction();
    return vec4(c164_behind(param), _174.GameFogColor.w);
}

float c164_levelled()
{
    float far = clamp((length(c164_ray.xz) - 60.0) / 90.0, 0.0, 1.0);
    float low = clamp((12.0 - (c164_height() + c164_ray.y)) / 4.0, 0.0, 1.0);
    return far * low;
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

vec4 apply_fog(vec4 inColor, float sphericalVertexDistance_1, float cylindricalVertexDistance_1, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd, vec4 fogColor)
{
    float param = environmentalStart;
    float param_1 = environmantalEnd;
    if (c164_open_air(param, param_1))
    {
        vec3 d = c164_direction();
        vec3 param_2 = d;
        float weight = dot(fogColor.xyz, vec3(1.0)) / max(dot(c164_behind(param_2), vec3(1.0)), 9.9999999747524270787835121154785e-07);
        vec3 param_3 = d;
        float param_4 = sphericalVertexDistance_1;
        float param_5 = d.y;
        vec3 hazed = mix(inColor.xyz, c164_band(param_3) * weight, vec3(c164_fogged(param_4, param_5) * fogColor.w));
        float param_6 = cylindricalVertexDistance_1;
        float param_7 = renderDistanceStart;
        float param_8 = renderDistanceEnd;
        float gone = max(c164_levelled(), linear_fog_value(param_6, param_7, param_8));
        return vec4(mix(hazed, fogColor.xyz, vec3(gone * fogColor.w)), inColor.w);
    }
    float param_9 = sphericalVertexDistance_1;
    float param_10 = cylindricalVertexDistance_1;
    float param_11 = environmentalStart;
    float param_12 = environmantalEnd;
    float param_13 = renderDistanceStart;
    float param_14 = renderDistanceEnd;
    float fogValue = total_fog_value(param_9, param_10, param_11, param_12, param_13, param_14);
    return vec4(mix(inColor.xyz, fogColor.xyz, vec3(fogValue * fogColor.w)), inColor.w);
}

vec4 calculateFinalColor(inout vec4 color)
{
    vec4 param = color;
    color = sampleColorForAccumulation(param);
    vec4 fogColor = vec4(c164_fog_color().xyz * color.w, c164_fog_color().w);
    vec4 param_1 = color;
    float param_2 = sphericalVertexDistance;
    float param_3 = cylindricalVertexDistance;
    float param_4 = _174.FogEnvironmentalStart;
    float param_5 = _174.FogEnvironmentalEnd;
    float param_6 = _174.FogRenderDistanceStart;
    float param_7 = _174.FogRenderDistanceEnd;
    vec4 param_8 = fogColor;
    color = apply_fog(param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8);
    return color;
}

void main()
{
    vec4 texColor = texture(Sampler0, texCoord0);
    vec4 color = (texColor * vertexColor) * _1078.ColorModulator;
    if (color.w < 0.100000001490116119384765625)
    {
        discard;
    }
    vec4 param = color;
    vec4 _1093 = calculateFinalColor(param);
    fragColor = _1093;
}

