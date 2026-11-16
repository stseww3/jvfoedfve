#version 330

layout(std140) uniform Projection
{
    mat4 ProjMat;
} _67;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _75;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _172;

out vec3 c164_ray;
layout(location = 0) in vec3 Position;
out float sphericalVertexDistance;
out float cylindricalVertexDistance;

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
    if (Position.y > 0.0)
    {
        vec2 corner = Position.xz / vec2(256.0);
        mat4 back = inverse(_67.ProjMat * _75.ModelViewMat);
        vec4 near = back * vec4(corner, 0.25, 1.0);
        vec4 far = back * vec4(corner, 0.75, 1.0);
        vec3 ray = (far.xyz * near.w) - (near.xyz * far.w);
        vec3 forward = -vec3(_75.ModelViewMat[0].z, _75.ModelViewMat[1].z, _75.ModelViewMat[2].z);
        vec3 _128 = vec3(0.0);
        if (dot(ray, forward) < 0.0)
        {
            _128 = -ray;
        }
        else
        {
            _128 = ray;
        }
        c164_ray = _128;
        gl_Position = vec4(corner, 0.5, 1.0);
        sphericalVertexDistance = -1.0;
        cylindricalVertexDistance = -1.0;
    }
    else
    {
        gl_Position = (_67.ProjMat * _75.ModelViewMat) * vec4(Position, 1.0);
        vec3 param = Position;
        float _166 = fog_spherical_distance(param);
        sphericalVertexDistance = _166;
        vec3 param_1 = Position;
        cylindricalVertexDistance = fog_cylindrical_distance(param_1);
    }
}

