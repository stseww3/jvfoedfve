#version 330

layout(std140) uniform ChunkSection
{
    ivec3 ChunkPosition;
    float ChunkVisibility;
} _80;

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
} _105;

layout(std140) uniform TerrainUniform
{
    mat4 ModelViewMat;
    ivec2 TextureSize;
} _111;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _165;

uniform sampler2D Sampler2;

layout(location = 0) in vec3 Position;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
out vec4 vertexColor;
layout(location = 1) in vec4 Color;
layout(location = 3) in ivec2 UV2;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;
out float chunkVisibility;

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

vec4 sample_lightmap(sampler2D lightMap, ivec2 uv)
{
    return textureLod(lightMap, clamp((vec2(uv) / vec2(256.0)) + vec2(0.03125), vec2(0.03125), vec2(0.96875)), 0.0);
}

void main()
{
    vec3 pos = (Position + vec3(_80.ChunkPosition - _87.CameraBlockPos)) + _87.CameraOffset;
    gl_Position = (_105.ProjMat * _111.ModelViewMat) * vec4(pos, 1.0);
    vec3 param = pos;
    sphericalVertexDistance = fog_spherical_distance(param);
    vec3 param_1 = pos;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    ivec2 param_2 = UV2;
    vertexColor = Color * sample_lightmap(Sampler2, param_2);
    texCoord0 = UV0;
    float dist = length(pos);
    chunkVisibility = mix(1.0, _80.ChunkVisibility, clamp((dist - 16.0) / 16.0, 0.0, 1.0));
}

