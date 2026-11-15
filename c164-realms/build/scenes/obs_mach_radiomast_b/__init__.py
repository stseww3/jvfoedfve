"""Test scene machines/mast version b: the same stage and the same cameras as obs_mach_radiomast,
the mast's shaft built the other way. Legs and belts are the thin iron pipe block (B.IRON_PIPE), the
display models carry the diagonals and the joint plates only. Foot, head, lamp, guys and aerial are
the same in both. See obs_mach_radiomast for the stand-ins and the shots, and machines/mast for
what the two versions are compared for.

    python -m scenes.obs_mach_radiomast_b      writes shots.json (the same as obs_mach_radiomast)
"""
from scenes.obs_mach_radiomast import (  # noqa: F401
    BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, TIME, build_models, shots, stage, write_pack)

CATEGORY = "machines"
VERSION = "b"


def build():
    return stage(VERSION)
