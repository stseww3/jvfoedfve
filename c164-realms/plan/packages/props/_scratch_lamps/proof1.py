import sys, time
sys.path.insert(0, "/tmp/c164_lamps")
from mview import view, sheet
from scenes.obs.props import signs, electrics
t = time.time()
S, E = signs.models(), electrics.models()
tiles = []
for name in ("prop_sign_emblem", "prop_sign_great_emblem", "prop_sign_great_clock"):
    k = 16 if name.endswith("emblem") and "great" not in name else 6
    tiles.append((name + " front", view(S[name], ppu=k)))
    tiles.append((name + " 35deg", view(S[name], az=35, el=10, ppu=k)))
sheet(tiles, "/tmp/c164_lamps/proof_emblems.png", cols=2)
tiles = [(n.replace("prop_sign_", ""), view(S[n], ppu=12)) for n in sorted(S) if "plate" in n]
sheet(tiles, "/tmp/c164_lamps/proof_plates.png", cols=6)
tiles = []
for n in ("insulator", "lead_in", "junction_box", "elbow", "clip", "bell"):
    m = E["prop_elec_" + n]
    tiles.append((n + " front", view(m, ppu=14)))
    tiles.append((n + " 40", view(m, az=40, el=15, ppu=14)))
    tiles.append((n + " side", view(m, az=90, ppu=14)))
sheet(tiles, "/tmp/c164_lamps/proof_elec.png", cols=6)
tiles = []
for n in ("wall_phone", "telegraph_key"):
    m = E["prop_elec_" + n]
    for lab, az, el in (("front", 0, 0), ("right 40", 40, 15), ("left 40", -40, 15), ("side", 90, 0), ("top", 0, 89)):
        tiles.append((f"{n} {lab}", view(m, az=az, el=el, ppu=12)))
sheet(tiles, "/tmp/c164_lamps/proof_room.png", cols=5)
tiles = []
for lab, az, el in (("front (from +z)", 0, 0), ("back", 180, 0), ("35", 35, 10), ("top", 0, 89)):
    tiles.append(("flag " + lab, view(S["prop_sign_flag"], az=az, el=el, ppu=10)))
for n in ("pole_foot", "pole_head"):
    tiles.append((n, view(S["prop_sign_" + n], az=30, el=15, ppu=12)))
sheet(tiles, "/tmp/c164_lamps/proof_flag.png", cols=4)
print("done in", round(time.time() - t, 1), "s")
