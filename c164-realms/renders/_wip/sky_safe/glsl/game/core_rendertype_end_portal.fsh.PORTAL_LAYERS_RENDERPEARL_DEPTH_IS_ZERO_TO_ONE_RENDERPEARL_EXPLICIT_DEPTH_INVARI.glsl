#version 330

const vec3 _323[16] = vec3[](vec3(0.022087000310420989990234375, 0.09839899837970733642578125, 0.1108179986476898193359375), vec3(0.01189200021326541900634765625, 0.095923997461795806884765625, 0.089484997093677520751953125), vec3(0.02763600088655948638916015625, 0.101689003407955169677734375, 0.100326001644134521484375), vec3(0.0465640015900135040283203125, 0.109883002936840057373046875, 0.114837996661663055419921875), vec3(0.064901001751422882080078125, 0.11769600212574005126953125, 0.097189001739025115966796875), vec3(0.063761003315448760986328125, 0.086894996464252471923828125, 0.123645998537540435791015625), vec3(0.084816999733448028564453125, 0.1119939982891082763671875, 0.16638000309467315673828125), vec3(0.09748899936676025390625, 0.1541199982166290283203125, 0.091063998639583587646484375), vec3(0.106151998043060302734375, 0.13114400207996368408203125, 0.1951909959316253662109375), vec3(0.097721002995967864990234375, 0.110187999904155731201171875, 0.18722899258136749267578125), vec3(0.13351599872112274169921875, 0.13827799260616302490234375, 0.14858199656009674072265625), vec3(0.07000599801540374755859375, 0.2433319985866546630859375, 0.23579199612140655517578125), vec3(0.19676600396633148193359375, 0.1428990066051483154296875, 0.21469600498676300048828125), vec3(0.0472810007631778717041015625, 0.3153379857540130615234375, 0.3219699859619140625), vec3(0.20467500388622283935546875, 0.39000999927520751953125, 0.3020659983158111572265625), vec3(0.0809549987316131591796875, 0.3148210048675537109375, 0.661490976810455322265625));

layout(std140) uniform Globals
{
    ivec3 CameraBlockPos;
    float GlintAlpha;
    vec3 CameraOffset;
    float GameTime;
    vec2 ScreenSize;
    int MenuBlurRadius;
    int UseRgss;
} _156;

layout(std140) uniform Fog
{
    vec4 FogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
} _346;

uniform sampler2D Sampler0;
uniform sampler2D Sampler1;

in vec4 texProj0;
layout(location = 0) out vec4 fragColor;
in float sphericalVertexDistance;
in float cylindricalVertexDistance;

mat2 mat2_rotate_z(float _radians)
{
    return mat2(vec2(cos(_radians), -sin(_radians)), vec2(sin(_radians), cos(_radians)));
}

mat4 end_portal_layer(float layer)
{
    mat4 translate = mat4(vec4(1.0, 0.0, 0.0, 17.0 / layer), vec4(0.0, 1.0, 0.0, (2.0 + (layer / 1.5)) * (_156.GameTime * 1.5)), vec4(0.0, 0.0, 1.0, 0.0), vec4(0.0, 0.0, 0.0, 1.0));
    float param = radians((((layer * layer) * 4321.0) + (layer * 9.0)) * 2.0);
    mat2 rotate = mat2_rotate_z(param);
    float _189 = (4.5 - (layer / 4.0)) * 2.0;
    mat2 scale = mat2(vec2(_189, 0.0), vec2(0.0, _189));
    mat2 _195 = scale * rotate;
    return (mat4(vec4(_195[0].x, _195[0].y, 0.0, 0.0), vec4(_195[1].x, _195[1].y, 0.0, 0.0), vec4(0.0, 0.0, 1.0, 0.0), vec4(0.0, 0.0, 0.0, 1.0)) * translate) * mat4(vec4(0.5, 0.0, 0.0, 0.25), vec4(0.0, 0.5, 0.0, 0.25), vec4(0.0, 0.0, 1.0, 0.0), vec4(0.0, 0.0, 0.0, 1.0));
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
    float param = sphericalVertexDistance_1;
    float param_1 = environmentalStart;
    float param_2 = environmantalEnd;
    float param_3 = cylindricalVertexDistance_1;
    float param_4 = renderDistanceStart;
    float param_5 = renderDistanceEnd;
    return max(linear_fog_value(param, param_1, param_2), linear_fog_value(param_3, param_4, param_5));
}

vec4 apply_fog(vec4 inColor, float sphericalVertexDistance_1, float cylindricalVertexDistance_1, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd, vec4 fogColor)
{
    float param = sphericalVertexDistance_1;
    float param_1 = cylindricalVertexDistance_1;
    float param_2 = environmentalStart;
    float param_3 = environmantalEnd;
    float param_4 = renderDistanceStart;
    float param_5 = renderDistanceEnd;
    float fogValue = total_fog_value(param, param_1, param_2, param_3, param_4, param_5);
    return vec4(mix(inColor.xyz, fogColor.xyz, vec3(fogValue * fogColor.w)), inColor.w);
}

void main()
{
    vec4 _226 = texProj0;
    _226.z = _226.w;
    vec3 color = textureProj(Sampler0, _226.xyz).xyz * vec3(0.022087000310420989990234375, 0.09839899837970733642578125, 0.1108179986476898193359375);
    for (int i = 0; i < 15; i++)
    {
        float param = float(i + 1);
        vec4 _256 = texProj0 * end_portal_layer(param);
        _256.z = _256.w;
        color += (textureProj(Sampler1, _256.xyz).xyz * _323[i]);
    }
    vec4 param_1 = vec4(color, 1.0);
    float param_2 = sphericalVertexDistance;
    float param_3 = cylindricalVertexDistance;
    float param_4 = _346.FogEnvironmentalStart;
    float param_5 = _346.FogEnvironmentalEnd;
    float param_6 = _346.FogRenderDistanceStart;
    float param_7 = _346.FogRenderDistanceEnd;
    vec4 param_8 = _346.FogColor;
    fragColor = apply_fog(param_1, param_2, param_3, param_4, param_5, param_6, param_7, param_8);
}

