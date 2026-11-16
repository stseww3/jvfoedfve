#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _106;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _112;

layout(std140) uniform Lighting
{
    vec3 Light0_Direction;
    vec3 Light1_Direction;
} _138;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _173;

layout(location = 0) in vec3 Position;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;
layout(location = 5) in vec3 Normal;
out vec4 vertexPerFaceColorBack;
layout(location = 1) in vec4 Color;
out vec4 vertexPerFaceColorFront;
out vec2 texCoord0;
layout(location = 2) in vec2 UV0;
layout(location = 3) in ivec2 UV1;
layout(location = 4) in ivec2 UV2;
out vec4 lightMapColor;
out vec4 overlayColor;

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

vec2 minecraft_compute_light(vec3 lightDir0, vec3 lightDir1, vec3 normal)
{
    return vec2(dot(lightDir0, normal), dot(lightDir1, normal));
}

vec4 minecraft_mix_light_separate(vec2 light, vec4 color)
{
    vec2 lightValue = max(vec2(0.0), light);
    float lightAccum = min(1.0, ((lightValue.x + lightValue.y) * 0.60000002384185791015625) + 0.4000000059604644775390625);
    return vec4(color.xyz * lightAccum, color.w);
}

void main()
{
    gl_Position = (_106.ProjMat * _112.ModelViewMat) * vec4(Position, 1.0);
    vec3 param = Position;
    sphericalVertexDistance = fog_spherical_distance(param);
    vec3 param_1 = Position;
    cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    vec3 param_2 = _138.Light0_Direction;
    vec3 param_3 = _138.Light1_Direction;
    vec3 param_4 = Normal;
    vec2 light = minecraft_compute_light(param_2, param_3, param_4);
    vec2 param_5 = -light;
    vec4 param_6 = Color;
    vertexPerFaceColorBack = minecraft_mix_light_separate(param_5, param_6);
    vec2 param_7 = light;
    vec4 param_8 = Color;
    vertexPerFaceColorFront = minecraft_mix_light_separate(param_7, param_8);
    texCoord0 = UV0;
}

