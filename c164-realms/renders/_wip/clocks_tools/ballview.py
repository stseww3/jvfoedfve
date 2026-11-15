"""A flat look at the time ball's painted sides from the level of its waist: the layers taken as
drums, every pixel of the view read from the picture of the side it falls on. No ledges."""
import math
import sys
import numpy as np
from PIL import Image
sys.path.insert(0, ".")
from scenes.obs.common import palette as P
from scenes.obs.machines import clock as C

def faces(colour):
    name, (ramp, zones) = C.BALL_TONES[colour]
    tones = [P.colour(ramp, step) for step in range(max(zones) + 1)]
    colours = [tones[step] for step in zones]
    out = []
    for sign in (1.0, -1.0):
        for a0, a1 in zip(C.BALL_LAYERS, C.BALL_LAYERS[1:]):
            y0, y1 = min(sign * a0, sign * a1), max(sign * a0, sign * a1)
            mid = (y0 + y1) / 2.0
            r = math.sqrt(C.BALL_R ** 2 - mid * mid)
            pics = {}
            for side in range(C.BALL_SIDES // 2):
                turn = 360.0 * (side + 0.5) / C.BALL_SIDES
                pics[side] = C._ball_side("s", colours, r, y0, y1, turn, False).pixels
                pics[side + C.BALL_SIDES // 2] = C._ball_side("n", colours, r, y0, y1, turn, True).pixels
            out.append((y0, y1, r, pics))
    return out

def view(colour, from_deg, S=6):
    """from_deg: where the eye stands, degrees from south (+z) towards east (+x)."""
    layers = faces(colour)
    N = int(44 * S)
    img = np.zeros((N, N, 3), dtype=np.uint8)
    img[:] = (27, 32, 71)
    d = np.array([math.sin(math.radians(from_deg)), math.cos(math.radians(from_deg))])     # (x, z) to the eye
    right = np.array([d[1], -d[0]])
    step = 360.0 / C.BALL_SIDES
    for py in range(N):
        y = 22.0 - (py + 0.5) / S
        for y0, y1, r, pics in layers:
            if not (y0 <= y < y1):
                continue
            for pxl in range(N):
                u = (pxl + 0.5) / S - 22.0
                if abs(u) > r * math.cos(math.pi / C.BALL_SIDES):
                    continue
                p = u * right + math.sqrt(max(0.0, r * r - u * u)) * d
                phi = math.degrees(math.atan2(p[0], p[1])) - C.BALL_TURN
                k = int(math.floor(phi / step)) % C.BALL_SIDES
                delta = math.radians(phi - step * (k + 0.5) - 360.0 * round((phi - step * (k + 0.5)) / 360.0))
                pic = pics[k]
                h, w = pic.shape[:2]
                width = 2.0 * r * math.tan(math.pi / C.BALL_SIDES)
                i = min(w - 1, max(0, int(math.floor((r * math.tan(delta) / width + 0.5) * w))))
                j = min(h - 1, max(0, int(math.floor((y1 - y) / (y1 - y0) * h))))
                img[py, pxl] = (pic[j, i, :3] * 0.65 * np.array([0xe3, 0xc0, 0xa6]) / 255.0).astype(np.uint8)
    return Image.fromarray(img)

if __name__ == "__main__":
    out = sys.argv[1]
    views = [("copper", 90.0), ("copper", 45.0), ("copper", 135.0), ("copper", 0.0), ("red", 90.0), ("red", 45.0)]
    tiles = [view(c, a) for c, a in views]
    w, h = tiles[0].size
    sheet = Image.new("RGB", (3 * w + 20, 2 * h + 10), (10, 10, 14))
    for n, t in enumerate(tiles):
        sheet.paste(t, ((n % 3) * (w + 10), (n // 3) * (h + 10)))
    sheet.save(out)
    print(sheet.size)
