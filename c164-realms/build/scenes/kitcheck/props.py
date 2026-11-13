"""Test pieces for artkit.models: do turned parts land where the kit says they do?

Build and look at them with

    makepack.py kitcheck --out <resource pack>
    gallery.py kitcheck --pw-file <server>/.rcon_pw --at 3300 120 40 --shots /tmp/kitcheck.json

`check_rods` is the one that proves the rotation maths against the game: every rod and beam has to
end inside its unturned marker cube. The rest shows what the round shapes look like.
"""
from artkit import models as M
from artkit import pixelart as P

SCALE = {"check_rods": 2.0, "check_round": 2.0, "check_groups": 2.0}

TARGETS = [(14, 0, 0), (0, 14, 0), (0, 0, 14), (-10, 9, 4), (8, 11, -7), (-6, -9, -10), (9, -8, 9), (-12, 3, -8),
           (4, 13, 6)]


def check_rods():
    m = M.Model("check_rods", px=2)
    m.box((-1.5, -1.5, -1.5), (1.5, 1.5, 1.5), P.IRON)
    for i, t in enumerate(TARGETS):
        if i % 2:
            m.beam((0, 0, 0), t, 0.8, 1.6, P.WOOD)
        else:
            m.rod((0, 0, 0), t, 0.6, P.BRASS, sides=8)
        m.box((t[0] - 1, t[1] - 1, t[2] - 1), (t[0] + 1, t[1] + 1, t[2] + 1), P.RED_CLOTH if i % 2 else P.VERDIGRIS)
    return m


def check_round():
    m = M.Model("check_round", px=2, anchor=(0, -12, 0))
    m.ball((-12, -6, 0), 6.0, P.BRASS, sides=16, layers=8)
    m.ball((-12, 6, 0), 5.0, P.VERDIGRIS, sides=12, layers=5, part=(0.0, 1.0))
    m.tube("y", (0, 0), -12, 0, 4.0, P.COPPER, sides=24)
    m.taper("y", (0, 0), 0, 10, 4.0, 1.0, P.COPPER, sides=24, steps=6)
    m.ring("z", (12, -4, 0), 7.0, 1.0, 1.0, P.BRASS, sides=32)
    m.ring("z", (12, -4, 0), 4.5, 1.0, 1.0, P.IRON, sides=24, arc=(-30.0, 210.0))
    m.hose([(6, 6, 0), (10, 9, 0), (15, 9, 2), (18, 5, 4), (18, 0, 4)], [1.2, 1.1, 1.0, 0.9],
           [P.RED_CLOTH, P.CREAM_CLOTH, P.RED_CLOTH, P.CREAM_CLOTH], sides=12)
    return m


def check_groups():
    """The same small bracket drawn four times: plain, and turned as a whole in three ways."""
    m = M.Model("check_groups", px=2, anchor=(0, -10, 0))

    def bracket():
        m.box((-1, 0, -1), (1, 10, 1), P.DARK_WOOD, grain="y")
        m.box((1, 8, -0.75), (7, 9.5, 0.75), P.DARK_WOOD, grain="x")
        m.box((3, 3, -0.5), (4, 9, 0.5), P.IRON, rot=("z", -45.0, (1, 5.5, 0)))
        m.tube("y", (6, 0), 4.5, 8, 1.2, P.LAMP_GLOW, sides=8)

    with m.moved((-14, -10, 0)):
        bracket()
    for i, turns in enumerate(((("z", 25.0),), (("x", -30.0), ("y", 40.0)), (("y", 90.0), ("z", -20.0), ("x", 15.0)))):
        x = -4.0 + 9.0 * i
        with m.turned(*turns, about=(x, -10, 0)), m.moved((x, -10, 0)):
            bracket()
    return m


MODELS = [check_rods, check_round, check_groups]


def build_models():
    out = {}
    for f in MODELS:
        m = f()
        out[m.name] = m
    return out


GALLERY = [
    ("rods", [("check_rods", (0, 2.5, 0), {})], (3.2, 4.2, 4.6), (0, 2.5, 0)),
    ("rods_b", [("check_rods", (0, 2.5, 0), {"yaw": 180.0})], (3.2, 1.4, 4.6), (0, 2.5, 0)),
    ("round", [("check_round", None, {})], (2.2, 3.0, 5.2), (0, 1.5, 0)),
    ("groups", [("check_groups", None, {})], (1.5, 2.4, 5.0), (0, 1.3, 0)),
]
