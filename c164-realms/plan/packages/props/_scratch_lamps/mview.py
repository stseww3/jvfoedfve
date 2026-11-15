"""A look at single prop models without the game or the renderer: flat orthographic pictures of a
model's boxes with their painted faces, shaded as the game shades a display entity. For proofing
shapes and hand-drawn faces while the worker node is away; it is not a picture of the scene and
judges nothing about light. A model of a few hundred boxes takes well under a second.

    from mview import view, sheet
    img = view(model, yaw=0, az=25, el=12, ppu=10)       # az: camera swung to the viewer's right, el: raised
    sheet([(label, img), ...], "/tmp/c164_lamps/x.png")
"""
import math

import numpy as np
from PIL import Image, ImageDraw

from artkit import models as M

L0 = np.array([0.2, 1.0, -0.7]) / math.sqrt(0.2 ** 2 + 1.0 + 0.7 ** 2)
L1 = np.array([-0.2, 1.0, 0.7]) / math.sqrt(0.2 ** 2 + 1.0 + 0.7 ** 2)
BG = (58, 62, 74)

# face letter -> (corner of the picture's upper left, the way u runs, the way v runs), each as signs
# of (x, y, z) picking lo (-1) or hi (+1) of the box, and unit steps along the model's axes
FACES = {
    "s": ((-1, 1, 1), (1, 0, 0), (0, -1, 0)),
    "n": ((1, 1, -1), (-1, 0, 0), (0, -1, 0)),
    "e": ((1, 1, 1), (0, 0, -1), (0, -1, 0)),
    "w": ((-1, 1, -1), (0, 0, 1), (0, -1, 0)),
    "u": ((-1, 1, -1), (1, 0, 0), (0, 0, 1)),
    "d": ((-1, -1, 1), (1, 0, 0), (0, 0, -1)),
}


def _rot(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def _yaw(deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return np.array([[c, 0.0, -s], [0.0, 1.0, 0.0], [s, 0.0, c]])       # props/_kit.turn


def quads(model, yaw=0.0, scale=1.0):
    """Every face of the model as (corner, edge u, edge v, picture, shade), in world units of a
    sixteenth of a block, the model's anchor at the origin and turned by yaw as _kit.put turns it."""
    world = _yaw(yaw) * scale
    out = []
    faces = {}
    for pi, f, mat, w, h, grain, seed in model.faces():
        faces[pi, f] = (mat, w, h, grain, seed)
    for pi, p in enumerate(model.parts):
        lo, hi = np.array(p["lo"]), np.array(p["hi"])
        c, half = (lo + hi) / 2.0, (hi - lo) / 2.0
        r = _rot(p["rot"][0]) if p["rot"] else np.eye(3)
        for f, (corner, du, dv) in FACES.items():
            if (pi, f) not in faces:
                continue
            mat, w, h, grain, seed = faces[pi, f]
            tex = mat.paint(w, h, grain, seed)
            du, dv = np.array(du, float), np.array(dv, float)
            o = c + r @ (np.array(corner) * half)
            eu = r @ (du * 2.0 * half[int(np.argmax(np.abs(du)))])
            ev = r @ (dv * 2.0 * half[int(np.argmax(np.abs(dv)))])
            n = r @ np.array(M.NORMAL[f])
            nw = _yaw(yaw) @ n
            if p["emit"] or not p["shade"]:
                shade = 1.0
            else:
                shade = min(1.0, 0.4 + 0.6 * (max(0.0, float(nw @ L0)) + max(0.0, float(nw @ L1))))
            anchor = np.array(model.anchor)
            out.append((world @ (o - anchor), world @ eu, world @ ev, tex, shade))
    return out


def view(model, yaw=0.0, az=0.0, el=0.0, ppu=8, scale=1.0, pad=1.0, bg=BG, box=None, extra=()):
    """One orthographic picture. The camera looks at the model from the side its +z points to
    (after yaw), swung az degrees to the viewer's right and raised el degrees. ppu: pixels to a
    sixteenth of a block. box: (x0, y0, x1, y1) in screen units to cut the picture to, else the
    model's own extent plus pad. extra: more (model, yaw, scale, offset) to draw with it."""
    a, e = math.radians(az), math.radians(el)
    # the camera's place on a sphere about the model: straight in front of +z at az = el = 0
    cam = np.array([math.sin(a) * math.cos(e), math.sin(e), math.cos(a) * math.cos(e)])
    fwd = -cam
    right = np.cross(fwd, np.array([0.0, 1.0, 0.0]))
    right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    qs = quads(model, yaw, scale)
    for m2, yaw2, scale2, off in extra:
        off = np.array(off, float)
        qs += [(o + off, eu, ev, tex, sh) for o, eu, ev, tex, sh in quads(m2, yaw2, scale2)]
    pts = np.array([o + i * eu + j * ev for o, eu, ev, _, _ in qs for i in (0, 1) for j in (0, 1)])
    sx, sy = pts @ right, pts @ up
    if box is None:
        x0, x1, y0, y1 = sx.min() - pad, sx.max() + pad, sy.min() - pad, sy.max() + pad
    else:
        x0, y0, x1, y1 = box
    W, H = int(math.ceil((x1 - x0) * ppu)), int(math.ceil((y1 - y0) * ppu))
    img = np.empty((H, W, 3), dtype=np.float64)
    img[:] = bg
    depth = np.full((H, W), 1e18)
    for o, eu, ev, tex, shade in qs:
        p0 = np.array([o @ right, o @ up])
        a2 = np.array([[eu @ right, ev @ right], [eu @ up, ev @ up]])
        det = a2[0, 0] * a2[1, 1] - a2[0, 1] * a2[1, 0]
        if abs(det) < 1e-9:
            continue
        nrm = np.cross(eu, ev)
        corners = np.array([p0, p0 + a2[:, 0], p0 + a2[:, 1], p0 + a2[:, 0] + a2[:, 1]])
        px0 = max(0, int(math.floor((corners[:, 0].min() - x0) * ppu)))
        px1 = min(W, int(math.ceil((corners[:, 0].max() - x0) * ppu)))
        py0 = max(0, int(math.floor((y1 - corners[:, 1].max()) * ppu)))
        py1 = min(H, int(math.ceil((y1 - corners[:, 1].min()) * ppu)))
        if px0 >= px1 or py0 >= py1:
            continue
        xs = x0 + (np.arange(px0, px1) + 0.5) / ppu
        ys = y1 - (np.arange(py0, py1) + 0.5) / ppu
        gx, gy = np.meshgrid(xs, ys)
        rx, ry = gx - p0[0], gy - p0[1]
        s = (a2[1, 1] * rx - a2[0, 1] * ry) / det
        t = (-a2[1, 0] * rx + a2[0, 0] * ry) / det
        inside = (s >= 0) & (s < 1) & (t >= 0) & (t < 1)
        if not inside.any():
            continue
        th, tw = tex.shape[:2]
        ti = np.clip((s * tw).astype(int), 0, tw - 1)
        tj = np.clip((t * th).astype(int), 0, th - 1)
        texel = tex[tj, ti]
        d = (o @ fwd) + s * (eu @ fwd) + t * (ev @ fwd)
        sub = depth[py0:py1, px0:px1]
        hit = inside & (texel[..., 3] > 127) & (d < sub - 1e-6)
        sub[hit] = d[hit]
        img[py0:py1, px0:px1][hit] = texel[..., :3][hit] * shade
    return Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), "RGB")


def sheet(tiles, path, cols=4, gap=8, label=True, bg=(30, 32, 40)):
    """Lay pictures out on one sheet, each under its label."""
    tiles = list(tiles)
    lab = 14 if label else 0
    rows = [tiles[i:i + cols] for i in range(0, len(tiles), cols)]
    widths = [max(im.size[0] for _, im in col) for col in zip(*[r + [(None, Image.new("RGB", (1, 1)))] * (cols - len(r))
                                                                 for r in rows])]
    heights = [max(im.size[1] for _, im in r) + lab for r in rows]
    out = Image.new("RGB", (sum(widths) + gap * (cols + 1), sum(heights) + gap * (len(rows) + 1)), bg)
    draw = ImageDraw.Draw(out)
    y = gap
    for r, hgt in zip(rows, heights):
        x = gap
        for (name, im), wd in zip(r, widths):
            if label and name:
                draw.text((x, y), name, fill=(220, 220, 220))
            out.paste(im, (x, y + lab))
            x += wd + gap
        y += hgt + gap
    out.save(path)
    return out.size
