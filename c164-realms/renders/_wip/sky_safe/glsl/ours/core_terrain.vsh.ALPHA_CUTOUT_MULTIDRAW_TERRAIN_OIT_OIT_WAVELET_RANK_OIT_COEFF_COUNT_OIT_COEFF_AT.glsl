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
} _57;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _78;

layout(std140) uniform TerrainUniform
{
    mat4 ModelViewMat;
    ivec2 TextureSize;
} _85;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _132;

out vec3 c164_ray;
layout(location = 0) in vec3 Position;
layout(location = 4) in ivec3 ChunkPosition;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
layout(location = 1) in vec4 Color;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;
out float chunkVisibility;
layout(location = 5) in float ChunkVisibility;
layout(location = 3) in ivec2 UV2;

float fog_spherical_distance(vec3 pos)
{
    c164_ray = pos;
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
    vec3 pos = (Position + vec3(ChunkPosition - _57.CameraBlockPos)) + _57.CameraOffset;
    gl_Position = (_78.ProjMat * _85.ModelViewMat) * vec4(pos, 1.0);
    vec3 param = pos;
    float _102 = fog_spherical_distance(param);
    sphericalVertexDistance = _102;
    vec3 param_1 = pos;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    vertexColor = Color;
    texCoord0 = UV0;
    float dist = length(pos);
    chunkVisibility = mix(1.0, ChunkVisibility, clamp((dist - 16.0) / 16.0, 0.0, 1.0));
}

