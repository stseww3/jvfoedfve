"""Test scene of the work package motion/sound (plan/packages/motion/sound.md).

Sound cannot be photographed, so this scene is a row of plinths, each one voiced with a different
candidate from the sound card's VOICES table. The plinths stand 30 blocks apart -- further than any
reach the package uses -- so standing at one you hear only that one. That is the whole test: walk the
row and pick a voice.

  tick_a / tick_b / tick_c        the three candidates for the pendulum's escape
  engine_a ... telegraph_c        the same for each of the other events
  wind                            the wind bed, on its own plinth at the far end

Each plinth is one block of dressed stone with a brass cap, labelled by nothing but its position: a
sound has no label, and the card wants the voices judged by ear. `shots.json` carries one wide view
of the row (to show where the plinths are) -- the rest of the checking is listening.

    python -m scenes.obs_mot_sound        writes shots.json from the layout
"""
from artkit.canvas import Canvas

from scenes.obs import materials
from scenes.obs.common import blocks as B
from scenes.obs.motion import sound

BIOME = "obs_blue"
CATEGORY = "motion"
TIME = 14000

ROW_Z = 0
SPACING = 30                       # blocks: more than any reach in the package
PLINTH_TOP = 1                     # the plinth is one block; its cap sits on top
WALL = B.TUFF_BRICK.block
CAP = B.BRASS_PLATE.block if hasattr(B, "BRASS_PLATE") else B.IRON_PLATE.block

# one plinth per candidate, in the card's order
CANDIDATES = [(event, i) for event in sound.VOICES for i in range(len(sound.VOICES[event]))]


def layout(c=None):
    c = c or Canvas()
    x = 0
    for event, i in CANDIDATES:
        c.set(x, 0, ROW_Z, WALL)
        c.set(x, PLINTH_TOP, ROW_Z, CAP)
        x += SPACING
    n = 0
    # every candidate at its own plinth, each on its own period so no two plinths speak at once: the
    # row is meant to be walked and one voice heard at a time
    for k, (event, i) in enumerate(CANDIDATES):
        px = k * SPACING
        _name, volume, pitch = sound.VOICES[event][i]
        cycle = 23 + 7 * k                       # a different period per plinth
        sound.MK.sound(c, (px + 0.5, PLINTH_TOP + 1, ROW_Z + 0.5), event, cycle,
                       at=(0,), volume=volume, pitch=pitch, reach=10.0)
    return c, n


def build():
    c, _ = layout()
    return c


def build_models():
    return {}


def write_pack(pack_dir):
    out = materials.pack(pack_dir)
    out += sound.pack(pack_dir)
    return out


def shots():
    """One wide view of the row. Sound is not in a picture; this only shows where the plinths are."""
    span = (len(CANDIDATES) - 1) * SPACING
    return [{"name": "row", "pos": [span / 2.0, 26.0, 44.0], "look_at": [span / 2.0, 1.0, ROW_Z],
             "time": TIME}]
