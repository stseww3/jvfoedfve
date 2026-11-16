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
    float sky_brightness = get_brightness(param_1) * lightmapInfo.SkyFactor;
    vec3 nightVisionColor = lightmapInfo.NightVisionColor * lightmapInfo.NightVisionFactor;
    vec3 color = max(lightmapInfo.AmbientColor, nightVisionColor);
    color += (lightmapInfo.SkyLightColor * sky_brightness);
    float param_2 = block_level;
    vec3 BlockLightColor = mix(lightmapInfo.BlockLightTint, vec3(1.0), vec3(0.89999997615814208984375 * parabolicMixFactor(param_2)));
    color += (BlockLightColor * block_brightness);
    color = mix(color, color * vec3(0.699999988079071044921875, 0.60000002384185791015625, 0.60000002384185791015625), vec3(lightmapInfo.BossOverlayWorldDarkeningFactor));
    color -= vec3(lightmapInfo.DarknessScale);
    color = clamp(color, vec3(0.0), vec3(1.0));
    vec3 param_3 = color;
    vec3 notGamma_1 = notGamma(param_3);
    color = mix(color, notGamma_1, vec3(lightmapInfo.BrightnessFactor));
    fragColor = vec4(color, 1.0);
}

