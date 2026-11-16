"""Procedural pixel-art materials for custom model textures.

Each material is a short colour ramp (dark to light) plus a rule for how levels vary across a face, in
the manner of the vanilla textures: a few flat tones, one-pixel shading, no gradients.
"""
import copy
import math

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
    bevel  0 none, 1 light top and left edge with a dark bottom and right edge,
           "along" only the two edges that run with the grain, "ends" only the two across it
    base   index into the ramp used for the bulk of the face (default: the middle)
    """

    def __init__(self, name, ramp, kind="plain", noise=0.2, bevel=1, base=None, alpha=255):
        self.name = name
        self.ramp = np.array([hx(c) for c in ramp], dtype=np.uint8).reshape(-1, 3)
        self.kind = kind
        self.noise = noise
        self.bevel = bevel
        self.base = len(ramp) // 2 if base is None else base
        self.alpha = alpha
        self._variants = {}

    def variant(self, shift=0, bevel=None):
        """The same material `shift` steps lighter or darker, optionally with another bevel mode."""
        b = self.bevel if bevel is None else bevel
        if shift == 0 and b == self.bevel:
            return self
        key = (shift, b)
        if key not in self._variants:
            m = copy.copy(self)   # keeps subclasses and whatever else they carry
            m.name = f"{self.name}~{shift}~{b}"
            m.bevel = b
            m.base = int(min(len(self.ramp) - 1, max(0, self.base + shift)))
            m._variants = {}
            self._variants[key] = m
        return self._variants[key]

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
        elif kind == "metal":  # mostly flat, a few short brushed streaks along the grain
            if grain == "cap":
                lv = lv + (r > 1 - self.noise / 2).astype(np.int32) - (r < self.noise / 2).astype(np.int32)
            else:
                line, along = (jj, ii) if grain == "u" else (ii, jj)
                streak = _hash(line, along // 5, seed + 7)
                lv = lv + (streak > 1 - self.noise / 2).astype(np.int32) - (streak < self.noise / 2).astype(np.int32)
        else:  # plain
            lv = lv + (r > 1 - self.noise / 2).astype(np.int32) - (r < self.noise / 2).astype(np.int32)
        if self.bevel and kind != "cloth":
            every = self.bevel not in ("along", "ends") or grain == "cap"
            rows = every or (self.bevel == "along") == (grain == "u")
            cols = every or (self.bevel == "along") == (grain == "v")
            lo, hi = (1, h - 1) if rows and h >= 3 else (0, h)
            if rows:
                if h >= 3:
                    lv[0, :] += 1
                    lv[-1, :] -= 1
                elif h == 2:
                    lv[1, :] -= 1
            if cols:
                if w >= 3:
                    lv[lo:hi, 0] += 1
                    lv[lo:hi, -1] -= 1
                elif w == 2:
                    lv[lo:hi, 1] -= 1
            if kind == "metal" and rows and cols and w >= 4 and h >= 4:
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


class Frames:
    """A picture that changes with time: `mats` are shown one after the other, each for `frametime`
    ticks (a twentieth of a second), and round again. Anything with paint() will do for a frame (a
    Mat, a Sprite, a kit's drawn picture). A model with such a material on any face gets an animated
    sheet (models.Model.export): the game runs it by itself in every client, without a command and
    without an entity, and out of step with the server's clock and with every other client.

    The first frame is the one the offline pictures and the checks see: make it the look the thing
    is to have in a still. interpolate: the game blends each frame into the next, tick by tick
    (soft, and the client redraws the whole sheet every tick: for small sheets only).
    Rules and examples: plan/parts/materials.md, section 2 D.
    """

    def __init__(self, name, mats, frametime=2, interpolate=False):
        mats = list(mats)
        if len(mats) < 2:
            raise ValueError(f"{name}: a moving picture needs two frames at least")
        if int(frametime) < 1:
            raise ValueError(f"{name}: frametime {frametime!r}; a frame lasts one tick at least")
        self.name = name
        self.mats = mats
        self.frametime = int(frametime)
        self.interpolate = bool(interpolate)

    def variant(self, shift=0, bevel=None):
        """The same frames, each `shift` steps lighter or darker where a frame can be (a Mat)."""
        if shift == 0 and bevel is None:
            return self
        mats = [m.variant(shift, bevel) if hasattr(m, "variant") else m for m in self.mats]
        return Frames(f"{self.name}~{shift}~{bevel}", mats, self.frametime, self.interpolate)

    def paint(self, w, h, grain="u", seed=0):
        return self.mats[0].paint(w, h, grain, seed)

    def frames(self, w, h, grain="u", seed=0):
        return [m.paint(w, h, grain, seed) for m in self.mats]


class Picture:
    """Ready pixels as a material: an (h, w, 4) array for a face of that size. On a larger face it
    is centred and the rest left clear; of a smaller face it shows its middle."""

    def __init__(self, name, pixels):
        self.name = name
        self.pixels = np.asarray(pixels, dtype=np.uint8)

    def paint(self, w, h, grain="u", seed=0):
        ph, pw = self.pixels.shape[:2]
        out = np.zeros((h, w, 4), dtype=np.uint8)
        y0, x0 = (h - ph) // 2, (w - pw) // 2
        ys, xs = max(0, y0), max(0, x0)
        ye, xe = min(h, y0 + ph), min(w, x0 + pw)
        out[ys:ye, xs:xe] = self.pixels[ys - y0:ye - y0, xs - x0:xe - x0]
        return out


def shimmer(name, pixels, ramp, frames=6, frametime=3, share=0.3, seed=0, interpolate=False):
    """A drawn picture of something that glows, made to flicker: Frames whose first frame is the
    picture itself; in each later frame a `share` of the pixels that have a colour of `ramp` (hex
    strings or (r, g, b), dark to light) go one step up or down it. Every other pixel stays, so
    the iron round a fire does not move. For coals, embers, a filament, a glowing slot or pane."""
    base = np.asarray(pixels, dtype=np.uint8)
    steps = np.array([hx(c) if isinstance(c, str) else tuple(c) for c in ramp], dtype=np.int32).reshape(-1, 3)
    level = np.full(base.shape[:2], -1, dtype=np.int32)
    for n, rgb in enumerate(steps):
        level[(base[..., :3] == rgb).all(axis=2) & (base[..., 3] > 0)] = n
    jj, ii = np.meshgrid(np.arange(base.shape[0]), np.arange(base.shape[1]), indexing="ij")
    out = [Picture(f"{name}_0", base)]
    for k in range(1, int(frames)):
        r = _hash(ii, jj, seed * 131 + k * 17 + 5)
        move = np.where(r < share / 2.0, -1, np.where(r > 1.0 - share / 2.0, 1, 0))
        new = np.where(level >= 0, np.clip(level + move, 0, len(steps) - 1), -1)
        frame = base.copy()
        frame[..., :3] = np.where((new >= 0)[..., None], steps[np.maximum(new, 0)], base[..., :3])
        out.append(Picture(f"{name}_{k}", frame))
    return Frames(name, out, frametime, interpolate)


def flame(name, ramp, w, h, frames=8, frametime=2, seed=0, fan=False):
    """A small flame on a clear ground, w by h pixels, as Frames: `ramp` is three colours from the
    flame's edge to its heart (hex strings or (r, g, b)). A tongue that stands on the middle of the
    bottom row, leans a pixel to either side and rises and sinks by one (an oil lamp, a candle);
    fan=True is the flat fishtail of a gas burner, widest above its middle, whose top edge ripples.
    The first frame is the flame upright at its mean height."""
    tones = [hx(c) if isinstance(c, str) else tuple(c) for c in ramp]
    if len(tones) != 3:
        raise ValueError(f"{name}: a flame takes three colours (edge, body, heart), got {len(tones)}")
    out = []
    for k in range(int(frames)):
        # the tip goes once round a small circle in the course of the frames: (lean, drop) from
        # upright and mean, to one side, up, to the other side, down
        turn = 2.0 * math.pi * k / int(frames) + (0.0 if k == 0 else 0.4 * (float(_hash(k, 1, seed)) - 0.5))
        lean = 0 if k == 0 else int(round(1.2 * math.sin(turn)))
        drop = 0 if k == 0 else int(round(1.2 * math.sin(turn * 2.0 + 1.0 + seed)))
        px = np.zeros((h, w, 4), dtype=np.uint8)
        top = min(max(1 + drop, 0), h - 2)
        tall = h - top
        for y in range(top, h):
            t = (h - 1 - y) / max(1.0, tall - 1.0)              # 0 at the foot, 1 at the tip
            if fan:
                half = (0.5 + 2.4 * t / 0.6) * (w / 7.0) if t < 0.6 else (2.9 - 2.2 * (t - 0.6) / 0.4) * (w / 7.0)
                half += 0.9 * (float(_hash(k, y, seed + 9)) - 0.5) if t > 0.6 and k else 0.0
            else:
                half = (0.45 + 1.6 * math.sin(math.pi * min(1.0, 0.15 + t * 0.85)) * (1.0 - 0.45 * t)) * (w / 5.0)
            mid = (w - 1) / 2.0 + (lean if t > 0.55 else 0)
            for x in range(w):
                d = abs(x - mid)
                if d > half:
                    continue
                inner = d <= half - 1.0
                heart = inner and d <= max(0.0, half - 2.0) and 0.08 < t < 0.6
                px[y, x, :3] = tones[2] if heart else tones[1] if inner else tones[0]
                px[y, x, 3] = 255
        out.append(Picture(f"{name}_{k}", px))
    return Frames(name, out, frametime)


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
