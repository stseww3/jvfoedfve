"""The second colour of the time ball on the tower of obs_mach_clocks: the same scene, the dark red
ball on the mast instead of the old-copper one.

The ball is seen against the sky under the comet, and that can only be judged with the ball in its
place: one mast holds one ball. So the two colours are compared picture by picture: every shot of
this scene has its twin of the same name in obs_mach_clocks. (Side by side, close, they stand in
that scene's shot balls_pair.)

    python -m scenes.obs_mach_clocks_b      # writes shots.json (the tower shots of the other scene)
"""
from scenes import obs_mach_clocks as first
from scenes.obs_mach_clocks import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, TIME, write_pack  # noqa: F401

BALL = "red"
SHOTS = ("v1_tower", "tower_far", "v5_up", "tower_foot", "top_close")


def build():
    return first.build(ball=BALL)


def shots():
    return [s for s in first.shots() if s["name"] in SHOTS]
