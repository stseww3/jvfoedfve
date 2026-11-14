"""Read numbers off a picture that already exists. Draws nothing; needs only zlib and numpy (no PIL).

For the reviewers (S3): the cloud never renders, but a review may quote what a kept picture measures --
the colour of a wall, how strong the lines of a texture are from a distance. This reads an 8-bit,
non-interlaced PNG (grey, RGB or RGBA) into an array and prints means.

    python3 pngread.py <picture.png> x0,y0,x1,y1 [x0,y0,x1,y1 ...]

prints, for each box (pixels of the file as stored, not of a scaled preview): the mean colour, its hue,
saturation and value, R-G and B-G (R above G is where a grey turns pink), and how much the row means and
the column means wave about their running mean, as a share of the mean luminance (horizontal lines,
vertical lines).
"""
import colorsys
import struct
import sys
import zlib

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722])


def read(path):
    """The picture as a float array (height, width, 3)."""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG")
    pos, idat = 8, []
    while pos < len(data):
        n, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if kind == b"IHDR":
            w, h, depth, ctype, _, _, interlace = struct.unpack(">IIBBBBB", body)
            if depth != 8 or interlace != 0 or ctype not in (0, 2, 4, 6):
                raise ValueError(f"{path}: only 8-bit non-interlaced grey/RGB/RGBA is read")
            ch = {0: 1, 2: 3, 4: 2, 6: 4}[ctype]
        elif kind == b"IDAT":
            idat.append(body)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(b"".join(idat))
    stride = w * ch
    out = np.zeros((h, stride), dtype=np.uint8)
    prev = [0] * stride
    p = 0
    for y in range(h):
        kind = raw[p]
        line = raw[p + 1:p + 1 + stride]
        p += 1 + stride
        if kind == 0:
            cur = list(line)
        elif kind == 1:
            cur = (np.frombuffer(line, dtype=np.uint8).astype(np.int64).reshape(w, ch).cumsum(axis=0)
                   .reshape(-1) & 255).tolist()
        elif kind == 2:
            cur = ((np.frombuffer(line, dtype=np.uint8).astype(np.int64) + np.array(prev)) & 255).tolist()
        elif kind == 3:
            cur = [0] * stride
            for i in range(stride):
                left = cur[i - ch] if i >= ch else 0
                cur[i] = (line[i] + ((left + prev[i]) >> 1)) & 255
        elif kind == 4:
            cur = [0] * stride
            for i in range(stride):
                a = cur[i - ch] if i >= ch else 0
                b = prev[i]
                c = prev[i - ch] if i >= ch else 0
                pa, pb, pc = abs(b - c), abs(a - c), abs(a + b - 2 * c)
                cur[i] = (line[i] + (a if pa <= pb and pa <= pc else b if pb <= pc else c)) & 255
        else:
            raise ValueError(f"{path}: unknown filter {kind} on row {y}")
        out[y] = cur
        prev = cur
    px = out.reshape(h, w, ch).astype(float)
    if ch == 1:
        return np.repeat(px, 3, axis=2)
    if ch == 2:
        return np.repeat(px[..., :1], 3, axis=2)
    return px[..., :3]


def hexof(rgb):
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in rgb)


def describe(rgb):
    """One line for a colour: hex, hue, saturation, value, and the two differences that name a cast."""
    r, g, b = (float(v) for v in rgb)
    h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    return f"{hexof(rgb)}  hue {h * 360:5.1f}  sat {s:.2f}  val {v:.2f}  R-G {r - g:+5.1f}  B-G {b - g:+5.1f}"


def waviness(patch, window=9):
    """(horizontal lines, vertical lines) of a patch: how far the row means, and the column means, of its
    luminance stand off their running mean over `window` pixels, as a percentage of the mean luminance.
    A wall of courses waves in its rows only; a grid of square tiles waves in both."""
    lum = patch @ LUMA

    def off(v):
        smooth = np.convolve(np.pad(v, window // 2, mode="edge"), np.ones(window) / window, mode="valid")
        return float((v - smooth).std() / v.mean() * 100)

    return off(lum.mean(axis=1)), off(lum.mean(axis=0))


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    px = read(argv[1])
    print(f"{argv[1]}: {px.shape[1]}x{px.shape[0]}")
    for box in argv[2:]:
        x0, y0, x1, y1 = (int(v) for v in box.split(","))
        patch = px[y0:y1, x0:x1]
        rows, cols = waviness(patch) if min(patch.shape[:2]) >= 9 else (float("nan"), float("nan"))
        print(f"  {box:>19}  {describe(patch.reshape(-1, 3).mean(axis=0))}  "
              f"lines: horizontal {rows:.1f}%  vertical {cols:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
