"""Gradient noise on numpy arrays (2D and 3D), with fractal sums."""
import numpy as np

_G2 = np.array([[1, 1], [-1, 1], [1, -1], [-1, -1], [1, 0], [-1, 0], [0, 1], [0, -1]], dtype=float)
_G2 /= np.linalg.norm(_G2, axis=1)[:, None]
_G3 = np.array([[1, 1, 0], [-1, 1, 0], [1, -1, 0], [-1, -1, 0], [1, 0, 1], [-1, 0, 1], [1, 0, -1], [-1, 0, -1],
                [0, 1, 1], [0, -1, 1], [0, 1, -1], [0, -1, -1], [1, 1, 0], [-1, 1, 0], [0, -1, 1], [0, -1, -1]],
               dtype=float) / np.sqrt(2.0)
_perms = {}


def _perm(seed):
    p = _perms.get(seed)
    if p is None:
        base = np.random.default_rng(seed).permutation(256)
        p = _perms[seed] = np.concatenate([base, base, base])
    return p


def _fade(t):
    return t * t * t * (t * (t * 6 - 15) + 10)


def perlin2(x, y, seed=0):
    """2D gradient noise, roughly in [-1, 1]."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    p = _perm(seed)
    xf, yf = np.floor(x), np.floor(y)
    xi, yi = xf.astype(int) & 255, yf.astype(int) & 255
    dx, dy = x - xf, y - yf
    u, v = _fade(dx), _fade(dy)

    def corner(ix, iy, ddx, ddy):
        g = _G2[p[p[ix] + iy] & 7]
        return g[..., 0] * ddx + g[..., 1] * ddy

    n00 = corner(xi, yi, dx, dy)
    n10 = corner(xi + 1, yi, dx - 1, dy)
    n01 = corner(xi, yi + 1, dx, dy - 1)
    n11 = corner(xi + 1, yi + 1, dx - 1, dy - 1)
    a = n00 + u * (n10 - n00)
    b = n01 + u * (n11 - n01)
    return (a + v * (b - a)) * 1.6


def perlin3(x, y, z, seed=0):
    """3D gradient noise, roughly in [-1, 1]."""
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    p = _perm(seed)
    xf, yf, zf = np.floor(x), np.floor(y), np.floor(z)
    xi, yi, zi = xf.astype(int) & 255, yf.astype(int) & 255, zf.astype(int) & 255
    dx, dy, dz = x - xf, y - yf, z - zf
    u, v, w = _fade(dx), _fade(dy), _fade(dz)

    def corner(ix, iy, iz, ddx, ddy, ddz):
        g = _G3[p[p[p[ix] + iy] + iz] & 15]
        return g[..., 0] * ddx + g[..., 1] * ddy + g[..., 2] * ddz

    c000 = corner(xi, yi, zi, dx, dy, dz)
    c100 = corner(xi + 1, yi, zi, dx - 1, dy, dz)
    c010 = corner(xi, yi + 1, zi, dx, dy - 1, dz)
    c110 = corner(xi + 1, yi + 1, zi, dx - 1, dy - 1, dz)
    c001 = corner(xi, yi, zi + 1, dx, dy, dz - 1)
    c101 = corner(xi + 1, yi, zi + 1, dx - 1, dy, dz - 1)
    c011 = corner(xi, yi + 1, zi + 1, dx, dy - 1, dz - 1)
    c111 = corner(xi + 1, yi + 1, zi + 1, dx - 1, dy - 1, dz - 1)
    x00 = c000 + u * (c100 - c000)
    x10 = c010 + u * (c110 - c010)
    x01 = c001 + u * (c101 - c001)
    x11 = c011 + u * (c111 - c011)
    y0 = x00 + v * (x10 - x00)
    y1 = x01 + v * (x11 - x01)
    return (y0 + w * (y1 - y0)) * 1.5


def fbm2(x, y, seed=0, octaves=4, gain=0.5, lacunarity=2.0):
    total, amp, norm = 0.0, 1.0, 0.0
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    for i in range(octaves):
        total = total + amp * perlin2(x, y, seed + i * 31)
        norm += amp
        amp *= gain
        x = x * lacunarity
        y = y * lacunarity
    return total / norm


def fbm3(x, y, z, seed=0, octaves=3, gain=0.5, lacunarity=2.0):
    total, amp, norm = 0.0, 1.0, 0.0
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    z = np.asarray(z, dtype=float)
    for i in range(octaves):
        total = total + amp * perlin3(x, y, z, seed + i * 31)
        norm += amp
        amp *= gain
        x, y, z = x * lacunarity, y * lacunarity, z * lacunarity
    return total / norm


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)
