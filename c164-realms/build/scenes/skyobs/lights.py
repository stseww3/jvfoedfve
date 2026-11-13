"""Lamplight that shows from outside: glowing windows.

A lit room behind glass still looks dark from across an island, because all the eye gets is a
far wall at block-light brightness. So every window gets a sheet of painted lamplight just behind
its panes (a custom model that is always fully lit): by day it reads as sun on a curtain, at dusk
and at night the windows glow.
"""
import math

from . import props

DEPTH = 0.3   # how far behind the panes the sheet stands


def window(c, x0, y0, z0, x1, y1, z1, out):
    """Light the window whose panes fill the cells x0..x1, y0..y1, z0..z1 (one cell deep).
    out = (dx, dz) is the way out of the building."""
    w = max(abs(x1 - x0), abs(z1 - z0)) + 1
    h = abs(y1 - y0) + 1
    name = f"glow_{w}x{h}"
    if name not in props.SCALE:
        raise ValueError(f"no window light of {w} by {h}")
    x = (min(x0, x1) + max(x0, x1) + 1) / 2.0 - out[0] * DEPTH
    z = (min(z0, z1) + max(z0, z1) + 1) / 2.0 - out[1] * DEPTH
    y = (min(y0, y1) + max(y0, y1) + 1) / 2.0
    props.place(c, name, x, y, z, yaw=math.degrees(math.atan2(-out[0], out[1])))
