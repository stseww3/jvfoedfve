"""A flat look at a test scene without the game or the renderer: an orthographic elevation of its
blocks, each visible face with the picture its block has in the scene's pack, and the display
entities' models drawn over it where they hang. For checking where things sit on a wall while the
worker node is away; no light, no perspective, stairs and bars drawn as whole cubes.

    from sview import Scene
    s = Scene("obs_props_elecsign", "/tmp/c164_lamps/pack_es")
    img = s.elevation("east", (z0, y0, z1, y1), ppb=32)    # looking at fronts that face east
"""
import importlib
import json
import math
import os

import numpy as np
from PIL import Image

from artkit import models as M

import mview

SIDES = {   # the front looked at -> (camera forward, screen right, block face letter, depth axis sign)
    "east": ((-1, 0, 0), (0, 0, -1)),
    "west": ((1, 0, 0), (0, 0, 1)),
    "south": ((0, 0, -1), (1, 0, 0)),
    "north": ((0, 0, 1), (-1, 0, 0)),
}
SKIP = ("light", "air", "barrier", "structure_void")
PLAIN = {   # the game's own blocks the pack leaves alone: their mean colours
    "polished_deepslate": (72, 72, 73), "deepslate_bricks": (70, 70, 71), "deepslate_brick_stairs": (70, 70, 71),
    "polished_tuff": (97, 104, 99), "deepslate_tiles": (54, 54, 55), "polished_blackstone": (53, 48, 56),
}


class Scene:
    def __init__(self, scene, pack_dir, build=None):
        self.pack = pack_dir
        self._pictures = {}
        orig = M.display

        def display(model, yaw=0.0, scale=1.0, turns=(), **kw):
            nbt = orig(model, yaw=yaw, scale=scale, turns=turns, **kw)
            nbt["_view"] = (model, yaw, scale, tuple(turns))
            return nbt

        M.display = display
        try:
            mod = importlib.import_module("scenes." + scene)
            self.canvas = (build or mod.build)()
        finally:
            M.display = orig

    # ---- the blocks' pictures -----------------------------------------------------------------
    def _json(self, ref, kind):
        ns, _, path = ref.partition(":") if ":" in ref else ("minecraft", ":", ref)
        f = os.path.join(self.pack, "assets", ns, kind, path + ".json")
        if os.path.exists(f):
            with open(f) as fh:
                return json.load(fh)
        return None

    def picture(self, state):
        name = state.partition("[")[0].replace("minecraft:", "")
        if name in self._pictures:
            return self._pictures[name]
        pic = None
        bs = self._json(name, "blockstates")
        model = None
        if bs:
            v = bs.get("variants")
            if v:
                first = next(iter(v.values()))
                model = (first[0] if isinstance(first, list) else first).get("model")
            elif bs.get("multipart"):
                ap = bs["multipart"][0]["apply"]
                model = (ap[0] if isinstance(ap, list) else ap).get("model")
        seen = 0
        tex = {}
        while model and seen < 6:
            mj = self._json(model, "models")
            if not mj:
                break
            for k, v in (mj.get("textures") or {}).items():
                tex.setdefault(k, v)
            model = mj.get("parent")
            seen += 1
        for key in ("particle", "side", "all", "north", "east", "wall", "texture", "pane", "bars", "front"):
            ref = tex.get(key)
            for _ in range(4):
                if isinstance(ref, dict):
                    ref = ref.get("sprite")
                if isinstance(ref, str) and ref.startswith("#"):
                    ref = tex.get(ref[1:])
            if isinstance(ref, str):
                ns, _, path = ref.partition(":") if ":" in ref else ("minecraft", ":", ref)
                f = os.path.join(self.pack, "assets", ns, "textures", path + ".png")
                if os.path.exists(f):
                    im = Image.open(f).convert("RGBA")
                    pic = np.array(im)[:16, :16]
                    break
        if pic is None:
            pic = np.zeros((16, 16, 4), dtype=np.uint8)
            h = sum(ord(ch) for ch in name) % 40
            pic[..., :3] = PLAIN.get(name, (90 + h, 90 + h, 96 + h))
            pic[..., 3] = 255
            if "glass" in name:
                pic[..., :3] = (40, 50, 80)
            pic[0, :, :3] = pic[0, :, :3] * 0.85                # a joint, so that the cells can be counted
            pic[:, 0, :3] = pic[:, 0, :3] * 0.85
        self._pictures[name] = pic
        return pic

    # ---- the pictures ----------------------------------------------------------------------------
    def elevation(self, side, box, ppb=32, depth=None, bg=(20, 24, 40), entities=True, shade=True):
        """The fronts that face `side`, between box = (h0, y0, h1, y1) in blocks, h the horizontal
        scene coordinate across the picture (z for east and west, x for south and north). depth:
        (lo, hi) of the coordinate looked along, to cut the scene to a slab."""
        fwd, right = (np.array(v, float) for v in SIDES[side])
        up = np.array([0.0, 1.0, 0.0])
        k = 0 if side in ("east", "west") else 2            # the axis looked along
        hk = 2 if k == 0 else 0
        h0, y0, h1, y1 = box
        sgn = right[hk]
        x0, x1 = sorted((h0 * sgn, h1 * sgn))
        W, H = int(round((x1 - x0) * ppb)), int(round((y1 - y0) * ppb))
        img = np.empty((H, W, 3), dtype=np.float64)
        img[:] = bg
        zbuf = np.full((H, W), 1e18)
        c = self.canvas
        front = {}
        for (bx, by, bz), state in c.b.items():
            name = state.partition("[")[0]
            if name.replace("minecraft:", "") in SKIP:
                continue
            p = (bx, by, bz)
            if depth is not None and not depth[0] <= p[k] <= depth[1]:
                continue
            if not (min(h0, h1) - 1 <= p[hk] <= max(h0, h1) and y0 - 1 <= by <= y1):
                continue
            key = (p[hk], by)
            d = p[k] * fwd[k]                                # smaller = nearer the camera
            if key not in front or d < front[key][0]:
                front[key] = (d, state)
        nearest = min((d for d, _ in front.values()), default=0.0)
        for (h, y), (d, state) in front.items():
            pic = self.picture(state)
            lo_y, hi_y = float(y), y + 1.0
            if "type=bottom" in state:
                hi_y = y + 0.5
            elif "type=top" in state:
                lo_y = y + 0.5
            sx0, sx1 = sorted((h * sgn, (h + 1) * sgn))
            px0, px1 = int(round((sx0 - x0) * ppb)), int(round((sx1 - x0) * ppb))
            py0, py1 = int(round((y1 - hi_y) * ppb)), int(round((y1 - lo_y) * ppb))
            a0, a1, b0, b1 = max(px0, 0), min(px1, W), max(py0, 0), min(py1, H)
            if a0 >= a1 or b0 >= b1:
                continue
            ii = ((np.arange(a0, a1) - px0) * 16 // max(px1 - px0, 1)).clip(0, 15)
            jj = ((np.arange(b0, b1) - int(round((y1 - (y + 1.0)) * ppb))) * 16 // ppb).clip(0, 15)
            if sgn < 0:
                pass                                         # the picture's left is the viewer's left either way
            tile = pic[jj][:, ii]
            f = 1.0 if not shade else max(0.45, 1.0 - 0.07 * (d - nearest))     # further back, darker
            rgb = tile[..., :3] * f
            alpha = tile[..., 3:4] / 255.0
            img[b0:b1, a0:a1] = img[b0:b1, a0:a1] * (1 - alpha) + rgb * alpha
            zbuf[b0:b1, a0:a1] = d + (0.5 if fwd[k] > 0 else -0.5) * 0 + (0.0)
            # the face's plane: the side of the block towards the camera
            zbuf[b0:b1, a0:a1] = (bxyz_face(d, fwd[k]))
        if entities:
            for ex, ey, ez, nbt in c.entities:
                if "_view" not in nbt:
                    continue
                model, yaw, scale, turns = nbt["_view"]
                self._draw(img, zbuf, model, yaw, scale, turns, (ex, ey, ez), fwd, right, up, x0, y1, ppb)
        return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")

    def plan(self, box, ppb=16, top=None, bg=(20, 24, 40), entities=True):
        """From above, north up and east to the right: box = (x0, z0, x1, z1); top: leave out what
        stands above this height (to look under a roof)."""
        fwd = np.array([0.0, -1.0, 0.0])
        right = np.array([1.0, 0.0, 0.0])
        up = np.array([0.0, 0.0, -1.0])
        bx0, bz0, bx1, bz1 = box
        W, H = int(round((bx1 - bx0) * ppb)), int(round((bz1 - bz0) * ppb))
        img = np.empty((H, W, 3), dtype=np.float64)
        img[:] = bg
        zbuf = np.full((H, W), 1e18)
        tops = {}
        for (x, y, z), state in self.canvas.b.items():
            if state.partition("[")[0].replace("minecraft:", "") in SKIP:
                continue
            if top is not None and y > top:
                continue
            if not (bx0 - 1 <= x <= bx1 and bz0 - 1 <= z <= bz1):
                continue
            if (x, z) not in tops or y > tops[(x, z)][0]:
                tops[(x, z)] = (y, state)
        highest = max((y for y, _ in tops.values()), default=0)
        for (x, z), (y, state) in tops.items():
            pic = self.picture(state)
            px0, px1 = int(round((x - bx0) * ppb)), int(round((x + 1 - bx0) * ppb))
            py0, py1 = int(round((z - bz0) * ppb)), int(round((z + 1 - bz0) * ppb))
            a0, a1, b0, b1 = max(px0, 0), min(px1, W), max(py0, 0), min(py1, H)
            if a0 >= a1 or b0 >= b1:
                continue
            ii = ((np.arange(a0, a1) - px0) * 16 // max(px1 - px0, 1)).clip(0, 15)
            jj = ((np.arange(b0, b1) - py0) * 16 // max(py1 - py0, 1)).clip(0, 15)
            tile = pic[jj][:, ii]
            f = max(0.4, 1.0 - 0.035 * (highest - y)) if y < highest else 1.0
            f = 0.55 + 0.45 * (y - (-2)) / max(highest + 2, 1)          # higher, lighter
            alpha = tile[..., 3:4] / 255.0
            img[b0:b1, a0:a1] = img[b0:b1, a0:a1] * (1 - alpha) + tile[..., :3] * f * alpha
            zbuf[b0:b1, a0:a1] = -(y + 1.0)
        if entities:
            for ex, ey, ez, nbt in self.canvas.entities:
                if "_view" not in nbt or (top is not None and ey > top + 1):
                    continue
                model, yaw, scale, turns = nbt["_view"]
                # the drawing's frame: screen x = the point . right - x0, screen y = y1 - the point . up
                self._draw(img, zbuf, model, yaw, scale, turns, (ex, ey, ez), fwd, right, up, bx0, -bz0, ppb)
        return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")

    def _draw(self, img, zbuf, model, yaw, scale, turns, pos, fwd, right, up, x0, y1, ppb):
        H, W = zbuf.shape
        s = np.array((scale, scale, scale) if isinstance(scale, (int, float)) else scale, float)
        q = M.IDENT
        for axis, deg in turns:
            q = M._qmul(M.quat(axis, deg), q)
        rot = mview._yaw(yaw) @ mview._rot(q)
        world = rot @ np.diag(s) / 16.0
        pos = np.array(pos, float)
        for o, eu, ev, tex, _ in mview.quads(model, 0.0, 1.0):
            n_model = np.cross(eu, ev)
            o, eu, ev = world @ o + pos, world @ eu, world @ ev
            nw = rot @ (n_model / (np.linalg.norm(n_model) or 1.0))
            sh = min(1.0, 0.4 + 0.6 * (max(0.0, float(nw @ mview.L0)) + max(0.0, float(nw @ mview.L1))))
            p0 = np.array([o @ right, o @ up])
            a2 = np.array([[eu @ right, ev @ right], [eu @ up, ev @ up]])
            det = a2[0, 0] * a2[1, 1] - a2[0, 1] * a2[1, 0]
            if abs(det) < 1e-12:
                continue
            corners = np.array([p0, p0 + a2[:, 0], p0 + a2[:, 1], p0 + a2[:, 0] + a2[:, 1]])
            px0 = max(0, int(math.floor((corners[:, 0].min() - x0) * ppb)))
            px1 = min(W, int(math.ceil((corners[:, 0].max() - x0) * ppb)))
            py0 = max(0, int(math.floor((y1 - corners[:, 1].max()) * ppb)))
            py1 = min(H, int(math.ceil((y1 - corners[:, 1].min()) * ppb)))
            if px0 >= px1 or py0 >= py1:
                continue
            xs = x0 + (np.arange(px0, px1) + 0.5) / ppb
            ys = y1 - (np.arange(py0, py1) + 0.5) / ppb
            gx, gy = np.meshgrid(xs, ys)
            rx, ry = gx - p0[0], gy - p0[1]
            u = (a2[1, 1] * rx - a2[0, 1] * ry) / det
            v = (-a2[1, 0] * rx + a2[0, 0] * ry) / det
            inside = (u >= 0) & (u < 1) & (v >= 0) & (v < 1)
            if not inside.any():
                continue
            th, tw = tex.shape[:2]
            texel = tex[np.clip((v * th).astype(int), 0, th - 1), np.clip((u * tw).astype(int), 0, tw - 1)]
            d = (o @ fwd) + u * (eu @ fwd) + v * (ev @ fwd)
            sub = zbuf[py0:py1, px0:px1]
            hit = inside & (texel[..., 3] > 127) & (d < sub - 1e-6)
            sub[hit] = d[hit]
            img[py0:py1, px0:px1][hit] = texel[..., :3][hit] * sh


def bxyz_face(d, f):
    """Depth of the face of a block towards the camera: d is the block's coordinate along the view
    times the view's sign; the face is half a block nearer than the block's middle."""
    return d + (0.0 if f > 0 else -1.0)
