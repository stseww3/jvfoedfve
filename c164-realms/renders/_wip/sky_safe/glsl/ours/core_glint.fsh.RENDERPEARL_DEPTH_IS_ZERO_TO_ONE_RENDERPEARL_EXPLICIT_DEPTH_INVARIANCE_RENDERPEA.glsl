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
} _114;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _290;

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _308;

uniform sampler2D Sampler0;

in vec3 c164_ray;
in vec2 texCoord0;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
layout(location = 0) out vec4 fragColor;

float linear_fog_value(float vertexDistance, float fogStart, float fogEnd)
{
    if (vertexDistance <= fogStart)
    {
        return 0.0;
    }
    else
    {
        if (vertexDistance >= fogEnd)
        {
            return 1.0;
        }
    }
    return (vertexDistance - fogStart) / (fogEnd - fogStart);
}

bool c164_open_air(float environmentalStart, float environmentalEnd)
{
    return ((environmentalEnd > 192.0) && (environmentalEnd < 1000000015047466219876688855040.0)) && (environmentalStart > (-4.0));
}

vec3 c164_direction()
{
    float l = length(c164_ray);
    vec3 _97 = vec3(0.0);
    if (l > 9.9999999747524270787835121154785e-07)
    {
        _97 = c164_ray / vec3(l);
    }
    else
    {
        _97 = vec3(0.0, 0.0, 1.0);
    }
    return _97;
}

float c164_height()
{
    return (float(_114.CameraBlockPos.y) - _114.CameraOffset.y) - 172.0;
}

float c164_depth(float _distance, float rise)
{
    float height = max(c164_height(), 0.0);
    float _137 = 0.0;
    if (rise < 0.0)
    {
        _137 = min(_distance, height / max(-rise, 9.9999997473787516355514526367188e-06));
    }
    else
    {
        _137 = _distance;
    }
    float reach = _137;
    float a = (reach * rise) / 12.0;
    float start = exp((-height) / 12.0);
    float mist = 0.0;
    if (abs(a) < 0.001000000047497451305389404296875)
    {
        mist = (reach * start) * (1.0 - (0.5 * a));
    }
    else
    {
        mist = ((start - exp((-max(height + (reach * rise), 0.0)) / 12.0)) * 12.0) / rise;
    }
    return (_distance / 1600.0) + (mist / 587.0);
}

float c164_fogged(float _distance, float rise)
{
    float param = _distance;
    float param_1 = rise;
    return 1.0 - exp(-c164_depth(param, param_1));
}

float c164_levelled()
{
    float far = clamp((length(c164_ray.xz) - 60.0) / 90.0, 0.0, 1.0);
    float low = clamp((12.0 - (c164_height() + c164_ray.y)) / 4.0, 0.0, 1.0);
    return far * low;
}

float total_fog_value(float sphericalVertexDistance_1, float cylindricalVertexDistance_1, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd)
{
    float param = cylindricalVertexDistance_1;
    float param_1 = renderDistanceStart;
    float param_2 = renderDistanceEnd;
    float edge = linear_fog_value(param, param_1, param_2);
    float param_3 = environmentalStart;
    float param_4 = environmantalEnd;
    if (c164_open_air(param_3, param_4))
    {
        float param_5 = sphericalVertexDistance_1;
        float param_6 = c164_direction().y;
        return 1.0 - ((1.0 - c164_fogged(param_5, param_6)) * (1.0 - max(edge, c164_levelled())));
    }
    float param_7 = sphericalVertexDistance_1;
    float param_8 = environmentalStart;
    float param_9 = environmantalEnd;
    return max(linear_fog_value(param_7, param_8, param_9), edge);
}

void main()
{
    vec4 color = texture(Sampler0, texCoord0) * _290.ColorModulator;
    if (color.w < 0.100000001490116119384765625)
    {
        discard;
    }
    float param = sphericalVertexDistance;
    float param_1 = cylindricalVertexDistance;
    float param_2 = _308.FogEnvironmentalStart;
    float param_3 = _308.FogEnvironmentalEnd;
    float param_4 = _308.FogRenderDistanceStart;
    float param_5 = _308.FogRenderDistanceEnd;
    float fade = (1.0 - total_fog_value(param, param_1, param_2, param_3, param_4, param_5)) * _114.GlintAlpha;
    fragColor = vec4(color.xyz * fade, color.w);
}

