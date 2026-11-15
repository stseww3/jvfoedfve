"""A contact sheet of pictures drawn with tools/selfshots.py --out: many shots, or the two versions'
twins side by side, in one file. For a look at work in progress and for the comparison of a and b;
nothing of it goes into the map.

    python -m scenes.obs_main_dome.sheet <out.png> <folder> [<folder> ...]
        [--only v1,roof]        these shots only, in this order (default: every picture found)
        [--cols 4]              tiles in a row (default: one row per shot when there are several
                                folders, else 4)
        [--crop x0,y0,x1,y1]    cut this window out of every picture first (pixels of the picture)
        [--scale 0.5]           then scale it: below 1 smoothly, above 1 pixel for pixel
        [--grey]                without colour, to judge the values

A folder holds <scene>-<shot>.png as selfshots.py --out leaves them; several folders are laid shot
by shot, so that a shot of obs_main_dome stands beside its twin of obs_main_dome_a.
"""
import argparse
import os
import sys

from PIL import Image, ImageDraw, ImageFont

GAP = 6
LABEL = 12
PAPER = (22, 24, 30)
INK = (226, 220, 205)


def pictures(folder):
    """{shot: path} of the pictures selfshots.py left in a folder, and the scene they show."""
    found, scene = {}, None
    for name in sorted(os.listdir(folder)):
        stem, ext = os.path.splitext(name)
        if ext.lower() != ".png" or "-" not in stem:
            continue
        scene, _, shot = stem.rpartition("-")
        found[shot] = os.path.join(folder, name)
    return found, scene


def tile(path, crop, scale, grey):
    im = Image.open(path).convert("RGB")
    if crop:
        im = im.crop(crop)
    if scale != 1.0:
        size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
        im = im.resize(size, Image.NEAREST if scale > 1.0 else Image.LANCZOS)
    return im.convert("L").convert("RGB") if grey else im


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("out")
    ap.add_argument("folders", nargs="+")
    ap.add_argument("--only")
    ap.add_argument("--cols", type=int)
    ap.add_argument("--crop")
    ap.add_argument("--scale", type=float, default=0.5)
    ap.add_argument("--grey", action="store_true")
    args = ap.parse_args()

    sets = [pictures(folder) for folder in args.folders]
    names = args.only.split(",") if args.only else sorted({shot for found, _ in sets for shot in found})
    crop = tuple(int(v) for v in args.crop.split(",")) if args.crop else None
    tiles = []
    for shot in names:
        for found, scene in sets:
            if shot in found:
                tiles.append((f"{scene} {shot}", tile(found[shot], crop, args.scale, args.grey)))
            else:
                print(f"sheet: no picture of {shot} in {scene or 'a folder'}", file=sys.stderr)
    if not tiles:
        sys.exit("sheet: no pictures to lay out")
    cols = args.cols or (len(sets) if len(sets) > 1 else 4)
    rows = -(-len(tiles) // cols)
    w = max(im.width for _, im in tiles)
    h = max(im.height for _, im in tiles)
    sheet = Image.new("RGB", (cols * (w + GAP) + GAP, rows * (h + LABEL + GAP) + GAP), PAPER)
    pen = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    for i, (label, im) in enumerate(tiles):
        x = GAP + (i % cols) * (w + GAP)
        y = GAP + (i // cols) * (h + LABEL + GAP)
        pen.text((x, y), label, fill=INK, font=font)
        sheet.paste(im, (x, y + LABEL))
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    sheet.save(args.out)
    print(f"{len(tiles)} tiles, {sheet.width}x{sheet.height} -> {args.out}")


if __name__ == "__main__":
    main()
