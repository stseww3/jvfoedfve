"""Trial, on the scratch branch only (never delivered): the dials and the time ball of
machines/clock on the real tower of main/tower (c327) with the radio mast of machines/mast (c346),
to see the interfaces meet before any of the three is in the assembly."""
from scenes import obs_mach_clocks as first
from scenes import obs_main_tower as base
from scenes.obs import materials, sky
from scenes.obs.common import skeleton as S
from scenes.obs.machines import clock
from scenes.obs.main import tower
from scenes.obs_main_tower import BIOME, BIOME_MARGIN, BIOME_MARGIN_Y, TIME  # noqa: F401


def build():
    c = base.build()
    n = clock.tower(c)
    n += first._radiomast(c)
    c.entity_counts = dict(getattr(c, "entity_counts", {}) or {}, machines=n)
    return c


def write_pack(pack_dir):
    return list(sky.pack(pack_dir) or []) + list(materials.pack(pack_dir) or [])


def shots():
    ax, az = tower.AXIS
    east = tower.X1 + 1.0
    dial = clock.DIAL_Y
    out = []

    def shot(name, pos, look_at):
        out.append({"name": name, "pos": [round(v, 2) for v in pos], "look_at": [round(v, 2) for v in look_at],
                    "time": TIME})

    shot("v1", S.V1["pos"], S.V1["look_at"])
    shot("v5_up", (44.5, 1.7, -22.5), (ax, 33.0, az))
    shot("dial_close", (east + 13.0, 22.0, az + 6.0), (east, dial, az))
    shot("top_close", (east + 14.0, 45.0, az + 11.0), (ax, clock.BALL_HALF_Y - 1.0, az))
    shot("dial_front", (east + 6.0, dial, az), (east, dial, az))
    shot("dial_south", (east + 10.0, 25.0, az + 13.5), (ax + 1.5, dial, az + 2.0))
    shot("tower_foot", (east + 22.0, 1.7, az), (east, dial, az))
    shot("v2", S.V2["pos"], S.V2["look_at"])
    return out
