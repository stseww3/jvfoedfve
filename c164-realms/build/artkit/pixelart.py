"""Procedural pixel-art materials for custom model textures.

Each material is a short colour ramp (dark to light) plus a rule for how levels vary across a face, in
the manner of the vanilla textures: a few flat tones, one-pixel shading, no gradients.
"""
import numpy as np


def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _hash(i, j, seed):
    """Integer lattice hash to [0, 1); i and j may be arrays."""
    i = np.asarray(i, dtype=np.int64)
    j = np.asarray(j, dtype=np.int64)
    h = (i * 374761393 + j * 668265263 + int(seed) * 2147483647) & 0xFFFFFFFF
    h = ((h ^ (h >> 13)) * 1274126177) & 0xFFFFFFFF
    h = h ^ (h >> 16)
    return (h & 0xFFFFFF) / float(1 << 24)


class Mat:
    """A paintable material.

    ramp   colours from dark to light
    kind   plain | wood | metal | glow | cloth | rope | flat
    noise  share of pixels nudged one step up or down
    bevel  0 none, 1 light top and left edge with a dark bottom and right edge
    base   index into the ramp used for the bulk of the face (default: the middle)
    """

    def __init__(self, name, ramp, kind="plain", noise=0.2, bevel=1, base=None, alpha=255):
        self.name = name
        self.ramp = np.array([hx(c) for c in ramp], dtype=np.uint8)
        self.kind = kind
        self.noise = noise
        self.bevel = bevel
        self.base = len(ramp) // 2 if base is None else base
        self.alpha = alpha

    def levels(self, w, h, grain, seed):
        jj, ii = np.meshgrid(np.arange(h), np.arange(w), indexing="ij")
        lv = np.full((h, w), self.base, dtype=np.int32)
        r = _hash(ii, jj, seed)
        kind = self.kind
        if kind == "flat":
            return lv
        if kind == "wood":
            if grain == "cap":  # end grain: rings
                ring = np.minimum(np.minimum(ii, w - 1 - ii), np.minimum(jj, h - 1 - jj))
                lv = lv - (ring % 2)
                lv = lv + (r > 0.9)
            else:
                line, along = (jj, ii) if grain == "u" else (ii, jj)
                tone = _hash(line, 0 * line, seed + 17)
                lv = lv + (tone > 0.72).astype(np.int32) - (tone < 0.3).astype(np.int32)
                run = _hash(line, along // 3, seed + 31)
                lv = lv - (run < 0.16).astype(np.int32) + (run > 0.93).astype(np.int32)
        elif kind == "glow":
            edge = np.minimum(np.minimum(ii, w - 1 - ii), np.minimum(jj, h - 1 - jj))
            lv = np.minimum(len(self.ramp) - 1, self.base + edge + (r > 0.6))
            return lv
        elif kind == "cloth":
            lv = lv - (((ii + jj) % 2 == 0) & (r < 0.55)).astype(np.int32)
            fold = np.sin((ii + 0.5) / max(w, 1) * np.pi * 2.0 + seed)
            lv = lv + (fold > 0.55).astype(np.int32) - (fold < -0.55).astype(np.int32)
        elif kind == "rope":
            lv = lv - ((ii + jj) % 3 == 0).astype(np.int32) + ((ii + jj) % 3 == 1).astype(np.int32) * (r > 0.5)
        else:  # plain, metal
            lv = lv + (r > 1 - self.noise / 2).astype(np.int32) - (r < self.noise / 2).astype(np.int32)
        if self.bevel and kind != "cloth":
            lo, hi = (1, h - 1) if h >= 3 else (0, h)
            if h >= 3:
                lv[0, :] += 1
                lv[-1, :] -= 1
            elif h == 2:
                lv[1, :] -= 1
            if w >= 3:
                lv[lo:hi, 0] += 1
                lv[lo:hi, -1] -= 1
            elif w == 2:
                lv[lo:hi, 1] -= 1
            if kind == "metal" and w >= 4 and h >= 4:
                lv[1, 1] += 1  # glint
        return lv

    def paint(self, w, h, grain="u", seed=0):
        lv = np.clip(self.levels(w, h, grain, seed), 0, len(self.ramp) - 1)
        out = np.empty((h, w, 4), dtype=np.uint8)
        out[..., :3] = self.ramp[lv]
        out[..., 3] = self.alpha
        return out


class Sprite:
    """Hand-drawn pixels: rows of characters, each mapped to a colour ('.' and ' ' are transparent).

    On a face larger than the sprite the drawing is centred over `back` (a Mat) or left transparent.
    """

    def __init__(self, name, rows, colours, back=None):
        self.name = name
        self.rows = rows
        self.colours = {k: hx(v) for k, v in colours.items()}
        self.back = back

    def mirrored(self):
        out = Sprite(self.name + "_m", [row[::-1] for row in self.rows], {}, self.back)
        out.colours = self.colours
        return out

    def paint(self, w, h, grain="u", seed=0):
        if self.back is not None:
            out = self.back.paint(w, h, grain, seed)
        else:
            out = np.zeros((h, w, 4), dtype=np.uint8)
        sh, sw = len(self.rows), max(len(r) for r in self.rows)
        oy, ox = (h - sh) // 2, (w - sw) // 2
        for j, row in enumerate(self.rows):
            for i, ch in enumerate(row):
                y, x = oy + j, ox + i
                if ch in self.colours and 0 <= y < h and 0 <= x < w:
                    out[y, x, :3] = self.colours[ch]
                    out[y, x, 3] = 255
        return out


# ---- stock materials -------------------------------------------------------------------------
IRON = Mat("iron", ["#15161a", "#1e2026", "#2a2c34", "#383b45", "#4b4f5b", "#666b78"], kind="metal", noise=0.14)
IRON_FLAT = Mat("iron_flat", ["#2a2c34"], kind="flat", bevel=0)
BRASS = Mat("brass", ["#5a3c12", "#7a551a", "#9c7424", "#bf9433", "#dcb650", "#f3d98a"], kind="metal", noise=0.16)
BRASS_FLAT = Mat("brass_flat", ["#9c7424"], kind="flat", bevel=0)
BRASS_DARK = Mat("brass_dark", ["#3d2a0e", "#553a12", "#6e4d18", "#8a6220", "#a67a2c"], kind="metal", noise=0.14)
COPPER = Mat("copper", ["#7a3b22", "#9a4e2c", "#b9653a", "#d2814e", "#e6a070"], kind="metal", noise=0.16)
VERDIGRIS = Mat("verdigris", ["#2f6f5c", "#3d8a70", "#4fa487", "#6dbb9c", "#93d3b6"], kind="metal", noise=0.22)
DARK_WOOD = Mat("dark_wood", ["#2c1d10", "#3a2716", "#4a331d", "#5b4025", "#6c4d2e"], kind="wood")
WOOD = Mat("wood", ["#5c4023", "#72512c", "#8a6437", "#a17843", "#b78c53"], kind="wood")
PALE_WOOD = Mat("pale_wood", ["#9a7d4f", "#b0935f", "#c4a871", "#d5bb86", "#e3cf9f"], kind="wood")
STONE = Mat("stone", ["#55565a", "#66676b", "#78797d", "#8b8c90", "#9fa0a4"], noise=0.3)
LAMP_GLOW = Mat("lamp_glow", ["#c96a1c", "#f09a2e", "#ffc65a", "#ffe9a6", "#fff8dc"], kind="glow", bevel=0, base=2)
LENS = Mat("lens", ["#27506b", "#3a7391", "#5b9bb8", "#8cc4da", "#c9ecf6"], kind="glow", bevel=0, base=0)
RED_CLOTH = Mat("red_cloth", ["#5e1717", "#7c2020", "#9c2b2b", "#b83a36", "#cf5248"], kind="cloth", bevel=0)
CREAM_CLOTH = Mat("cream_cloth", ["#a79a7e", "#c2b596", "#d9cdb0", "#eadfc6", "#f6eedb"], kind="cloth", bevel=0)
ROPE = Mat("rope", ["#6b5330", "#866a3e", "#a3844f", "#bd9d64"], kind="rope", bevel=0)
PARCHMENT = Mat("parchment", ["#b79e6c", "#cbb482", "#dcc898", "#eadbb1"], noise=0.25, bevel=0)
