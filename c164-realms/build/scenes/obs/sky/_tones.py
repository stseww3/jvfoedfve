"""Tone check: what a picture's lights and darks are, in numbers and in pictures (card
plan/packages/sky/tones.md; ART-PLAN 11, row A2: the sky darkest, the walls in the middle, windows
and lamps brightest, nothing dead black; RUBRIC 3).

    python scenes/obs/sky/_tones.py <picture> [<picture> ...] [--out <folder>]
                                    [--probe wall=0.42,0.35,0.55,0.60 ...] [--ladder]

Takes any picture, a screenshot of the game or an offline rendering. It judges nothing: it gives
the numbers and the pictures a reviewer reads the picture's values from. The lines are the
rubric's (the bright area at most a third of the picture, no patch of dead black).

Per picture, printed and, with --out, drawn onto one sheet (<name>-tones.jpg):
  grey     the picture without its colour
  levels   three flat tones, dark / middle / bright, and the share of each; dead black marked red
  warmth   which pixels are warm (redder than blue), which cool, and at which level they sit
  bright   the area brighter than 0.6: its share, its centre of gravity, how gathered it is
  dead     the area darker than 0.03: its share and the largest patch of it
  probes   named rectangles (--probe, --probes): mean, median, the brightest hundredth, the mean
           colour; listed from dark to bright, so "sky < wall < window" is read off one line
  stamps   the picture, grey and levels at 96 pixels wide

Brightness is Rec.601 luma of the picture's own values, 0 to 1 (what PIL's "L" gives; the tone
ladder in plan/parts/sky-notes.md 7 is in the same unit). Where dark ends and the middle begins
depends on the light version (SPLIT): it is taken from --look, else from the shots.txt beside a
kept picture or from --shots, else it is the blue hour's. Rectangles are x0,y0,x1,y1 in pixels, or
in fractions of the picture when no number is above 1; the sheet's first panel has a tick at every
tenth to read them from.

Needs numpy and Pillow only and takes about a second a picture. The leading underscore keeps the
module out of the scene's packages. --ladder also prints what the plan expects of the light
version (from sky/mood.py and the game's light table); for that it has to run inside build/.
"""
import argparse
import json
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
GRID = 320             # patches are counted on a grid about this many cells wide

TONES = (38, 128, 235)                 # the three flat tones of the levels picture
RED = (214, 40, 57)
MARK = (255, 196, 0)
INK, PAPER = (235, 235, 235), (16, 18, 28)
WARM, COOL = np.array([1.0, 0.62, 0.20]), np.array([0.30, 0.55, 1.0])
LEVELS = ("dark", "middle", "bright")


def look_at(tick):
    """The light version a time of day shows (the plateaus of sky/mood.py; trials count as blue)."""
    tick %= 24000
    return "glow" if 12300 <= tick < 13400 else "deep" if 15500 <= tick < 21500 else "blue"


def load(path, crop=None):
    """The picture as floats 0..1, height x width x 3."""
    picture = Image.open(path).convert("RGB")
    if crop:
        picture = picture.crop(_box(crop, picture.size))
    return np.asarray(picture, dtype=np.float64) / 255.0


def _box(numbers, size):
    """x0, y0, x1, y1 in pixels; four numbers none above 1 are fractions of the picture."""
    x0, y0, x1, y1 = numbers
    if max(numbers) <= 1.0:
        x0, x1, y0, y1 = x0 * size[0], x1 * size[0], y0 * size[1], y1 * size[1]
    x0, x1 = sorted((int(round(x0)), int(round(x1))))
    y0, y1 = sorted((int(round(y0)), int(round(y1))))
    x0, y0 = max(0, min(size[0] - 1, x0)), max(0, min(size[1] - 1, y0))
    return x0, y0, max(x0 + 1, min(size[0], x1)), max(y0 + 1, min(size[1], y1))


def luma(rgb):
    return rgb @ COEF


def _hex(rgb):
    return "#" + "".join(f"{int(round(max(0.0, min(1.0, c)) * 255.0)):02x}" for c in rgb)


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


def probe(rgb, box):
    """What a rectangle of the picture holds."""
    h, w = rgb.shape[:2]
    x0, y0, x1, y1 = _box(box, (w, h))
    part = rgb[y0:y1, x0:x1].reshape(-1, 3)
    y = np.sort(luma(part))
    edge = max(1, len(y) // 100)
    warmth = part[:, 0] - part[:, 2]
    return dict(box=(x0, y0, x1, y1), mean=float(y.mean()), median=float(np.median(y)),
                top=float(y[-edge:].mean()), low=float(y[:edge].mean()), colour=_hex(part.mean(axis=0)),
                warm=float((warmth > WARMTH).mean()), cool=float((warmth < -WARMTH).mean()))


def measure(rgb, split, probes=None):
    """The numbers of one picture. probes: {name: (x0, y0, x1, y1)}."""
    y = luma(rgb)
    h, w = y.shape
    dark, bright = y < split, y > BRIGHT
    middle = ~dark & ~bright
    dead, white = y < DEAD, y > WHITE
    warmth = rgb[..., 0] - rgb[..., 2]
    warm, cool = warmth > WARMTH, warmth < -WARMTH
    centiles = (1, 5, 50, 95, 99)
    out = dict(
        width=w, height=h, split=split, mean=float(y.mean()),
        **{f"p{q}": float(v) for q, v in zip(centiles, np.percentile(y, centiles))},
        dark=float(dark.mean()), middle=float(middle.mean()), bright=float(bright.mean()),
        dead=float(dead.mean()), white=float(white.mean()),
        warm=float(warm.mean()), cool=float(cool.mean()),
    )
    for name, where in (("dead", dead), ("bright", bright), ("white", white)):
        out[f"{name}_patches"], out[f"{name}_largest"] = patches(where)
    if bright.any():
        ys, xs = np.nonzero(bright)
        out["bright_centre"] = (float(xs.mean() / w), float(ys.mean() / h))
        out["bright_box"] = tuple(float(v) for v in (np.percentile(xs, 5) / w, np.percentile(ys, 5) / h,
                                                     np.percentile(xs, 95) / w, np.percentile(ys, 95) / h))
    # where the warm and the cool pixels sit among the three levels: shares of the whole picture
    levels = dict(zip(LEVELS, (dark, middle, bright)))
    out["table"] = {
        level: {name: float((where & tone).mean()) for name, tone in (("warm", warm), ("cool", cool), ("neutral", ~warm & ~cool))}
        for level, where in levels.items()
    }
    for level, where in levels.items():
        out[f"{level}_luma"] = float(y[where].mean()) if where.any() else None
    out["probes"] = {name: probe(rgb, box) for name, box in (probes or {}).items()}
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
        draw.rectangle((x0 * w, y0 * h, x1 * w, y1 * h), outline=MARK, width=max(1, w // 640))
        arm = max(6, w // 80)
        draw.line((cx - arm, cy, cx + arm, cy), fill=MARK, width=max(2, w // 400))
        draw.line((cx, cy - arm, cx, cy + arm), fill=MARK, width=max(2, w // 400))
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
    counts, _ = np.histogram(luma(rgb), bins=256, range=(0.0, 1.0))
    w, h = size
    picture = Image.new("RGB", size, PAPER)
    draw = ImageDraw.Draw(picture)
    top = max(1.0, float(np.sort(counts)[-3]))       # two runaway bins do not flatten the rest
    for i, c in enumerate(counts):
        x0, x1 = i * w // 256, max(i * w // 256, (i + 1) * w // 256 - 1)
        bar = int(round(min(1.0, c / top) * (h - 14)))
        at = (i + 0.5) / 256
        tone = TONES[0] + 40 if at < split else TONES[2] if at > BRIGHT else TONES[1]
        draw.rectangle((x0, h - 1 - bar, x1, h - 1), fill=RED if at < DEAD else (tone, tone, tone))
    for at in (DEAD, split, BRIGHT):
        x = int(at * w)
        draw.line((x, 0, x, h - 1), fill=MARK)
        draw.text((x + 3, 0), f"{at:.2f}", fill=MARK, font=_font(11))
    return picture


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:                       # an older Pillow: the small bitmap face
        return ImageFont.load_default()


def _pc(v):
    return f"{v * 100.0:5.1f}%"


def lines(name, n):
    """The numbers of one picture as text."""
    def tone(v):
        return "  -  " if v is None else f"{v:.2f}"

    def patched(n, what):
        count, largest = n[f"{what}_patches"], n[f"{what}_largest"]
        if not count:
            cell = max(1, round(n["width"] / GRID))
            return f"in specks only, none fills a square of {cell} pixels" if n[what] > 0.0 else "none"
        return (f"{count} patch{'es' if count > 1 else ''}, the largest {largest * 100.0:.2f}% of the picture "
                f"(as a square, {int(round((largest * n['width'] * n['height']) ** 0.5))} pixels a side)")

    out = [
        f"{name}  {n['width']}x{n['height']}",
        f"  luma    mean {n['mean']:.2f}   p1 {n['p1']:.2f}  p5 {n['p5']:.2f}  median {n['p50']:.2f}  p95 {n['p95']:.2f}  p99 {n['p99']:.2f}",
        f"  levels  dark {_pc(n['dark'])} (below {n['split']:.2f}, mean {tone(n['dark_luma'])})   "
        f"middle {_pc(n['middle'])} (mean {tone(n['middle_luma'])})   bright {_pc(n['bright'])} (above {BRIGHT:.2f}, mean {tone(n['bright_luma'])})",
    ]
    if "bright_centre" in n:
        cx, cy = n["bright_centre"]
        x0, y0, x1, y1 = n["bright_box"]
        out.append(f"  bright  centre x {cx:.2f} y {cy:.2f} (0 0 = top left)   nine tenths of it within x {x0:.2f}..{x1:.2f}, y {y0:.2f}..{y1:.2f}")
        out.append(f"          {patched(n, 'bright')}")
    else:
        out.append("  bright  none")
    out.append(f"  white   above {WHITE:.2f}: {_pc(n['white'])}   {patched(n, 'white')}")
    out.append(f"  dead    below {DEAD:.2f}: {_pc(n['dead'])}   {patched(n, 'dead')}")
    t = n["table"]
    out.append(f"  warmth  warm {_pc(n['warm'])}   cool {_pc(n['cool'])}   neutral {_pc(1.0 - n['warm'] - n['cool'])}")
    for level in LEVELS:
        out.append(f"          {level:<7} warm {_pc(t[level]['warm'])}   cool {_pc(t[level]['cool'])}   neutral {_pc(t[level]['neutral'])}")
    if n["probes"]:
        width = max(len(name) for name in n["probes"])
        for name, p in sorted(n["probes"].items(), key=lambda item: item[1]["mean"]):
            out.append(f"  probe   {name:<{width}}  mean {p['mean']:.2f}  median {p['median']:.2f}  brightest 1% {p['top']:.2f}  darkest 1% {p['low']:.2f}  "
                       f"{p['colour']}  warm {_pc(p['warm']).strip()}  cool {_pc(p['cool']).strip()}")
        out.append("  order   " + " < ".join(f"{name} {p['mean']:.2f}" for name, p in sorted(n["probes"].items(), key=lambda item: item[1]["mean"])))
    return out


def _ticks(picture):
    """A tick at every tenth along the top and the left edge, to read rectangles from."""
    draw = ImageDraw.Draw(picture)
    w, h = picture.size
    font = _font(10)
    for i in range(1, 10):
        x, y = i * w // 10, i * h // 10
        draw.line((x, 0, x, 5), fill=MARK)
        draw.line((0, y, 5, y), fill=MARK)
        if i > 1:                                   # the first one would sit under the panel's label
            draw.text((x + 2, 5), f".{i}", fill=MARK, font=font)
        draw.text((7, y - 6), f".{i}", fill=MARK, font=font)


def sheet(name, rgb, n):
    """One picture to pass round: the picture, grey, levels, warmth; numbers; histogram; stamps."""
    h, w = rgb.shape[:2]
    pw = 640
    ph = int(round(h * pw / float(w)))
    font = _font(13)
    line_h = 17
    original = Image.fromarray(np.uint8(np.round(rgb * 255.0)), "RGB")
    first = original.resize((pw, ph), Image.LANCZOS)
    draw = ImageDraw.Draw(first)
    for label, p in n["probes"].items():
        x0, y0, x1, y1 = (v * pw / float(w) for v in p["box"])
        draw.rectangle((x0, y0, x1, y1), outline=MARK)
        draw.text((x0 + 2, y0 + 1 if y1 - y0 > line_h else y1 + 1), label, fill=MARK, font=_font(11))
    _ticks(first)
    panels = [first, grey_picture(rgb), levels_picture(rgb, n["split"], n), warmth_picture(rgb)]
    labels = ["picture", "grey", f"levels: dark < {n['split']:.2f} < middle < {BRIGHT:.2f} < bright; red: dead black; cross: centre of the bright area",
              "warmth: orange warm, blue cool, grey neither"]
    text = lines(name, n)
    stamp = (96, int(round(96.0 * h / w)))
    side = 3 * (stamp[0] + 8) + 8                      # the stamps' column on the right
    foot = max(line_h * len(text), 96 + 8 + stamp[1]) + 16
    out = Image.new("RGB", (pw * 2, ph * 2 + foot), PAPER)
    draw = ImageDraw.Draw(out)
    for i, (panel, label) in enumerate(zip(panels, labels)):
        x, y = (i % 2) * pw, (i // 2) * ph
        if panel.size != (pw, ph):
            panel = panel.resize((pw, ph), Image.LANCZOS if i == 1 else Image.NEAREST)
        out.paste(panel, (x, y))
        draw.rectangle((x, y, x + 8 + int(draw.textlength(label, font=font)), y + line_h), fill=PAPER)
        draw.text((x + 4, y + 1), label, fill=INK, font=font)
    y0 = ph * 2 + 8
    for i, row in enumerate(text):
        draw.text((8, y0 + i * line_h), row, fill=INK, font=font)
    # right of the numbers: the histogram, and under it the picture at the size of a stamp, shown
    # at that size (a picture has to read as one shape and three values when it is this small)
    x0 = pw * 2 - side
    out.paste(histogram_picture(rgb, n["split"], (side - 8, 96)), (x0, y0))
    for i, panel in enumerate((original, panels[1], panels[2])):
        out.paste(panel.resize(stamp, Image.LANCZOS if i < 2 else Image.BOX), (x0 + i * (stamp[0] + 8), y0 + 96 + 8))
    return out


def summary(rows):
    """One line a picture, for pictures taken to be compared (the three light versions, two
    versions of a package)."""
    width = max(len(name) for name, _ in rows)
    shares = ("dark", "middle", "bright", "dead", "white", "warm", "cool")
    out = [f"{'':<{width}}  {'mean':>6}" + "".join(f"{c:>8}" for c in shares) + "   largest dead patch   centre of the bright area"]
    for name, n in rows:
        centre = "x %.2f y %.2f" % n["bright_centre"] if "bright_centre" in n else "-"
        out.append(f"{name:<{width}}  {n['mean']:>6.2f}" + "".join(f"{_pc(n[c]).strip():>8}" for c in shares)
                   + f"   {n['dead_largest'] * 100.0:>17.2f}%   {centre}")
    return out


def ladder(look):
    """What the plan expects of a light version, dark to bright: [(name, colour, luma)]. The sky's
    two colours are the look's own; the stone is the palette's dressed stone under the game's light
    table at the default brightness setting (plan/parts/sky-notes.md 7)."""
    build = str(Path(__file__).resolve().parents[3])
    if build not in sys.path:
        sys.path.insert(0, build)
    from artkit import gamelook
    from scenes.obs.common.palette import RAMPS
    from scenes.obs.sky import mood

    a = {key: gamelook.colour(v) if isinstance(v, str) and v.startswith("#") else v for key, v in mood.values(look).items()}
    table = gamelook.lightmap(a)
    stone, glass = gamelook.colour(RAMPS["ashlar"][3]), gamelook.colour(RAMPS["glow"][2])
    east, south, top = 0.6, 0.8, 1.0                     # the game's shading of a block's faces
    rows = [("sky overhead", gamelook.colour(mood.look(look)["zenith"])),
            ("sky at the horizon, not facing west", gamelook.colour(mood.look(look)["horizon"])),
            ("stone out of the sky's and the lamps' reach, top face", stone * table[0][0] * top),
            ("stone under the sky, east or west face", stone * table[15][0] * east),
            ("stone under the sky, north or south face", stone * table[15][0] * south),
            ("stone under the sky, top face", stone * table[15][0] * top),
            ("stone washed by a lamp (level 7), east or west face", stone * table[15][7] * east),
            ("stone beside a lamp (level 10), east or west face", stone * table[15][10] * east),
            ("stone beside a lamp (level 12), east or west face", stone * table[15][12] * east),
            ("stone beside a lamp (level 10), top face", stone * table[15][10] * top),
            ("glass of a lit window at full light", glass)]
    rows = [(name, _hex(np.clip(c, 0.0, 1.0)), float(luma(np.clip(c, 0.0, 1.0)))) for name, c in rows]
    return sorted(rows, key=lambda row: row[2])


def _times(shots):
    """{shot name: tick} of a shots.json."""
    listed = json.loads(Path(shots).read_text())
    listed = listed.get("shots", []) if isinstance(listed, dict) else listed
    return {s["name"]: int(s["time"]) for s in listed if isinstance(s.get("time"), int)}


def look_of(path, times=None):
    """The light version a picture was taken in: from the shots.txt beside a kept picture, or from
    the times of a shots.json when the picture's name ends in a shot's name."""
    stem = Path(path).stem
    listing = Path(path).with_name("shots.txt")
    if listing.is_file():
        for row in listing.read_text().splitlines():
            cells = row.split("\t")
            if len(cells) >= 2 and cells[0] == stem and cells[1].isdigit():
                return look_at(int(cells[1]))
    for name in sorted(times or {}, key=len, reverse=True):
        if stem == name or stem.endswith("-" + name):
            return look_at(times[name])
    return None


def _probes(args, stem):
    """The rectangles asked for one picture: --probe for every picture, --probes by picture."""
    out = {}
    if args.probes:
        table = json.loads(Path(args.probes).read_text())
        for key in ("*", stem):
            out.update({name: tuple(box) for name, box in table.get(key, {}).items()})
    for spec in args.probe or []:
        name, _, numbers = spec.partition("=")
        box = tuple(float(v) for v in numbers.split(","))
        if not name or len(box) != 4:
            raise SystemExit(f"--probe wants name=x0,y0,x1,y1, got {spec!r}")
        out[name] = box
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Tone check: the lights and darks of pictures, in numbers and on a sheet. It judges nothing.")
    ap.add_argument("pictures", nargs="+")
    ap.add_argument("--out", help="folder for the sheets, <name>-tones.jpg (without it: numbers only)")
    ap.add_argument("--parts", action="store_true", help="with --out: also the grey, levels and warmth pictures on their own, full size")
    ap.add_argument("--look", choices=sorted(SPLIT), help="light version of the pictures (default: read from shots.txt or --shots, else blue)")
    ap.add_argument("--shots", help="the scene's shots.json: a picture whose name ends in a shot's name takes its time, so its light version")
    ap.add_argument("--split", type=float, help="where dark ends and the middle begins (default: by light version)")
    ap.add_argument("--probe", action="append", metavar="NAME=X0,Y0,X1,Y1", help="measure a rectangle (pixels, or fractions when no number is above 1); may be given several times")
    ap.add_argument("--probes", help='rectangles by picture: {"<picture or *>": {"<name>": [x0, y0, x1, y1]}}')
    ap.add_argument("--crop", type=float, nargs=4, metavar=("X0", "Y0", "X1", "Y1"), help="look at this part of the picture only")
    ap.add_argument("--ladder", action="store_true", help="print what the plan expects of each light version met (run inside build/)")
    ap.add_argument("--json", help="write every number to this file")
    args = ap.parse_args(argv)
    out = Path(args.out) if args.out else None
    if out:
        out.mkdir(parents=True, exist_ok=True)
    times = _times(args.shots) if args.shots else None
    stems = [Path(p).stem for p in args.pictures]
    rows, everything = [], {}
    for path in args.pictures:
        stem = Path(path).stem
        name = stem if stems.count(stem) == 1 else f"{Path(path).resolve().parent.name}-{stem}"
        look = args.look or look_of(path, times) or "blue"
        split = args.split if args.split is not None else SPLIT[look]
        rgb = load(path, args.crop)
        n = measure(rgb, split, _probes(args, stem))
        title = f"{name} [{look}]"
        print("\n".join(lines(title, n)))
        rows.append((title, n))
        everything[name] = dict(n, look=look, picture=str(path))
        if out:
            target = out / f"{name}-tones.jpg"
            sheet(title, rgb, n).save(target, quality=90)
            print(f"  sheet   {target}")
            if args.parts:
                grey_picture(rgb).save(out / f"{name}-grey.png")
                levels_picture(rgb, split, n).save(out / f"{name}-levels.png")
                warmth_picture(rgb).save(out / f"{name}-warmth.png")
    if len(rows) > 1:
        print("\n" + "\n".join(summary(rows)))
    if args.ladder:
        for look in sorted({n["look"] for n in everything.values()}):
            print(f"\nexpected in {look} (brightness setting 50%):")
            for name, colour, tone in ladder(look):
                print(f"  {tone:.2f}  {colour}  {name}")
    if args.json:
        Path(args.json).write_text(json.dumps(everything, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
