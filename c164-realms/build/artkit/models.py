"""Custom item models built from boxes, with a generated texture sheet per model.

Units are 1/16 of a block. A model is drawn in its own local space around `anchor`; on export it is
shifted to fit the engine's -16..32 element range, and `display()` folds that shift into the display
entity's translation, so the anchor always lands on the entity position.

Since 26.x a model element may be turned by any angle about all three axes, so a box can sit at any
attitude. Everything here builds on that: `tube()`, `ring()` and `ball()` make round shapes with as
many sides as wanted, `rod()`, `beam()` and `hose()` run between points, and whatever is drawn inside
`with m.turned(...)` or `with m.aimed(a, b)` is moved as one piece.
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
NORMAL = {"w": (-1.0, 0.0, 0.0), "e": (1.0, 0.0, 0.0), "d": (0.0, -1.0, 0.0), "u": (0.0, 1.0, 0.0),
          "n": (0.0, 0.0, -1.0), "s": (0.0, 0.0, 1.0)}
IDENT = (0.0, 0.0, 0.0, 1.0)

# where the highlight painted into round shapes comes from (model space: up, a little west and north)
LIGHT = (-0.35, 0.80, -0.48)


def _flat(mat, shift=-1):
    if isinstance(mat, Mat):
        i = int(min(len(mat.ramp) - 1, max(0, mat.base + shift)))
        c = mat.ramp[i]
        return Mat(f"{mat.name}_cap{i}", ["#%02x%02x%02x" % tuple(int(v) for v in c)], kind="flat", bevel=0)
    return mat


def _lit(mat, normal, bevel):
    """Variant of `mat` for a face of a round shape that looks along `normal`."""
    if not isinstance(mat, Mat):
        return mat
    d = sum(n * l for n, l in zip(normal, LIGHT))
    return mat.variant(1 if d > 0.45 else -1 if d < -0.45 else 0, bevel)


def _shade(mat, normal, mode):
    """Material for a face that ends up looking along `normal`.

    mode: "ends" / "along" keep only that pair of bevel edges, "plain" has none, "cap" is one flat
    tone (the end of a tube), "inner" is the darker inside of a ring.
    """
    if mode == "cap":
        d = sum(n * l for n, l in zip(normal, LIGHT))
        return _flat(mat, 0 if d > 0.6 else -2 if d < -0.6 else -1)
    if mode == "inner":
        return _lit(mat, (normal[0] * 0.5, normal[1] * 0.5 - 0.3, normal[2] * 0.5), "along")
    return _lit(mat, normal, 0 if mode == "plain" else mode)


class _Group:
    def __init__(self, model, move, value=None):
        self.model, self.move, self.value = model, move, value

    def __enter__(self):
        self.model._moves.append(self.move)
        return self.value

    def __exit__(self, *exc):
        self.model._moves.pop()
        return False


class Model:
    def __init__(self, name, px=1.0, anchor=(0.0, 0.0, 0.0)):
        self.name = name
        self.px = px
        self.anchor = anchor
        self.parts = []
        self._n = 0
        self._moves = []    # (quaternion, offset) applied to everything drawn, outermost first

    def _seed(self, kw):
        seed = kw.pop("seed", None)
        if seed is None:
            self._n += 1
            seed = self._n
        return seed

    # ---- moving whole groups -----------------------------------------------------------------
    def moved(self, by):
        """`with m.moved((x, y, z)):` shifts all that is drawn inside."""
        return _Group(self, (IDENT, (float(by[0]), float(by[1]), float(by[2]))))

    def turned(self, *turns, about=(0.0, 0.0, 0.0)):
        """`with m.turned(("z", 20), ("y", 45), about=p):` turns all that is drawn inside as one
        piece about the point p: first 20 degrees about z, then 45 about y (fixed axes)."""
        q = IDENT
        for axis, deg in turns:
            q = _qmul(quat(axis, deg), q)
        o = _qrot(q, about)
        return _Group(self, (q, (about[0] - o[0], about[1] - o[1], about[2] - o[2])))

    def aimed(self, a, b, axis="y"):
        """`with m.aimed(a, b) as length:` gives a frame whose origin is a and whose `axis` points
        at b, `length` units away.

        With axis "y" the frame is tipped over the shortest way. With "x" or "z" it is swung
        round and then raised, so its own y axis stays in the vertical plane: a plank drawn in
        it keeps its faces level from side to side.
        """
        d = [b[i] - a[i] for i in range(3)]
        length = math.sqrt(sum(v * v for v in d))
        if length < 1e-9:
            return _Group(self, (IDENT, tuple(a)), 0.0)
        ux, uy, uz = (v / length for v in d)
        if axis == "y":
            if uy < -1.0 + 1e-9:
                q = (1.0, 0.0, 0.0, 0.0)
            else:
                n = math.sqrt(uz * uz + ux * ux + (1.0 + uy) ** 2)
                q = (uz / n, 0.0, -ux / n, (1.0 + uy) / n)
        elif axis == "z":
            q = _qmul(quat("y", math.degrees(math.atan2(ux, uz))),
                      quat("x", -math.degrees(math.asin(max(-1.0, min(1.0, uy))))))
        else:
            q = _qmul(quat("y", math.degrees(math.atan2(-uz, ux))),
                      quat("z", math.degrees(math.asin(max(-1.0, min(1.0, uy))))))
        return _Group(self, (q, tuple(a)), length)

    # ---- drawing -----------------------------------------------------------------------------
    def box(self, a, b, mat, rot=None, skip="", grain=None, seed=None, emit=0, shade=True, faces=None, lit=None):
        """Box from corner a to corner b. skip = letters of faces to omit.

        rot = (axis, degrees, origin) turns it about one axis; rot = ("xyz", (rx, ry, rz), origin)
        about x, then y, then z (fixed axes). faces = {letter: material} overrides single faces;
        lit = {letter: mode} picks a face's tone from where it ends up looking (see _shade), or
        {letter: (mode, normal)} with the normal given in the box's own frame.
        Boxes sharing a seed share texture.
        """
        lo = [float(min(a[i], b[i])) for i in range(3)]
        hi = [float(max(a[i], b[i])) for i in range(3)]
        half = [(hi[i] - lo[i]) / 2.0 for i in range(3)]
        c = [(hi[i] + lo[i]) / 2.0 for i in range(3)]
        q = IDENT
        if rot is not None:
            axis, angle, origin = rot
            if axis == "xyz":
                q = _euler(angle)
            elif axis in AXES:
                q = quat(axis, angle)
            else:
                raise ValueError(f"{self.name}: bad rotation {rot!r}")
            d = _qrot(q, [c[i] - origin[i] for i in range(3)])
            c = [origin[i] + d[i] for i in range(3)]
        for gq, gt in reversed(self._moves):
            d = _qrot(gq, c)
            c = [d[i] + gt[i] for i in range(3)]
            q = _qmul(gq, q)
        faces = dict(faces or {})
        for letter, mode in (lit or {}).items():
            if letter in faces:
                continue
            normal = NORMAL[letter]
            if isinstance(mode, tuple):
                mode, normal = mode
            faces[letter] = _shade(mat, _qrot(q, normal), mode)
        self._n += 1
        self.parts.append({
            "lo": tuple(c[i] - half[i] for i in range(3)), "hi": tuple(c[i] + half[i] for i in range(3)),
            "mat": mat, "rot": None if abs(q[3]) > 1.0 - 1e-12 else (q, tuple(c)), "skip": set(skip), "grain": grain,
            "seed": self._n if seed is None else seed, "emit": emit, "shade": shade, "faces": faces,
        })
        return self

    def tube(self, axis, c, a0, a1, radius, mat, sides=8, cap=None, **kw):
        """Prism along `axis` from a0 to a1; c = the two other coordinates of its centre line.

        sides is even: the prism is sides/2 slabs crossing on the centre line.
        """
        k = AXES.index(axis)
        o1, o2 = [i for i in range(3) if i != k]
        origin = [0.0, 0.0, 0.0]
        origin[k], origin[o1], origin[o2] = (a0 + a1) / 2.0, c[0], c[1]
        kw.setdefault("grain", axis)
        seed = self._seed(kw)
        ends = {SIDE[k][0]: cap, SIDE[k][1]: cap} if cap else {}
        lit = {SIDE[k][0]: "cap", SIDE[k][1]: "cap"}
        lo, hi = [0.0] * 3, [0.0] * 3
        lo[k], hi[k] = a0, a1
        if sides == 4:
            lo[o1], hi[o1] = c[0] - radius, c[0] + radius
            lo[o2], hi[o2] = c[1] - radius, c[1] + radius
            return self.box(lo, hi, mat, faces=ends, lit=lit, seed=seed, **kw)
        hw = radius * math.tan(math.pi / sides)
        lo[o1], hi[o1] = c[0] - hw, c[0] + hw
        lo[o2], hi[o2] = c[1] - radius, c[1] + radius
        # the long faces continue around the tube: no bevel between them, and a painted highlight
        # on the side that looks towards the light
        lit.update({SIDE[o2][0]: "ends", SIDE[o2][1]: "ends"})
        for i in range(sides // 2):
            angle = 360.0 * i / sides
            self.box(lo, hi, mat, rot=(axis, angle, tuple(origin)) if angle else None, skip="".join(SIDE[o1]),
                     faces=ends, lit=lit, seed=seed, **kw)
        return self

    def taper(self, axis, c, a0, a1, r0, r1, mat, sides=8, steps=4, **kw):
        """Tube whose radius goes from r0 at a0 to r1 at a1 in `steps` short lengths."""
        seed = self._seed(kw)
        for i in range(steps):
            t0, t1 = i / steps, (i + 1) / steps
            self.tube(axis, c, a0 + (a1 - a0) * t0, a0 + (a1 - a0) * t1, r0 + (r1 - r0) * (t0 + t1) / 2.0, mat,
                      sides=sides, seed=seed, **kw)
        return self

    def ball(self, centre, radius, mat, sides=12, layers=6, squash=1.0, part=(-1.0, 1.0), **kw):
        """Sphere as a stack of prisms about the vertical axis. squash < 1 flattens it;
        part = (from, to) keeps a slice of its height, -1 the bottom and 1 the top."""
        seed = self._seed(kw)
        h = radius * squash
        hw_k = math.tan(math.pi / sides)
        for i in range(layers):
            t0 = part[0] + (part[1] - part[0]) * i / layers
            t1 = part[0] + (part[1] - part[0]) * (i + 1) / layers
            tm = (t0 + t1) / 2.0
            r = radius * math.sqrt(max(0.0, 1.0 - tm * tm))
            if r < 1e-6:
                continue
            slope = math.sqrt(max(0.0, 1.0 - tm * tm))
            lo = (centre[0] - r * hw_k, centre[1] + h * t0, centre[2] - r)
            hi = (centre[0] + r * hw_k, centre[1] + h * t1, centre[2] + r)
            lit = {"n": ("plain", (0.0, tm, -slope)), "s": ("plain", (0.0, tm, slope)), "u": "plain", "d": "plain"}
            for s in range(sides // 2):
                angle = 360.0 * s / sides
                self.box(lo, hi, mat, rot=("y", angle, tuple(centre)) if angle else None, skip="ew", lit=lit,
                         seed=seed, grain="x", **kw)
        return self

    def rod(self, a, b, radius, mat, sides=8, **kw):
        """Round bar from point a to point b."""
        with self.aimed(a, b, "y") as length:
            if length > 1e-9:
                self.tube("y", (0.0, 0.0), 0.0, length, radius, mat, sides=sides, **kw)
        return self

    def beam(self, a, b, width, height, mat, **kw):
        """Square-edged bar from point a to point b, standing upright: `height` is its size in the
        vertical plane through it, `width` its size sideways."""
        kw.setdefault("grain", "z")
        with self.aimed(a, b, "z") as length:
            if length > 1e-9:
                self.box((-width / 2.0, -height / 2.0, 0.0), (width / 2.0, height / 2.0, length), mat, **kw)
        return self

    def hose(self, points, radii, mats, sides=8, lap=0.25, **kw):
        """Round bar through a list of points. radii and mats are one value or one per stretch;
        each stretch runs `lap` radii into the next so that bends stay closed."""
        n = len(points) - 1
        radii = list(radii) if isinstance(radii, (list, tuple)) else [radii] * n
        mats = list(mats) if isinstance(mats, (list, tuple)) else [mats] * n
        seed = self._seed(kw)
        for i in range(n):
            with self.aimed(points[i], points[i + 1], "y") as length:
                if length < 1e-9:
                    continue
                more = radii[i] * lap
                self.tube("y", (0.0, 0.0), -more if i else 0.0, length + (more if i < n - 1 else 0.0), radii[i],
                          mats[i], sides=sides, seed=seed + i, **kw)
        return self

    def ring(self, axis, centre, radius, thick, width, mat, sides=16, arc=(0.0, 360.0), **kw):
        """Ring around `axis` through `centre`. thick = radial size, width = size along the axis.

        arc = (from, to) in degrees keeps part of it. Angles start at the first of the two other
        axes (x for rings about y or z, y for rings about x) and turn right-handed about `axis`.
        """
        k = AXES.index(axis)
        o1, o2 = [i for i in range(3) if i != k]
        step = 360.0 / sides
        count = max(1, int(round((arc[1] - arc[0]) / step)))
        half = (radius + thick / 2.0) * math.tan(math.pi / sides)
        seed = self._seed(kw)
        lo, hi = [0.0] * 3, [0.0] * 3
        lo[k], hi[k] = centre[k] - width / 2.0, centre[k] + width / 2.0
        lo[o1], hi[o1] = centre[o1] + radius - thick / 2.0, centre[o1] + radius + thick / 2.0
        lo[o2], hi[o2] = centre[o2] - half, centre[o2] + half
        lit = {SIDE[o1][1]: "along", SIDE[o1][0]: "inner", SIDE[k][0]: "along", SIDE[k][1]: "along"}
        whole = count == sides
        for s in range(count):
            theta = arc[0] + step * (s if whole else s + 0.5)
            self.box(lo, hi, mat, rot=(axis, theta, tuple(centre)) if theta else None, seed=seed,
                     skip="" if not whole and s in (0, count - 1) else "".join(SIDE[o2]), grain=AXES[o2], lit=lit, **kw)
        return self

    # ---- geometry ----------------------------------------------------------------------------
    def bounds(self):
        lo = [min(p["lo"][i] for p in self.parts) for i in range(3)]
        hi = [max(p["hi"][i] for p in self.parts) for i in range(3)]
        return lo, hi

    def reach(self):
        """Box around the model as it is seen, with every part turned into place."""
        lo, hi = [1e9] * 3, [-1e9] * 3
        for p in self.parts:
            c = [(p["lo"][i] + p["hi"][i]) / 2.0 for i in range(3)]
            h = [(p["hi"][i] - p["lo"][i]) / 2.0 for i in range(3)]
            q = p["rot"][0] if p["rot"] else IDENT
            for sx in (-1, 1):
                for sy in (-1, 1):
                    for sz in (-1, 1):
                        v = _qrot(q, (sx * h[0], sy * h[1], sz * h[2]))
                        for i in range(3):
                            lo[i] = min(lo[i], c[i] + v[i])
                            hi[i] = max(hi[i], c[i] + v[i])
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
                q, origin = p["rot"]
                el["rotation"] = {"origin": [round(origin[0] + sx, 4), round(origin[1] + sy, 4), round(origin[2] + sz, 4)]}
                el["rotation"].update(_element_turn(q))
            if not p["shade"]:
                el["shade_direction_override"] = "up"  # 26.x dropped "shade": false
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


# ---- rotations -------------------------------------------------------------------------------
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


def _euler(turn):
    """Quaternion of a turn by (rx, ry, rz) degrees: about x first, then y, then z."""
    return _qmul(quat("z", turn[2]), _qmul(quat("y", turn[1]), quat("x", turn[0])))


def _element_turn(q):
    """The "rotation" entry of a model element for quaternion q: one axis and an angle where that
    is enough, otherwise the three angles the engine applies as x, then y, then z."""
    x, y, z, w = q
    if w < 0.0:
        x, y, z, w = -x, -y, -z, -w
    for i, axis in enumerate(AXES):
        others = [v for j, v in enumerate((x, y, z)) if j != i]
        if all(abs(v) < 1e-9 for v in others):
            return {"axis": axis, "angle": round(math.degrees(2.0 * math.atan2((x, y, z)[i], w)), 4)}
    # rows of the rotation matrix
    m00, m10, m20 = 1 - 2 * (y * y + z * z), 2 * (x * y + z * w), 2 * (x * z - y * w)
    m11, m12 = 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)
    m21, m22 = 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)
    if abs(m20) > 1.0 - 1e-9:
        rx, ry, rz = math.atan2(-m12, m11), -math.copysign(math.pi / 2.0, m20), 0.0
    else:
        rx, ry, rz = math.atan2(m21, m22), -math.asin(m20), math.atan2(m10, m00)
    return {"x": round(math.degrees(rx), 4), "y": round(math.degrees(ry), 4), "z": round(math.degrees(rz), 4)}


# ---- display entities ------------------------------------------------------------------------
def display(model, yaw=0.0, scale=1.0, turns=(), brightness=None, ns="c164", view=3.0):
    """NBT of an item_display that shows `model` with its anchor on the entity position.

    With yaw 0 the model's axes line up with the world's. yaw turns it about the vertical axis like
    an entity's facing; `turns` is a list of (axis, degrees) applied to the model first, in order.
    scale is one number or (x, y, z) along the model's own axes. brightness overrides the light the
    model would take from the block it stands in: one level, or (sky, block).
    """
    sx, sy, sz = model.shift()
    q = (0.0, 0.0, 0.0, 1.0)
    for axis, deg in turns:
        q = _qmul(quat(axis, deg), q)
    # the item renderer centres the model on (8, 8, 8) and turns it half a turn about y, so the
    # rotation is expressed in that turned frame
    q = (-q[0], q[1], -q[2], q[3])
    s = (scale, scale, scale) if isinstance(scale, (int, float)) else tuple(scale)
    a = ((model.anchor[0] + sx - 8.0) / 16.0, (model.anchor[1] + sy - 8.0) / 16.0, (model.anchor[2] + sz - 8.0) / 16.0)
    flipped = (-a[0] * s[0], a[1] * s[1], -a[2] * s[2])
    t = _qrot(q, flipped)
    nbt = {
        "id": "minecraft:item_display",
        "item": {"id": "minecraft:stick", "count": 1, "components": {"minecraft:item_model": f"{ns}:{model.name}"}},
        "item_display": "none",
        "transformation": {
            "left_rotation": [Float(q[0]), Float(q[1]), Float(q[2]), Float(q[3])],
            "right_rotation": [Float(0.0), Float(0.0), Float(0.0), Float(1.0)],
            "scale": [Float(s[0]), Float(s[1]), Float(s[2])],
            "translation": [Float(-t[0]), Float(-t[1]), Float(-t[2])],
        },
        "Rotation": [Float((180.0 + yaw) % 360.0), Float(0.0)],
        "view_range": Float(view),
        "Tags": ["c164art"],
    }
    if brightness is not None:
        sky, block = brightness if isinstance(brightness, (tuple, list)) else (brightness, brightness)
        nbt["brightness"] = {"sky": int(sky), "block": int(block)}
    return nbt


def between(model, a, b, thick=1.0, length=48.0, **kw):
    """Display NBT (to be summoned at a) that stretches `model` from point a to point b.

    The model must run along +z from its anchor and be `length` units long.
    """
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    flat = math.hypot(dx, dz)
    dist = math.hypot(flat, dy)
    yaw = math.degrees(math.atan2(-dx, dz))
    pitch = math.degrees(math.atan2(dy, flat))
    return display(model, yaw=yaw, scale=(thick, thick, dist * 16.0 / length), turns=(("x", -pitch),), **kw)


def write_pack(pack_dir, models, ns="c164", description="c164 art test props"):
    os.makedirs(pack_dir, exist_ok=True)
    with open(os.path.join(pack_dir, "pack.mcmeta"), "w") as fh:
        json.dump({"pack": {"description": description, "min_format": 97, "max_format": 97}}, fh, indent=1)
    return [m.export(pack_dir, ns) for m in models]
