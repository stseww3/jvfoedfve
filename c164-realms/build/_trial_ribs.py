"""Scratch: how far the dome's raster courses reach under a rib that swings about the axis.

For a rib at 27 degrees, half a block wide either side of its meridian, swinging +-A: for every
course (ring) the least and the greatest radius at which the footprint still finds a column of that
course, and the same for a rib that stands still (A = 0).
"""
import math
import sys

sys.path.insert(0, ".")

from scenes.obs.main import _dome as D  # noqa: E402

AX, AZ = D.CX + 0.5, D.CZ + 0.5
PLATES = D.plates()


def ring_at(px, pz):
    col = (math.floor(px), math.floor(pz))
    return D._ring(*col) if col in PLATES else None


def survey(angle, swing, half):
    out = {}
    steps = max(1, int(round(swing / 0.25)))
    for i in range(-steps, steps + 1):
        phi = math.radians(angle + (swing * i / steps if swing else 0.0))
        c, s = math.cos(phi), math.sin(phi)
        for j in range(-9, 10):
            t = half * j / 9.0
            for n in range(0, 15 * 50):
                rho = n / 50.0
                ring = ring_at(AX + rho * c - t * s, AZ + rho * s + t * c)
                if ring is None:
                    continue
                lo, hi = out.get(ring, (rho, rho))
                out[ring] = (min(lo, rho), max(hi, rho))
    return out


def inner_edges(angle, swing, half):
    """For every ring: the least, over the footprint's rays, of the radius at which the ray leaves the ring."""
    out = {}
    steps = max(1, int(round(swing / 0.25)))
    for i in range(-steps, steps + 1):
        phi = math.radians(angle + (swing * i / steps if swing else 0.0))
        c, s = math.cos(phi), math.sin(phi)
        for j in range(-9, 10):
            t = half * j / 9.0
            last = {}
            for n in range(0, 15 * 50):
                rho = n / 50.0
                ring = ring_at(AX + rho * c - t * s, AZ + rho * s + t * c)
                if ring is not None:
                    last[ring] = rho
            for ring, rho in last.items():
                out[ring] = min(out.get(ring, rho), rho)
    return out


for a in (27.0, 63.0, 153.0):
    for swing in (0.0, 2.0, 3.0, 4.5):
        reach = survey(a, swing, 0.45)
        least = inner_edges(a, swing, 0.45)
        print(f"rib at {a:g}, swing +-{swing:g}:")
        for ring in range(D.R, 4, -1):
            lo, hi = reach.get(ring, (None, None))
            top = D.course(ring)
            print(f"  ring {ring:2d} top {top:5.1f}: found from {lo} to {hi}; its outer edge is at least {least.get(ring)}"
                  f" -> proud up to {None if hi is None else round(hi - least[ring], 2)}")
