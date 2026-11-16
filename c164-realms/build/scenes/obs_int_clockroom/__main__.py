"""python -m scenes.obs_int_clockroom: write shots.json of the scene and of its twin without the
room from the scene's VIEWS, and count the light outside the tower with the room and without it."""
import json
import os

from scenes import obs_int_clockroom_bare as twin
from scenes.obs.main import tower

from . import _levels, outside_light, room, shots, walk_light, way_light


def write(folder, rows):
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), folder, "shots.json")
    with open(path, "w") as fh:
        fh.write("[\n" + ",\n".join(" " + json.dumps(row) for row in rows) + "\n]\n")
    print(f"{path}: {len(rows)} shots")


def main():
    write("obs_int_clockroom", shots())
    write("obs_int_clockroom_bare", twin.shots())
    (bare, bare_sources), (full, full_sources) = _levels(False), _levels(True)
    print("sources without the room:", " ".join(f"{c}={v}" for c, v in sorted(bare_sources.items())) or "none")
    print("sources the room adds:", " ".join(f"{c}={v}" for c, v in sorted(full_sources.items())
                                             if bare_sources.get(c) != v) or "none")
    changed = outside_light((bare, full))
    if not changed:
        print("light outside the tower: the same in every cell with the room and without it")
    else:
        print(f"light outside the tower: {len(changed)} cells differ (cell without>with):",
              " ".join(f"{c}{a}>{b}" for c, (a, b) in changed.items()))
    walk = walk_light(full)
    low = {column: v for column, v in walk.items() if v < room.WALK_LIGHT}
    print(f"light on the walk: {len(walk)} places, the least {min(walk.values())}, the most {max(walk.values())};",
          "under %d: %s" % (room.WALK_LIGHT, " ".join(f"{c}={v}" for c, v in sorted(low.items())) or "none"))
    from scenes.obs.props import _kit as K
    loose = {name: len(K.unsettled(m)) for name, m in room.models().items() if K.unsettled(m)}
    print("faces between two axes:", " ".join(f"{name}={n}" for name, n in sorted(loose.items())) or "none")
    way = way_light(full)
    print(f"light on the way up: {len(way)} cells, the least {min(way.values())};",
          " ".join(f"{c}={v}" for c, v in way.items()))
    glass = {f.name: [(x, y, z) for y in range(tower.SLIT_Y[0], tower.SLIT_Y[1] + 1)] for f in tower.FACES
             for x, z in [f.cell(tower.MID, 1)]}
    for name, cells in glass.items():
        print(f"slit {name}: glass", " ".join(f"{c} {bare.get(c, 0)}>{full.get(c, 0)}" for c in cells))


if __name__ == "__main__":
    main()
