#version 330

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _135;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _199;

layout(std140) uniform DynamicTransforms
{
    mat4 ModelViewMat;
    mat4 TextureMat;
    vec4 ColorModulator;
    vec3 ModelOffset;
} _675;

uniform sampler2D Sampler0;

in vec3 c164_ray;
in vec4 overlayColor;
in vec4 lightMapColor;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec2 texCoord0;
in vec4 vertexColor;
layout(location = 0) out vec4 fragColor;

bool c164_open_air(float environmentalStart, float environmentalEnd)
{
    return ((environmentalEnd > 192.0) && (environmentalEnd < 1000000015047466219876688855040.0)) && (environmentalStart > (-4.0));
}

bool c164_open()
{
    float param = _135.FogEnvironmentalStart;
    float param_1 = _135.FogEnvironmentalEnd;
    return c164_open_air(param, param_1);
}

vec3 c164_direction()
{
    float l = length(c164_ray);
    vec3 _157 = vec3(0.0);
    if (l > 9.9999999747524270787835121154785e-07)
    {
        _157 = c164_ray / vec3(l);
    }
    else
    {
        _157 = vec3(0.0, 0.0, 1.0);
    }
    return _157;
}

float c164_height()
{
    return (float(_199.CameraBlockPos.y) - _199.CameraOffset.y) - 172.0;
}

vec3 c164_level(vec3 d)
{
    float l = length(d.xz);
    vec3 _177 = vec3(0.0);
    if (l > 9.9999997473787516355514526367188e-05)
    {
        _177 = vec3(d.x / l, 0.0, d.z / l);
    }
    else
    {
        _177 = vec3(0.0, 0.0, 1.0);
    }
    return _177;
}

vec3 c164_ring(vec3 d)
{
    float stain = 0.3499999940395355224609375 * max(0.0, dot(d, vec3(-1.0, 0.0, 0.0)));
    return mix(mix(vec3(0.2627449929714202880859375, 0.26666700839996337890625, 0.5215690135955810546875), vec3(0.91372501850128173828125, 0.4862749874591827392578125, 0.2980389893054962158203125), vec3(stain)), vec3(0.02745099924504756927490234375, 0.0588239990174770355224609375, 0.16470600664615631103515625), vec3(0.1867119967937469482421875));
}

float c164_fan(vec3 d)
{
    float lift = (3.0 * d.y) / 0.3499999940395355224609375;
    float k = dot(d, vec3(-1.0, 0.0, 0.0)) - lift;
    if (k <= 0.0)
    {
        return 0.0;
    }
    return (0.4199999868869781494140625 * k) / (length(vec2(lift, dot(d, vec3(0.0, 0.0, 1.0)))) + (1.2000000476837158203125 * k));
}

vec3 c164_band(vec3 d)
{
    vec3 param = d;
    vec3 level = c164_level(param);
    float _384 = 0.0;
    if (d.y < 0.0)
    {
        _384 = 1.0;
    }
    else
    {
        _384 = 1.0 - smoothstep(0.0, 0.0350000001490116119384765625, d.y);
    }
    float soft = _384;
    vec3 param_1 = (d.y < 0.0) ? level : d;
    vec3 param_2 = level;
    return mix(c164_ring(param_1), vec3(0.91372501850128173828125, 0.4862749874591827392578125, 0.2980389893054962158203125), vec3(c164_fan(param_2) * soft));
}

float c164_depth(float _distance, float rise)
{
    float height = max(c164_height(), 0.0);
    float _219 = 0.0;
    if (rise < 0.0)
    {
        _219 = min(_distance, height / max(-rise, 9.9999997473787516355514526367188e-06));
    }
    else
    {
        _219 = _distance;
    }
    float reach = _219;
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

vec3 c164_sea(vec3 d)
{
    float reach = max(c164_height(), 0.5) / max(-d.y, 9.9999997473787516355514526367188e-06);
    vec3 param = d;
    float param_1 = reach;
    float param_2 = d.y;
    return mix(vec3(0.337255001068115234375, 0.360783994197845458984375, 0.549019992351531982421875), c164_band(param), vec3(c164_fogged(param_1, param_2)));
}

vec3 c164_behind(vec3 d)
{
    vec3 _439 = vec3(0.0);
    if (d.y < 0.0)
    {
        vec3 param = d;
        _439 = c164_sea(param);
    }
    else
    {
        vec3 param_1 = d;
        _439 = c164_band(param_1);
    }
    return _439;
}

vec4 c164_fog_color()
{
    if (!c164_open())
    {
        return _135.GameFogColor;
    }
    vec3 param = c164_direction();
    return vec4(c164_behind(param), _135.GameFogColor.w);
}

float c164_levelled()
{
    float far = clamp((length(c164_ray.xz) - 60.0) / 90.0, 0.0, 1.0);
    float low = clamp((12.0 - (c164_height() + c164_ray.y)) / 4.0, 0.0, 1.0);
    return far * low;
}

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

vec4 apply_fog(vec4 inColor, float sphericalVertexDistance_1, float cylindricalVertexDistance_1, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd, vec4 fogColor)
{
    float param = environmentalStart;
    float param_1 = environmantalEnd;
    if (c164_open_air(param, param_1))
    {
        vec3 d = c164_direction();
        vec3 param_2 = d;
        float weight = dot(fogColor.xyz, vec3(1.0)) / max(dot(c164_behind(param_2), vec3(1.0)), 9.9999999747524270787835121154785e-07);
        vec3 param_3 = d;
        float param_4 = sphericalVertexDistance_1;
        float param_5 = d.y;
        vec3 hazed = mix(inColor.xyz, c164_band(param_3) * weight, vec3(c164_fogged(param_4, param_5) * fogColor.w));
        float param_6 = cylindricalVertexDistance_1;
        float param_7 = renderDistanceStart;
        float param_8 = renderDistanceEnd;
        float gone = max(c164_levelled(), linear_fog_value(param_6, param_7, param_8));
        return vec4(mix(hazed, fogColor.xyz, vec3(gone * fogColor.w)), inColor.w);
    }
    float param_9 = sphericalVertexDistance_1;
    float param_10 = cylindricalVertexDistance_1;
    float param_11 = environmentalStart;
    float param_12 = environmantalEnd;
    float param_13 = renderDistanceStart;
    float param_14 = renderDistanceEnd;
    float fogValue = total_fog_value(param_9, param_10, param_11, param_12, param_13, param_14);
    return vec4(mix(inColor.xyz, fogColor.xyz, vec3(fogValue * fogColor.w)), inColor.w);
}

vec4 calculateFinalColor(inout vec4 color)
{
    vec4 _613 = color;
    vec3 _618 = mix(overlayColor.xyz, _613.xyz, vec3(overlayColor.w));
    color.x = _618.x;
    color.y = _618.y;
    color.z = _618.z;
    color *= lightMapColor;
    vec4 fogColor = c164_fog_color();
    vec4 param = color;
    float param_1 = sphericalVertexDistance;
    float param_2 = cylindricalVertexDistance;
    float param_3 = _135.FogEnvironmentalStart;
    float param_4 = _135.FogEnvironmentalEnd;
    float param_5 = _135.FogRenderDistanceStart;
    float param_6 = _135.FogRenderDistanceEnd;
    vec4 param_7 = fogColor;
    return apply_fog(param, param_1, param_2, param_3, param_4, param_5, param_6, param_7);
}

void main()
{
    vec4 color = texture(Sampler0, texCoord0);
    vec4 faceVertexColor = vertexColor;
    color *= (faceVertexColor * _675.ColorModulator);
    vec4 param = color;
    vec4 _685 = calculateFinalColor(param);
    fragColor = _685;
}

