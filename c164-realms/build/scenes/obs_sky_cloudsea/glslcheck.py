"""Does the far sea's GLSL come to the numbers of its numpy twin?

    python -m scenes.obs_sky_cloudsea.glslcheck [--points 200000] [--keep FOLDER]

sky/cloudsea.py holds the far sea twice: far_colour() in numpy, which the forecast draws with
(preview.py), and far_glsl(), the text sky/_shaders.py puts into the resource pack's shaders. The
game's own shaderc says whether that text compiles (plan/parts/figs/sky_shaders.py). This says
whether it does the same sums.

The text is GLSL of the kind that is C++ as well, once vec2, vec3, ivec2 and a dozen functions are
there: whole numbers wrap round at 32 bits in both, a negative one turns into an unsigned one the
same way, a shift of an unsigned one brings in zeros. So the text is compiled with g++ behind a
small header and called for a few hundred thousand places, and every answer is held against
numpy's:

  the hash    c164_hash against artkit.clouds._hash3: the same to the last bit
  the face    c164_face against cloudsea._face: the same but for the floats, which have 32 bits
              here as on the card and 64 in numpy; at the rim of a heap, where the dome falls
              straight down, a hair's breadth across is a hundredth of a block in height
  the colour  c164_far_sea against cloudsea.far_colour: the same, but for the few columns whose
              light stands on the border between two tones

It ends with ``result: PASS`` or ``result: FAIL``.
"""
import argparse
import ctypes
import os
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from artkit.clouds import _hash3                            # noqa: E402
from scenes.obs.sky import cloudsea                         # noqa: E402

# GLSL's words, for C++. Everything stands in one namespace so that floor(), sqrt() and the others
# are these, with floats of 32 bits, and not the C library's with doubles.
HEADER = r"""
#include <cmath>
namespace glsl {
typedef unsigned int uint;
struct vec2 {
    float x, y;
    vec2() : x(0.0f), y(0.0f) {}
    vec2(float a, float b) : x(a), y(b) {}
    explicit vec2(float a) : x(a), y(a) {}
};
struct ivec2 {
    int x, y;
    ivec2() : x(0), y(0) {}
    ivec2(int a, int b) : x(a), y(b) {}
    explicit ivec2(vec2 v) : x(int(v.x)), y(int(v.y)) {}
};
struct vec3 {
    float x, y, z;
    vec3() : x(0.0f), y(0.0f), z(0.0f) {}
    vec3(float a, float b, float c) : x(a), y(b), z(c) {}
    explicit vec3(float a) : x(a), y(a), z(a) {}
};
static inline vec2 operator+(vec2 a, vec2 b) { return vec2(a.x + b.x, a.y + b.y); }
static inline vec2 operator-(vec2 a, vec2 b) { return vec2(a.x - b.x, a.y - b.y); }
static inline vec2 operator*(vec2 a, vec2 b) { return vec2(a.x * b.x, a.y * b.y); }
static inline vec2 operator/(vec2 a, vec2 b) { return vec2(a.x / b.x, a.y / b.y); }
static inline vec2 operator+(vec2 a, float b) { return vec2(a.x + b, a.y + b); }
static inline vec2 operator-(vec2 a, float b) { return vec2(a.x - b, a.y - b); }
static inline vec2 operator*(vec2 a, float b) { return vec2(a.x * b, a.y * b); }
static inline vec2 operator/(vec2 a, float b) { return vec2(a.x / b, a.y / b); }
static inline vec2 operator+(float a, vec2 b) { return vec2(a + b.x, a + b.y); }
static inline vec2 operator*(float a, vec2 b) { return vec2(a * b.x, a * b.y); }
static inline vec3 operator+(vec3 a, vec3 b) { return vec3(a.x + b.x, a.y + b.y, a.z + b.z); }
static inline vec3 operator-(vec3 a, vec3 b) { return vec3(a.x - b.x, a.y - b.y, a.z - b.z); }
static inline vec3 operator*(vec3 a, vec3 b) { return vec3(a.x * b.x, a.y * b.y, a.z * b.z); }
static inline vec3 operator*(vec3 a, float b) { return vec3(a.x * b, a.y * b, a.z * b); }
static inline vec3 operator*(float a, vec3 b) { return vec3(a * b.x, a * b.y, a * b.z); }
static inline float floor(float v) { return std::floor(v); }
static inline vec2 floor(vec2 v) { return vec2(std::floor(v.x), std::floor(v.y)); }
static inline float sqrt(float v) { return std::sqrt(v); }
static inline float tanh(float v) { return std::tanh(v); }
static inline float max(float a, float b) { return a > b ? a : b; }
static inline float min(float a, float b) { return a < b ? a : b; }
static inline float clamp(float v, float lo, float hi) { return min(max(v, lo), hi); }
static inline float dot(vec2 a, vec2 b) { return a.x * b.x + a.y * b.y; }
static inline float mix(float a, float b, float t) { return a * (1.0f - t) + b * t; }
static inline vec3 mix(vec3 a, vec3 b, float t) { return a * (1.0f - t) + b * t; }
"""

ENTRY = r"""
}   // namespace glsl

extern "C" {
void far_hash(int n, const int* x, const int* y, const int* z, int seed, float* out) {
    for (int i = 0; i < n; i++) out[i] = glsl::c164_hash(x[i], y[i], z[i], seed);
}
void far_face(int n, const float* x, const float* z, float* out) {
    for (int i = 0; i < n; i++) out[i] = glsl::c164_face(glsl::vec2(x[i], z[i]));
}
void far_sea(int n, const float* sea, const float* x, const float* z, const float* reach, float height, float* out) {
    for (int i = 0; i < n; i++) {
        glsl::vec3 c = glsl::c164_far_sea(glsl::vec3(sea[0], sea[1], sea[2]), glsl::vec2(x[i], z[i]), reach[i], height);
        out[3 * i] = c.x;
        out[3 * i + 1] = c.y;
        out[3 * i + 2] = c.z;
    }
}
}
"""


def compiled(text, folder):
    """The GLSL ``text`` as a library of this machine: (the library, the g++ flags it took)."""
    source, lib = os.path.join(folder, "far_sea.cpp"), os.path.join(folder, "far_sea.so")
    with open(source, "w") as f:
        f.write(HEADER + text + ENTRY)
    # numbers written 1.0 are floats of 32 bits in GLSL; g++ can be told to read them so
    for flags in (["-fsingle-precision-constant"], []):
        done = subprocess.run(["g++", "-O1", "-shared", "-fPIC", *flags, "-o", lib, source], capture_output=True, text=True)
        if done.returncode == 0:
            return ctypes.CDLL(lib), flags
    raise SystemExit("g++ does not take the far sea's GLSL:\n" + done.stderr[-3000:])


def _floats(a):
    a = np.ascontiguousarray(a, dtype=np.float32)
    return a, a.ctypes.data_as(ctypes.POINTER(ctypes.c_float))


def _ints(a):
    a = np.ascontiguousarray(a, dtype=np.int32)
    return a, a.ctypes.data_as(ctypes.POINTER(ctypes.c_int))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--points", type=int, default=200000)
    ap.add_argument("--keep", help="leave the C++ source and the library in this folder")
    args = ap.parse_args()
    n = args.points
    rng = np.random.default_rng(164)
    ok = True

    def say(passed, text):
        nonlocal ok
        ok = ok and bool(passed)
        print(("[PASS] " if passed else "[FAIL] ") + text)

    with tempfile.TemporaryDirectory() as tmp:
        folder = args.keep or tmp
        os.makedirs(folder, exist_ok=True)
        lib, flags = compiled(cloudsea.far_glsl(), folder)
        print(f"g++ took the far sea's GLSL ({len(cloudsea.far_glsl().splitlines())} lines)"
              + (", numbers read as 32-bit floats" if flags else ", numbers read as doubles"))

        # the hash, negative columns as well
        x, px = _ints(rng.integers(-6000, 6000, n))
        y, py = _ints(rng.integers(-6000, 6000, n))
        z, pz = _ints(rng.integers(0, 5, n))
        out, pout = _floats(np.zeros(n))
        worst = 0.0
        for seed in (cloudsea.SEED, cloudsea.SEED + 7, cloudsea.SEED + 48):
            lib.far_hash(n, px, py, pz, int(seed), pout)
            worst = max(worst, float(np.abs(out - _hash3(x.astype(np.int64), y.astype(np.int64), z.astype(np.int64), seed)).max()))
        say(worst == 0.0, f"the hash: {3 * n} places, the largest difference {worst:g}")

        # the face, at whole columns and between them
        xs = np.concatenate([rng.integers(-3000, 3000, n // 2).astype(float), rng.uniform(-3000, 3000, n - n // 2)])
        zs = np.concatenate([rng.integers(-3000, 3000, n // 2).astype(float), rng.uniform(-3000, 3000, n - n // 2)])
        x, px = _floats(xs)
        z, pz = _floats(zs)
        lib.far_face(n, px, pz, pout)
        twin = np.clip(cloudsea._face(x.astype(float), z.astype(float), cloudsea.SEED)[1], cloudsea.TROUGH, cloudsea.MEAN + 1.45) \
            - cloudsea.MEAN
        off = np.abs(out - twin)
        say(np.quantile(off, 0.999) < 2e-3 and off.max() < 0.08,
            f"the face: {n} places, 999 in 1000 within {np.quantile(off, 0.999):.2g} of a block, the largest difference "
            f"{off.max():.2g} (the face runs from {twin.min():.2f} to {twin.max():.2f})")

        # the colour, from three heights of the eye, near and far
        sea = np.array([0.34, 0.36, 0.55])
        _, psea = _floats(sea)
        out3, pout3 = _floats(np.zeros(3 * n))
        for height in (4.0, 30.0, 118.0):
            x, px = _floats(rng.uniform(-2500, 2500, n))
            z, pz = _floats(rng.uniform(-2500, 2500, n))
            limit = np.sqrt(cloudsea.FAR_FINE[1] * height * cloudsea.FAR_PIXEL)     # where the tones have run together
            reach, preach = _floats(rng.uniform(0.3 * height, 1.3 * limit, n))
            lib.far_sea(n, psea, px, pz, preach, ctypes.c_float(height), pout3)
            twin = cloudsea.far_colour(sea, x.astype(float), z.astype(float), reach.astype(float), height)
            off = np.abs(out3.reshape(n, 3) - twin).max(axis=1)
            other = float((off > 2e-4).mean())
            whole = reach.astype(float) ** 2 / (height * cloudsea.FAR_PIXEL) < cloudsea.FAR_FINE[0]
            say(other < 0.004, f"the colour, the eye {height:g} over the sea: {n} places ({whole.mean():.0%} of them with whole tones), "
                               f"another colour at {other:.2%} of them (a tone's border), elsewhere within {off[off <= 2e-4].max():.1g}")
    print("result: " + ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
