#!/usr/bin/env python3
"""Write the resource pack with a scene's custom models.

    makepack.py <scene> --out <resource pack directory>

The scene module must provide scenes/<scene>/props.py with build_models().
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
    props = importlib.import_module(f"scenes.{args.scene}.props")
    built = props.build_models()
    for info in M.write_pack(args.out, list(built.values())):
        print(f"{info['name']:18s} {info['elements']:3d} elements, {info['rects']:3d} texture patches, sheet {info['texture']}px")


if __name__ == "__main__":
    main()
