"""The look carried by the resource pack: core shaders written from mood.LOOKS (card sky/safe-look).

Realms takes no map whose data pack holds registry files, so the finished map has no biome and no
timeline of its own: a vanilla biome, the clock and the weather stopped. What sky/mood.py states is
then drawn by the game's own shaders, replaced in the resource pack. mood.LOOKS stays the only
place a number is written; this module turns one look into shader text.

    files(look)      -> {path under assets/minecraft/shaders/: text}
    pack(pack_dir)   -> [str]      write them (the scene's write_pack() calls it)
    Twin(look)       the same arithmetic in numpy, for the checks and for a picture without the game

What is replaced, and what each file does (the game's text is read from the client jar and changed
in a few places, so a new game version shows as a failed patch and not as a broken picture; only
sky.vsh, sky.fsh, stars.vsh and stars.fsh are written whole):

  include/fog.glsl   every shader that takes fog includes it. In open air (told from the game's own
                     fog distances: not under water, in lava, in powder snow, blind, in the menus)
                     the fog is ours. How much: mood.fog_depth(), the air's haze and the mist that
                     lies on the sea, along the line of sight to the pixel. Its colour: the horizon
                     band in the direction of the pixel (the afterglow stains it in the west).
                     What lies on the sea is taken into the far sea painted behind it
                     (mood.levelled()), and the game's own fog at the edge of the view distance is
                     kept and fades to what is painted behind as well: the band above the horizon,
                     the far cloud sea below it. So the block clouds end without an edge. The
                     direction comes from the vertex shaders: each hands its position to
                     fog_spherical_distance(), which passes it on in one more varying.
  core/sky.vsh/.fsh  the sky's upper disc is spread over the whole screen and every pixel is
                     painted by its direction: zenith to horizon as the game's fogged plane has
                     it, the afterglow fan in the west, the far cloud sea below the horizon.
  core/lightmap.fsh  the colour and strength of sky light, the ambient colour and the lamp tint
                     are the look's and no longer the hour's.
  core/item.vsh      a face lit to the full by block light (a model element with light_emission
                     15, a display entity with brightness 15) is not shaded by the way it faces.
  core/rendertype_beacon_beam.vsh   only passes the direction on (its fragment shader takes fog).
  core/clouds.vsh    the vanilla cloud layer is not drawn: its height is an attribute, and without
                     a file of ours it would stand four blocks under the terrace.
  core/stars.vsh/.fsh  the star field at the look's own turn and brightness instead of the
                     hour's, and no star below the horizon.
  include/c164_layers.glsl   what other sky packages paint on the sky (the far ridges): see
                     layers().

Read off the 26.3 client (plan/parts/sky-notes.md 11): shaders are compiled to SPIR-V by shaderc for
both renderers, the stage macros GL_VERTEX_SHADER / GL_FRAGMENT_SHADER are there, a fragment input
needs a vertex output at the same location (the pipeline is refused otherwise), and a uniform block
a shader declares has to be among the pipeline's bind groups (Globals is in every one that has Fog).
"""
import math
import os
import re

import numpy as np

from artkit.gameassets import Assets

from . import mood

ROOT = "assets/minecraft/shaders/"
RAY_LOCATION = 12           # the varying that carries the direction; the game's own use 0..7
WEST = (-1.0, 0.0, 0.0)     # the afterglow's side while the sun angle's sine is positive
HORIZON_SOFT = 0.035        # sine of 2 degrees: over this height blocks lose the fan's stain (see c164_haze)
PARTS = ("fog", "sky", "lightmap", "item", "clouds", "stars")

_game = None


def jar():
    """The client jar: MC_JAR, or the one under MC_ROOT (as render.py and the job runner have it)."""
    path = os.environ.get("MC_JAR") or os.path.join(os.environ.get("MC_ROOT", "/agent/realms-study"),
                                                     "client26", "versions", "26.3", "26.3.jar")
    if not os.path.isfile(path):
        raise FileNotFoundError(f"the shaders are the game's own with a few lines changed, and there is no "
                                f"client jar at {path}; set MC_JAR or MC_ROOT")
    return path


def vanilla(name):
    """The game's own text of a shader file (name under assets/minecraft/shaders/)."""
    global _game
    if _game is None:
        _game = Assets(jar())
    raw = _game.zip.read(ROOT + name) if ROOT + name in _game.names else None
    if raw is None:
        raise FileNotFoundError(f"the game has no shader file {name}")
    return raw.decode("utf-8")


def _swap(text, old, new, name, count=1):
    """Replace `old` by `new`; the game's text has to hold it exactly `count` times."""
    found = text.count(old)
    if found != count:
        raise ValueError(f"{name}: expected {count} of {old!r} in the game's text, found {found} "
                         f"(a new game version? read the file again and adjust sky/_shaders.py)")
    return text.replace(old, new)


def _f(x):
    """A float the way GLSL wants it."""
    text = repr(round(float(x), 6))
    return text if ("." in text or "e" in text) else text + ".0"


def _vec3(rgb):
    return "vec3(" + ", ".join(_f(c) for c in rgb) + ")"


def numbers(look=mood.DEFAULT):
    """Everything the shaders take from a look, as plain numbers."""
    v = mood.look(look)
    sky_hex, fog_hex = mood.derive(v["zenith"], v["horizon"], v["sky_fog_end"])
    side = 1.0 if math.sin(math.radians(v["sun_angle"])) > 0.0 else -1.0
    return dict(
        look=look,
        sky=mood._rgb(sky_hex), fog=mood._rgb(fog_hex),          # the attributes the registry look writes
        glow=mood._rgb(v["glow"]), glow_alpha=float(v["glow_alpha"]),
        share=mood.mix_share(v["sky_fog_end"]), sky_end=float(v["sky_fog_end"]),
        west=tuple(side * c for c in WEST),
        sea=mood._rgb(v["cloud"]), sea_y=float(mood.GROUND_Y + mood.CLOUD_TOP),
        air=float(mood.AIR), mist=float(mood.MIST), mist_height=float(mood.MIST_HEIGHT),
        fog_start=float(mood.FOG_START), fog_end=float(mood.FOG_END),
        level_full=float(mood.LEVEL_FULL), level_none=float(mood.LEVEL_NONE),
        sky_light=mood._rgb(v["sky_light"]), sky_factor=float(v["sky_factor"]),
        ambient=mood._rgb(v["ambient"]), lamp=mood._rgb(mood.LAMP),
        stars=float(v["stars"]), star_angle=float(mood.STAR_ANGLE), game_star_angle=float(mood.GAME_STAR_ANGLE),
    )


HEAD = """// c164 observatory: written by build/scenes/obs/sky/_shaders.py from sky/mood.py, look "{look}".
// Do not edit: change the look and write the pack again.
"""

# ---- include/fog.glsl ---------------------------------------------------------------------------
# What the game's file has to hold for ours to stand in for it: the uniform block as it is laid
# out, and the functions the shaders call.
FOG_EXPECT = (
    "layout(std140) uniform Fog {\n    vec4 FogColor;\n    float FogEnvironmentalStart;\n    float FogEnvironmentalEnd;\n"
    "    float FogRenderDistanceStart;\n    float FogRenderDistanceEnd;\n    float FogSkyEnd;\n    float FogCloudsEnd;\n};\n",
    "float linear_fog_value(float vertexDistance, float fogStart, float fogEnd) {",
    "float total_fog_value(float sphericalVertexDistance, float cylindricalVertexDistance, float environmentalStart, "
    "float environmantalEnd, float renderDistanceStart, float renderDistanceEnd) {",
    "vec4 apply_fog(vec4 inColor, float sphericalVertexDistance, float cylindricalVertexDistance, float environmentalStart, "
    "float environmantalEnd, float renderDistanceStart, float renderDistanceEnd, vec4 fogColor) {",
    "float fog_spherical_distance(vec3 pos) {",
    "float fog_cylindrical_distance(vec3 pos) {",
)
FOG_FUNCTIONS = 5           # the game's file defines these five functions and nothing else

FOG_GLSL = """#ifndef MINECRAFT_FOG_GLSL
#define MINECRAFT_FOG_GLSL

{head}
layout(std140) uniform Fog {{
    vec4 GameFogColor;
    float FogEnvironmentalStart;
    float FogEnvironmentalEnd;
    float FogRenderDistanceStart;
    float FogRenderDistanceEnd;
    float FogSkyEnd;
    float FogCloudsEnd;
}};

float linear_fog_value(float vertexDistance, float fogStart, float fogEnd) {{
    if (vertexDistance <= fogStart) {{
        return 0.0;
    }} else if (vertexDistance >= fogEnd) {{
        return 1.0;
    }}

    return (vertexDistance - fogStart) / (fogEnd - fogStart);
}}

// Open air: the game's own fog distances of a clear overworld (0 and 1024). Water, lava, powder
// snow, blindness, a boss's fog and the menus have others and keep the game's fog.
bool c164_open_air(float environmentalStart, float environmentalEnd) {{
    return environmentalEnd > 192.0 && environmentalEnd < 1.0e30 && environmentalStart > -4.0;
}}

#ifdef GL_VERTEX_SHADER

layout(location = {ray}) out vec3 c164_ray;       // the position as seen from the camera, in the world's axes

float fog_spherical_distance(vec3 pos) {{
    c164_ray = pos;
    return length(pos);
}}

#define FogColor GameFogColor

#else

layout(location = {ray}) in vec3 c164_ray;

#include <minecraft:globals.glsl>

const vec3 C164_SKY = {sky};          // sky_color and fog_color as the look's registry files had them
const vec3 C164_FOG = {fog};
const vec3 C164_GLOW = {glow};         // the afterglow, and how strong
const float C164_GLOW_ALPHA = {glow_alpha};
const float C164_SHARE = {share};      // how far the game draws the fog colour towards the sky colour
const float C164_SKY_END = {sky_end};  // the sky's own fog distance
const vec3 C164_WEST = {west};
const vec3 C164_SEA = {sea};          // the cloud sea: its colour and the world height of its top
const float C164_SEA_Y = {sea_y};
const float C164_AIR = {air};          // mood.fog_depth(): the air's haze, the mist on the sea
const float C164_MIST = {mist};
const float C164_MIST_HEIGHT = {mist_height};
const float C164_FOG_START = {fog_start};     // mood.levelled(): what lies on the sea goes into the far sea
const float C164_FOG_END = {fog_end};
const float C164_LEVEL_FULL = {level_full};
const float C164_LEVEL_NONE = {level_none};

float fog_spherical_distance(vec3 pos) {{
    return length(pos);
}}

bool c164_open() {{
    return c164_open_air(FogEnvironmentalStart, FogEnvironmentalEnd);
}}

vec3 c164_direction() {{
    float l = length(c164_ray);
    return l > 1.0e-6 ? c164_ray / l : vec3(0.0, 0.0, 1.0);
}}

vec3 c164_level(vec3 d) {{
    float l = length(d.xz);
    return l > 1.0e-4 ? vec3(d.x / l, 0.0, d.z / l) : vec3(0.0, 0.0, 1.0);
}}

// the camera above the top of the cloud sea
float c164_height() {{
    return float(CameraBlockPos.y) - CameraOffset.y - C164_SEA_Y;
}}

// mood.fog_depth(): the fog's optical depth along a line of sight of this length that gains `rise`
// in height per block. The mist ends at the sea top.
float c164_depth(float distance, float rise) {{
    float height = max(c164_height(), 0.0);
    float reach = rise < 0.0 ? min(distance, height / max(-rise, 1.0e-5)) : distance;
    float a = reach * rise / C164_MIST_HEIGHT;
    float start = exp(-height / C164_MIST_HEIGHT);
    float mist;
    if (abs(a) < 1.0e-3) {{
        mist = reach * start * (1.0 - 0.5 * a);
    }} else {{
        mist = (start - exp(-max(height + reach * rise, 0.0) / C164_MIST_HEIGHT)) * C164_MIST_HEIGHT / rise;
    }}
    return distance / C164_AIR + mist / C164_MIST;
}}

float c164_fogged(float distance, float rise) {{
    return 1.0 - exp(-c164_depth(distance, rise));
}}

// mood.levelled(): the share to which the thing drawn here is taken into the far sea painted
// behind it, by its distance on the map. In full for what lies on the sea, not at all for what
// stands above it.
float c164_levelled() {{
    float far = clamp((length(c164_ray.xz) - C164_FOG_START) / (C164_FOG_END - C164_FOG_START), 0.0, 1.0);
    float low = clamp((C164_LEVEL_NONE - (c164_height() + c164_ray.y)) / (C164_LEVEL_NONE - C164_LEVEL_FULL), 0.0, 1.0);
    return far * low;
}}

// the horizon band in direction d as the game makes it: the fog colour, stained by the afterglow
// towards the west, drawn towards the sky colour
vec3 c164_ring(vec3 d) {{
    float stain = C164_GLOW_ALPHA * max(0.0, dot(d, C164_WEST));
    return mix(mix(C164_FOG, C164_GLOW, stain), C164_SKY, C164_SHARE);
}}

// how strongly the game's afterglow fan covers direction d: a shallow cone whose rim is lifted in
// the west (its closed form: plan/parts/sky-notes.md 11)
float c164_fan(vec3 d) {{
    float lift = 3.0 * d.y / C164_GLOW_ALPHA;
    float k = dot(d, C164_WEST) - lift;
    if (k <= 0.0) {{
        return 0.0;
    }}
    return C164_GLOW_ALPHA * 1.2 * k / (length(vec2(lift, dot(d, vec3(C164_WEST.z, 0.0, -C164_WEST.x)))) + 1.2 * k);
}}

// What a thing fades to in direction d: the horizon band. At and below the horizon it carries the
// fan's glow of its bearing; above, the band alone, as the game has it (a far tower stays a
// silhouette before the glow). The two meet over the first two degrees above the horizon.
vec3 c164_band(vec3 d) {{
    vec3 level = c164_level(d);
    float soft = d.y < 0.0 ? 1.0 : 1.0 - smoothstep(0.0, {soft}, d.y);
    return mix(c164_ring(d.y < 0.0 ? level : d), C164_GLOW, c164_fan(level) * soft);
}}

// below the horizon: the cloud sea carried on beyond the block clouds, under the same fog as they
vec3 c164_sea(vec3 d) {{
    float reach = max(c164_height(), 0.5) / max(-d.y, 1.0e-5);
    return mix(C164_SEA, c164_band(d), c164_fogged(reach, d.y));
}}

// what is painted behind everything in direction d, as far as blocks are concerned
vec3 c164_behind(vec3 d) {{
    return d.y < 0.0 ? c164_sea(d) : c164_band(d);
}}

// the sky in direction d: the game's plane 16 blocks overhead, fogged by distance, and the fan on it
vec3 c164_sky(vec3 d) {{
    if (d.y < 0.0) {{
        return c164_sea(d);
    }}
    float across = 16.0 * length(d.xz) / max(d.y, 1.0e-4);
    float share = min(1.0, (16.0 + 496.25 * across / 512.0) / C164_SKY_END);
    return mix(mix(C164_SKY, c164_ring(d), share), C164_GLOW, c164_fan(d));
}}

vec4 c164_fog_color() {{
    if (!c164_open()) {{
        return GameFogColor;
    }}
    return vec4(c164_behind(c164_direction()), GameFogColor.a);
}}

#define FogColor c164_fog_color()

#endif

float total_fog_value(float sphericalVertexDistance, float cylindricalVertexDistance, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd) {{
    float edge = linear_fog_value(cylindricalVertexDistance, renderDistanceStart, renderDistanceEnd);
#ifndef GL_VERTEX_SHADER
    if (c164_open_air(environmentalStart, environmantalEnd)) {{
        return 1.0 - (1.0 - c164_fogged(sphericalVertexDistance, c164_direction().y)) * (1.0 - max(edge, c164_levelled()));
    }}
#endif
    return max(linear_fog_value(sphericalVertexDistance, environmentalStart, environmantalEnd), edge);
}}

vec4 apply_fog(vec4 inColor, float sphericalVertexDistance, float cylindricalVertexDistance, float environmentalStart, float environmantalEnd, float renderDistanceStart, float renderDistanceEnd, vec4 fogColor) {{
#ifndef GL_VERTEX_SHADER
    if (c164_open_air(environmentalStart, environmantalEnd)) {{
        // fogColor is FogColor, what is painted behind, or that times the caller's alpha where a
        // shader blends with alpha multiplied in: the band takes the same weight
        vec3 d = c164_direction();
        float weight = dot(fogColor.rgb, vec3(1.0)) / max(dot(c164_behind(d), vec3(1.0)), 1.0e-6);
        vec3 hazed = mix(inColor.rgb, c164_band(d) * weight, c164_fogged(sphericalVertexDistance, d.y) * fogColor.a);
        float gone = max(c164_levelled(), linear_fog_value(cylindricalVertexDistance, renderDistanceStart, renderDistanceEnd));
        return vec4(mix(hazed, fogColor.rgb, gone * fogColor.a), inColor.a);
    }}
#endif
    float fogValue = total_fog_value(sphericalVertexDistance, cylindricalVertexDistance, environmentalStart, environmantalEnd, renderDistanceStart, renderDistanceEnd);
    return vec4(mix(inColor.rgb, fogColor.rgb, fogValue * fogColor.a), inColor.a);
}}

float fog_cylindrical_distance(vec3 pos) {{
    float distXZ = length(pos.xz);
    float distY = abs(pos.y);
    return max(distXZ, distY);
}}

#endif
"""


def fog_glsl(n):
    """include/fog.glsl, written whole. The game's file is read to see that ours still stands in
    for it: the same uniform block, the same five functions."""
    name = "include/fog.glsl"
    text = vanilla(name)
    for piece in FOG_EXPECT:
        _swap(text, piece, piece, name)
    functions = re.findall(r"^(?:float|vec4|vec3|bool|void)\s+(\w+)\s*\(", text, flags=re.M)
    if len(functions) != FOG_FUNCTIONS:
        raise ValueError(f"{name}: the game's file defines {functions}, not the {FOG_FUNCTIONS} functions this was "
                         f"written for (a new game version? read the file again and adjust sky/_shaders.py)")
    return FOG_GLSL.format(head=HEAD.format(**n), ray=RAY_LOCATION, soft=_f(HORIZON_SOFT), **_glsl(n))


def _glsl(n):
    """The numbers as GLSL text."""
    out = {}
    for key, value in n.items():
        if isinstance(value, str):
            out[key] = value
        elif isinstance(value, (list, tuple)):
            out[key] = _vec3(value)
        else:
            out[key] = _f(value)
    return out


# ---- core/sky ------------------------------------------------------------------------------------
SKY_VSH = """#version 330
#extension GL_ARB_separate_shader_objects : require

{head}
#include <minecraft:fog.glsl>
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:projection.glsl>

layout(location = 0) in vec3 Position;

layout(location = 0) out float sphericalVertexDistance;
layout(location = 1) out float cylindricalVertexDistance;

void main() {{
    if (Position.y > 0.0) {{
        // The upper disc (a fan 512 wide, 16 overhead) reaches only down to two degrees above the
        // horizon. It is spread over the whole screen instead, and each corner carries the
        // direction it is seen in: two points on the corner's line of sight, brought back from
        // the screen. The direction is a plane function of the screen position, so what the
        // fragment shader gets between the corners is exact.
        vec2 corner = Position.xz / 256.0;
        mat4 back = inverse(ProjMat * ModelViewMat);
        vec4 near = back * vec4(corner, 0.25, 1.0);
        vec4 far = back * vec4(corner, 0.75, 1.0);
        vec3 ray = far.xyz * near.w - near.xyz * far.w;
        vec3 forward = -vec3(ModelViewMat[0][2], ModelViewMat[1][2], ModelViewMat[2][2]);
        c164_ray = dot(ray, forward) < 0.0 ? -ray : ray;
        gl_Position = vec4(corner, 0.5, 1.0);
        sphericalVertexDistance = -1.0;
        cylindricalVertexDistance = -1.0;
    }} else {{
        // the dark disc under a viewer below the horizon's height: as the game has it
        gl_Position = ProjMat * ModelViewMat * vec4(Position, 1.0);
        sphericalVertexDistance = fog_spherical_distance(Position);
        cylindricalVertexDistance = fog_cylindrical_distance(Position);
    }}
}}
"""

SKY_FSH = """#version 330
#extension GL_ARB_separate_shader_objects : require

{head}
#include <minecraft:fog.glsl>
#include <minecraft:c164_layers.glsl>
#include <minecraft:dynamictransforms.glsl>

layout(location = 0) in float sphericalVertexDistance;
layout(location = 1) in float cylindricalVertexDistance;

layout(location = 0) out vec4 fragColor;

void main() {{
    if (sphericalVertexDistance < 0.0) {{
        // the upper disc, spread over the screen by sky.vsh
        vec3 d = c164_direction();
        fragColor = c164_open() ? vec4(c164_ridges(c164_sky(d), d), 1.0) : vec4(GameFogColor.rgb, 1.0);
    }} else {{
        float fogValue = max(linear_fog_value(sphericalVertexDistance, 0.0, FogSkyEnd), linear_fog_value(cylindricalVertexDistance, FogSkyEnd, FogSkyEnd));
        fragColor = vec4(mix(ColorModulator.rgb, GameFogColor.rgb, fogValue * GameFogColor.a), ColorModulator.a);
    }}
}}
"""

# ---- core/stars ----------------------------------------------------------------------------------
STARS_VSH = """#version 330
#extension GL_ARB_separate_shader_objects : require

{head}
#include <minecraft:dynamictransforms.glsl>
#include <minecraft:projection.glsl>

layout(location = 0) in vec3 Position;

layout(location = 0) out vec3 c164_star;

// The game turns the star field about the north-south axis by the hour's star angle ({game_star_angle} at the
// hour the clock is stopped at). The look wants {star_angle}: the field is turned by the difference first.
const mat3 C164_TURN = {turn};      // from the game's turn to the look's, in the field's own axes
const mat3 C164_PLACE = {place};     // the look's turn: where a star stands in the world

void main() {{
    gl_Position = ProjMat * ModelViewMat * vec4(C164_TURN * Position, 1.0);
    c164_star = C164_PLACE * Position;
}}
"""

STARS_FSH = """#version 330
#extension GL_ARB_separate_shader_objects : require

{head}
#include <minecraft:c164_layers.glsl>
#include <minecraft:dynamictransforms.glsl>

layout(location = 0) in vec3 c164_star;

layout(location = 0) out vec4 fragColor;

void main() {{
    // no star below the horizon (the far cloud sea lies there) or behind what stands on it, and
    // the lowest ones are dimmed by the horizon's haze
    vec3 d = normalize(c164_star);
    float floor_y = max(0.02, c164_skyline(d));
    if (d.y < floor_y || ColorModulator.a < 0.001) {{
        discard;
    }}
    fragColor = vec4({stars}) * smoothstep(floor_y, floor_y + 0.06, d.y);
}}
"""

# ---- include/c164_layers.glsl --------------------------------------------------------------------
# What the other sky packages paint on the sky. A module of the sky category may offer
#     shader_layer(look) -> dict(skyline=<GLSL>, ridges=<GLSL>)
# skyline defines  float c164_skyline(vec3 d): the y of the unit direction below which the sky of
#                  d's bearing is covered (-1.0 where nothing stands). It may use nothing but its
#                  own constants: the star shader includes it and has no fog.
# ridges  defines  vec3 c164_ridges(vec3 colour, vec3 d): the sky's colour in direction d with the
#                  layer painted on it. It may call the functions of include/fog.glsl (c164_band,
#                  c164_fogged, c164_fan, c164_ring).
LAYERS_GLSL = """#ifndef C164_LAYERS_GLSL
#define C164_LAYERS_GLSL

{head}
{skyline}
#ifdef MINECRAFT_FOG_GLSL
#ifndef GL_VERTEX_SHADER
{ridges}
#endif
#endif

#endif
"""
NO_SKYLINE = "float c164_skyline(vec3 d) {\n    return -1.0;\n}\n"
NO_RIDGES = "vec3 c164_ridges(vec3 colour, vec3 d) {\n    return colour;\n}\n"


def layers(look):
    """(skyline, ridges): the GLSL of the sky package that paints on the sky, or the empty pair."""
    from ..common import assembly
    offers = [m for m in assembly.category(__package__).parts() if hasattr(m, "shader_layer")]
    if len(offers) > 1:
        raise ValueError(f"only one sky package may paint on the sky for now: {[m.__name__ for m in offers]}")
    if not offers:
        return NO_SKYLINE, NO_RIDGES
    layer = offers[0].shader_layer(look)
    for key, name in (("skyline", "float c164_skyline(vec3 d)"), ("ridges", "vec3 c164_ridges(vec3 colour, vec3 d)")):
        if name not in layer.get(key, ""):
            raise ValueError(f"{offers[0].__name__}.shader_layer(): its {key!r} has to define {name}")
    return layer["skyline"], layer["ridges"]


def _rot_x(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]])


def _rot_y(deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]])


def _mat3(m):
    """A matrix as GLSL text (GLSL lists columns)."""
    return "mat3(" + ", ".join(_f(m[r][c]) for c in range(3) for r in range(3)) + ")"


def star_turns(n):
    """(turn, place): the field's extra turn in its own axes, and the look's whole turn.

    SkyRenderer: the pose is rotateY(-90) rotateX(star angle) for the stars."""
    game = _rot_y(-90.0) @ _rot_x(n["game_star_angle"])
    ours = _rot_y(-90.0) @ _rot_x(n["star_angle"])
    return game.T @ ours, ours


# ---- the files -----------------------------------------------------------------------------------
def files(look=mood.DEFAULT, parts=PARTS):
    """{name under assets/minecraft/shaders/: text} for a look."""
    n = numbers(look)
    g = _glsl(n)
    head = HEAD.format(**n).rstrip("\n")
    out = {}
    if "fog" in parts:
        out["include/fog.glsl"] = fog_glsl(n)
        name = "core/rendertype_beacon_beam.vsh"
        text = vanilla(name)
        text = _swap(text, "#include <minecraft:dynamictransforms.glsl>\n",
                     head + "\n#include <minecraft:fog.glsl>\n#include <minecraft:dynamictransforms.glsl>\n", name)
        text = _swap(text, "    vertexColor = Color;\n",
                     "    fog_spherical_distance(Position);     // passes the direction on: the fragment shader takes fog\n"
                     "    vertexColor = Color;\n", name)
        out[name] = text
    if "sky" in parts:
        if "fog" not in parts:
            raise ValueError("the sky is painted by the functions of include/fog.glsl: parts needs \"fog\" as well")
        out["core/sky.vsh"] = SKY_VSH.format(head=head)
        out["core/sky.fsh"] = SKY_FSH.format(head=head)
    if "sky" in parts or "stars" in parts:
        skyline, ridges = layers(look)
        out["include/c164_layers.glsl"] = LAYERS_GLSL.format(head=head, skyline=skyline, ridges=ridges)
    if "lightmap" in parts:
        name = "core/lightmap.fsh"
        text = vanilla(name)
        text = _swap(text, "float get_brightness(float level) {\n",
                     head + "\n"
                     f"const float C164_SKY_FACTOR = {g['sky_factor']};\n"
                     f"const vec3 C164_SKY_LIGHT = {g['sky_light']};\n"
                     f"const vec3 C164_AMBIENT = {g['ambient']};\n"
                     f"const vec3 C164_LAMP = {g['lamp']};\n\n"
                     "float get_brightness(float level) {\n", name)
        text = _swap(text, "get_brightness(sky_level) * lightmapInfo.SkyFactor;", "get_brightness(sky_level) * C164_SKY_FACTOR;", name)
        text = _swap(text, "max(lightmapInfo.AmbientColor, nightVisionColor)", "max(C164_AMBIENT, nightVisionColor)", name)
        text = _swap(text, "color += lightmapInfo.SkyLightColor * sky_brightness;", "color += C164_SKY_LIGHT * sky_brightness;", name)
        text = _swap(text, "mix(lightmapInfo.BlockLightTint, vec3(1.0),", "mix(C164_LAMP, vec3(1.0),", name)
        out[name] = text
    if "item" in parts:
        name = "core/item.vsh"
        text = vanilla(name)
        text = _swap(text, "#include <minecraft:light.glsl>\n", head + "\n#include <minecraft:light.glsl>\n", name)
        text = _swap(
            text,
            "    vertexColor = minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color);\n",
            "    // A face lit to the full by block light glows of itself (a model element with light_emission 15,\n"
            "    // a display entity with brightness 15): it is not shaded by the way it faces. Icons in the\n"
            "    // inventory are drawn without perspective and keep the game's shading.\n"
            "    vertexColor = (UV2.x >= 240 && abs(ProjMat[3][3]) < 0.5) ? Color"
            " : minecraft_mix_light(Light0_Direction, Light1_Direction, Normal, Color);\n",
            name)
        out[name] = text
    if "clouds" in parts:
        name = "core/clouds.vsh"
        text = vanilla(name)
        text = _swap(text, "#include <minecraft:fog.glsl>\n", head + "\n#include <minecraft:fog.glsl>\n", name)
        text = _swap(text, "    gl_Position = ProjMat * ModelViewMat * vec4(pos, 1.0);\n",
                     "    // The vanilla cloud layer is not drawn: without a file of ours it stands at the game's own\n"
                     "    // height, four blocks under the terrace. The cloud sea is blocks, and beyond them the sky\n"
                     "    // shader paints it.\n"
                     "    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);\n", name)
        out[name] = text
    if "stars" in parts:
        turn, place = star_turns(n)
        out["core/stars.vsh"] = STARS_VSH.format(head=head, turn=_mat3(turn), place=_mat3(place), **g)
        out["core/stars.fsh"] = STARS_FSH.format(head=head, **g)
    return out


def pack(pack_dir, look=mood.DEFAULT, parts=PARTS):
    """Write the shaders of a look into a resource pack. Returns the lines the drivers print."""
    written = files(look, parts)
    for name, text in written.items():
        path = os.path.join(pack_dir, *(ROOT + name).split("/"))
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", newline="\n") as fh:
            fh.write(text)
    return [f"sky: the look \"{look}\" as core shaders, {len(written)} files ({', '.join(sorted(written))})"]


# ---- the same arithmetic in numpy ---------------------------------------------------------------
class Twin:
    """What the shaders paint, worked out here: directions are (n, 3) arrays of unit vectors
    (x east, y up, z south), colours 0..1, camera_y the world height of the eye."""

    def __init__(self, look=mood.DEFAULT):
        self.n = n = numbers(look)
        self.sky, self.fog, self.glow, self.sea_colour = (np.array(n[k]) for k in ("sky", "fog", "glow", "sea"))
        self.west = np.array(n["west"])
        self.north = np.array([n["west"][2], 0.0, -n["west"][0]])

    @staticmethod
    def _mix(a, b, t):
        t = np.asarray(t, dtype=float)[..., None]
        return a * (1.0 - t) + b * t

    def fogged(self, distance, camera_y, rise):
        """The share of the fog on a thing `distance` away along a line that gains `rise` per block."""
        return 1.0 - np.exp(-mood.fog_depth(distance, camera_y - self.n["sea_y"], rise))

    def ring(self, d):
        stain = self.n["glow_alpha"] * np.maximum(0.0, d @ self.west)
        return self._mix(self._mix(self.fog, self.glow, stain), self.sky, self.n["share"])

    def fan(self, d):
        a = self.n["glow_alpha"]
        lift = 3.0 * d[:, 1] / a
        k = d @ self.west - lift
        out = a * 1.2 * k / (np.hypot(lift, d @ self.north) + 1.2 * k + 1e-30)
        return np.where(k > 0.0, out, 0.0)

    @staticmethod
    def level(d):
        l = np.hypot(d[:, 0], d[:, 2])
        ok = l > 1e-4
        safe = np.where(ok, l, 1.0)
        return np.stack([np.where(ok, d[:, 0] / safe, 0.0), np.zeros(len(d)), np.where(ok, d[:, 2] / safe, 1.0)], axis=1)

    def band(self, d):
        level = self.level(d)
        e = np.clip(d[:, 1] / HORIZON_SOFT, 0.0, 1.0)
        soft = np.where(d[:, 1] < 0.0, 1.0, 1.0 - e * e * (3.0 - 2.0 * e))
        ring = np.where((d[:, 1] < 0.0)[:, None], self.ring(level), self.ring(d))
        return self._mix(ring, self.glow, self.fan(level) * soft)

    def sea(self, d, camera_y):
        reach = max(camera_y - self.n["sea_y"], 0.5) / np.maximum(-d[:, 1], 1e-5)
        return self._mix(self.sea_colour, self.band(d), self.fogged(reach, camera_y, d[:, 1]))

    def behind(self, d, camera_y):
        return np.where((d[:, 1] < 0.0)[:, None], self.sea(d, camera_y), self.band(d))

    def sky_at(self, d, camera_y):
        across = 16.0 * np.hypot(d[:, 0], d[:, 2]) / np.maximum(d[:, 1], 1e-4)
        share = np.minimum(1.0, (16.0 + 496.25 * across / 512.0) / self.n["sky_end"])
        above = self._mix(self._mix(self.sky, self.ring(d), share), self.glow, self.fan(d))
        return np.where((d[:, 1] < 0.0)[:, None], self.sea(d, camera_y), above)

    def levelled(self, distance, d, camera_y):
        """The share to which a thing `distance` away in direction d is taken into the far sea."""
        distance = np.asarray(distance, dtype=float)
        return mood.levelled(distance * np.hypot(d[:, 0], d[:, 2]), camera_y - self.n["sea_y"] + distance * d[:, 1])

    def apply(self, colour, distance, d, camera_y, edge=0.0):
        """A thing's colour on the screen: `distance` away in direction d; edge is the share of the
        game's fog at the rim of the view distance."""
        hazed = self._mix(np.asarray(colour, dtype=float), self.band(d), self.fogged(distance, camera_y, d[:, 1]))
        return self._mix(hazed, self.behind(d, camera_y), np.maximum(self.levelled(distance, d, camera_y), edge))
