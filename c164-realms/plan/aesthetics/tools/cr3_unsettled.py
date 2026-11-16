"""How many drawn faces of each machine family stand between two model axes (props/_kit.unsettled).

Such a face is lit as "up" or as a side by the last bit of a float, so two pieces of one kind can
come out a different brightness in the game (props/_kit.settle says how). Run from c164-realms:

    python plan/aesthetics/tools/cr3_unsettled.py

One line per family: models, models with such faces, faces, and the three models that have most.
"""
import importlib
import os
import sys

sys.path.insert(0, os.path.join(os.getcwd(), "build"))

FAMILIES = ["armillary", "astro", "batteryboard", "board", "boiler", "cable", "clock", "dome",
            "engine", "mast", "meridian", "orrery", "rec", "scope"]


def main():
    from scenes.obs.props import _kit as K
    print("family       models  with  faces  most")
    for family in FAMILIES:
        try:
            module = importlib.import_module("scenes.obs.machines." + family)
            models = module.models()
        except Exception as error:      # a family that cannot be built is reported, not hidden
            print(f"{family:<12} cannot be built: {type(error).__name__}: {error}")
            continue
        counts = []
        for name, model in sorted(models.items()):
            parts = getattr(model, "parts", None)
            if parts is None:
                continue
            try:
                counts.append((len(K.unsettled(model)), name))
            except Exception as error:
                counts.append((-1, f"{name} ({type(error).__name__})"))
        faces = sum(n for n, _ in counts if n > 0)
        with_faces = sum(1 for n, _ in counts if n > 0)
        most = ", ".join(f"{name} {n}" for n, name in sorted(counts, reverse=True)[:3] if n)
        print(f"{family:<12} {len(counts):>6} {with_faces:>5} {faces:>6}  {most}")


if __name__ == "__main__":
    main()
