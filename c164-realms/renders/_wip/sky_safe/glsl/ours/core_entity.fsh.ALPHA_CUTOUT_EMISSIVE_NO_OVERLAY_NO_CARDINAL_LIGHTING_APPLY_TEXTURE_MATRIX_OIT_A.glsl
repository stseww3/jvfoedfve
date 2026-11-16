#version 330

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _60;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _81;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _87;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _119;

uniform sampler2D Sampler0;
uniform sampler2D DepthBoundsSampler;

in vec2 texCoord0;
in vec4 vertexColor;
in vec3 c164_ray;
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
    color *= (faceVertexColor * _60.ColorModulator);
    float param = gl_FragCoord.z;
    float param_1 = color.w;
    executeAlphaOnlyPhase(param, param_1);
}

