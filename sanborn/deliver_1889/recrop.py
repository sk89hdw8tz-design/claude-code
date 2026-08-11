"""Tighten the delivered crop to drawn content and refresh the overview.

The driver's crop uses fixed fractional margins, which on 1889 overshoots
into a band below 25th that no sheet draws and into one-sided bay. Trim
rows/cols where coverage collapses, but KEEP the western columns that
carry sheet 2's wharf ink (Morgan/Central Line wharves, Navigation Slip).
"""
import cv2, numpy as np, json, sys
sys.path.insert(0, "/home/user/claude-code/sanborn")
import config
img = cv2.imread("build/1889/galveston_1889_composite.tif", cv2.IMREAD_COLOR)
mask = cv2.imread("build/1889/coverage_mask.png", cv2.IMREAD_GRAYSCALE)
m = json.load(open("deliver/1889/downtown_wharf_meta.json"))
bx0, by0, bx1, by1 = m["crop"] if "crop_base" not in m else m["crop_base"]
sub = mask[by0:by1, bx0:bx1] > 0
rows = sub.mean(axis=1)
r0 = int(np.argmax(rows > 0.55)); r1 = len(rows) - int(np.argmax(rows[::-1] > 0.55))
g = cv2.cvtColor(img[by0:by1, bx0:bx1], cv2.COLOR_BGR2GRAY)
ink = (g < 150)
inkcol = np.array([ink[:, x:x+50].sum() for x in range(0, ink.shape[1]-50, 50)])
first = next((i*50 for i, v in enumerate(inkcol) if v > 900), 0)
c0 = max(0, first - 60)
x0, y0, x1, y1 = bx0+c0, by0+r0, bx1, by0+r1
tile = img[y0:y1, x0:x1]; s2 = mask[y0:y1, x0:x1]
cover = 100.0*(s2 > 0).mean()
print(f"crop [{x0},{y0},{x1},{y1}] -> {tile.shape[1]}x{tile.shape[0]} "
      f"aspect {tile.shape[1]/tile.shape[0]:.3f} coverage {cover:.2f}%")
cv2.imwrite("deliver/1889/galveston_1889_downtown_wharf.png", tile)
m.update({"crop_base": [bx0,by0,bx1,by1], "crop": [x0,y0,x1,y1],
          "size": [tile.shape[1], tile.shape[0]], "coverage_pct": cover})
json.dump(m, open("deliver/1889/downtown_wharf_meta.json","w"), indent=1)
sc = 1500.0/tile.shape[1]
cv2.imwrite("qc/ov1889.jpg", cv2.resize(tile, None, fx=sc, fy=sc,
            interpolation=cv2.INTER_AREA), [cv2.IMWRITE_JPEG_QUALITY, 88])
