"""The seam test's second half (director, 11-16): a resource-pack override of the vanilla cloud
shader, so the vanilla layer fogs like the block clouds do instead of just fading out.

The block clouds of `sky/cloudsea` mix their colour towards the fog from 60 to 192 blocks. The
vanilla layer does something else: it keeps its colour and multiplies its alpha by
(1 - vertexDistance / FogCloudsEnd), so what shows through is the void behind it. Two laws, and the
join between them reads as a rim round the mountain. This module writes one file into the pack --
`assets/minecraft/shaders/core/clouds.fsh` -- with the alpha line replaced by a colour mix towards
the fog:

    color.rgb = mix(color.rgb, FogColor.rgb, linear_fog_value(vertexDistance, FogEnvironmentalStart,
                                                             FogEnvironmentalEnd) * FogColor.a);

Nothing else changes: the fog's own 60 to 192 is not touched, so the whole scene reads as before;
the layer simply no longer lets stars and the afterglow through.

ART-PLAN section 8: replacing a core shader in the finished map needs the admin's own approval.
This module is a trial and is NOT switched on by any look or scene: `sky/look` calls it only when
its `SHADER_SEAM` flag is set, which the director asked to keep off until the picture is judged.
The file is written under `assets/minecraft/shaders/core/`, a path no other package in the project
writes to (checked: only `comet.py` and `lights.py` write into `assets/minecraft/`, both under
`textures/`).
"""
import os

# The vanilla file, from 26.3's own jar except for the one line this module replaces. Kept whole
# rather than patched at write time so that a change in the game's shader shows up as a diff here.
SHADER = """#version 330
#extension GL_ARB_separate_shader_objects : require

#include <minecraft:fog.glsl>
#include <minecraft:oit.glsl>

layout(location = 0) in float vertexDistance;
layout(location = 1) in vec4 vertexColor;

#ifndef OIT_ALPHA_ONLY
layout(location = 0) out vec4 fragColor;
#endif

vec4 calculateFinalColor(vec4 color) {
    #ifdef OIT_ACCUMULATE
    color = sampleColorForAccumulation(color);
    #endif
    return color;
}

void main() {
    vec4 color = vertexColor;
    #ifndef OIT_DEPTH_BOUNDS
    // seam trial: the layer fogs like the block clouds instead of fading to nothing (vanilla line:
    // color.a *= 1.0f - linear_fog_value(vertexDistance, 0, FogCloudsEnd);)
    color.rgb = mix(color.rgb, FogColor.rgb, linear_fog_value(vertexDistance, FogEnvironmentalStart,
                                                             FogEnvironmentalEnd) * FogColor.a);
    #endif

    #ifdef OIT_ALPHA_ONLY
    executeAlphaOnlyPhase(gl_FragCoord.z, color.a);
    #else
    fragColor = calculateFinalColor(color);
    #endif
}
"""

PATH = "assets/minecraft/shaders/core/clouds.fsh"


def wanted():
    """Whether this round asks for the override. Off unless C164_SEAM_SHADER is set to 1.

    A resource pack that replaces a core shader needs the admin's own approval (ART-PLAN 8), so the
    file must never ride into the assembly by accident: it is written only when the round is the
    seam trial and someone set the switch on purpose. The director's picture test sets it; a normal
    export, a check.py run or a delivery leaves it alone.
    """
    return os.environ.get("C164_SEAM_SHADER", "") == "1"


def pack(pack_dir):
    """Write the override. Returns the one-line summary the export prints."""
    path = os.path.join(pack_dir, *PATH.split("/"))
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="\n") as fh:
        fh.write(SHADER)
    return [f"cloud shader overridden ({PATH}): the layer fogs like the block clouds"]
