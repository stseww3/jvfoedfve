"""python -m scenes.obs_sky_lights.master (in build/): the lights of the master scene. Builds
scenes.obs as this tree has it (every line, with the switches as they stand) and prints what
sky/lights placed there: its report, the sources by what throws them, where the wall wash stands
and what was left out. The ledger of every light source of the map (the card's "who lights what").
Ends with 1 when the report names a problem. The whole master scene is built: run it on a node.
"""
import sys

from scenes import obs
from scenes.obs.sky import lights


def _kind(why):
    """What throws a source, without the window or bay it belongs to."""
    if why.startswith("sky/lights:"):
        return why.split(" ")[0] + (", lent" if ", lent to" in why else "")
    return why


def ledger(canvas):
    """The report of sky/lights on a canvas as lines of text, with the sources by kind."""
    r = lights.report(canvas)
    out = list(lights.summary(canvas))
    kinds = {}
    for cell, (level, why) in r["placed"].items():
        kinds.setdefault(_kind(why), []).append((level, cell))
    out.append("")
    out.append(f"sources by what throws them ({len(kinds)} kinds):")
    for kind in sorted(kinds):
        found = sorted(kinds[kind], reverse=True)
        count = {}
        for level, _ in found:
            count[level] = count.get(level, 0) + 1
        cells = " ".join(str(cell) for _, cell in found[:8]) + (" ..." if len(found) > 8 else "")
        out.append(f"  {kind:<36} {len(found):>3}: " + ", ".join(f"{lv}x{n}" for lv, n in sorted(count.items(), reverse=True))
                   + f"   at {cells}")
    out.append("")
    out.append(f"wall wash: {len(r['wash'])} projectors at {sorted(r['wash'])}")
    out.append(f"entrance: doorway {r['doors'] or 'not lit'}; behind it {sorted(r['hall']) or 'nothing'}")
    return out, r


def main():
    canvas = obs.build()
    out, r = ledger(canvas)
    print("\n".join(out))
    return 1 if r["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
