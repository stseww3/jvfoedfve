"""Tone check: what a picture's lights and darks are, in numbers and in pictures (card
plan/packages/sky/tones.md; ART-PLAN 11, row A2: the sky darkest, the walls in the middle, windows
and lamps brightest, nothing dead black; RUBRIC 3).

    python scenes/obs/sky/_tones.py <picture> [<picture> ...] [--out <folder>]

Takes any picture, a screenshot of the game or an offline rendering. It judges nothing: it gives
the numbers and the pictures a reviewer reads the picture's values from. The lines are the
rubric's (the bright area at most a third of the picture, no patch of dead black).

Per picture, printed and drawn onto one sheet (<name>-tones.jpg):
  grey     the picture without its colour
  levels   three flat tones, dark / middle / bright, and the share of each; dead black marked red
  warmth   which pixels are warm (redder than blue), which cool, and how bright those are
  bright   the area brighter than 0.6: its share, its centre of gravity, how gathered it is
  dead     the area darker than 0.03: its share and the largest patch of it

Brightness is Rec.601 luma of the picture's own values, 0 to 1 (what PIL's "L" gives and what the
tone ladder in plan/parts/sky-notes.md 7 is written in). Needs numpy and Pillow only; a picture
takes about a second. The leading underscore keeps the module out of the scene's packages.
"""
import argparse
import sys
from collections import deque
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

COEF = np.array([0.299, 0.587, 0.114])
DEAD = 0.03            # darker than this is dead black (card)
BRIGHT = 0.60          # brighter than this is the bright area (card, rubric)
WHITE = 0.97           # blown out
WARMTH = 0.03          # red above blue by this much is warm, blue above red by it cool
# Where dark ends and the middle begins, per light version: between the sky over the roofs and a
# wall the sky alone lights (sky/look's record: blue 0.13 and 0.24, deep 0.05 and 0.17, glow 0.20
# and 0.29).
SPLIT = {"blue": 0.18, "deep": 0.12, "glow": 0.25}
TICKS = {14000: "blue", 18000: "deep", 12900: "glow"}
GRID = 320             # patches are counted on a grid about this many cells wide

TONES = (38, 128, 235)                 # the three flat tones of the levels picture
RED = (214, 40, 57)
WARM, COOL = np.array([1.0, 0.62, 0.20]), np.array([0.30, 0.55, 1.0])


def load(path, crop=None):
    """The picture as floats 0..1, height x width x 3."""
    picture = Image.open(path).convert("RGB")
    if crop:
        picture = picture.crop(_box(crop, picture.size))
    return np.asarray(picture, dtype=np.float64) / 255.0


def _box(numbers, size):
    """x0, y0, x1, y1 in pixels; four numbers no greater than 1 are fractions of the picture."""
    x0, y0, x1, y1 = numbers
    if max(numbers) <= 1.0:
        x0, x1, y0, y1 = x0 * size[0], x1 * size[0], y0 * size[1], y1 * size[1]
    return int(round(x0)), int(round(y0)), int(round(x1)), int(round(y1))


def luma(rgb):
    return rgb @ COEF


def patches(mask):
    """(how many patches, the largest one's share of the picture) of a mask, counted on a coarse
    grid: a cell belongs when more than half of it does, cells touching by a side are one patch."""
    h, w = mask.shape
    cell = max(1, round(w / GRID))
    gh, gw = h // cell, w // cell
    if not gh or not gw:
        return 0, 0.0
    coarse = mask[:gh * cell, :gw * cell].reshape(gh, cell, gw, cell).mean(axis=(1, 3)) > 0.5
    todo = coarse.copy()
    count, largest = 0, 0
    for y, x in zip(*np.nonzero(coarse)):
        if not todo[y, x]:
            continue
        count += 1
        size, queue = 0, deque([(y, x)])
        todo[y, x] = False
        while queue:
            cy, cx = queue.popleft()
            size += 1
            for ny, nx in ((cy - 1, cx), (cy + 1, cx), (cy, cx - 1), (cy, cx + 1)):
                if 0 <= ny < gh and 0 <= nx < gw and todo[ny, nx]:
                    todo[ny, nx] = False
                    queue.append((ny, nx))
        largest = max(largest, size)
    return count, largest / float(gh * gw)


def measure(rgb, split):
    """The numbers of one picture."""
    y = luma(rgb)
    h, w = y.shape
    dark, bright = y < split, y > BRIGHT
    middle = ~dark & ~bright
    dead, white = y < DEAD, y > WHITE
    warmth = rgb[..., 0] - rgb[..., 2]
    warm, cool = warmth > WARMTH, warmth < -WARMTH
    out = dict(
        width=w, height=h, split=split,
        mean=float(y.mean()), **{f"p{q}": float(v) for q, v in zip((1, 5, 50, 95, 99), np.percentile(y, (1, 5, 50, 95, 99)))},
        dark=float(dark.mean()), middle=float(middle.mean()), bright=float(bright.mean()),
        dead=float(dead.mean()), white=float(white.mean()),
        warm=float(warm.mean()), cool=float(cool.mean()),
    )
    out["dead_patches"], out["dead_largest"] = patches(dead)
    out["bright_patches"], out["bright_largest"] = patches(bright)
    if bright.any():
        ys, xs = np.nonzero(bright)
        out["bright_centre"] = (float(xs.mean() / w), float(ys.mean() / h))
        out["bright_box"] = tuple(float(v) for v in (np.percentile(xs, 5) / w, np.percentile(ys, 5) / h,
                                                     np.percentile(xs, 95) / w, np.percentile(ys, 95) / h))
    # where the warm and the cool pixels sit among the three levels: shares of the whole picture
    out["table"] = {
        level: {name: float((where & tone).mean()) for name, tone in (("warm", warm), ("cool", cool), ("neutral", ~warm & ~cool))}
        for level, where in (("dark", dark), ("middle", middle), ("bright", bright))
    }
    for name, where in (("dark", dark), ("middle", middle), ("bright", bright)):
        out[f"{name}_luma"] = float(y[where].mean()) if where.any() else None
    return out


def grey_picture(rgb):
    return Image.fromarray(np.uint8(np.round(luma(rgb) * 255.0)), "L").convert("RGB")


def levels_picture(rgb, split, numbers=None):
    y = luma(rgb)
    out = np.empty(y.shape + (3,), dtype=np.uint8)
    out[...] = TONES[1]
    out[y < split] = TONES[0]
    out[y > BRIGHT] = TONES[2]
    out[y < DEAD] = RED
    picture = Image.fromarray(out, "RGB")
    if numbers and "bright_centre" in numbers:
        draw = ImageDraw.Draw(picture)
        w, h = picture.size
        cx, cy = numbers["bright_centre"][0] * w, numbers["bright_centre"][1] * h
        x0, y0, x1, y1 = numbers["bright_box"]
        draw.rectangle((x0 * w, y0 * h, x1 * w, y1 * h), outline=(255, 196, 0), width=max(1, w // 640))
        arm = max(6, w // 80)
        draw.line((cx - arm, cy, cx + arm, cy), fill=(255, 196, 0), width=max(2, w // 400))
        draw.line((cx, cy - arm, cx, cy + arm), fill=(255, 196, 0), width=max(2, w // 400))
    return picture


def warmth_picture(rgb):
    """Warm pixels orange, cool pixels blue, the rest grey; each as bright as it is in the picture."""
    y = luma(rgb)
    warmth = rgb[..., 0] - rgb[..., 2]
    shade = (0.25 + 0.75 * y)[..., None]
    out = np.repeat(shade, 3, axis=2) * 0.55
    out[warmth > WARMTH] = (shade * WARM)[warmth > WARMTH]
    out[warmth < -WARMTH] = (shade * COOL)[warmth < -WARMTH]
    return Image.fromarray(np.uint8(np.round(np.clip(out, 0.0, 1.0) * 255.0)), "RGB")


def histogram_picture(rgb, split, size=(512, 96)):
    y = luma(rgb)
    counts, _ = np.histogram(y, bins=256, range=(0.0, 1.0))
    w, h = size
    picture = Image.new("RGB", size, (16, 18, 28))
    draw = ImageDraw.Draw(picture)
    top = max(1.0, float(np.sort(counts)[-3]))       # two runaway bins do not flatten the rest
    for i, c in enumerate(counts):
        x0, x1 = i * w // 256, (i + 1) * w // 256 - 1
        bar = int(round(min(1.0, c / top) * (h - 14)))
        at = (i + 0.5) / 256
        tone = TONES[0] + 40 if at < split else TONES[2] if at > BRIGHT else TONES[1]
        draw.rectangle((x0, h - 1 - bar, x1, h - 1), fill=RED if at < DEAD else (tone, tone, tone))
    for at, label in ((DEAD, f"{DEAD:.2f}"), (split, f"{split:.2f}"), (BRIGHT, f"{BRIGHT:.2f}")):
        x = int(at * w)
        draw.line((x, 0, x, h - 1), fill=(255, 196, 0))
        draw.text((x + 3, 0), label, fill=(255, 196, 0), font=_font(11))
    return picture


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                       # an older Pillow: the small bitmap face
        return ImageFont.load_default()


def lines(name, n):
    """The numbers of one picture as text."""
    def pc(v):
        return f"{v * 100.0:5.1f}%"

    def tone(v):
        return "  -  " if v is None else f"{v:.2f}"

    out = [
        f"{name}  {n['width']}x{n['height']}",
        f"  luma    mean {n['mean']:.2f}   p1 {n['p1']:.2f}  p5 {n['p5']:.2f}  median {n['p50']:.2f}  p95 {n['p95']:.2f}  p99 {n['p99']:.2f}",
        f"  levels  dark {pc(n['dark'])} (below {n['split']:.2f}, mean {tone(n['dark_luma'])})   "
        f"middle {pc(n['middle'])} (mean {tone(n['middle_luma'])})   bright {pc(n['bright'])} (above {BRIGHT:.2f}, mean {tone(n['bright_luma'])})",
    ]
    if "bright_centre" in n:
        cx, cy = n["bright_centre"]
        x0, y0, x1, y1 = n["bright_box"]
        out.append(f"  bright  centre x {cx:.2f} y {cy:.2f} (0 0 = top left)   nine tenths of it within x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}")
        out.append(f"          {n['bright_patches']} patches, the largest {pc(n['bright_largest'])} of the picture   blown out (above {WHITE:.2f}): {pc(n['white'])}")
    else:
        out.append("  bright  none")
    out.append(f"  dead    below {DEAD:.2f}: {pc(n['dead'])}   {n['dead_patches']} patches, the largest {pc(n['dead_largest'])} of the picture")
    t = n["table"]
    out.append(f"  warmth  warm {pc(n['warm'])}   cool {pc(n['cool'])}   neutral {pc(1.0 - n['warm'] - n['cool'])}")
    for level in ("dark", "middle", "bright"):
        out.append(f"          {level:<7} warm {pc(t[level]['warm'])}   cool {pc(t[level]['cool'])}   neutral {pc(t[level]['neutral'])}")
    return out


def sheet(name, rgb, n):
    """One picture to pass round: the picture, grey, levels, warmth; stamps; histogram; numbers."""
    h, w = rgb.shape[:2]
    pw = 640
    ph = int(round(h * pw / float(w)))
    original = Image.fromarray(np.uint8(np.round(rgb * 255.0)), "RGB")
    panels = [original, grey_picture(rgb), levels_picture(rgb, n["split"], n), warmth_picture(rgb)]
    labels = ["picture", "grey", f"levels: dark < {n['split']:.2f} < middle < {BRIGHT:.2f} < bright; red: dead black; cross: centre of the bright area",
              "warmth: orange warm, blue cool, grey neither"]
    text = lines(name, n)
    font = _font(13)
    line_h = 17
    stamp = (96, int(round(96.0 * h / w)))
    side = 3 * (stamp[0] + 8) + 8                      # the stamps' column on the right
    foot = max(line_h * len(text), 96 + 8 + stamp[1]) + 16
    out = Image.new("RGB", (pw * 2, ph * 2 + foot), (16, 18, 28))
    draw = ImageDraw.Draw(out)
    for i, (panel, label) in enumerate(zip(panels, labels)):
        x, y = (i % 2) * pw, (i // 2) * ph
        out.paste(panel.resize((pw, ph), Image.LANCZOS if i in (0, 1) else Image.NEAREST), (x, y))
        draw.rectangle((x, y, x + 8 + int(draw.textlength(label, font=font)), y + line_h), fill=(16, 18, 28))
        draw.text((x + 4, y + 1), label, fill=(235, 235, 235), font=font)
    y0 = ph * 2 + 8
    for i, row in enumerate(text):
        draw.text((8, y0 + i * line_h), row, fill=(235, 235, 235), font=font)
    # right of the numbers: the histogram, and under it the picture at the size of a stamp, shown
    # at that size (a picture has to read as one shape, three values, when it is this small)
    x0 = pw * 2 - side
    out.paste(histogram_picture(rgb, n["split"], (side - 8, 96)), (x0, y0))
    for i, panel in enumerate(panels[:3]):
        out.paste(panel.resize(stamp, Image.LANCZOS if i < 2 else Image.BOX), (x0 + i * (stamp[0] + 8), y0 + 96 + 8))
    return out


def look_of(path):
    """The light version a kept picture was taken in, read from the shots.txt beside it."""
    listing = Path(path).with_name("shots.txt")
    if not listing.is_file():
        return None
    for row in listing.read_text().splitlines():
        cells = row.split("\t")
        if len(cells) >= 2 and cells[0] == Path(path).stem and cells[1].isdigit():
            return TICKS.get(int(cells[1]))
    return None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pictures", nargs="+")
    ap.add_argument("--out", help="folder for the sheets (default: no pictures, numbers only)")
    ap.add_argument("--look", choices=sorted(SPLIT), help="light version of the pictures (default: from shots.txt beside the picture, else blue)")
    ap.add_argument("--split", type=float, help="where dark ends and the middle begins (default: by light version)")
    ap.add_argument("--crop", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), help="look at this part only (pixels, or fractions of the picture)")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    for path in args.pictures:
        look = args.look or look_of(path) or "blue"
        split = args.split if args.split is not None else SPLIT[look]
        rgb = load(path, args.crop)
        n = measure(rgb, split)
        name = Path(path).stem
        print("\n".join(lines(f"{name} [{look}]", n)))
        if out:
            target = out / f"{name}-tones.jpg"
            sheet(f"{name} [{look}]", rgb, n).save(target, quality=90)
            print(f"  sheet   {target}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
