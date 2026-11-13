#!/usr/bin/env python3
"""Write the resource pack with a scene's custom models.

    makepack.py <scene> --out <resource pack directory>

The scene module must provide scenes/<scene>/props.py with build_models(). If the scene package has
a write_pack(pack_dir) function it is called too, for repainted blocks and replaced vanilla textures.
"""
import argparse
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artkit import models as M  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    scene_mod = importlib.import_module(f"scenes.{args.scene}")
    # a multi-line scene (obs) collects its models at the scene level; a single scene keeps them in
    # its props module. Prefer the scene-level build_models(), fall back to scenes.<scene>.props.
    builder = getattr(scene_mod, "build_models", None)
    if builder is None:
        builder = importlib.import_module(f"scenes.{args.scene}.props").build_models
    built = builder()
    for info in M.write_pack(args.out, list(built.values())):
        print(f"{info['name']:18s} {info['elements']:3d} elements, {info['rects']:3d} texture patches, sheet {info['texture']}px")
    extra = getattr(scene_mod, "write_pack", None)
    if extra:
        for line in extra(args.out):
            print(line)


if __name__ == "__main__":
    main()
