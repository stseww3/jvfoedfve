#version 330

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _59;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _80;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _83;

uniform sampler2D Sampler0;
uniform sampler2D DepthBoundsSampler;

in vec2 texCoord0;
in vec4 vertexColor;
layout(location = 0) out vec4 coeff[2];
in float sphericalVertexDistance;
in float cylindricalVertexDistance;

void executeAlphaOnlyPhase(float deviceDepth, float alpha)
{
    discard;
}

void main()
{
    vec4 color = texture(Sampler0, texCoord0);
    color.w = min(0.9900000095367431640625, color.w);
    if (color.w < 0.100000001490116119384765625)
    {
        discard;
    }
    vec4 faceVertexColor = vertexColor;
    color *= (faceVertexColor * _59.ColorModulator);
    float param = gl_FragCoord.z;
    float param_1 = color.w;
    executeAlphaOnlyPhase(param, param_1);
}

