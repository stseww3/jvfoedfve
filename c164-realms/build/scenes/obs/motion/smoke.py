"""motion/smoke -- the smoke, steam and sparks, from the game's own particles.

Card plan/packages/motion/smoke.md; detail plan/parts/motion.md 9; ART-PLAN 9.

NO PARTICLE PICTURES ARE ADDED (card): every puff is one of the game's particles, sent by command at
a fixed point. The four places the card names:

  the power house chimney   campfire_signal_smoke, one particle every half second, rising and leaning
                            south with the wind, with `force` so it carries. Position: site/powerhouse's
                            SMOKE (the middle of the flue's mouth).
  the safety valve and the pipe joints   cloud, two or three at a time, a few seconds apart. Their
                            hiss is motion/sound's, on the same period.
  the boiler's fire door    small_flame, a few now and then.
  the dynamo's brushes and the switchboard's knives   electric_spark, very few.

THE WIND IS THE SKELETON'S, NOT OURS (A0 #39156): everything that rises is written as
`count=0, spread=MK.downwind(), speed=<blocks a tick>` and never with a direction of our own --
MK.downwind() reads S.WIND for us. The chimney's smoke uses the campfire's own 0.07 a tick.

RESTRAINT, because the card asks for a thread and not a cloud: the chimney is one particle at a time,
the steam two or three, the sparks are counted so that no tick ever has more than four bright
particles in flight. Nothing is placed where it could hide a window or the comet.

  what moves        where it comes from        how often
  ----------------  -------------------------  ---------------------------------------------
  chimney smoke     site/powerhouse.SMOKE      one every 10 ticks, rising 0.07 a tick
  steam             the safety valve           3 at a time every 60 ticks
  steam             the pipe joints            2 at a time every 80 ticks
  fire sparks       the boiler's fire door     one every 40 ticks
  electric sparks   the dynamo's brush gear    one every 30 ticks
  electric sparks   the switchboard's knives   one every 50 ticks

    from scenes.obs.motion import smoke
    n = smoke.build(canvas, origin)     # 0 entities, 0 blocks
"""
from scenes.obs.motion import _kit as MK

NAME = "motion/smoke"

# --- the periods, in ticks -----------------------------------------------------------------------
SMOKE_EVERY = 10                   # half a second, the card's figure
STEAM_EVERY = 60                   # the safety valve lifts about every three seconds
JOINT_EVERY = 80                   # a joint weeps more slowly
FIRE_EVERY = 40
BRUSH_EVERY = 30
KNIFE_EVERY = 50

# --- how thick -----------------------------------------------------------------------------------
# The card wants the smoke thin in V6 and V12: one particle at a time on the chimney, and the steam
# in small clusters. These are the numbers a first look at the real game can move; the alternates the
# card asks for (1, 2 and 4 particles a second) are one edit away.
SMOKE_DENSITY = 1                  # particles per puff (1, 2 or 4: the card's comparison)
STEAM_COUNT = 3
JOINT_COUNT = 2

SMOKE_RISE = 0.07                  # the campfire's own rise, a tick
STEAM_RISE = 0.06


def _sources():
    """Where the four places are, read from the packages that own them; a package not in the tree
    contributes nothing (the card's rule)."""
    out = {}
    try:
        from scenes.obs.site import powerhouse as PH
        out["chimney"] = tuple(float(v) for v in PH.SMOKE)
    except Exception:
        pass
    try:
        from scenes.obs.machines import switchboard_boiler as SB
        out["valve"] = (SB.BOILER_C[0], SB.FEET + 2.2, SB.BOILER_C[2] - 1.4)
        out["fire"] = (SB.BOILER_C[0] - 1.2, SB.FEET + 1.4, SB.BOILER_C[2])
    except Exception:
        pass
    try:
        from scenes.obs.machines import engine_dynamo as ED
        out["brushes"] = (ED.CX + ED.DYNAMO_X, ED.FEET + 1.5, ED.CZ)
    except Exception:
        pass
    try:
        from scenes.obs.machines import switchboard_boiler as SB
        out["knives"] = (SB.BOARD_AT[0] + 0.4, SB.BOARD_AT[1] + 2.1, SB.BOARD_AT[2])
    except Exception:
        pass
    return out


def build(canvas, origin=(0, 0, 0)):
    """Register the puffs. 0 display entities, 0 blocks (the card's budget line). Returns 0."""
    where = _sources()

    # the chimney: one particle every half second, rising and leaning with the wind
    if "chimney" in where:
        MK.puff(canvas, where["chimney"], "campfire_signal_smoke", SMOKE_EVERY, at=(0,),
                count=0, spread=MK.downwind(rise=SMOKE_RISE), speed=SMOKE_RISE, far=True,
                origin=origin)

    # the safety valve: a small cluster of steam every few seconds
    if "valve" in where:
        MK.puff(canvas, where["valve"], "cloud", STEAM_EVERY, at=(0,), count=STEAM_COUNT,
                spread=MK.downwind(rise=STEAM_RISE), speed=STEAM_RISE, far=True, origin=origin)

    # the pipe joints: two, more slowly
    if "valve" in where:
        j = (where["valve"][0] + 0.6, where["valve"][1] - 0.8, where["valve"][2])
        MK.puff(canvas, j, "cloud", JOINT_EVERY, at=(0,), count=JOINT_COUNT,
                spread=MK.downwind(rise=STEAM_RISE * 0.7), speed=STEAM_RISE * 0.7, origin=origin)

    # the boiler's fire door: a few small flames, now and then
    if "fire" in where:
        MK.puff(canvas, where["fire"], "small_flame", FIRE_EVERY, at=(0,), count=1,
                spread=(0.06, 0.10, 0.06), speed=0.02, origin=origin)

    # the dynamo's brushes and the switchboard's knives: very few bright sparks
    if "brushes" in where:
        MK.puff(canvas, where["brushes"], "electric_spark", BRUSH_EVERY, at=(0,), count=1,
                spread=(0.10, 0.10, 0.10), speed=0.03, origin=origin)
    if "knives" in where:
        MK.puff(canvas, where["knives"], "electric_spark", KNIFE_EVERY, at=(7,), count=1,
                spread=(0.08, 0.08, 0.08), speed=0.02, origin=origin)
    return 0
