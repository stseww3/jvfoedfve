"""Drawing a scene by following rays through it, with the game's own arithmetic for light.

The scene is a grid of palette numbers; a palette entry is a list of boxes (the block's model as
gameassets places it). Display entities are boxes too, kept in a coarse grid of their own. A ray
walks the grid cell by cell and stops at the first face whose texture is not transparent there.
What is done with that face follows the game:

  blocks  texture x tint x face shade x corner shade x light colour  (ModelBlockRenderer and
          BlockModelLighter: each corner of a face averages the shade and the light of the cells
          around it, and the face blends its corners; models without that take one light value)
  items   texture x two fixed lamps on the face's nearest axis direction x light colour
          (item.vsh, light.glsl; an item takes one light value, from where its entity stands)
  air     fog by distance, the sky fading into the fog colour towards the horizon (fog.glsl,
          sky.fsh)

All of it is compiled with numba; the first run compiles for a minute or two and caches the result.
Face and direction numbers are the game's: down, up, north, south, west, east.
"""
import math
from collections import namedtuple

import numpy as np
from numba import njit, prange

FIELDS = (
    ("grid", np.uint16), ("sky", np.uint8), ("blk", np.uint8), ("origin", np.int64),
    ("pal_start", np.int32), ("pal_n", np.int32), ("pal_flags", np.int32), ("pal_emit", np.int32), ("pal_class", np.int32),
    ("el_inv", np.float64), ("el_off", np.float64), ("el_lo", np.float64), ("el_hi", np.float64),
    ("el_tex", np.int32), ("el_uv", np.float64), ("el_uvrot", np.int32), ("el_tint", np.int32), ("el_shade", np.float64),
    ("el_dir", np.int32), ("el_cull", np.int32), ("el_cubic", np.int32), ("el_flags", np.int32), ("el_emit", np.int32),
    ("tints", np.float64), ("tex_px", np.uint8), ("tex_off", np.int64), ("tex_w", np.int32), ("tex_h", np.int32),
    ("tex_kind", np.int32),
    ("eb_inv", np.float64), ("eb_off", np.float64), ("eb_lo", np.float64), ("eb_hi", np.float64), ("eb_tex", np.int32),
    ("eb_uv", np.float64), ("eb_shade", np.float64), ("eb_light", np.float64),
    ("cg_start", np.int32), ("cg_n", np.int32), ("cg_list", np.int32),
    ("lightmap", np.float64), ("env", np.float64), ("bodies", np.float64), ("body_px", np.uint8),
    ("stars", np.uint8), ("star_rot", np.float64),
)
World = namedtuple("World", [name for name, _ in FIELDS])


def world(**arrays):
    """A World with every array in the type the compiled code was built for."""
    return World(*(np.ascontiguousarray(arrays[name], dtype=kind) for name, kind in FIELDS))


# palette flags
SHADE, AO, OPAQUE, WET, OFF_XZ, OFF_XYZ = 1, 2, 4, 8, 16, 32
# element flags
ALIGNED, WORLD_UV, WATER = 1, 2, 4
COARSE = 4                      # cells of the entity grid are this many blocks wide
BIG = 1e30
# places in World.env
FOG, SKY, FOG_START, FOG_END, FAR_START, FAR_END, SKY_END, STARS, PIXEL = 0, 3, 6, 7, 8, 9, 10, 11, 12
ENV_SIZE = 13
BODY_SIZE = 13                  # direction (3), across (3), along (3), half size, texture start, size, strength

DIRV = np.array([(0, -1, 0), (0, 1, 0), (0, 0, -1), (0, 0, 1), (-1, 0, 0), (1, 0, 0)], dtype=np.int64)
# BlockModelLighter.AdjacencyInfo: the four cells beside a face, as direction numbers
CORNERS = np.array([(4, 5, 2, 3), (5, 4, 2, 3), (1, 0, 5, 4), (4, 5, 0, 1), (1, 0, 2, 3), (0, 1, 2, 3)], dtype=np.int64)


@njit(cache=True)
def box_hit(inv, off, lo, hi, px, py, pz, dx, dy, dz, tmin, back):
    """Where a ray meets a placed box after tmin: (t, face, x, y, z in the box's frame); face -1
    for a miss. Only the way in counts, as the game only draws the outside of a face; with `back`
    the way out counts too (faces drawn on both sides)."""
    ox = inv[0, 0] * px + inv[0, 1] * py + inv[0, 2] * pz + off[0]
    oy = inv[1, 0] * px + inv[1, 1] * py + inv[1, 2] * pz + off[1]
    oz = inv[2, 0] * px + inv[2, 1] * py + inv[2, 2] * pz + off[2]
    ex = inv[0, 0] * dx + inv[0, 1] * dy + inv[0, 2] * dz
    ey = inv[1, 0] * dx + inv[1, 1] * dy + inv[1, 2] * dz
    ez = inv[2, 0] * dx + inv[2, 1] * dy + inv[2, 2] * dz
    tn, tf, axis, far = -BIG, BIG, -1, -1
    if abs(ex) < 1e-12:
        if ox < lo[0] - 1e-9 or ox > hi[0] + 1e-9:
            return BIG, -1, 0.0, 0.0, 0.0
    else:
        a, b = (lo[0] - ox) / ex, (hi[0] - ox) / ex
        if a > b:
            a, b = b, a
        if a > tn:
            tn, axis = a, 0
        if b < tf:
            tf, far = b, 0
    if abs(ey) < 1e-12:
        if oy < lo[1] - 1e-9 or oy > hi[1] + 1e-9:
            return BIG, -1, 0.0, 0.0, 0.0
    else:
        a, b = (lo[1] - oy) / ey, (hi[1] - oy) / ey
        if a > b:
            a, b = b, a
        if a > tn:
            tn, axis = a, 1
        if b < tf:
            tf, far = b, 1
    if abs(ez) < 1e-12:
        if oz < lo[2] - 1e-9 or oz > hi[2] + 1e-9:
            return BIG, -1, 0.0, 0.0, 0.0
    else:
        a, b = (lo[2] - oz) / ez, (hi[2] - oz) / ez
        if a > b:
            a, b = b, a
        if a > tn:
            tn, axis = a, 2
        if b < tf:
            tf, far = b, 2
    if axis < 0 or tn > tf + 1e-7:
        return BIG, -1, 0.0, 0.0, 0.0
    if tn > tmin:
        if axis == 0:
            face = 4 if ex > 0.0 else 5
        elif axis == 1:
            face = 0 if ey > 0.0 else 1
        else:
            face = 2 if ez > 0.0 else 3
        return tn, face, ox + ex * tn, oy + ey * tn, oz + ez * tn
    if back and tf > tmin and far >= 0:
        if far == 0:
            face = 5 if ex > 0.0 else 4
        elif far == 1:
            face = 1 if ey > 0.0 else 0
        else:
            face = 3 if ez > 0.0 else 2
        return tf, face, ox + ex * tf, oy + ey * tf, oz + ez * tf
    return BIG, -1, 0.0, 0.0, 0.0


@njit(cache=True)
def face_uv(f, lo, hi, uv, rot, lx, ly, lz):
    """Texture position (0..1) of a point on face f of a box, as FaceBakery lays pictures out."""
    wx = max(hi[0] - lo[0], 1e-9)
    wy = max(hi[1] - lo[1], 1e-9)
    wz = max(hi[2] - lo[2], 1e-9)
    if f == 0:
        s, r = (lx - lo[0]) / wx, (hi[2] - lz) / wz
    elif f == 1:
        s, r = (lx - lo[0]) / wx, (lz - lo[2]) / wz
    elif f == 2:
        s, r = (hi[0] - lx) / wx, (hi[1] - ly) / wy
    elif f == 3:
        s, r = (lx - lo[0]) / wx, (hi[1] - ly) / wy
    elif f == 4:
        s, r = (lz - lo[2]) / wz, (hi[1] - ly) / wy
    else:
        s, r = (hi[2] - lz) / wz, (hi[1] - ly) / wy
    if rot == 1:
        s, r = r, 1.0 - s
    elif rot == 2:
        s, r = 1.0 - s, 1.0 - r
    elif rot == 3:
        s, r = 1.0 - r, s
    return uv[0] + s * (uv[2] - uv[0]), uv[1] + r * (uv[3] - uv[1])


@njit(cache=True)
def world_uv(d, x, y, z):
    """The same for a picture that keeps its attitude (uvlock): from where the point is in its cell."""
    if d == 0:
        return x, 1.0 - z
    if d == 1:
        return x, z
    if d == 2:
        return 1.0 - x, 1.0 - y
    if d == 3:
        return x, 1.0 - y
    if d == 4:
        return z, 1.0 - y
    return 1.0 - z, 1.0 - y


@njit(cache=True)
def texel(w, tid, u, v, lod):
    """Colour and opacity of a texture at (u, v): colour from the mip level, opacity from the full
    picture, so that leaves keep their holes at any distance."""
    tw, th = w.tex_w[tid], w.tex_h[tid]
    x, y = int(u * tw), int(v * th)
    x = 0 if x < 0 else (tw - 1 if x >= tw else x)
    y = 0 if y < 0 else (th - 1 if y >= th else y)
    i = w.tex_off[tid, 0] + y * tw + x
    a = w.tex_px[i, 3] / 255.0
    while lod > 0 and w.tex_off[tid, lod] < 0:
        lod -= 1
    if lod > 0:
        lw, lh = max(1, tw >> lod), max(1, th >> lod)
        x, y = int(u * lw), int(v * lh)
        x = 0 if x < 0 else (lw - 1 if x >= lw else x)
        y = 0 if y < 0 else (lh - 1 if y >= lh else y)
        j = w.tex_off[tid, lod] + y * lw + x
        if w.tex_px[j, 3] > 0:
            i = j
    return w.tex_px[i, 0] / 255.0, w.tex_px[i, 1] / 255.0, w.tex_px[i, 2] / 255.0, a


@njit(cache=True)
def light_colour(lm, sky, blk):
    """The lightmap between whole levels, as the game's linear filter reads it."""
    s0 = int(sky)
    b0 = int(blk)
    s0 = 0 if s0 < 0 else (14 if s0 > 14 else s0)
    b0 = 0 if b0 < 0 else (14 if b0 > 14 else b0)
    fs = min(1.0, max(0.0, sky - s0))
    fb = min(1.0, max(0.0, blk - b0))
    w00, w01, w10, w11 = (1 - fs) * (1 - fb), (1 - fs) * fb, fs * (1 - fb), fs * fb
    r = lm[s0, b0, 0] * w00 + lm[s0, b0 + 1, 0] * w01 + lm[s0 + 1, b0, 0] * w10 + lm[s0 + 1, b0 + 1, 0] * w11
    g = lm[s0, b0, 1] * w00 + lm[s0, b0 + 1, 1] * w01 + lm[s0 + 1, b0, 1] * w10 + lm[s0 + 1, b0 + 1, 1] * w11
    b = lm[s0, b0, 2] * w00 + lm[s0, b0 + 1, 2] * w01 + lm[s0 + 1, b0, 2] * w10 + lm[s0 + 1, b0 + 1, 2] * w11
    return r, g, b


@njit(cache=True)
def stored(w, x, y, z):
    """Sky and block light kept for a cell. Outside the scene there is open sky."""
    nx, ny, nz = w.grid.shape
    if x < 0 or y < 0 or z < 0 or x >= nx or y >= ny or z >= nz:
        return 15.0, 0.0
    return float(w.sky[x, y, z]), float(w.blk[x, y, z])


@njit(cache=True)
def probe(w, x, y, z):
    """A cell as its neighbours see it: shade, sky light, block light (a lamp counts its own), flags."""
    nx, ny, nz = w.grid.shape
    if x < 0 or y < 0 or z < 0 or x >= nx or y >= ny or z >= nz:
        return 1.0, 15.0, 0.0, 0
    p = w.grid[x, y, z]
    flags = w.pal_flags[p]
    return (0.2 if flags & SHADE else 1.0), float(w.sky[x, y, z]), float(max(w.blk[x, y, z], w.pal_emit[p])), flags


@njit(cache=True)
def _blend(s1, b1, s2, b2, s3, b3, sc, bc):
    """LightCoordsUtil.smoothBlend: neighbours inside a block take the light of the middle."""
    if sc > 2.0 or bc > 2.0:
        if s1 == 0.0:
            s1 = sc
            if b1 == 0.0:
                b1 = bc
        if s2 == 0.0:
            s2 = sc
            if b2 == 0.0:
                b2 = bc
        if s3 == 0.0:
            s3 = sc
            if b3 == 0.0:
                b3 = bc
    return (s1 + s2 + s3 + sc) * 0.25, (b1 + b2 + b3 + bc) * 0.25


@njit(cache=True)
def _toward(d, x, y, z):
    v = y if d < 2 else (z if d < 4 else x)
    v = 0.0 if v < 0.0 else (1.0 if v > 1.0 else v)
    return v if d & 1 else 1.0 - v


@njit(cache=True)
def smooth_light(w, cx, cy, cz, d, cubic, hx, hy, hz):
    """BlockModelLighter.prepareQuadAmbientOcclusion for a face of the block in cell c that looks
    in direction d, at the point (hx, hy, hz) of the cell. cubic: the face lies on the cell's
    boundary. Returns sky light, block light and shade there."""
    vx, vy, vz = DIRV[d, 0], DIRV[d, 1], DIRV[d, 2]
    bx, by, bz = cx, cy, cz
    if cubic:
        bx, by, bz = cx + vx, cy + vy, cz + vz
    c0, c1, c2, c3 = CORNERS[d, 0], CORNERS[d, 1], CORNERS[d, 2], CORNERS[d, 3]
    x0, y0, z0 = bx + DIRV[c0, 0], by + DIRV[c0, 1], bz + DIRV[c0, 2]
    x1, y1, z1 = bx + DIRV[c1, 0], by + DIRV[c1, 1], bz + DIRV[c1, 2]
    x2, y2, z2 = DIRV[c2, 0], DIRV[c2, 1], DIRV[c2, 2]
    x3, y3, z3 = DIRV[c3, 0], DIRV[c3, 1], DIRV[c3, 2]
    sh0, sk0, bl0, _ = probe(w, x0, y0, z0)
    sh1, sk1, bl1, _ = probe(w, x1, y1, z1)
    sh2, sk2, bl2, _ = probe(w, bx + x2, by + y2, bz + z2)
    sh3, sk3, bl3, _ = probe(w, bx + x3, by + y3, bz + z3)
    _, _, _, f0 = probe(w, x0 + vx, y0 + vy, z0 + vz)
    _, _, _, f1 = probe(w, x1 + vx, y1 + vy, z1 + vz)
    _, _, _, f2 = probe(w, bx + x2 + vx, by + y2 + vy, bz + z2 + vz)
    _, _, _, f3 = probe(w, bx + x3 + vx, by + y3 + vy, bz + z3 + vz)
    open0, open1, open2, open3 = (f0 & OPAQUE) == 0, (f1 & OPAQUE) == 0, (f2 & OPAQUE) == 0, (f3 & OPAQUE) == 0
    # the cells diagonally beside the face; shut in between two walls they count as the first side
    if open2 or open0:
        sh02, sk02, bl02, _ = probe(w, x0 + x2, y0 + y2, z0 + z2)
    else:
        sh02, sk02, bl02 = sh0, sk0, bl0
    if open3 or open0:
        sh03, sk03, bl03, _ = probe(w, x0 + x3, y0 + y3, z0 + z3)
    else:
        sh03, sk03, bl03 = sh0, sk0, bl0
    if open2 or open1:
        sh12, sk12, bl12, _ = probe(w, x1 + x2, y1 + y2, z1 + z2)
    else:
        sh12, sk12, bl12 = sh0, sk0, bl0
    if open3 or open1:
        sh13, sk13, bl13, _ = probe(w, x1 + x3, y1 + y3, z1 + z3)
    else:
        sh13, sk13, bl13 = sh0, sk0, bl0
    _, skc, blc, _ = probe(w, cx, cy, cz)
    _, skn, bln, fn = probe(w, cx + vx, cy + vy, cz + vz)
    if cubic or (fn & OPAQUE) == 0:
        skc, blc = skn, bln
    shc, _, _, _ = probe(w, bx, by, bz)

    w0 = _toward(c0, hx, hy, hz)
    w2 = _toward(c2, hx, hy, hz)
    w1, w3 = 1.0 - w0, 1.0 - w2
    a03, a02, a12, a13 = w0 * w3, w0 * w2, w1 * w2, w1 * w3
    shade = ((sh3 + sh0 + sh03 + shc) * a03 + (sh2 + sh0 + sh02 + shc) * a02
             + (sh2 + sh1 + sh12 + shc) * a12 + (sh3 + sh1 + sh13 + shc) * a13) * 0.25
    s03, b03 = _blend(sk3, bl3, sk0, bl0, sk03, bl03, skc, blc)
    s02, b02 = _blend(sk2, bl2, sk0, bl0, sk02, bl02, skc, blc)
    s12, b12 = _blend(sk2, bl2, sk1, bl1, sk12, bl12, skc, blc)
    s13, b13 = _blend(sk3, bl3, sk1, bl1, sk13, bl13, skc, blc)
    return (s03 * a03 + s02 * a02 + s12 * a12 + s13 * a13,
            b03 * a03 + b02 * a02 + b12 * a12 + b13 * a13, shade)


@njit(cache=True)
def fogged(env, r, g, b, t, dx, dy, dz):
    """fog.glsl: haze by distance, and the wall of fog where the game stops drawing."""
    f = 0.0
    if t > env[FOG_START]:
        f = 1.0 if t >= env[FOG_END] else (t - env[FOG_START]) / (env[FOG_END] - env[FOG_START])
    c = t * max(math.sqrt(dx * dx + dz * dz), abs(dy))
    if c > env[FAR_START]:
        f2 = 1.0 if c >= env[FAR_END] else (c - env[FAR_START]) / (env[FAR_END] - env[FAR_START])
        if f2 > f:
            f = f2
    return r + (env[FOG] - r) * f, g + (env[FOG + 1] - g) * f, b + (env[FOG + 2] - b) * f


@njit(cache=True)
def sky_colour(w, dx, dy, dz):
    """sky.fsh over the game's sky disc 16 blocks above the eye: sky colour overhead, fog colour
    from a few degrees above the horizon down. Then the stars and the bodies, which only add."""
    env = w.env
    f = 1.0
    if dy > 1e-4:
        reach = 16.0 * math.sqrt(dx * dx + dz * dz) / dy
        if reach < 512.0:
            f = min(1.0, (16.0 + 496.25 * reach / 512.0) / env[SKY_END])
    r = env[SKY] + (env[FOG] - env[SKY]) * f
    g = env[SKY + 1] + (env[FOG + 1] - env[SKY + 1]) * f
    b = env[SKY + 2] + (env[FOG + 2] - env[SKY + 2]) * f
    if env[STARS] > 0.0 and w.stars.shape[1] > 1:
        m = w.star_rot
        sx = m[0, 0] * dx + m[0, 1] * dy + m[0, 2] * dz
        sy = m[1, 0] * dx + m[1, 1] * dy + m[1, 2] * dz
        sz = m[2, 0] * dx + m[2, 1] * dy + m[2, 2] * dz
        n = w.stars.shape[1]
        top = max(abs(sx), abs(sy), abs(sz))
        if top == abs(sx):
            face, u, v = (0 if sx > 0 else 1), sy / top, sz / top
        elif top == abs(sy):
            face, u, v = (2 if sy > 0 else 3), sx / top, sz / top
        else:
            face, u, v = (4 if sz > 0 else 5), sx / top, sy / top
        i = min(n - 1, int((u * 0.5 + 0.5) * n))
        j = min(n - 1, int((v * 0.5 + 0.5) * n))
        s = w.stars[face, i, j] / 255.0 * env[STARS]
        r, g, b = r + s, g + s, b + s
    for k in range(w.bodies.shape[0]):
        bd = w.bodies[k]
        along = dx * bd[0] + dy * bd[1] + dz * bd[2]
        if along <= 0.0 or bd[9] <= 0.0:
            continue
        u = (dx * bd[3] + dy * bd[4] + dz * bd[5]) / along / bd[9]
        v = (dx * bd[6] + dy * bd[7] + dz * bd[8]) / along / bd[9]
        if abs(u) >= 1.0 or abs(v) >= 1.0:
            continue
        size = int(bd[11])
        i = int(bd[10]) + min(size - 1, int((v * 0.5 + 0.5) * size)) * size + min(size - 1, int((u * 0.5 + 0.5) * size))
        a = w.body_px[i, 3] / 255.0 * bd[12]
        r += w.body_px[i, 0] / 255.0 * a
        g += w.body_px[i, 1] / 255.0 * a
        b += w.body_px[i, 2] / 255.0 * a
    return min(r, 1.0), min(g, 1.0), min(b, 1.0)


@njit(cache=True)
def offset(flags, x, z):
    """BlockBehaviour.OffsetType: how far a plant stands off the middle of its cell (world x, z)."""
    a = (x * 3129871) & 0xFFFFFFFF
    if a >= 0x80000000:
        a -= 0x100000000
    seed = a ^ (z * 116129781)
    seed = seed * seed * 42317861 + seed * 11
    seed = seed >> 16
    ox = ((seed & 15) / 15.0 - 0.5) * 0.5
    oz = (((seed >> 8) & 15) / 15.0 - 0.5) * 0.5
    oy = 0.0
    if flags & OFF_XYZ:
        oy = (((seed >> 4) & 15) / 15.0 - 1.0) * 0.2
    return ox, oy, oz


@njit(cache=True)
def cell_hit(w, pal, cx, cy, cz, px, py, pz, dx, dy, dz, tmin, tmax, lod):
    """First face of the block in a cell that the ray meets after tmin and whose texture holds
    there. Returns (t, element, face, r, g, b, a, x, y, z of the point within the cell)."""
    best_t, best_e, best_f = BIG, -1, 0
    br = bg = bb = ba = 0.0
    hx = hy = hz = 0.0
    qx, qy, qz = px - cx, py - cy, pz - cz
    nx, ny, nz = w.grid.shape
    flags = w.pal_flags[pal]
    if flags & (OFF_XZ | OFF_XYZ):
        jx, jy, jz = offset(flags, cx + w.origin[0], cz + w.origin[2])
        qx, qy, qz = qx - jx, qy - jy, qz - jz
    start = w.pal_start[pal]
    for e in range(start, start + w.pal_n[pal]):
        water = (w.el_flags[e] & WATER) != 0
        t, f, lx, ly, lz = box_hit(w.el_inv[e], w.el_off[e], w.el_lo[e], w.el_hi[e], qx, qy, qz, dx, dy, dz, tmin, water)
        if f < 0 or t > best_t + 1e-6 or t > tmax + 1e-5:
            continue
        tid = w.el_tex[e, f]
        if tid < 0:
            continue
        cull = w.el_cull[e, f]
        if cull >= 0:
            # glass against glass, water against water: the game leaves the face between them out
            ox, oy, oz = cx + DIRV[cull, 0], cy + DIRV[cull, 1], cz + DIRV[cull, 2]
            if 0 <= ox < nx and 0 <= oy < ny and 0 <= oz < nz:
                q = w.grid[ox, oy, oz]
                if water:
                    if w.pal_flags[q] & WET or (cull != 1 and w.pal_flags[q] & OPAQUE):
                        continue
                elif w.pal_class[pal] != 0 and w.pal_class[q] == w.pal_class[pal]:
                    continue
        x, y, z = qx + dx * t, qy + dy * t, qz + dz * t
        if w.el_flags[e] & WORLD_UV:
            u, v = world_uv(w.el_dir[e, f], min(1.0, max(0.0, x)), min(1.0, max(0.0, y)), min(1.0, max(0.0, z)))
        else:
            u, v = face_uv(f, w.el_lo[e], w.el_hi[e], w.el_uv[e, f], w.el_uvrot[e, f], lx, ly, lz)
        r, g, b, a = texel(w, tid, u, v, lod)
        kind = w.tex_kind[tid]
        if kind == 0:
            a = 1.0
        elif kind == 1:
            if a < 0.5:
                continue
            a = 1.0
        elif a < 0.004:
            continue
        best_t, best_e, best_f = t, e, f
        br, bg, bb, ba = r, g, b, a
        hx, hy, hz = x, y, z
    return best_t, best_e, best_f, br, bg, bb, ba, hx, hy, hz


@njit(cache=True)
def block_colour(w, pal, e, f, cx, cy, cz, hx, hy, hz, r, g, b):
    """Texture colour of a block face -> what the game puts on screen before fog."""
    ti = w.el_tint[e, f]
    r, g, b = r * w.tints[ti, 0], g * w.tints[ti, 1], b * w.tints[ti, 2]
    d = w.el_dir[e, f]
    cubic = w.el_cubic[e, f] != 0
    shade = 1.0
    if w.el_flags[e] & WATER:
        # FluidRenderer: the brighter of the cell and the one above it (below it for the underside)
        sk, bl = stored(w, cx, cy, cz)
        if d == 0:
            s2, b2 = stored(w, cx, cy - 1, cz)
        else:
            s2, b2 = stored(w, cx, cy + 1, cz)
        sk, bl = max(sk, s2), max(bl, b2)
    elif w.el_flags[e] & ALIGNED and w.pal_flags[pal] & AO:
        sk, bl, shade = smooth_light(w, cx, cy, cz, d, cubic, hx, hy, hz)
    else:
        cull = w.el_cull[e, f]
        if cull >= 0:
            sk, bl = stored(w, cx + DIRV[cull, 0], cy + DIRV[cull, 1], cz + DIRV[cull, 2])
        elif cubic:
            sk, bl = stored(w, cx + DIRV[d, 0], cy + DIRV[d, 1], cz + DIRV[d, 2])
        else:
            sk, bl = stored(w, cx, cy, cz)
        bl = max(bl, float(w.pal_emit[pal]))
    emit = float(w.el_emit[e])
    lr, lg, lb = light_colour(w.lightmap, max(sk, emit), max(bl, emit))
    s = w.el_shade[e, f] * shade
    return r * lr * s, g * lg * s, b * lb * s


@njit(cache=True)
def entity_hit(w, k, px, py, pz, dx, dy, dz, tmin, lod):
    t, f, lx, ly, lz = box_hit(w.eb_inv[k], w.eb_off[k], w.eb_lo[k], w.eb_hi[k], px, py, pz, dx, dy, dz, tmin, False)
    if f < 0:
        return BIG, 0.0, 0.0, 0.0, 0.0
    tid = w.eb_tex[k, f]
    if tid < 0:
        return BIG, 0.0, 0.0, 0.0, 0.0
    u, v = face_uv(f, w.eb_lo[k], w.eb_hi[k], w.eb_uv[k, f], 0, lx, ly, lz)
    r, g, b, a = texel(w, tid, u, v, lod)
    if w.tex_kind[tid] != 2:
        if a < 0.1:
            return BIG, 0.0, 0.0, 0.0, 0.0
        a = 1.0
    elif a < 0.004:
        return BIG, 0.0, 0.0, 0.0, 0.0
    lr, lg, lb = light_colour(w.lightmap, w.eb_light[k, 0], w.eb_light[k, 1])
    s = w.eb_shade[k, f]
    return t, r * lr * s, g * lg * s, b * lb * s, a


@njit(cache=True)
def trace(w, px, py, pz, dx, dy, dz):
    """Colour seen from (px, py, pz) along the unit vector (dx, dy, dz); grid coordinates."""
    env = w.env
    nx, ny, nz = w.grid.shape
    t0, t1 = 0.0, BIG
    # the stretch of the ray that lies inside the grid, and inside what the game would still draw
    if abs(dx) > 1e-12:
        a, b = (0.0 - px) / dx, (nx - px) / dx
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif px < 0.0 or px >= nx:
        t1 = -1.0
    if abs(dy) > 1e-12:
        a, b = (0.0 - py) / dy, (ny - py) / dy
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif py < 0.0 or py >= ny:
        t1 = -1.0
    if abs(dz) > 1e-12:
        a, b = (0.0 - pz) / dz, (nz - pz) / dz
        t0, t1 = max(t0, min(a, b)), min(t1, max(a, b))
    elif pz < 0.0 or pz >= nz:
        t1 = -1.0
    t1 = min(t1, env[FAR_END] / max(math.sqrt(dx * dx + dz * dz), abs(dy), 1e-9))
    sr, sg, sb = sky_colour(w, dx, dy, dz)
    if t0 >= t1:
        return sr, sg, sb

    t = t0 + 1e-5
    cx = min(nx - 1, max(0, int(math.floor(px + dx * t))))
    cy = min(ny - 1, max(0, int(math.floor(py + dy * t))))
    cz = min(nz - 1, max(0, int(math.floor(pz + dz * t))))
    stx = 1 if dx > 0 else -1
    sty = 1 if dy > 0 else -1
    stz = 1 if dz > 0 else -1
    tdx = abs(1.0 / dx) if abs(dx) > 1e-12 else BIG
    tdy = abs(1.0 / dy) if abs(dy) > 1e-12 else BIG
    tdz = abs(1.0 / dz) if abs(dz) > 1e-12 else BIG
    tmx = (cx + (1 if dx > 0 else 0) - px) / dx if abs(dx) > 1e-12 else BIG
    tmy = (cy + (1 if dy > 0 else 0) - py) / dy if abs(dy) > 1e-12 else BIG
    tmz = (cz + (1 if dz > 0 else 0) - pz) / dz if abs(dz) > 1e-12 else BIG

    trans = 1.0
    cr = cg = cb = 0.0
    tmin = 0.0
    ent_t, ent_r, ent_g, ent_b, ent_a = BIG, 0.0, 0.0, 0.0, 0.0
    last = -1
    gy, gz = w.cg_start.shape[1], w.cg_start.shape[2]
    first = t0 == 0.0
    while True:
        t_exit = min(tmx, tmy, tmz)
        lod = 0
        span = t_exit * env[PIXEL] * 16.0
        if span > 1.42:
            lod = 1 if span < 2.83 else (2 if span < 5.66 else 3)
        coarse = ((cx // COARSE) * gy + cy // COARSE) * gz + cz // COARSE
        if coarse != last:
            last = coarse
            s = w.cg_start[cx // COARSE, cy // COARSE, cz // COARSE]
            for i in range(s, s + w.cg_n[cx // COARSE, cy // COARSE, cz // COARSE]):
                et, er, eg, eb, ea = entity_hit(w, w.cg_list[i], px, py, pz, dx, dy, dz, tmin, lod)
                if et < ent_t:
                    ent_t, ent_r, ent_g, ent_b, ent_a = et, er, eg, eb, ea
        pal = w.grid[cx, cy, cz]
        ht, he, hf = BIG, -1, 0
        hr = hg = hb = ha = 0.0
        hx = hy = hz = 0.0
        if pal != 0 and not (first and w.pal_flags[pal] & OPAQUE):
            ht, he, hf, hr, hg, hb, ha, hx, hy, hz = cell_hit(w, pal, cx, cy, cz, px, py, pz, dx, dy, dz, tmin, t_exit, lod)
        if ent_t < ht and ent_t <= t_exit + 1e-6:
            fr, fg, fb = fogged(env, ent_r, ent_g, ent_b, ent_t, dx, dy, dz)
            cr += trans * ent_a * fr
            cg += trans * ent_a * fg
            cb += trans * ent_a * fb
            trans *= 1.0 - ent_a
            if trans < 0.004:
                return cr, cg, cb
            tmin = ent_t + 1e-5
            ent_t, last = BIG, -1
            continue
        if he >= 0:
            r, g, b = block_colour(w, pal, he, hf, cx, cy, cz, hx, hy, hz, hr, hg, hb)
            fr, fg, fb = fogged(env, r, g, b, ht, dx, dy, dz)
            cr += trans * ha * fr
            cg += trans * ha * fg
            cb += trans * ha * fb
            trans *= 1.0 - ha
            if trans < 0.004:
                return cr, cg, cb
            tmin = ht + 1e-5
            continue
        if t_exit >= t1:
            break
        first = False
        if tmx <= tmy and tmx <= tmz:
            cx += stx
            tmx += tdx
            if cx < 0 or cx >= nx:
                break
        elif tmy <= tmz:
            cy += sty
            tmy += tdy
            if cy < 0 or cy >= ny:
                break
        else:
            cz += stz
            tmz += tdz
            if cz < 0 or cz >= nz:
                break
    return cr + trans * sr, cg + trans * sg, cb + trans * sb


@njit(cache=True, parallel=True)
def render(w, cam, width, height, ss, out):
    """cam = eye (3), forward (3), right (3), up (3), tan(half the vertical field of view); the
    eye in grid coordinates. ss x ss rays per pixel."""
    half = cam[12]
    aspect = width / height
    for j in prange(height):
        for i in range(width):
            r = g = b = 0.0
            for sj in range(ss):
                for si in range(ss):
                    x = ((i + (si + 0.5) / ss) / width * 2.0 - 1.0) * half * aspect
                    y = (1.0 - (j + (sj + 0.5) / ss) / height * 2.0) * half
                    dx = cam[3] + x * cam[6] + y * cam[9]
                    dy = cam[4] + x * cam[7] + y * cam[10]
                    dz = cam[5] + x * cam[8] + y * cam[11]
                    n = math.sqrt(dx * dx + dy * dy + dz * dz)
                    pr, pg, pb = trace(w, cam[0], cam[1], cam[2], dx / n, dy / n, dz / n)
                    r += pr
                    g += pg
                    b += pb
            k = 1.0 / (ss * ss)
            out[j, i, 0] = r * k
            out[j, i, 1] = g * k
            out[j, i, 2] = b * k


# ---- light ---------------------------------------------------------------------------------------
@njit(cache=True)
def _push(buf, n, x, y, z):
    if n == buf.shape[0]:
        bigger = np.empty((2 * n, 3), dtype=np.int32)
        bigger[:n] = buf
        buf = bigger
    buf[n, 0], buf[n, 1], buf[n, 2] = x, y, z
    return buf, n + 1


@njit(cache=True)
def _flood(grid, opq, occ, light, cur, n):
    """Spread light from the cells in cur (all of the highest level set so far, or seeds of lower
    levels already written into `light`): one level less per step (LightEngine)."""
    nx, ny, nz = grid.shape
    nxt = np.empty((1 << 16, 3), dtype=np.int32)
    seeds = np.empty((max(1, n), 4), dtype=np.int32)
    for i in range(n):
        seeds[i, 0], seeds[i, 1], seeds[i, 2] = cur[i, 0], cur[i, 1], cur[i, 2]
        seeds[i, 3] = light[cur[i, 0], cur[i, 1], cur[i, 2]]
    total = n
    n = 0
    for level in range(15, 1, -1):
        for i in range(total):
            if seeds[i, 3] == level and light[seeds[i, 0], seeds[i, 1], seeds[i, 2]] == level:
                cur, n = _push(cur, n, seeds[i, 0], seeds[i, 1], seeds[i, 2])
        m = 0
        for i in range(n):
            x, y, z = cur[i, 0], cur[i, 1], cur[i, 2]
            if light[x, y, z] != level:
                continue
            own = occ[grid[x, y, z]]
            for f in range(6):
                ox, oy, oz = x + DIRV[f, 0], y + DIRV[f, 1], z + DIRV[f, 2]
                if ox < 0 or oy < 0 or oz < 0 or ox >= nx or oy >= ny or oz >= nz:
                    continue
                if light[ox, oy, oz] >= level - 1:
                    continue
                q = grid[ox, oy, oz]
                if opq[q] >= 15 or (own >> f) & 1 or (occ[q] >> (f ^ 1)) & 1:
                    continue
                light[ox, oy, oz] = level - 1
                nxt, m = _push(nxt, m, ox, oy, oz)
        cur, nxt = nxt, cur
        n = m
    return light


@njit(cache=True)
def sky_light(grid, opq, occ):
    """Light from the sky per cell (SkyLightEngine): 15 wherever nothing stands above, one less
    for every step away from there. opq: what a block takes from passing light (0, 1 or 15) by
    palette number; occ: bit f set where its face f is a whole square that shuts light out."""
    nx, ny, nz = grid.shape
    sky = np.zeros(grid.shape, dtype=np.uint8)
    for x in range(nx):
        for z in range(nz):
            for y in range(ny - 1, -1, -1):
                p = grid[x, y, z]
                if opq[p] != 0 or (occ[p] >> 1) & 1:
                    break
                if y < ny - 1 and occ[grid[x, y + 1, z]] & 1:
                    break
                sky[x, y, z] = 15
    cur = np.empty((1 << 16, 3), dtype=np.int32)
    n = 0
    for x in range(nx):
        for y in range(ny):
            for z in range(nz):
                if sky[x, y, z] != 15:
                    continue
                if ((x > 0 and sky[x - 1, y, z] < 14) or (x < nx - 1 and sky[x + 1, y, z] < 14)
                        or (y > 0 and sky[x, y - 1, z] < 14) or (z > 0 and sky[x, y, z - 1] < 14)
                        or (z < nz - 1 and sky[x, y, z + 1] < 14)):
                    cur, n = _push(cur, n, x, y, z)
    return _flood(grid, opq, occ, sky, cur, n)


@njit(cache=True)
def block_light(grid, opq, occ, emit):
    """Light from lamps per cell (BlockLightEngine). emit: light level by palette number."""
    nx, ny, nz = grid.shape
    blk = np.zeros(grid.shape, dtype=np.uint8)
    cur = np.empty((1 << 12, 3), dtype=np.int32)
    n = 0
    for x in range(nx):
        for y in range(ny):
            for z in range(nz):
                e = emit[grid[x, y, z]]
                if e > 0:
                    blk[x, y, z] = e
                    cur, n = _push(cur, n, x, y, z)
    return _flood(grid, opq, occ, blk, cur, n)
