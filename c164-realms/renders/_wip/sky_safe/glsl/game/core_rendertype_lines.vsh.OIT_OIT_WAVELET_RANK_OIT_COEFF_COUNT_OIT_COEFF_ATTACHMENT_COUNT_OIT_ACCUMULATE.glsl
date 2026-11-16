#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _48;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _65;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _118;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _210;

layout(location = 0) in vec3 Position;
layout(location = 2) in vec3 Normal;
layout(location = 3) in float LineWidth;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
layout(location = 1) in vec4 Color;

float fog_spherical_distance(vec3 pos)
{
    return length(pos);
}

float fog_cylindrical_distance(vec3 pos)
{
    float distXZ = length(pos.xz);
    float distY = abs(pos.y);
    return max(distXZ, distY);
}

void main()
{
    vec4 linePosStart = ((_48.ProjMat * mat4(vec4(0.99609375, 0.0, 0.0, 0.0), vec4(0.0, 0.99609375, 0.0, 0.0), vec4(0.0, 0.0, 0.99609375, 0.0), vec4(0.0, 0.0, 0.0, 1.0))) * _65.ModelViewMat) * vec4(Position, 1.0);
    vec4 linePosEnd = ((_48.ProjMat * mat4(vec4(0.99609375, 0.0, 0.0, 0.0), vec4(0.0, 0.99609375, 0.0, 0.0), vec4(0.0, 0.0, 0.99609375, 0.0), vec4(0.0, 0.0, 0.0, 1.0))) * _65.ModelViewMat) * vec4(Position + Normal, 1.0);
    vec3 ndc1 = linePosStart.xyz / vec3(linePosStart.w);
    vec3 ndc2 = linePosEnd.xyz / vec3(linePosEnd.w);
    vec2 lineScreenDirection = normalize((ndc2.xy - ndc1.xy) * _118.ScreenSize);
    vec2 lineOffset = (vec2(-lineScreenDirection.y, lineScreenDirection.x) * LineWidth) / _118.ScreenSize;
    if (lineOffset.x < 0.0)
    {
        lineOffset *= (-1.0);
    }
    if ((gl_VertexID % 2) == 0)
    {
        gl_Position = vec4((ndc1 + vec3(lineOffset, 0.0)) * linePosStart.w, linePosStart.w);
    }
    else
    {
        gl_Position = vec4((ndc1 - vec3(lineOffset, 0.0)) * linePosStart.w, linePosStart.w);
    }
    vec3 param = Position;
    sphericalVertexDistance = fog_spherical_distance(param);
    vec3 param_1 = Position;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    vertexColor = Color;
}

