"""Mean brightness of every wall of the board in a picture of the whole board (the middle four by four of each wall)."""
import json, sys
sys.path.insert(0, "/tmp/c164_a1/proto")
from PIL import Image
from proj import project
from scenes import obs_mat_board as M

def lum(p):
    return (0.2126 * p[0] + 0.7152 * p[1] + 0.0722 * p[2]) / 255.0

def mean(im, box):
    px = list(im.crop(box).getdata())
    return sum(lum(p) for p in px) / len(px), tuple(round(sum(p[i] for p in px) / len(px)) for i in range(3))

path, name = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "all")
shot = next(s for s in M.shots() if s["name"] == name)
im = Image.open(path).convert("RGB")
for k, (tier, walls) in enumerate(M.TIERS):
    if not walls:
        continue
    y, z = M.at(k)
    for x, (wall, _, _) in zip(M.places(k), walls):
        (x0, y0), (x1, y1) = project(shot["pos"], shot["look_at"], [(x + 2, y + 6, z + 1), (x + 6, y + 2, z + 1)])
        v, rgb = mean(im, (x0, y0, x1, y1))
        print(f"{tier:6s} {wall:15s} {v:.3f}  {rgb}  box {x0},{y0}..{x1},{y1}")
    # the riser between two walls of this tier, and above the walls
    xs = M.places(k)
    gx = xs[1] - 1.0 if xs[1] - xs[0] > M.N else None
    (x0, y0), (x1, y1) = project(shot["pos"], shot["look_at"], [(xs[-1] + 1, y + 8.9, z), (xs[-1] + 7, y + 8.1, z)])
    v, rgb = mean(im, (x0, y0, x1, max(y1, y0 + 2)))
    print(f"{tier:6s} {'riser (top row)':15s} {v:.3f}  {rgb}")
v, rgb = mean(im, (20, 300, 80, 400))
print(f"sky {v:.3f} {rgb}")
