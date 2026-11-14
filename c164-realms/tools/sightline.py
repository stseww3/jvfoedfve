"""What stands in a line of sight, worked out from the blocks and the display entities.

No picture is drawn. Rays from one eye are stepped through the cells of the scene and tested
against the boxes of the block models and of the display entities, read from the game's own files
(the jar) and from the scene's resource pack. A box whose pictures are mostly opaque hides what is
behind it; glass, bars and the like are seen through and are named apart.

tools/check.py uses this for its check "sight". Scene coordinates throughout: a cell k fills the
span k .. k + 1.
"""
import math

import numpy as np

from artkit import blockfacts as F
from artkit.gameassets import rot
from artkit.shapes import Shaper, full

OPAQUE_SHARE = 0.5      # a box hides what is behind it when this share of its pictures is opaque
OPAQUE_ALPHA = 230      # a pixel is opaque from this alpha on
THIN = 1.0 / 16.0       # a turned box thinner than this is a plant's or a chain's plane: left out
TINY = 1e-12

EMPTY, CUBE, GLASS, PARTS = 0, 1, 2, 3      # a state, to a ray: nothing; a whole cube that hides;
#                                             a whole cube seen through; boxes inside the cell
BARE, VEIL, HIDES = 0, 1, 2                 # a face of a box, to a ray that enters through it: it has no
#                                             picture and is not drawn; it is seen through; it hides
# A box's six faces are numbered axis * 2 + side: x low, x high, y low, y high, z low, z high. The
# game's order is down, up, north, south, west, east.
OWN_FACE = (2, 3, 4, 5, 0, 1)
NORMALS = np.array([(0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)], dtype=float)


def _quat(q):
    x, y, z, w = (float(v) for v in q)
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def _corners(lo, hi):
    return np.array([[(lo, hi)[i][0], (lo, hi)[j][1], (lo, hi)[k][2]]
                     for i in (0, 1) for j in (0, 1) for k in (0, 1)], dtype=float)


class Shapes:
    """The boxes of block states and of item models, and whether each hides what is behind it."""

    def __init__(self, assets):
        self.assets = assets
        self._share, self._state, self._item = {}, {}, {}

    def _opaque_share(self, ref, uv):
        """The share of opaque pixels in the part of a picture a face shows (uv in sixteenths)."""
        key = (ref, tuple(float(v) for v in uv))
        hit = self._share.get(key)
        if hit is None:
            alpha = self.assets.texture(ref)[..., 3]
            h, w = alpha.shape
            u0, u1 = sorted((key[1][0], key[1][2]))
            v0, v1 = sorted((key[1][1], key[1][3]))
            c0 = min(max(int(math.floor(u0 / 16.0 * w + 1e-6)), 0), w - 1)
            r0 = min(max(int(math.floor(v0 / 16.0 * h + 1e-6)), 0), h - 1)
            c1 = min(max(int(math.ceil(u1 / 16.0 * w - 1e-6)), c0 + 1), w)
            r1 = min(max(int(math.ceil(v1 / 16.0 * h - 1e-6)), r0 + 1), h)
            hit = self._share[key] = float((alpha[r0:r1, c0:c1] >= OPAQUE_ALPHA).mean())
        return hit

    def _faces(self, el):
        """Per face of an element, in the game's order: BARE, VEIL or HIDES."""
        size = el.hi - el.lo
        areas = (size[0] * size[2],) * 2 + (size[0] * size[1],) * 2 + (size[2] * size[1],) * 2
        out = []
        for f in range(6):
            if el.tex[f] is None or areas[f] <= 0.0:
                out.append(BARE)
            else:
                out.append(HIDES if self._opaque_share(el.tex[f], el.uv[f]) >= OPAQUE_SHARE else VEIL)
        return out

    def state(self, text):
        """(kind, [(lo, hi, faces)]) of a block state. The boxes lie in the cell's own frame; faces
        holds BARE, VEIL or HIDES for the six faces of the box as it stands in the cell."""
        hit = self._state.get(text)
        if hit is None:
            name, props = full(text)
            boxes = []
            if name not in F.INVISIBLE and name != "water":
                for choices in self.assets.parts(name, props):
                    # the variants of a state differ in their picture or their turn, not in their bulk
                    _, model, x, y, uvlock = choices[0]
                    for el in self.assets.elements(model, x, y, uvlock)[0]:
                        if not el.aligned and float((el.hi - el.lo).min()) < THIN:
                            continue
                        back = np.linalg.inv(el.inv)
                        placed = (_corners(el.lo, el.hi) - el.off) @ back.T
                        faces = [BARE] * 6
                        for f, kind in enumerate(self._faces(el)):
                            n = back @ NORMALS[f]
                            axis = int(np.abs(n).argmax())
                            k = axis * 2 + int(n[axis] > 0)
                            faces[k] = max(faces[k], kind)
                        if not el.aligned:
                            faces = [max(faces)] * 6
                        boxes.append((placed.min(axis=0), placed.max(axis=0), faces))
            whole = [b for b in boxes if b[0].max() <= 1e-6 and b[1].min() >= 1.0 - 1e-6]
            if any(min(b[2]) == HIDES for b in whole):
                kind = CUBE
            elif not boxes:
                kind = EMPTY
            elif len(whole) == len(boxes) and all(set(b[2]) == {VEIL} for b in boxes):
                kind = GLASS
            else:
                kind = PARTS
            hit = self._state[text] = (kind, boxes)
        return hit

    def is_cube(self, text):
        """Does the block fill its cell (so that walls, fences and panes join it)?"""
        return any(b[0].max() <= 1e-6 and b[1].min() >= 1.0 - 1e-6 for b in self.state(text)[1])

    def item(self, ref):
        """[(inv, off, lo, hi, faces)] of an item model: inv and off take a point of the item's unit
        cube into the box's own frame, where it lies between lo and hi. None if there is no model."""
        if ref not in self._item:
            model = self.assets.item_model(ref)
            self._item[ref] = None if model is None else [
                (el.inv, el.off, el.lo, el.hi, [k for _, k in sorted(zip(OWN_FACE, self._faces(el)))])
                for el in self.assets.elements(model)[0]]
        return self._item[ref]


def _turn_of(nbt):
    yaw, pitch = (float(v) for v in nbt.get("Rotation", (0.0, 0.0)))
    return rot("y", -yaw) @ rot("x", pitch)


def _shown_matrix(nbt, turn):
    tr = nbt.get("transformation") or {}
    return (turn @ _quat(tr.get("left_rotation", (0, 0, 0, 1)))
            @ np.diag([float(v) for v in tr.get("scale", (1, 1, 1))])
            @ _quat(tr.get("right_rotation", (0, 0, 0, 1))))


def entity_boxes(shapes, x, y, z, nbt):
    """The boxes of one display entity in scene coordinates: [(inv, off, lo, hi, faces, label)].
    An item display shows its model about the entity's position, a block display shows the block
    from the position on (DisplayRenderer); a text display is a sheet of letters and is left out."""
    kind = nbt.get("id")
    turn = _turn_of(nbt)
    at = np.array([x, y, z], dtype=float) + turn @ np.array(
        [float(v) for v in (nbt.get("transformation") or {}).get("translation", (0, 0, 0))])
    g = _shown_matrix(nbt, turn)
    if kind == "minecraft:item_display":
        ref = ((nbt.get("item") or {}).get("components") or {}).get("minecraft:item_model")
        parts = shapes.item(ref) if ref else None
        if not parts:
            return []
        g = g @ rot("y", 180.0)
        centre, label = 0.5, f"model {ref}"
    elif kind == "minecraft:block_display":
        bs = nbt.get("block_state") or {}
        name = str(bs.get("Name", "")).split(":", 1)[-1]
        props = bs.get("Properties") or {}
        text = name + ("[" + ",".join(f"{k}={props[k]}" for k in sorted(props)) + "]" if props else "")
        try:
            boxes = shapes.state(text)[1]
        except (KeyError, ValueError):
            return []
        parts = [(np.eye(3), np.zeros(3), lo, hi, faces) for lo, hi, faces in boxes]
        centre, label = 0.0, f"block display {name}"
    else:
        return []
    if abs(np.linalg.det(g)) < TINY:
        return []
    gi = np.linalg.inv(g)
    out = []
    for inv0, off0, lo, hi, faces in parts:
        inv = inv0 @ gi
        off = inv0 @ (centre - gi @ at) + off0
        out.append((inv, off, np.asarray(lo, dtype=float), np.asarray(hi, dtype=float),
                    np.array(faces, dtype=np.int8), label))
    return out


class Blockers:
    """The blocks and display entities inside a box of cells, laid out for rays from one eye."""

    def __init__(self, cells, entities, shapes, lo, hi):
        """cells {(x, y, z): state}; entities [(x, y, z, nbt)]; lo, hi: the corner cells of the box
        the rays stay in, both included. What the game works out from a block's neighbours (how
        walls, fences and panes join, where stairs turn) is filled in first, on a copy."""
        self.lo = np.array([int(v) for v in lo], dtype=np.int64)
        self.shape = np.array([int(b) - int(a) + 1 for a, b in zip(lo, hi)], dtype=np.int64)
        x0, y0, z0 = (int(v) - 1 for v in lo)
        x1, y1, z1 = (int(v) + 1 for v in hi)
        near = {p: s for p, s in cells.items()
                if x0 <= p[0] <= x1 and y0 <= p[1] <= y1 and z0 <= p[2] <= z1}
        Shaper(near, shapes.is_cube).run()
        self.labels, ids, kinds = ["air"], {}, [EMPTY]
        self.parts = {}
        self.grid = np.zeros(tuple(self.shape), dtype=np.int32)
        for (x, y, z), state in near.items():
            if not (x0 < x < x1 and y0 < y < y1 and z0 < z < z1):
                continue
            sid = ids.get(state)
            if sid is None:
                kind, boxes = shapes.state(state)
                sid = ids[state] = len(kinds)
                kinds.append(kind)
                self.labels.append(state.partition("[")[0])
                if kind == PARTS:
                    self.parts[sid] = (np.array([b[0] for b in boxes]), np.array([b[1] for b in boxes]),
                                       np.array([b[2] for b in boxes], dtype=np.int8))
            self.grid[x - x0 - 1, y - y0 - 1, z - z0 - 1] = sid
        self.kind = np.array(kinds, dtype=np.int8)
        self.boxes = []
        box_lo, box_hi = self.lo.astype(float), (self.lo + self.shape).astype(float)
        for x, y, z, nbt in entities:
            for inv, off, blo, bhi, faces, label in entity_boxes(shapes, x, y, z, nbt):
                world = (_corners(blo, bhi) - off) @ np.linalg.inv(inv).T
                wlo, whi = world.min(axis=0), world.max(axis=0)
                if np.any(whi < box_lo) or np.any(wlo > box_hi) or not faces.any():
                    continue
                if label not in ids:
                    ids[label] = len(self.labels)
                    self.labels.append(label)
                self.boxes.append(dict(inv=inv, off=off, lo=blo, hi=bhi, faces=faces, what=ids[label],
                                       centre=(wlo + whi) / 2.0, radius=float(np.linalg.norm(whi - wlo)) / 2.0,
                                       bottom=float(wlo[1]),
                                       cell=np.floor(np.array([x, y, z], dtype=float)).astype(np.int64)))

    def cast(self, eye, dirs, reach):
        """Follow the rays eye + t * dirs[i] for 0 <= t <= reach[i]; dirs are unit vectors.

        Returns a dict of arrays, one entry per ray: t, the distance to the first thing that hides
        what is behind it (inf where the ray gets through); what, its number in self.labels (-1);
        cell, the cell it stands in (for a display entity, the cell of its position); box, its
        number in self.boxes if it is a display entity (-1 for a block); and thru_t, thru,
        thru_cell, thru_box for the first thing the ray is seen through before that (glass, bars).
        A box counts by the face the ray enters it through: a face without a picture is not drawn,
        and the ray goes on."""
        eye = np.asarray(eye, dtype=float)
        dirs = np.asarray(dirs, dtype=float).reshape(-1, 3)
        n = len(dirs)
        reach = np.broadcast_to(np.asarray(reach, dtype=float), (n,)).copy()
        d = np.where(np.abs(dirs) < TINY, TINY, dirs)
        inv = 1.0 / d
        out = dict(t=np.full(n, np.inf), what=np.full(n, -1, dtype=np.int64), cell=np.zeros((n, 3), dtype=np.int64),
                   box=np.full(n, -1, dtype=np.int64),
                   thru_t=np.full(n, np.inf), thru=np.full(n, -1, dtype=np.int64),
                   thru_cell=np.zeros((n, 3), dtype=np.int64), thru_box=np.full(n, -1, dtype=np.int64))
        glo, ghi = self.lo.astype(float), (self.lo + self.shape).astype(float)
        ta, tb = (glo - eye) * inv, (ghi - eye) * inv
        t0 = np.maximum(np.minimum(ta, tb).max(axis=1), 0.0)
        t1 = np.minimum(np.maximum(ta, tb).min(axis=1), reach)

        live = np.nonzero(t0 < t1)[0]
        tcur = t0[live] + 1e-7
        cell = np.floor(eye + d[live] * tcur[:, None]).astype(np.int64)
        cell = np.minimum(np.maximum(cell, self.lo), self.lo + self.shape - 1)
        step = np.where(d[live] > 0, 1, -1).astype(np.int64)
        tnext = (cell + (step > 0) - eye) * inv[live]
        tdelta = np.abs(inv[live])
        while len(live):
            rel = cell - self.lo
            sid = self.grid[rel[:, 0], rel[:, 1], rel[:, 2]]
            kinds = self.kind[sid]
            done = np.zeros(len(live), dtype=bool)

            m = kinds == CUBE
            if m.any():
                out["t"][live[m]], out["what"][live[m]], out["cell"][live[m]] = tcur[m], sid[m], cell[m]
                done |= m
            m = (kinds == GLASS) & (out["thru"][live] < 0)
            if m.any():
                out["thru_t"][live[m]], out["thru"][live[m]], out["thru_cell"][live[m]] = tcur[m], sid[m], cell[m]
            m = kinds == PARTS
            for s in np.unique(sid[m]) if m.any() else ():
                k = np.nonzero(sid == s)[0]
                blo, bhi, faces = self.parts[int(s)]
                base = cell[k][:, None, :] - eye
                a = (base + blo[None]) * inv[live[k]][:, None, :]
                b = (base + bhi[None]) * inv[live[k]][:, None, :]
                first = np.minimum(a, b)
                tn, tf = first.max(axis=2), np.maximum(a, b).min(axis=2)
                axis = first.argmax(axis=2)
                high = np.take_along_axis(np.broadcast_to(d[live[k]][:, None, :] < 0, first.shape),
                                          axis[..., None], axis=2)[..., 0]
                entered = faces[np.arange(len(blo))[None, :], axis * 2 + high]
                ok = (tn <= tf) & (tn >= 0.0) & (tn <= t1[live[k]][:, None])
                hid = np.where(ok & (entered == HIDES), tn, np.inf).min(axis=1)
                seen = np.where(ok & (entered == VEIL), tn, np.inf).min(axis=1)
                m2 = np.isfinite(seen) & (seen < hid) & (out["thru"][live[k]] < 0)
                if m2.any():
                    r = live[k[m2]]
                    out["thru_t"][r], out["thru"][r], out["thru_cell"][r] = seen[m2], s, cell[k[m2]]
                m2 = np.isfinite(hid)
                if m2.any():
                    r = live[k[m2]]
                    out["t"][r], out["what"][r], out["cell"][r] = hid[m2], s, cell[k[m2]]
                    done[k[m2]] = True

            rows = np.arange(len(live))
            axis = tnext.argmin(axis=1)
            tcur = tnext[rows, axis]
            cell[rows, axis] += step[rows, axis]
            tnext[rows, axis] += tdelta[rows, axis]
            keep = ~done & (tcur < t1[live]) & np.all((cell >= self.lo) & (cell < self.lo + self.shape), axis=1)
            live, tcur, cell, step, tnext, tdelta = (v[keep] for v in (live, tcur, cell, step, tnext, tdelta))

        for number, box in enumerate(self.boxes):
            v = box["centre"] - eye
            dist = float(np.linalg.norm(v))
            if dist > box["radius"]:
                # only the rays that pass within the box's reach are tested
                cone = math.sqrt(1.0 - (box["radius"] / dist) ** 2)
                near = np.nonzero(dirs @ (v / dist) >= cone - 1e-9)[0]
            else:
                near = np.arange(n)
            if not len(near):
                continue
            o2 = box["inv"] @ eye + box["off"]
            d2 = d[near] @ box["inv"].T
            d2 = np.where(np.abs(d2) < TINY, TINY, d2)
            a, b = (box["lo"] - o2) / d2, (box["hi"] - o2) / d2
            first = np.minimum(a, b)
            tn, tf = first.max(axis=1), np.maximum(a, b).min(axis=1)
            axis = first.argmax(axis=1)
            entered = box["faces"][axis * 2 + (d2[np.arange(len(near)), axis] < 0)]
            ok = (tn <= tf) & (tn >= 0.0) & (tn <= reach[near])
            for want, t_key, w_key, c_key, b_key in ((HIDES, "t", "what", "cell", "box"),
                                                     (VEIL, "thru_t", "thru", "thru_cell", "thru_box")):
                m = ok & (entered == want) & (tn < out[t_key][near])
                if m.any():
                    r = near[m]
                    out[t_key][r], out[w_key][r], out[c_key][r], out[b_key][r] = tn[m], box["what"], box["cell"], number

        late = out["thru_t"] >= out["t"]
        out["thru_t"][late], out["thru"][late], out["thru_box"][late] = np.inf, -1, -1
        return out


# ---- cameras -------------------------------------------------------------------------------------
def frame(pos, look_at):
    """A camera at pos looking at look_at: eye, forward, right, up (as render.py and the game)."""
    pos = np.array(pos, dtype=float)
    f = np.array(look_at, dtype=float) - pos
    f = f / np.linalg.norm(f)
    r = np.cross(f, (0.0, 1.0, 0.0))
    if float(np.linalg.norm(r)) < 1e-6:
        r = np.array([-1.0, 0.0, 0.0])
    r = r / np.linalg.norm(r)
    return pos, f, r, np.cross(r, f)


def picture_rays(cam, fov, aspect, width, height):
    """Unit vectors through the middles of the pixels of a width x height picture: (height, width, 3),
    row 0 at the top. fov is the vertical field of view in degrees."""
    _, f, r, u = cam
    ty = math.tan(math.radians(fov) / 2.0)
    xs = ((np.arange(width) + 0.5) / width * 2.0 - 1.0) * ty * aspect
    ys = (1.0 - (np.arange(height) + 0.5) / height * 2.0) * ty
    d = f[None, None, :] + xs[None, :, None] * r[None, None, :] + ys[:, None, None] * u[None, None, :]
    return d / np.linalg.norm(d, axis=2, keepdims=True)


def in_picture(cam, fov, aspect, direction):
    """Where a direction falls in the picture: (across, down), each 0 .. 1 from the left and from the
    top edge inside the picture. None for a direction behind the camera."""
    _, f, r, u = cam
    direction = np.asarray(direction, dtype=float)
    depth = float(direction @ f)
    if depth <= 1e-9:
        return None
    ty = math.tan(math.radians(fov) / 2.0)
    return (0.5 + float(direction @ r) / depth / (2.0 * ty * aspect),
            0.5 - float(direction @ u) / depth / (2.0 * ty))
