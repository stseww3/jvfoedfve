"""A scene laid out for the ray tracer: the palette of block looks, the grid, the light in every
cell and the boxes of the display entities. What changes with the time of day (sky, fog, the
colours of light) is added per picture from a gamelook.Look.

Which variant of a block stands where is worked out as the game does it (the block's position
seeds java.util.Random), so the grain of a lawn or a cliff comes out the same as in the game.
"""
import collections
import math

import numpy as np

from . import blockfacts as F
from . import raytrace as R
from .gameassets import NORMALS, Element, rot, split
from .shapes import Shaper, full

CARDINAL = (0.5, 1.0, 0.8, 0.8, 0.6, 0.6)          # CardinalLighting.DEFAULT: brightness by face
FACE_AXIS = (1, 1, 2, 2, 0, 0)
# Lighting: the two lamps every item is lit by, fixed in the world
LAMPS = [np.array(v) / np.linalg.norm(v) for v in ((0.2, 1.0, -0.7), (-0.2, 1.0, 0.7))]
STAR_MAP = 1024
MASK48 = np.uint64((1 << 48) - 1)
MUL, ADD = np.uint64(0x5DEECE66D), np.uint64(0xB)


# ---- java.util.Random, for arrays of seeds -------------------------------------------------------
def _pos_seed(x, y, z):
    """Mth.getSeed for arrays of block positions."""
    a = (x * 3129871).astype(np.int32).astype(np.int64)
    s = a ^ (z * 116129781) ^ y
    s = s * s * 42317861 + s * 11
    return s >> 16


def _scramble(seed):
    return (seed.astype(np.uint64) ^ MUL) & MASK48


def _next(state, bits):
    state = (state * MUL + ADD) & MASK48
    return state, (state >> np.uint64(48 - bits)).astype(np.int64)


def _next_int(state, bound):
    state, r = _next(state, 31)
    if bound & (bound - 1) == 0:
        return state, (bound * r) >> 31
    return state, r % bound


def _next_long(state):
    state, hi = _next(state, 32)
    state, lo = _next(state, 32)
    hi = hi.astype(np.uint32).astype(np.int32).astype(np.int64)
    lo = lo.astype(np.uint32).astype(np.int32).astype(np.int64)
    return state, (hi << 32) + lo


def _pick(r, weights):
    """Which entry of a weighted list a draw falls on."""
    return np.searchsorted(np.cumsum(weights), r, side="right")


class _Random:
    """One java.util.Random, for the stars."""

    def __init__(self, seed):
        self.s = (seed ^ 0x5DEECE66D) & ((1 << 48) - 1)

    def next(self, bits):
        self.s = (self.s * 0x5DEECE66D + 0xB) & ((1 << 48) - 1)
        return self.s >> (48 - bits)

    def float(self):
        return self.next(24) * 5.9604645e-8

    def double(self):
        return ((self.next(26) << 27) + self.next(27)) * 1.1102230246251565e-16


# ---- pictures ------------------------------------------------------------------------------------
# The smaller sizes of a texture, as MipmapGenerator makes them. They decide what things look like
# from afar: leaves grow darker and denser, grass and flowers keep as much of their outline as
# they have close by.
_X = np.arange(256) / 255.0
TO_LINEAR = np.round(np.where(_X >= 0.04045, ((_X + 0.055) / 1.055) ** 2.4, _X / 12.92) * 1023.0).astype(np.int64)
_X = np.arange(1024) / 1023.0
TO_SRGB = np.round(np.where(_X >= 0.0031308, 1.055 * _X ** (1 / 2.4) - 0.055, 12.92 * _X) * 255.0).astype(np.int64)
MIP_LEVELS = 4                  # the game's "mipmap levels" option


def _coverage(alpha, ref, scale):
    """Share of a picture that passes the alpha test, looked at between its pixels."""
    if alpha.shape[0] < 2 or alpha.shape[1] < 2:
        return float("nan")
    a = np.clip(alpha * scale, 0.0, 1.0)
    a00, a10, a01, a11 = a[:-1, :-1], a[:-1, 1:], a[1:, :-1], a[1:, 1:]
    count = np.zeros(a00.shape)
    for sy in range(4):
        fy = (sy + 0.5) / 4.0
        for sx in range(4):
            fx = (sx + 0.5) / 4.0
            count += (a00 * (1 - fx) * (1 - fy) + a10 * fx * (1 - fy) + a01 * (1 - fx) * fy + a11 * fx * fy) > ref
    return float(count.mean() / 16.0)


def _keep_coverage(img, wanted, ref, bias):
    """scaleAlphaToCoverage: strengthen a smaller picture's alpha until as much of it passes."""
    alpha = img[..., 3] / 255.0
    lo, hi, scale, best, error = 0.0, 4.0, 1.0, 1.0, float("inf")
    for _ in range(5):
        cover = _coverage(alpha, ref, scale)
        if abs(cover - wanted) < error:
            error, best = abs(cover - wanted), scale
        if cover < wanted:
            lo = scale
        elif cover > wanted:
            hi = scale
        else:
            break
        scale = (lo + hi) * 0.5
    img[..., 3] = (np.clip(alpha * best + bias + 0.025, 0.0, 1.0) * 255.0).astype(np.uint8)


def _solidify(img):
    """Give the empty pixels the colour of the nearest filled one (their alpha stays 0)."""
    h, w = img.shape[:2]
    queue = collections.deque((x, y) for x in range(w) for y in range(h) if img[y, x, 3] != 0)
    dist = {p: 0 for p in queue}
    while queue:
        x, y = queue.popleft()
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            q = (x + dx, y + dy)
            if 0 <= q[0] < w and 0 <= q[1] < h and dist.get(q, 1 << 30) > dist[(x, y)] + 1:
                dist[q] = dist[(x, y)] + 1
                img[q[1], q[0], :3] = img[y, x, :3]
                queue.append(q)


def _fill_dark(img):
    """Give the empty pixels three quarters of the picture's darkest colour."""
    filled = img[..., 3] != 0
    if not filled.any():
        return
    colours = img[filled][:, :3].astype(int)
    img[~filled, :3] = 3 * colours[np.argmin(colours.sum(axis=1))] // 4


def mip_levels(img, name, strategy="auto", bias=0.0, levels=MIP_LEVELS):
    """[picture, half size, quarter size, ...] as the game would upload them."""
    img = img.copy()
    alpha = img[..., 3]
    if strategy == "auto":
        strategy = "cutout" if (alpha == 0).any() else "mean"
    if not name.startswith("item/"):
        if strategy in ("cutout", "strict_cutout"):
            _solidify(img)
        elif strategy == "dark_cutout":
            _fill_dark(img)
    cutout = strategy in ("cutout", "strict_cutout", "dark_cutout")
    ref = 0.3 if strategy == "strict_cutout" else 0.5
    wanted = _coverage(img[..., 3] / 255.0, ref, 1.0) if cutout else 0.0
    out = [img]
    for _ in range(levels):
        last = out[-1]
        if last.shape[0] < 2 or last.shape[1] < 2 or last.shape[0] % 2 or last.shape[1] % 2:
            break
        h, w = last.shape[0] // 2, last.shape[1] // 2
        q = last.reshape(h, 2, w, 2, 4).transpose(0, 2, 1, 3, 4).reshape(h, w, 4, 4).astype(np.int64)
        new = np.empty((h, w, 4), dtype=np.uint8)
        if strategy == "dark_cutout":
            there = (q[..., 3:4] != 0)
            total = (TO_LINEAR[q] / 1023.0 * there).sum(axis=2) / 4.0
            new[...] = TO_SRGB[np.floor(total * 1023.0).astype(np.int64)]
        else:
            new[..., :3] = TO_SRGB[TO_LINEAR[q[..., :3]].sum(axis=2) // 4]
            new[..., 3] = q[..., 3].sum(axis=2) // 4
        if cutout:
            _keep_coverage(new, wanted, ref, bias)
        out.append(new)
    return out


class Textures:
    """Every picture the scene uses, in one array, each with its smaller sizes."""

    def __init__(self, assets):
        self.assets = assets
        self.ids = {}
        self.px, self.off, self.w, self.h, self.kind = [], [], [], [], []
        self.total = 0

    def id(self, ref):
        if ref is None:
            return -1
        hit = self.ids.get(ref)
        if hit is None:
            img = self.assets.texture(ref)
            hit = self.ids[ref] = len(self.w)
            a = img[..., 3]
            # as the game sorts its layers: solid, cutout (holes only), translucent
            self.kind.append(0 if a.min() == 255 else 1 if np.all((a == 0) | (a == 255)) else 2)
            self.h.append(img.shape[0])
            self.w.append(img.shape[1])
            ns, path = split(ref)
            meta = (self.assets.json(f"assets/{ns}/textures/{path}.png.mcmeta") or {}).get("texture", {})
            offs = [-1] * (MIP_LEVELS + 1)
            for n, level in enumerate(mip_levels(img, path, meta.get("mipmap_strategy", "auto"),
                                                 float(meta.get("alpha_cutoff_bias", 0.0)))):
                offs[n] = self.total
                self.px.append(level.reshape(-1, 4))
                self.total += level.shape[0] * level.shape[1]
            self.off.append(offs)
        return hit

    def arrays(self):
        if not self.px:
            return np.zeros((1, 4), np.uint8), np.full((1, MIP_LEVELS + 1), -1), np.ones(1), np.ones(1), np.zeros(1)
        return np.concatenate(self.px), np.array(self.off), np.array(self.w), np.array(self.h), np.array(self.kind)


def _quat(q):
    x, y, z, w = (float(v) for v in q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


FACE_UV_AXES = ((0, 2), (0, 2), (0, 1), (0, 1), (2, 1), (2, 1))     # the box axes a face's picture runs along


def _density(lo, hi, axes, uv, uvrot, tw, th):
    """Texels per block on a face, along the side where they lie closest. axes: how long the box's
    own axes are in the world; uv in fractions of the picture."""
    out = []
    for f in range(6):
        a, b = FACE_UV_AXES[f]
        if uvrot[f] & 1:
            a, b = b, a
        across = abs(uv[f][2] - uv[f][0]) * tw[f] / max((hi[a] - lo[a]) * axes[a], 1e-6)
        down = abs(uv[f][3] - uv[f][1]) * th[f] / max((hi[b] - lo[b]) * axes[b], 1e-6)
        out.append(max(across, down))
    return out


def _whole(el):
    return bool(el.aligned and np.allclose(el.lo, 0.0) and np.allclose(el.hi, 1.0) and all(t is not None for t in el.tex))


def _box(lo, hi, tex, uv=None, cull=False, tint=-1):
    """A box in the cell's own frame, for the few things that are not block models."""
    e = Element()
    e.lo, e.hi = np.array(lo, dtype=float), np.array(hi, dtype=float)
    e.inv, e.off = np.eye(3), np.zeros(3)
    for f in range(6):
        e.tex[f] = tex[f] if isinstance(tex, (list, tuple)) else tex
        e.uv[f] = uv[f] if uv is not None else (0, 0, 16, 16)
        e.tint[f] = tint
        if cull:
            e.cull[f] = f
    return e


def _water(height):
    """FluidRenderer: still water on top and below, the running picture on the sides."""
    side = (0, (1.0 - height) * 8.0, 8, 8)
    return _box((0, 0, 0), (1, height, 1), ["block/water_still"] * 2 + ["block/water_flow"] * 4,
                [(0, 0, 16, 16)] * 2 + [side] * 4, cull=True, tint=0)


def _pot():
    """Stand-in for the decorated pot, which the game draws as a block entity."""
    side = "entity/decorated_pot/decorated_pot_side"
    return [_box((1 / 16, 0, 1 / 16), (15 / 16, 1, 15 / 16), [("block/terracotta")] * 2 + [side] * 4,
                 [(1, 1, 15, 15)] * 2 + [(1, 0, 15, 16)] * 4)]


class Scene:
    def __init__(self, assets, cells, entities, colours, place=(0, 200, 0), say=None):
        """cells: {(x, y, z): state}, changed in place (what the game works out from the
        neighbours is filled in); entities: [(x, y, z, nbt)] of item displays; colours: the
        biome's .grass, .foliage, .dry_foliage and .water; place: where the scene's (0, 0, 0)
        lies in the world."""
        say = say or (lambda *a: None)
        self.assets, self.colours = assets, colours
        self.place = np.array(place, dtype=np.int64)
        self.tex = Textures(assets)
        self.tints, self._tints = [(1.0, 1.0, 1.0)], {}
        self.missing = collections.Counter()
        self._cubes, self._classes = {}, {}
        self._stars = None
        Shaper(cells, self.cube).run()

        boxes = []
        for x, y, z, nbt in entities:
            boxes += self._entity(float(x), float(y), float(z), nbt)
        pts = np.array(list(cells), dtype=np.int64).reshape(-1, 3)
        lo, hi = pts.min(axis=0), pts.max(axis=0)
        for b in boxes:
            lo = np.minimum(lo, np.floor(b["lo_w"]).astype(np.int64))
            hi = np.maximum(hi, np.floor(b["hi_w"]).astype(np.int64))
        self.lo = lo - 1
        self.shape = tuple(int(v) for v in hi - self.lo + 2)
        say(f"grid {self.shape[0]} x {self.shape[1]} x {self.shape[2]}, {len(pts)} blocks, {len(boxes)} entity boxes")

        # the palette: entry 0 is air
        self.p = {k: [0] for k in ("start", "n", "flags", "emit", "cls", "opq", "occ")}
        self.e = {k: [] for k in ("inv", "off", "lo", "hi", "tex", "uv", "uvrot", "tint", "shade", "dir", "cull",
                                  "cubic", "flags", "emit", "res")}
        names = {}
        sid = np.fromiter((names.setdefault(s, len(names)) for s in cells.values()), dtype=np.int64, count=len(cells))
        wet_state = np.array([F.wet(*full(s)) for s in names], dtype=bool)
        wet_cells = set(map(tuple, pts[wet_state[sid]].tolist()))
        self.grid = np.zeros(self.shape, dtype=np.uint16)
        order = np.argsort(sid, kind="stable")
        cuts = np.searchsorted(sid[order], np.arange(len(names) + 1))
        for state, n in names.items():
            idx = order[cuts[n]:cuts[n + 1]]
            rel = pts[idx] - self.lo
            self.grid[rel[:, 0], rel[:, 1], rel[:, 2]] = self._palette(state, pts[idx], wet_cells)
        say(f"{len(names)} states -> {len(self.p['start'])} looks, {len(self.e['inv'])} boxes, {len(self.tex.w)} pictures")

        opq, occ, emit = (np.array(self.p[k], dtype=np.uint8) for k in ("opq", "occ", "emit"))
        self.sky = R.sky_light(self.grid, opq, occ)
        self.blk = R.block_light(self.grid, opq, occ, emit)
        say("light done")
        self._boxes(boxes)

    # ---- blocks ----------------------------------------------------------------------------------
    def cube(self, state):
        """Does the block fill its cell? (Read off its model.)"""
        hit = self._cubes.get(state)
        if hit is None:
            name, props = full(state)
            parts = [] if name == "water" else self.assets.parts(name, props)
            hit = False
            if len(parts) == 1:
                _, model, x, y, uvlock = parts[0][0]
                hit = any(_whole(el) for el in self.assets.elements(model, x, y, uvlock)[0])
            self._cubes[state] = hit
        return hit

    def _palette(self, state, p, wet_cells):
        """Palette numbers for the cells p, which all hold `state`."""
        name, props = full(state)
        wet = F.wet(name, props)
        parts = [] if name == "water" else self.assets.parts(name, props)
        none = np.zeros(len(p), dtype=np.int64)
        cols = [none for _ in parts]
        if any(len(c) > 1 for c in parts):
            at = p + self.place
            st = _scramble(_pos_seed(at[:, 0], at[:, 1], at[:, 2]))
            if self.assets.multipart(name):
                st = _scramble(_next_long(st)[1])
            for k, choices in enumerate(parts):
                if len(choices) > 1:
                    weights = [c[0] for c in choices]
                    cols[k] = _pick(_next_int(st, sum(weights))[1], weights)
        if wet:
            cols.append(np.fromiter(((x, y + 1, z) in wet_cells for x, y, z in p.tolist()), dtype=np.int64, count=len(p)))
        if not cols:
            return np.full(len(p), self._look(name, props, parts, (), wet))
        keys = np.stack(cols, axis=1)
        uniq, inverse = np.unique(keys, axis=0, return_inverse=True)
        ids = np.array([self._look(name, props, parts, tuple(int(v) for v in k), wet) for k in uniq])
        return ids[np.asarray(inverse).reshape(-1)]

    def _look(self, name, props, parts, key, wet):
        """A new palette entry: the block with these variants chosen."""
        pid = len(self.p["start"])
        if pid > 65535:
            raise ValueError("more than 65535 different looks")
        els, ao = [], True
        for k, choices in enumerate(parts):
            _, model, x, y, uvlock = choices[key[k]]
            got, model_ao = self.assets.elements(model, x, y, uvlock)
            if k == 0:
                ao = model_ao
            els += got
        cube = any(_whole(el) for el in els)
        if name == "decorated_pot":
            els, ao = _pot(), False
        if not els and not wet and name not in F.INVISIBLE:
            self.missing[name] += 1
        emission = F.emission(name, props)
        solid = F.solid(name, cube)
        flags = (R.SHADE if F.casts_shade(name, cube) else 0) | (R.AO if ao and emission == 0 else 0) \
            | (R.OPAQUE if solid else 0) | (R.WET if wet else 0) | (0, R.OFF_XZ, R.OFF_XYZ)[F.offset(name)]
        start = len(self.e["inv"])
        for el in els:
            self._element(el, name, 0)
        if wet:
            level = int(props.get("level", 0)) if name == "water" else 0
            height = 1.0 if key[-1] else ((8 - level) / 9.0 if 0 < level < 8 else 8.0 / 9.0) - 0.001
            self._element(_water(height), "water", R.WATER)
        for k, v in (("start", start), ("n", len(self.e["inv"]) - start), ("flags", flags), ("emit", emission),
                     ("cls", self._class(name)), ("opq", F.dampening(name, props, cube)),
                     ("occ", 0 if solid else F.shut_faces(name, props))):
            self.p[k].append(v)
        return pid

    def _class(self, name):
        if not F.cull_class(name):
            return 0
        return self._classes.setdefault(name, len(self._classes) + 1)

    def _tint(self, name, index):
        if index < 0:
            return 0
        key = (name, index)
        if key not in self._tints:
            c = F.tint(name, index, self.colours)
            if c is None:
                self._tints[key] = 0
            else:
                self._tints[key] = len(self.tints)
                self.tints.append(tuple(float(v) for v in c[:3]))
        return self._tints[key]

    def _element(self, el, name, extra):
        e = self.e
        dirs = list(el.dirs)
        back = np.linalg.inv(el.inv)
        cubic = []
        for f in range(6):
            flat = 0
            if el.aligned:
                # where the face lies in the cell, along the way it looks
                c = (el.lo + el.hi) / 2.0
                c[FACE_AXIS[f]] = el.hi[FACE_AXIS[f]] if f & 1 else el.lo[FACE_AXIS[f]]
                v = (back @ (c - el.off))[FACE_AXIS[dirs[f]]]
                flat = int(v >= 0.9999 if dirs[f] & 1 else v <= 0.0001)
            cubic.append(flat)
        tex = [self.tex.id(t) for t in el.tex]
        uv = np.asarray(el.uv, dtype=float) / 16.0
        tw, th = [self.tex.w[t] if t >= 0 else 0 for t in tex], [self.tex.h[t] if t >= 0 else 0 for t in tex]
        e["inv"].append(el.inv)
        e["off"].append(el.off)
        e["lo"].append(el.lo)
        e["hi"].append(el.hi)
        e["tex"].append(tex)
        e["uv"].append(uv)
        e["res"].append([float(w) for w in tw] if el.world_uv else
                        _density(el.lo, el.hi, np.linalg.norm(back, axis=0), uv, el.uvrot, tw, th))
        e["uvrot"].append(list(el.uvrot))
        e["tint"].append([self._tint(name, t) for t in el.tint])
        e["shade"].append([CARDINAL[el.override if el.override >= 0 else d] for d in dirs])
        e["dir"].append(dirs)
        e["cull"].append(list(el.cull))
        e["cubic"].append(cubic)
        e["flags"].append((R.ALIGNED if el.aligned else 0) | (R.WORLD_UV if el.world_uv else 0) | extra)
        e["emit"].append(el.emit)

    # ---- display entities ------------------------------------------------------------------------
    def _entity(self, x, y, z, nbt):
        """The boxes of one item display, in scene coordinates (DisplayRenderer, ItemTransform)."""
        ref = nbt["item"]["components"]["minecraft:item_model"]
        model = self.assets.item_model(ref)
        if model is None:
            self.missing[ref] += 1
            return []
        tr = nbt["transformation"]
        yaw, pitch = (float(v) for v in nbt.get("Rotation", (0.0, 0.0)))
        turn = rot("y", -yaw) @ rot("x", pitch)
        g = turn @ _quat(tr["left_rotation"]) @ np.diag([float(v) for v in tr["scale"]]) \
            @ _quat(tr["right_rotation"]) @ rot("y", 180.0)
        if abs(np.linalg.det(g)) < 1e-12:
            return []
        gi = np.linalg.inv(g)
        centre = np.array([x, y, z]) + turn @ np.array([float(v) for v in tr["translation"]])
        light = nbt.get("brightness")
        if light is not None:
            light = (float(light["sky"]), float(light["block"]))
        out = []
        for el in self.assets.elements(model)[0]:
            inv = el.inv @ gi
            off = el.inv @ (0.5 - gi @ centre) + el.off
            corners = np.array([[(el.lo, el.hi)[i][0], (el.lo, el.hi)[j][1], (el.lo, el.hi)[k][2]]
                                for i in (0, 1) for j in (0, 1) for k in (0, 1)])
            back = np.linalg.inv(inv)
            world = (corners - off) @ back.T
            tex = [self.tex.id(t) for t in el.tex]
            uv = np.asarray(el.uv, dtype=float) / 16.0
            tw, th = [self.tex.w[t] if t >= 0 else 0 for t in tex], [self.tex.h[t] if t >= 0 else 0 for t in tex]
            shade = []
            for d in el.dirs:
                n = gi.T @ NORMALS[d]
                n /= np.linalg.norm(n)
                shade.append(min(1.0, 0.4 + 0.6 * (max(0.0, n @ LAMPS[0]) + max(0.0, n @ LAMPS[1]))))
            out.append({"inv": inv, "off": off, "lo": el.lo, "hi": el.hi, "tex": tex, "uv": uv,
                        "res": _density(el.lo, el.hi, np.linalg.norm(back, axis=0), uv, el.uvrot, tw, th),
                        "shade": shade, "emit": float(el.emit),
                        "light": light, "at": (x, y, z), "lo_w": world.min(axis=0), "hi_w": world.max(axis=0)})
        return out

    def _boxes(self, boxes):
        n = len(boxes)
        lo = self.lo.astype(float)
        self.eb = {
            "inv": np.array([b["inv"] for b in boxes]).reshape(n, 3, 3),
            "off": np.array([b["off"] + b["inv"] @ lo for b in boxes]).reshape(n, 3),
            "lo": np.array([b["lo"] for b in boxes]).reshape(n, 3),
            "hi": np.array([b["hi"] for b in boxes]).reshape(n, 3),
            "tex": np.array([b["tex"] for b in boxes]).reshape(n, 6),
            "uv": np.array([b["uv"] for b in boxes]).reshape(n, 6, 4),
            "shade": np.array([b["shade"] for b in boxes]).reshape(n, 6),
            "res": np.array([b["res"] for b in boxes]).reshape(n, 6),
        }
        light = np.zeros((n, 2))
        for i, b in enumerate(boxes):
            if b["light"] is not None:
                sky, blk = b["light"]
            else:
                # an item is lit by the cell its entity stands in
                c = np.floor(np.array(b["at"])).astype(np.int64) - self.lo
                if np.all(c >= 0) and np.all(c < self.shape):
                    sky, blk = float(self.sky[c[0], c[1], c[2]]), float(self.blk[c[0], c[1], c[2]])
                else:
                    sky, blk = 15.0, 0.0
            light[i] = max(sky, b["emit"]), max(blk, b["emit"])
        self.eb["light"] = light
        # which boxes reach into which cell of the entity grid
        span = np.zeros((n, 6), dtype=np.int64)
        for i, b in enumerate(boxes):
            span[i, :3] = np.floor((b["lo_w"] - lo - 0.01) / R.COARSE)
            span[i, 3:] = np.floor((b["hi_w"] - lo + 0.01) / R.COARSE)
        back = np.array([np.linalg.inv(m) for m in self.eb["inv"]]).reshape(n, 3, 3)
        self.cg = R.entity_grid(self.shape, *(np.ascontiguousarray(self.eb[k], dtype=np.float64)
                                              for k in ("inv", "off", "lo", "hi")), back, span)

    # ---- the moment ------------------------------------------------------------------------------
    def stars(self):
        """The game's 1500 stars (SkyRenderer.buildStars) on the six faces of a cube."""
        if self._stars is None:
            n = STAR_MAP
            out = np.zeros((6, n, n), dtype=np.uint8)
            rnd = _Random(10842)
            for _ in range(1500):
                v = np.array([rnd.float() * 2 - 1, rnd.float() * 2 - 1, rnd.float() * 2 - 1])
                size = 0.15 + rnd.float() * 0.1
                d2 = float(v @ v)
                if d2 <= 0.010000001 or d2 >= 1.0:
                    continue
                turn = rnd.double() * math.pi * 2.0
                c = v / math.sqrt(d2)
                a = np.cross(c, (0.0, 1.0, 0.0) if abs(c[1]) < 0.99 else (1.0, 0.0, 0.0))
                a /= np.linalg.norm(a)
                b = np.cross(c, a)
                a, b = a * math.cos(turn) + b * math.sin(turn), b * math.cos(turn) - a * math.sin(turn)
                axis = int(np.argmax(np.abs(c)))
                face = 2 * axis + (0 if c[axis] > 0 else 1)
                u_ax, v_ax = [(1, 2), (0, 2), (0, 1)][axis]
                ci, cj = ((c[u_ax] / abs(c[axis]) * 0.5 + 0.5) * n, (c[v_ax] / abs(c[axis]) * 0.5 + 0.5) * n)
                for i in range(max(0, int(ci) - 6), min(n, int(ci) + 7)):
                    for j in range(max(0, int(cj) - 6), min(n, int(cj) + 7)):
                        d = np.zeros(3)
                        d[axis] = 1.0 if c[axis] > 0 else -1.0
                        d[u_ax], d[v_ax] = (i + 0.5) / n * 2 - 1, (j + 0.5) / n * 2 - 1
                        along = d @ c
                        if along <= 0:
                            continue
                        p = d * (100.0 / along) - c * 100.0
                        if abs(p @ a) <= size and abs(p @ b) <= size:
                            out[face, i, j] = 255
            self._stars = out
        return self._stars

    def world(self, look, pixel):
        """The scene at a moment (a gamelook.Look); pixel: the angle one pixel covers."""
        env = np.zeros(R.ENV_SIZE)
        env[R.FOG:R.FOG + 3], env[R.SKY:R.SKY + 3] = look.fog, look.sky
        env[R.FOG_START], env[R.FOG_END] = look.fog_start, look.fog_end
        env[R.FAR_START], env[R.FAR_END], env[R.SKY_END] = look.far_start, look.far_end, look.sky_end
        env[R.STARS], env[R.PIXEL] = look.stars, pixel
        bodies, pixels, at = [], [], 0
        for angle, ref, size in ((look.sun_angle, "environment/celestial/sun", 30.0),
                                 (look.moon_angle, f"environment/celestial/moon/{look.moon_phase}", 20.0)):
            img = self.assets.texture(ref)
            n = min(img.shape[0], img.shape[1])
            img = img[:n, :n]
            if (img[..., :3] * (img[..., 3:] > 0)).max() == 0:
                continue                      # painted out
            r = math.radians(angle)
            bodies.append([-math.sin(r), math.cos(r), 0.0, 0.0, 0.0, 1.0, -math.cos(r), -math.sin(r), 0.0,
                           size / 100.0, at, n, 1.0])
            pixels.append(img.reshape(-1, 4))
            at += n * n
        tex_px, tex_off, tex_w, tex_h, tex_kind = self.tex.arrays()
        tex_levels = np.maximum(1, (np.asarray(tex_off) >= 0).sum(axis=1))
        e, p, eb = self.e, self.p, self.eb
        ne = max(1, len(e["inv"]))

        def els(key, shape, fill=0):
            a = np.full((ne,) + shape, fill, dtype=float)
            if e[key]:
                a[:len(e[key])] = np.array(e[key]).reshape((len(e[key]),) + shape)
            return a

        return R.world(
            grid=self.grid, sky=self.sky, blk=self.blk, origin=self.lo + self.place,
            pal_start=p["start"], pal_n=p["n"], pal_flags=p["flags"], pal_emit=p["emit"], pal_class=p["cls"],
            el_inv=els("inv", (3, 3)), el_off=els("off", (3,)), el_lo=els("lo", (3,)), el_hi=els("hi", (3,)),
            el_tex=els("tex", (6,), -1), el_uv=els("uv", (6, 4)), el_uvrot=els("uvrot", (6,)),
            el_tint=els("tint", (6,)), el_shade=els("shade", (6,)), el_dir=els("dir", (6,)),
            el_cull=els("cull", (6,), -1), el_cubic=els("cubic", (6,)), el_flags=els("flags", ()), el_emit=els("emit", ()),
            el_res=els("res", (6,)),
            tints=np.array(self.tints), tex_px=tex_px, tex_off=tex_off, tex_w=tex_w, tex_h=tex_h, tex_kind=tex_kind,
            tex_levels=tex_levels,
            eb_inv=eb["inv"], eb_off=eb["off"], eb_lo=eb["lo"], eb_hi=eb["hi"], eb_tex=eb["tex"], eb_uv=eb["uv"],
            eb_shade=eb["shade"], eb_light=eb["light"], eb_res=eb["res"],
            cg_start=self.cg[0], cg_n=self.cg[1], cg_list=self.cg[2],
            lightmap=look.lightmap, env=env,
            bodies=np.array(bodies, dtype=float).reshape(-1, R.BODY_SIZE),
            body_px=np.concatenate(pixels) if pixels else np.zeros((1, 4), np.uint8),
            stars=self.stars() if look.stars > 0.0 else np.zeros((6, 1, 1), np.uint8),
            star_rot=rot("x", -look.star_angle) @ rot("y", 90.0),
        )

    def camera(self, pos, look_at=None, yaw=0.0, pitch=0.0, fov=70.0):
        """The 13 numbers raytrace.render wants; pos is the eye, in scene coordinates."""
        pos = np.array(pos, dtype=float)
        if look_at is not None:
            f, y = np.array(look_at, dtype=float) - pos, 0.0
        else:
            y, p = math.radians(yaw), math.radians(pitch)
            f = np.array([-math.sin(y) * math.cos(p), -math.sin(p), math.cos(y) * math.cos(p)])
        f /= np.linalg.norm(f)
        r = np.cross(f, (0.0, 1.0, 0.0))
        if np.linalg.norm(r) < 1e-6:
            # straight up or down "up" gives no right-hand side; the yaw does, and that is 0 for a
            # look_at: tools/shoot.py turns the game's camera so
            r = np.array([-math.cos(y), 0.0, -math.sin(y)])
        r /= np.linalg.norm(r)
        u = np.cross(r, f)
        return np.concatenate([pos - self.lo, f, r, u, [math.tan(math.radians(fov) / 2.0)]])

    def picture(self, look, cam, size=(1280, 720), ss=1, fov=70.0):
        """8-bit RGB picture (h, w, 3) of the scene at the moment `look` from the camera `cam`.
        ss: rays per pixel along each side. 1 gives the game's picture, jagged edges included;
        more gives smooth edges, each ray then reading the textures as finely as its share of the
        pixel."""
        width, height = size
        w = self.world(look, 2.0 * math.tan(math.radians(fov) / 2.0) / (height * ss))
        out = np.zeros((height, width, 3))
        R.render(w, np.ascontiguousarray(cam, dtype=np.float64), width, height, ss, out)
        return (np.clip(out, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)
