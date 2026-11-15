#!/usr/bin/env python3
"""Write the resource pack with a scene's custom models.

    makepack.py <scene> --out <resource pack directory>

The models come from the scene's build_models(), else from scenes/<scene>/props.py; a scene with
neither has no models of its own (a board of repainted blocks). If the scene package has a
write_pack(pack_dir) function it is called too, for repainted blocks and replaced vanilla textures.
"""
import argparse
import importlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from artkit import models as M  # noqa: E402


def builder_of(scene_mod, scene_name):
    """The scene's build_models(): its own (the multi-line obs scene collects its models at the
    scene level), else its props module's, else none at all. render.py and tools/check.py take
    the models the same way, so a scene that passes the check also packs and renders."""
    builder = getattr(scene_mod, "build_models", None)
    if builder is not None:
        return builder
    try:
        return importlib.import_module(f"scenes.{scene_name}.props").build_models
    except ModuleNotFoundError as e:
        if e.name != f"scenes.{scene_name}.props":
            raise               # props.py is there and fails to import something: say so
        return dict


def write(scene_name, out):
    """Write the scene's pack into `out`. Returns (what M.write_pack says of each model, the lines
    the scene's write_pack() returns)."""
    scene_mod = importlib.import_module(f"scenes.{scene_name}")
    built = builder_of(scene_mod, scene_name)()
    infos = M.write_pack(out, list(built.values()))
    extra = getattr(scene_mod, "write_pack", None)
    return infos, list(extra(out) or ()) if extra else []


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("scene")
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    infos, lines = write(args.scene, args.out)
    for info in infos:
        print(f"{info['name']:18s} {info['elements']:3d} elements, {info['rects']:3d} texture patches, sheet {info['texture']}px")
    for line in lines:
        print(line)


if __name__ == "__main__":
    main()
