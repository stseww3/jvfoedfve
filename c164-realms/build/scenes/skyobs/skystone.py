"""Models for what holds the island up and what once held it down: clusters of glowing skystone
crystal, and heavy mooring chain.

Registered through props.py (SCALE, MODELS and GALLERY are merged into its lists).
"""
from artkit import models as M
from artkit import pixelart as P

SCALE = {"chain_run": 3.0}
CHAIN_RUN, CHAIN_STEP = 48.0, 42.0   # units: length of one run of three links, and where the next begins

# every face is painted darkest along its edges and lightest in the middle, and glows
CRYSTAL = P.Mat("skystone", ["#0a4660", "#0f6f8f", "#169bb5", "#2cc6cf", "#62e6dc", "#aef7ec"],
                kind="glow", noise=0.0, bevel=0, base=1)
RUST = P.Mat("rust", ["#241a16", "#33251d", "#473326", "#5f432f", "#7a573a"], kind="metal", noise=0.3)

# a cluster: shards as (lean from the cluster's axis, direction of the lean, length, radius, foot x, foot z)
SHARDS = {
    "a": [(0, 0, 41, 4.2, 0, 0), (24, 20, 30, 3.2, 1.5, 1), (30, 140, 26, 3.0, -1, 1.5), (20, 255, 34, 3.4, -1, -2),
          (42, 80, 18, 2.4, 2, 2), (46, 200, 16, 2.2, -2.5, 0), (38, 320, 20, 2.6, 2, -2), (11, 175, 35, 2.8, -3, 0.5)],
    "b": [(4, 0, 34, 3.4, 0, 0), (28, 40, 22, 2.6, 1.5, 1), (34, 170, 20, 2.4, -1.5, 0.5), (24, 290, 26, 2.8, 0.5, -1.5),
          (48, 110, 12, 1.8, 0, 2)],
    "c": [(8, 0, 22, 2.6, 0, 0), (32, 130, 14, 2.0, -1, 1), (36, 250, 12, 1.8, 0.5, -1.5)],
}
CLUSTERS = [(kind, hanging) for kind in SHARDS for hanging in (True, False)]


def cluster_name(kind, hanging=True):
    return f"crystal_{kind}" + ("" if hanging else "_up")


def crystal(kind, hanging):
    """A cluster of six-sided crystal shards growing out of one point, downwards when hanging.
    Anchor: that point, on the rock face."""
    m = M.Model(cluster_name(kind, hanging), px=4.0)
    with m.turned(*((("x", 180.0),) if hanging else ())):
        for i, (lean, to, length, radius, fx, fz) in enumerate(SHARDS[kind]):
            with m.turned(("z", lean), ("y", to)), m.moved((fx, 0, fz)):
                body = length * 0.7
                m.tube("y", (0, 0), -2.0, body, radius, CRYSTAL, sides=6, emit=15, shade=False, seed=1200 + i)
                m.taper("y", (0, 0), body, length, radius * 0.88, radius * 0.1, CRYSTAL, sides=6, steps=3,
                        emit=15, shade=False, seed=1220 + i)
    return m


def chain_run():
    """Three links of heavy chain along +z, 48 units long; the next run begins 42 units on and is
    turned a quarter round. Anchor: the near end, on the centre line."""
    m = M.Model("chain_run", px=3.0)
    for i, zc in enumerate((10.0, 24.0, 38.0)):
        mat = RUST if i == 1 else P.IRON
        with m.moved((0, 0, zc)), m.turned(("z", 90.0 * (i % 2))):
            for sx in (-1, 1):
                m.tube("z", (sx * 4.5, 0), -4.0, 4.0, 1.5, mat, sides=8, seed=1300 + i)
            m.ring("y", (0, 0, 4.0), 4.5, 3.0, 3.0, mat, sides=16, arc=(180.0, 360.0), seed=1310 + i)
            m.ring("y", (0, 0, -4.0), 4.5, 3.0, 3.0, mat, sides=16, arc=(0.0, 180.0), seed=1320 + i)
    return m


MODELS = [chain_run] + [(lambda k=k, h=h: crystal(k, h)) for k, h in CLUSTERS]
SCALE.update({cluster_name(k, h): 4.0 for k, h in CLUSTERS})

GALLERY = [
    ("crystals", [("crystal_a", (-3.5, 12.0, 0), {"brightness": 15}), ("crystal_b", (1.0, 12.0, 0), {"brightness": 15}),
                  ("crystal_c", (4.5, 12.0, 0), {"brightness": 15})], (2.0, 6.5, 16.0), (0.5, 6.5, 0)),
    ("crystals_up", [("crystal_a_up", (-3.5, 0, 0), {"brightness": 15}), ("crystal_c_up", (2.5, 0, 0), {"brightness": 15, "scale": 2.0})],
     (2.0, 5.0, 15.0), (0, 5.0, 0)),
    ("chain", [("chain_run", (0, 2.0, -4.5), {}), ("chain_run", (0, 2.0, 3.375), {"turns": (("z", 90.0),)})],
     (9.0, 4.0, 4.5), (0, 2.0, 4.5)),
]
