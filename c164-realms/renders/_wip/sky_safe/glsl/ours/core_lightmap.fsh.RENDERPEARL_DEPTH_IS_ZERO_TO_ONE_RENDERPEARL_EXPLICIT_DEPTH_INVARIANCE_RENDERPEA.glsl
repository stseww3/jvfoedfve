#version 330

layout(std140) uniform LightmapInfo
{
    float SkyFactor;
    float BlockFactor;
    float NightVisionFactor;
    float DarknessScale;
    float BossOverlayWorldDarkeningFactor;
    float BrightnessFactor;
    vec3 BlockLightTint;
    vec3 SkyLightColor;
    vec3 AmbientColor;
    vec3 NightVisionColor;
} lightmapInfo;

in vec2 texCoord;
layout(location = 0) out vec4 fragColor;

float get_brightness(float level)
{
    return level / (4.0 - (3.0 * level));
}

float parabolicMixFactor(float level)
{
    return ((2.0 * level) - 1.0) * ((2.0 * level) - 1.0);
}

vec3 notGamma(vec3 color)
{
    float maxComponent = max(max(color.x, color.y), color.z);
    float maxInverted = 1.0 - maxComponent;
    float maxScaled = 1.0 - (((maxInverted * maxInverted) * maxInverted) * maxInverted);
    return color * (maxScaled / maxComponent);
}

void main()
{
    float block_level = floor(texCoord.x * 16.0) / 15.0;
    float sky_level = floor(texCoord.y * 16.0) / 15.0;
    float param = block_level;
    float block_brightness = get_brightness(param) * lightmapInfo.BlockFactor;
    float param_1 = sky_level;
    float sky_brightness = get_brightness(param_1) * 0.4000000059604644775390625;
    vec3 nightVisionColor = lightmapInfo.NightVisionColor * lightmapInfo.NightVisionFactor;
    vec3 color = max(vec3(0.08627499639987945556640625, 0.10196100175380706787109375, 0.17254899442195892333984375), nightVisionColor);
    color += (vec3(0.4980390071868896484375, 0.57647097110748291015625, 0.8470590114593505859375) * sky_brightness);
    float param_2 = block_level;
    vec3 BlockLightColor = mix(vec3(1.0, 0.705882012844085693359375, 0.368627011775970458984375), vec3(1.0), vec3(0.89999997615814208984375 * parabolicMixFactor(param_2)));
    color += (BlockLightColor * block_brightness);
    color = mix(color, color * vec3(0.699999988079071044921875, 0.60000002384185791015625, 0.60000002384185791015625), vec3(lightmapInfo.BossOverlayWorldDarkeningFactor));
    color -= vec3(lightmapInfo.DarknessScale);
    color = clamp(color, vec3(0.0), vec3(1.0));
    vec3 param_3 = color;
    vec3 notGamma_1 = notGamma(param_3);
    color = mix(color, notGamma_1, vec3(lightmapInfo.BrightnessFactor));
    fragColor = vec4(color, 1.0);
}

