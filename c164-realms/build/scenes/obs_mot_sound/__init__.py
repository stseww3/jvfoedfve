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
SPACING = 24                       # blocks: more than twice the largest reach used here (10)
PLINTH_TOP = 1                     # the plinth is one block; its cap sits on top
WALL = B.TUFF_BRICK.block
CAP = B.BRASS_PLATE.block if hasattr(B, "BRASS_PLATE") else B.IRON_PLATE.block

# one plinth per candidate, in the card's order
CANDIDATES = [(event, i) for event in sound.VOICES for i in range(len(sound.VOICES[event]))]


ROWS = 2                           # two rows, so the whole set is a short walk and one wide picture


def _spot(k):
    """Plinth k's (x, z): eleven in the first row, the rest in a second row behind it."""
    per = (len(CANDIDATES) + ROWS - 1) // ROWS
    return (k % per) * SPACING, ROW_Z - (k // per) * SPACING * 2


def layout(c=None):
    c = c or Canvas()
    for k in range(len(CANDIDATES)):
        px, pz = _spot(k)
        c.set(px, 0, pz, WALL)
        c.set(px, PLINTH_TOP, pz, CAP)
    n = 0
    # every candidate at its own plinth, each on its own period so no two plinths speak at once: the
    # row is meant to be walked and one voice heard at a time
    for k, (event, i) in enumerate(CANDIDATES):
        px, pz = _spot(k)
        _name, volume, pitch = sound.VOICES[event][i]
        cycle = 23 + 7 * k                       # a different period per plinth
        sound.MK.sound(c, (px + 0.5, PLINTH_TOP + 1, pz + 0.5), event, cycle,
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
    per = (len(CANDIDATES) + ROWS - 1) // ROWS
    span = (per - 1) * SPACING
    mid_z = ROW_Z - SPACING
    return [{"name": "row", "pos": [span / 2.0, 22.0, mid_z + 38.0],
             "look_at": [span / 2.0, 1.0, mid_z], "time": TIME}]
