"""Contact sheet of pictures for a first look (light work: reads PNGs, writes one JPEG).

    python sheet.py <out.jpg> <cols> <cell_w> <picture> [<picture> ...]
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

out, cols, cw = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
paths = [Path(p) for p in sys.argv[4:]]
ch = cw * 9 // 16
rows = (len(paths) + cols - 1) // cols
sheet = Image.new("RGB", (cols * cw, rows * (ch + 14)), (16, 18, 28))
draw = ImageDraw.Draw(sheet)
for i, p in enumerate(paths):
    im = Image.open(p).convert("RGB").resize((cw, ch), Image.LANCZOS)
    x, y = (i % cols) * cw, (i // cols) * (ch + 14)
    sheet.paste(im, (x, y + 14))
    draw.text((x + 3, y + 1), p.stem, fill=(235, 235, 235))
sheet.save(out, quality=88)
print(out, sheet.size)
