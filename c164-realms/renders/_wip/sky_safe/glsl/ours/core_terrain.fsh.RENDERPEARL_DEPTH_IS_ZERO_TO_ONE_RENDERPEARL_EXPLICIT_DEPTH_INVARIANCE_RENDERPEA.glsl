#version 330

const vec2 _799[4] = vec2[](vec2(0.125, 0.375), vec2(-0.125, -0.375), vec2(0.375, -0.125), vec2(-0.375, 0.125));

layout(std140) uniform Fog
{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _162;

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _225;

layout(std140) uniform TerrainUniform
{
    mat4 ModelViewMat;
    ivec2 TextureSize;
} _895;

layout(std140) uniform ChunkSection
{
    ivec3 ChunkPosition;
    float ChunkVisibility;
} _941;

uniform sampler2D Sampler0;

in vec3 c164_ray;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;
in vec2 texCoord0;
in vec4 vertexColor;
in float chunkVisibility;
layout(location = 0) out vec4 fragColor;

vec4 sampleNearest(sampler2D source, inout vec2 uv, vec2 pixelSize, vec2 du, vec2 dv, vec2 texelScreenSize)
{
    vec2 uvTexelCoords = uv / pixelSize;
    vec2 texelCenter = round(uvTexelCoords) - vec2(0.5);
    vec2 texelOffset = uvTexelCoords - texelCenter;
    texelOffset = (((texelOffset - vec2(0.5)) * pixelSize) / texelScreenSize) + vec2(0.5);
    texelOffset = clamp(texelOffset, vec2(0.0), vec2(1.0));
    uv = (texelCenter + texelOffset) * pixelSize;
    return textureGrad(source, uv, du, dv);
}

vec4 sampleRGSS(sampler2D source, vec2 uv, vec2 pixelSize)
{
    vec2 du = dFdx(uv);
    vec2 dv = dFdy(uv);
    vec2 texelScreenSize = sqrt((du * du) + (dv * dv));
    float maxTexelSize = max(texelScreenSize.x, texelScreenSize.y);
    float minPixelSize = min(pixelSize.x, pixelSize.y);
    float transitionStart = minPixelSize * 1.0;
    float transitionEnd = minPixelSize * 2.0;
    float blendFactor = smoothstep(transitionStart, transitionEnd, maxTexelSize);
    float duLength = length(du);
    float dvLength = length(dv);
    float minDerivative = min(duLength, dvLength);
    float maxDerivative = max(duLength, dvLength);
    float effectiveDerivative = sqrt(minDerivative * maxDerivative);
    float mipLevelExact = max(0.0, log2(effectiveDerivative / minPixelSize));
    float mipLevelLow = floor(mipLevelExact);
    float mipLevelHigh = mipLevelLow + 1.0;
    float mipBlend = fract(mipLevelExact);
    vec4 rgssColorLow = vec4(0.0);
    vec4 rgssColorHigh = vec4(0.0);
    for (int i = 0; i < 4; i++)
    {
        vec2 sampleUV = uv + (_799[i] * pixelSize);
        rgssColorLow += textureLod(source, sampleUV, mipLevelLow);
        rgssColorHigh += textureLod(source, sampleUV, mipLevelHigh);
    }
    rgssColorLow *= 0.25;
    rgssColorHigh *= 0.25;
    vec4 rgssColor = mix(rgssColorLow, rgssColorHigh, vec4(mipBlend));
    vec2 param = uv;
    vec2 param_1 = pixelSize;
    vec2 param_2 = du;
    vec2 param_3 = dv;
    vec2 param_4 = texelScreenSize;
    vec4 _844 = sampleNearest(source, param, param_1, param_2, param_3, param_4);
    vec4 nearestColor = _844;
    return mix(nearestColor, rgssColor, vec4(blendFactor));
}

vec4 sampleNearest(sampler2D source, vec2 uv, vec2 pixelSize)
{
    vec2 du = dFdx(uv);
    vec2 dv = dFdy(uv);
    vec2 texelScreenSize = sqrt((du * du) + (dv * dv));
    vec2 param = uv;
    vec2 param_1 = pixelSize;
    vec2 param_2 = du;
    vec2 param_3 = dv;
    vec2 param_4 = texelScreenSize;
    vec4 _698 = sampleNearest(source, param, param_1, param_2, param_3, param_4);
    return _698;
}

bool c164_open_air(float environmentalStart, float environmentalEnd)
{
    return ((environmentalEnd > 192.0) && (environmentalEnd < 1000000015047466219876688855040.0)) && (environmentalStart > (-4.0));
}

bool c164_open()
{
    float param = _162.FogEnvironmentalStart;
    float param_1 = _162.FogEnvironmentalEnd;
    return c164_open_air(param, param_1);
}

vec3 c164_direction()
{
    float l = length(c164_ray);
    vec3 _184 = vec3(0.0);
    if (l > 9.9999999747524270787835121154785e-07)
    {
        _184 = c164_ray / vec3(l);
    }
    else
    {
        _184 = vec3(0.0, 0.0, 1.0);
    }
    return _184;
}

float c164_height()
{
    return (float(_225.CameraBlockPos.y) - _225.CameraOffset.y) - 172.0;
}

vec3 c164_level(vec3 d)
{
    float l = length(d.xz);
    vec3 _203 = vec3(0.0);
    if (l > 9.9999997473787516355514526367188e-05)
    {
        _203 = vec3(d.x / l, 0.0, d.z / l);
    }
    else
    {
        _203 = vec3(0.0, 0.0, 1.0);
    }
    return _203;
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
    float _410 = 0.0;
    if (d.y < 0.0)
    {
        _410 = 1.0;
    }
    else
    {
        _410 = 1.0 - smoothstep(0.0, 0.0350000001490116119384765625, d.y);
    }
    float soft = _410;
    vec3 param_1 = (d.y < 0.0) ? level : d;
    vec3 param_2 = level;
    return mix(c164_ring(param_1), vec3(0.91372501850128173828125, 0.4862749874591827392578125, 0.2980389893054962158203125), vec3(c164_fan(param_2) * soft));
}

float c164_depth(float _distance, float rise)
{
    float height = max(c164_height(), 0.0);
    float _245 = 0.0;
    if (rise < 0.0)
    {
        _245 = min(_distance, height / max(-rise, 9.9999997473787516355514526367188e-06));
    }
    else
    {
        _245 = _distance;
    }
    float reach = _245;
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
    vec3 _465 = vec3(0.0);
    if (d.y < 0.0)
    {
        vec3 param = d;
        _465 = c164_sea(param);
    }
    else
    {
        vec3 param_1 = d;
        _465 = c164_band(param_1);
    }
    return _465;
}

vec4 c164_fog_color()
{
    if (!c164_open())
    {
        return _162.GameFogColor;
    }
    vec3 param = c164_direction();
    return vec4(c164_behind(param), _162.GameFogColor.w);
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

vec4 calculateFinalColor(vec4 color)
{
    vec4 fogColor = c164_fog_color();
    vec4 param = color;
    float param_1 = sphericalVertexDistance;
    float param_2 = cylindricalVertexDistance;
    float param_3 = _162.FogEnvironmentalStart;
    float param_4 = _162.FogEnvironmentalEnd;
    float param_5 = _162.FogRenderDistanceStart;
    float param_6 = _162.FogRenderDistanceEnd;
    vec4 param_7 = fogColor;
    return apply_fog(param, param_1, param_2, param_3, param_4, param_5, param_6, param_7);
}

void main()
{
    vec4 _885 = vec4(0.0);
    if (_225.UseRgss == 1)
    {
        vec2 param = texCoord0;
        vec2 param_1 = vec2(1.0) / vec2(_895.TextureSize);
        _885 = sampleRGSS(Sampler0, param, param_1);
    }
    else
    {
        vec2 param_2 = texCoord0;
        vec2 param_3 = vec2(1.0) / vec2(_895.TextureSize);
        _885 = sampleNearest(Sampler0, param_2, param_3);
    }
    vec4 color = _885 * vertexColor;
    color = mix(c164_fog_color() * vec4(1.0, 1.0, 1.0, color.w), color, vec4(chunkVisibility));
    vec4 param_4 = color;
    fragColor = calculateFinalColor(param_4);
}

