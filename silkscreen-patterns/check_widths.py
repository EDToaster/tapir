"""Raster check: share of ink/gap pixels in features narrower than ~0.2 mm."""
import sys, glob, io, numpy as np, cairosvg
from PIL import Image
from scipy.ndimage import binary_opening
PX = 20  # px per mm (0.05 mm)
yy, xx = np.mgrid[-2:3, -2:3]; disk = (xx**2 + yy**2) <= 4  # ~0.2 mm diameter
for f in sorted(glob.glob(sys.argv[1] + "/*.svg")):
    s = open(f).read().replace('<g clip-path', '<rect width="400" height="250" fill="#fff"/><g clip-path', 1)
    png = cairosvg.svg2png(bytestring=s.encode(), output_width=400 * PX)
    a = np.array(Image.open(io.BytesIO(png)).convert("L"))[100:-100, 100:-100] < 128
    thin_ink = (a & ~binary_opening(a, disk)).sum() / max(1, a.sum())
    thin_gap = (~a & ~binary_opening(~a, disk)).sum() / max(1, (~a).sum())
    print(f"{f.split('/')[-1]:32s} ink {a.mean()*100:5.1f}%  thin-ink {thin_ink*100:5.2f}%  thin-gap {thin_gap*100:5.2f}%", flush=True)
