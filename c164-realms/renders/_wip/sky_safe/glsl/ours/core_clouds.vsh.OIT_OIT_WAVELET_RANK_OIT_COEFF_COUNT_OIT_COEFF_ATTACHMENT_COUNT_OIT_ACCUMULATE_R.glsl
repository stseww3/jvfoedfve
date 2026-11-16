#version 330

const vec4 _196[6] = vec4[](vec4(0.699999988079071044921875, 0.699999988079071044921875, 0.699999988079071044921875, 1.0), vec4(1.0), vec4(0.800000011920928955078125, 0.800000011920928955078125, 0.800000011920928955078125, 1.0), vec4(0.800000011920928955078125, 0.800000011920928955078125, 0.800000011920928955078125, 1.0), vec4(0.89999997615814208984375, 0.89999997615814208984375, 0.89999997615814208984375, 1.0), vec4(0.89999997615814208984375, 0.89999997615814208984375, 0.89999997615814208984375, 1.0));

layout(std140) uniform CloudInfo
{
    vec4 CloudColor;
    vec3 CloudOffset;
    vec3 CellSize;
} _148;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _209;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _213;

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _216;

uniform isamplerBuffer CloudFaces;

out vec3 c164_ray;
out float vertexDistance;
out vec4 vertexColor;

vec3 vertex(int index)
{
    vec3 pos = vec3(0.0);
    pos.x = float((15744195 >> index) & 1);
    pos.y = float((6711024 >> index) & 1);
    pos.z = float((12841062 >> index) & 1);
    return pos;
}

float fog_spherical_distance(vec3 pos)
{
    c164_ray = pos;
    return length(pos);
}

void main()
{
    int quadVertex = gl_VertexID % 4;
    int index = (gl_VertexID / 4) * 3;
    int cellX = texelFetch(CloudFaces, index).x;
    int cellZ = texelFetch(CloudFaces, index + 1).x;
    int dirAndFlags = texelFetch(CloudFaces, index + 2).x;
    int direction = dirAndFlags & 7;
    bool isInsideFace = (dirAndFlags & 16) == 16;
    bool useTopColor = (dirAndFlags & 32) == 32;
    cellX = (cellX << 1) | ((dirAndFlags & 128) >> 7);
    cellZ = (cellZ << 1) | ((dirAndFlags & 64) >> 6);
    int _132 = 0;
    if (isInsideFace)
    {
        _132 = 3 - quadVertex;
    }
    else
    {
        _132 = quadVertex;
    }
    int param = (direction * 4) + _132;
    vec3 faceVertex = vertex(param);
    vec3 pos = ((faceVertex * _148.CellSize) + (vec3(float(cellX), 0.0, float(cellZ)) * _148.CellSize)) + _148.CloudOffset;
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    vec3 param_1 = pos;
    float _179 = fog_spherical_distance(param_1);
    vertexDistance = _179;
    vec4 _183 = vec4(0.0);
    if (useTopColor)
    {
        _183 = vec4(1.0);
    }
    else
    {
        _183 = _196[direction];
    }
    vertexColor = _183 * _148.CloudColor;
}

