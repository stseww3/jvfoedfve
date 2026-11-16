#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _45;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _343;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _359;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _365;

uniform sampler2D DepthBoundsSampler;
uniform sampler2D Sampler0;
uniform sampler2D DissolveMaskSampler;

layout(location = 0) out vec4 coeff[2];
in vec2 texCoord0;
in vec4 vertexPerFaceColorFront;
in vec4 vertexPerFaceColorBack;
in vec3 c164_ray;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec4 lightMapColor;
in vec4 overlayColor;

float toAbsorbance(float transmittance)
{
    return clamp(-log(max(transmittance, 9.9999997473787516355514526367188e-05)), 0.0, 4.0);
}

float deviceToLinearDepth(inout float deviceDepth)
{
    deviceDepth = (deviceDepth - 0.5) * 2.0;
    return _45.ProjMat[3].z / (deviceDepth + _45.ProjMat[2].z);
}

float normalizeDepth(float fragmentDeviceDepth)
{
    vec4 depthBoundsSample = texelFetch(DepthBoundsSampler, ivec2(gl_FragCoord.xy), 0);
    float closestBoundLinearDepthNegated = depthBoundsSample.x;
    float closestBoundLinearDepth = -closestBoundLinearDepthNegated;
    float furthestBoundLinearDepth = depthBoundsSample.y;
    float param = fragmentDeviceDepth;
    float _102 = deviceToLinearDepth(param);
    float fragmentLinearDepth = _102;
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
    vec4 color = texture(Sampler0, texCoord0);
    if (color.w < 0.100000001490116119384765625)
    {
        discard;
    }
    vec4 faceVertexColor = gl_FrontFacing ? vertexPerFaceColorFront : vertexPerFaceColorBack;
    if (faceVertexColor.w < texture(DissolveMaskSampler, texCoord0).w)
    {
        discard;
    }
    faceVertexColor.w = 1.0;
    color *= (faceVertexColor * _343.ColorModulator);
    float param = gl_FragCoord.z;
    float param_1 = color.w;
    executeAlphaOnlyPhase(param, param_1);
}

