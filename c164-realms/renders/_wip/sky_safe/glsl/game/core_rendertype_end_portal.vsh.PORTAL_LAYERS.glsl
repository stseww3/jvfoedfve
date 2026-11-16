#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _87;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _93;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _124;

layout(location = 0) in vec3 Position;
out vec4 texProj0;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;

vec4 projection_from_position(vec4 position)
{
    vec4 projection = position * 0.5;
    float _53 = projection.x;
    float _56 = projection.w;
    float _59 = projection.y;
    float _61 = projection.w;
    vec2 _63 = vec2(_53 + _56, _59 + _61);
    projection.x = _63.x;
    projection.y = _63.y;
    projection.z = position.zw.x;
    projection.w = position.zw.y;
    return projection;
}

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
    gl_Position = (_87.ProjMat * _93.ModelViewMat) * vec4(Position, 1.0);
    vec4 param = gl_Position;
    texProj0 = projection_from_position(param);
    vec3 param_1 = Position;
    sphericalVertexDistance = fog_spherical_distance(param_1);
    vec3 param_2 = Position;
    cylindricalVertexDistance = fog_cylindrical_distance(param_2);
}

