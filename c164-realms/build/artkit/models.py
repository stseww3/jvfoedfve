"""Custom item models built from boxes, with a generated texture sheet per model.

Units are 1/16 of a block. A model is drawn in its own local space around `anchor`; on export it is
shifted to fit the engine's -16..32 element range, and `display()` folds that shift into the display
entity's translation, so the anchor always lands on the entity position.

Element rotations are limited to one axis and -45/-22.5/0/22.5/45 degrees, which is what the model
format guarantees; round shapes come from `tube()` and `ring()`.
"""
import json
import math
import os

import numpy as np
from PIL import Image

from .nbtw import Float
from .pixelart import Mat

AXES = "xyz"
FACE_NAMES = {"n": "north", "s": "south", "e": "east", "w": "west", "u": "up", "d": "down"}
# face letter -> (axis the face is normal to, model axis along texture u, model axis along texture v)
FACE_AXES = {"n": (2, 0, 1), "s": (2, 0, 1), "e": (0, 2, 1), "w": (0, 2, 1), "u": (1, 0, 2), "d": (1, 0, 2)}
SIDE = {0: ("w", "e"), 1: ("d", "u"), 2: ("n", "s")}
ANGLES = (-45.0, -22.5, 0.0, 22.5, 45.0)


def _flat(mat):
    if isinstance(mat, Mat):
        c = mat.ramp[max(0, mat.base - 1)]
        return Mat(mat.name + "_cap", ["#%02x%02x%02x" % tuple(int(v) for v in c)], kind="flat", bevel=0)
    return mat


class Model:
    def __init__(self, name, px=1.0, anchor=(0.0, 0.0, 0.0)):
        self.name = name
        self.px = px
        self.anchor = anchor
        self.parts = []
        self._n = 0

    # ---- drawing -----------------------------------------------------------------------------
    def box(self, a, b, mat, rot=None, skip="", grain=None, seed=None, emit=0, shade=True, faces=None):
        """Box from corner a to corner b. rot = (axis, angle, origin). skip = letters of faces to omit.
        faces = {letter: material} overrides for single faces. Boxes sharing a seed share texture."""
        lo = tuple(float(min(a[i], b[i])) for i in range(3))
        hi = tuple(float(max(a[i], b[i])) for i in range(3))
        if rot is not None and rot[1] not in ANGLES:
            raise ValueError(f"{self.name}: rotation {rot[1]} is not one of {ANGLES}")
        self._n += 1
        self.parts.append({
            "lo": lo, "hi": hi, "mat": mat, "rot": rot, "skip": set(skip), "grain": grain,
            "seed": self._n if seed is None else seed, "emit": emit, "shade": shade, "faces": faces or {},
        })
        return self

    def tube(self, axis, c, a0, a1, radius, mat, sides=8, cap=None, **kw):
        """Prism along `axis` from a0 to a1; c = the two other coordinates of its centre line."""
        k = AXES.index(axis)
        o1, o2 = [i for i in range(3) if i != k]
        hw = radius * math.tan(math.pi / sides)
        steps = [(False, 0.0), (False, 45.0), (True, 0.0), (False, -45.0)]
        if sides == 16:
            steps += [(False, 22.5), (False, -22.5), (True, 22.5), (True, -22.5)]
        elif sides == 4:
            steps = [(False, 0.0)]
            hw = radius
        cap = cap or _flat(mat)
        origin = [0.0, 0.0, 0.0]
        origin[k], origin[o1], origin[o2] = (a0 + a1) / 2.0, c[0], c[1]
        kw.setdefault("grain", axis)
        seed = kw.pop("seed", None)
        if seed is None:
            self._n += 1
            seed = self._n
        for swap, angle in steps:
            e1, e2 = (radius, hw) if swap else (hw, radius)
            lo, hi = [0.0] * 3, [0.0] * 3
            lo[k], hi[k] = a0, a1
            lo[o1], hi[o1] = c[0] - e1, c[0] + e1
            lo[o2], hi[o2] = c[1] - e2, c[1] + e2
            narrow = o2 if swap else o1
            skip = "" if sides == 4 else "".join(SIDE[narrow])
            caps = {SIDE[k][0]: cap, SIDE[k][1]: cap}
            self.box(lo, hi, mat, rot=(axis, angle, tuple(origin)) if angle else None, skip=skip,
                     faces=caps, seed=seed, **kw)
        return self

    def ring(self, axis, centre, radius, thick, width, mat, sides=16, **kw):
        """Ring around `axis` through `centre`. thick = radial size, width = size along the axis."""
        k = AXES.index(axis)
        o1, o2 = [i for i in range(3) if i != k]
        half = (radius + thick / 2.0) * math.tan(math.pi / sides)
        seed = kw.pop("seed", None)
        if seed is None:
            self._n += 1
            seed = self._n
        for s in range(sides):
            theta = 360.0 * s / sides
            quarter = int(round(theta / 90.0))
            delta = theta - 90.0 * quarter
            quarter %= 4
            lo, hi = [0.0] * 3, [0.0] * 3
            lo[k], hi[k] = centre[k] - width / 2.0, centre[k] + width / 2.0
            sign = 1.0 if quarter in (0, 1) else -1.0
            ra, rb = sign * (radius - thick / 2.0), sign * (radius + thick / 2.0)
            if quarter in (0, 2):
                lo[o1], hi[o1] = centre[o1] + min(ra, rb), centre[o1] + max(ra, rb)
                lo[o2], hi[o2] = centre[o2] - half, centre[o2] + half
            else:
                lo[o2], hi[o2] = centre[o2] + min(ra, rb), centre[o2] + max(ra, rb)
                lo[o1], hi[o1] = centre[o1] - half, centre[o1] + half
            self.box(lo, hi, mat, rot=(axis, delta, tuple(centre)) if delta else None, seed=seed, **kw)
        return self

    # ---- geometry ----------------------------------------------------------------------------
    def bounds(self):
        lo = [min(p["lo"][i] for p in self.parts) for i in range(3)]
        hi = [max(p["hi"][i] for p in self.parts) for i in range(3)]
        return lo, hi

    def shift(self):
        lo, hi = self.bounds()
        out = []
        for i in range(3):
            if hi[i] - lo[i] > 48.0 + 1e-6:
                raise ValueError(f"{self.name}: {AXES[i]} span {hi[i] - lo[i]} exceeds 48 units")
            mid = (lo[i] + hi[i]) / 2.0
            out.append(8.0 - mid)
        return tuple(out)

    # ---- export ------------------------------------------------------------------------------
    def export(self, pack_dir, ns="c164"):
        sx, sy, sz = self.shift()
        rects = {}     # key -> (w, h, painter args)
        uses = []      # (part index, face letter, key)
        for pi, p in enumerate(self.parts):
            size = [p["hi"][i] - p["lo"][i] for i in range(3)]
            if p["grain"] is None:
                g = max(range(3), key=lambda i: size[i])
            else:
                g = AXES.index(p["grain"])
            for f, (normal, ua, va) in FACE_AXES.items():
                if f in p["skip"]:
                    continue
                w = max(1, int(round(size[ua] * self.px)))
                h = max(1, int(round(size[va] * self.px)))
                mat = p["faces"].get(f, p["mat"])
                grain = "u" if g == ua else "v" if g == va else "cap"
                key = (mat.name, w, h, grain, p["seed"])
                rects.setdefault(key, (w, h, mat, grain, p["seed"]))
                uses.append((pi, f, key))

        order = sorted(rects, key=lambda kk: (-rects[kk][1], -rects[kk][0], str(kk)))
        for S in (16, 32, 64, 128, 256, 512):
            pos, x, y, row_h, ok = {}, 0, 0, 0, True
            for kk in order:
                w, h = rects[kk][0] + 2, rects[kk][1] + 2
                if w > S:
                    ok = False
                    break
                if x + w > S:
                    x, y, row_h = 0, y + row_h, 0
                if y + h > S:
                    ok = False
                    break
                pos[kk] = (x, y)
                x += w
                row_h = max(row_h, h)
            if ok:
                break
        else:
            raise ValueError(f"{self.name}: texture does not fit 512x512")

        img = np.zeros((S, S, 4), dtype=np.uint8)
        for kk, (x, y) in pos.items():
            w, h, mat, grain, seed = rects[kk]
            tex = mat.paint(w, h, grain, seed)
            padded = np.pad(tex, ((1, 1), (1, 1), (0, 0)), mode="edge")
            img[y:y + h + 2, x:x + w + 2] = padded

        elements = []
        by_part = {}
        for pi, f, kk in uses:
            by_part.setdefault(pi, []).append((f, kk))
        for pi, p in enumerate(self.parts):
            el = {
                "from": [round(p["lo"][0] + sx, 4), round(p["lo"][1] + sy, 4), round(p["lo"][2] + sz, 4)],
                "to": [round(p["hi"][0] + sx, 4), round(p["hi"][1] + sy, 4), round(p["hi"][2] + sz, 4)],
            }
            for v in el["from"] + el["to"]:
                if not -16.0 <= v <= 32.0:
                    raise ValueError(f"{self.name}: coordinate {v} outside -16..32 after shift")
            if p["rot"]:
                axis, angle, origin = p["rot"]
                el["rotation"] = {"angle": angle, "axis": axis,
                                  "origin": [round(origin[0] + sx, 4), round(origin[1] + sy, 4), round(origin[2] + sz, 4)]}
            if not p["shade"]:
                el["shade"] = False
            if p["emit"]:
                el["light_emission"] = int(p["emit"])
            faces = {}
            for f, kk in by_part.get(pi, []):
                x, y = pos[kk]
                w, h = rects[kk][0], rects[kk][1]
                k = 16.0 / S
                faces[FACE_NAMES[f]] = {"uv": [round((x + 1) * k, 4), round((y + 1) * k, 4),
                                               round((x + 1 + w) * k, 4), round((y + 1 + h) * k, 4)], "texture": "#0"}
            el["faces"] = faces
            elements.append(el)

        tex_dir = os.path.join(pack_dir, "assets", ns, "textures", "item")
        mdl_dir = os.path.join(pack_dir, "assets", ns, "models", "item")
        itm_dir = os.path.join(pack_dir, "assets", ns, "items")
        for d in (tex_dir, mdl_dir, itm_dir):
            os.makedirs(d, exist_ok=True)
        Image.fromarray(img, "RGBA").save(os.path.join(tex_dir, self.name + ".png"))
        tex = f"{ns}:item/{self.name}"
        with open(os.path.join(mdl_dir, self.name + ".json"), "w") as fh:
            json.dump({"textures": {"0": tex, "particle": tex}, "elements": elements}, fh, separators=(",", ":"))
        with open(os.path.join(itm_dir, self.name + ".json"), "w") as fh:
            json.dump({"model": {"type": "minecraft:model", "model": f"{ns}:item/{self.name}"}}, fh)
        return {"name": self.name, "elements": len(elements), "texture": S, "rects": len(rects)}


# ---- display entities ------------------------------------------------------------------------
def _qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _qrot(q, v):
    x, y, z, w = q
    p = _qmul(_qmul(q, (v[0], v[1], v[2], 0.0)), (-x, -y, -z, w))
    return p[0], p[1], p[2]


def quat(axis, degrees):
    h = math.radians(degrees) / 2.0
    v = [0.0, 0.0, 0.0]
    v[AXES.index(axis)] = math.sin(h)
    return (v[0], v[1], v[2], math.cos(h))


def display(model, yaw=0.0, scale=1.0, turns=(), brightness=None, ns="c164", view=3.0):
    """NBT of an item_display that shows `model` with its anchor on the entity position.

    With yaw 0 the model's axes line up with the world's. yaw turns it about the vertical axis like
    an entity's facing; `turns` is a list of (axis, degrees) applied to the model first, in order.
    """
    sx, sy, sz = model.shift()
    q = (0.0, 0.0, 0.0, 1.0)
    for axis, deg in turns:
        q = _qmul(quat(axis, deg), q)
    # the item renderer centres the model on (8, 8, 8) and turns it half a turn about y, so the
    # rotation is expressed in that turned frame
    q = (-q[0], q[1], -q[2], q[3])
    a = ((model.anchor[0] + sx - 8.0) / 16.0, (model.anchor[1] + sy - 8.0) / 16.0, (model.anchor[2] + sz - 8.0) / 16.0)
    flipped = (-a[0] * scale, a[1] * scale, -a[2] * scale)
    t = _qrot(q, flipped)
    nbt = {
        "id": "minecraft:item_display",
        "item": {"id": "minecraft:stick", "count": 1, "components": {"minecraft:item_model": f"{ns}:{model.name}"}},
        "item_display": "none",
        "transformation": {
            "left_rotation": [Float(q[0]), Float(q[1]), Float(q[2]), Float(q[3])],
            "right_rotation": [Float(0.0), Float(0.0), Float(0.0), Float(1.0)],
            "scale": [Float(scale), Float(scale), Float(scale)],
            "translation": [Float(-t[0]), Float(-t[1]), Float(-t[2])],
        },
        "Rotation": [Float((180.0 + yaw) % 360.0), Float(0.0)],
        "view_range": Float(view),
        "Tags": ["c164art"],
    }
    if brightness is not None:
        nbt["brightness"] = {"sky": int(brightness), "block": int(brightness)}
    return nbt


def write_pack(pack_dir, models, ns="c164", description="c164 art test props"):
    os.makedirs(pack_dir, exist_ok=True)
    with open(os.path.join(pack_dir, "pack.mcmeta"), "w") as fh:
        json.dump({"pack": {"description": description, "min_format": 97, "max_format": 97}}, fh, indent=1)
    return [m.export(pack_dir, ns) for m in models]
