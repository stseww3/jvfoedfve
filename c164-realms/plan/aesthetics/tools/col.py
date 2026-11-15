"""Mean colour of boxes in a picture: python col.py <picture> name=x0,y0,x1,y1 ...  (hex, hue, saturation, value, Rec.601 luma)."""
import sys, colorsys
import numpy as np
from PIL import Image

def stat(a, box, name):
    x0, y0, x1, y1 = box
    p = a[y0:y1, x0:x1].reshape(-1, 3)
    m = p.mean(0)
    h, s, v = colorsys.rgb_to_hsv(*(m / 255))
    lum = (0.299 * p[:, 0] + 0.587 * p[:, 1] + 0.114 * p[:, 2]) / 255
    hexa = '#%02x%02x%02x' % tuple(int(x) for x in m)
    print(f'  {name:26s} {hexa}  hue {h*360:5.1f}  sat {s*100:4.1f}%  val {v*100:4.1f}%  luma {lum.mean():.2f}  (p5 {np.percentile(lum,5):.2f} p95 {np.percentile(lum,95):.2f})')

if __name__ == '__main__':
    a = np.asarray(Image.open(sys.argv[1]).convert('RGB')).astype(float)
    print(sys.argv[1], a.shape[1], 'x', a.shape[0])
    for arg in sys.argv[2:]:
        name, box = arg.split('=')
        stat(a, [int(v) for v in box.split(',')], name)
