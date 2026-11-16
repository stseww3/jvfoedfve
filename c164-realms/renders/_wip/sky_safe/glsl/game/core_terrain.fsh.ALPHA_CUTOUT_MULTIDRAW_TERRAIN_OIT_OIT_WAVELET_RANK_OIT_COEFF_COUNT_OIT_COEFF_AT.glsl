#version 330

const vec2 _237[4] = vec2[](vec2(0.125, 0.375), vec2(-0.125, -0.375), vec2(0.375, -0.125), vec2(-0.375, 0.125));

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _297;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _543;

layout(std140) uniform TerrainUniform
{
    mat4 ModelViewMat;
    ivec2 TextureSize;
} _557;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _599;

uniform sampler2D DepthBoundsSampler;
uniform sampler2D Sampler0;

layout(location = 0) out vec4 coeff[2];
in vec2 texCoord0;
in vec4 vertexColor;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in float chunkVisibility;

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
        vec2 sampleUV = uv + (_237[i] * pixelSize);
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
    vec4 _283 = sampleNearest(source, param, param_1, param_2, param_3, param_4);
    vec4 nearestColor = _283;
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
    vec4 _129 = sampleNearest(source, param, param_1, param_2, param_3, param_4);
    return _129;
}

float toAbsorbance(float transmittance)
{
    return clamp(-log(max(transmittance, 9.9999997473787516355514526367188e-05)), 0.0, 4.0);
}

float deviceToLinearDepth(inout float deviceDepth)
{
    deviceDepth = (deviceDepth - 0.5) * 2.0;
    return _297.ProjMat[3].z / (deviceDepth + _297.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float _343 = deviceToLinearDepth(param);
    float fragmentLinearDepth = _343;
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
    vec4 _549 = vec4(0.0);
    if (_543.UseRgss == 1)
    {
        vec2 param = texCoord0;
        vec2 param_1 = vec2(1.0) / vec2(_557.TextureSize);
        _549 = sampleRGSS(Sampler0, param, param_1);
    }
    else
    {
        vec2 param_2 = texCoord0;
        vec2 param_3 = vec2(1.0) / vec2(_557.TextureSize);
        _549 = sampleNearest(Sampler0, param_2, param_3);
    }
    vec4 color = _549 * vertexColor;
    if (color.w < 0.100000001490116119384765625)
    {
        discard;
    }
    float param_4 = gl_FragCoord.z;
    float param_5 = color.w;
    executeAlphaOnlyPhase(param_4, param_5);
}

