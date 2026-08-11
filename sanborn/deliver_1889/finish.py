"""Finish pass: make unmapped canvas read as blank paper, then tint water.

The compositor fills canvas with the edition's RAW mean paper tone, but the
sheets are rendered through flatten_illumination, so their paper ends up
lighter than that mean. The unmapped south-west bay quadrant therefore
shows as a flat grey rectangle that reads as a defect rather than as the
honest 'this edition did not map here' it actually is. Repaint uncovered
canvas with the composite's own paper median so it reads as blank paper.
No content is added - the area stays empty and is disclosed in the caption.
"""
import cv2, numpy as np, json, sys
sys.path.insert(0, "/home/user/claude-code/sanborn")

SP = "/tmp/claude-0/-home-user-claude-code/2bd63ebc-a879-5d86-b98a-dc1ab929f20f/scratchpad/sanborn"
png = f"{SP}/deliver/1889/galveston_1889_downtown_wharf.png"
m = json.load(open(f"{SP}/deliver/1889/downtown_wharf_meta.json"))
x0, y0, x1, y1 = m["crop"]
img = cv2.imread(png)
cov = cv2.imread(f"{SP}/build/1889/coverage_mask.png", cv2.IMREAD_GRAYSCALE)[y0:y1, x0:x1]

c = img[cov > 0].reshape(-1, 3).astype(np.int16)
mx, mn = c.max(1), c.min(1)
paper = (mx > 170) & ((mx - mn) < 45) & ((c[:, 2] - c[:, 0]) > 20)
med = np.median(c[paper], axis=0)
print("composite paper median BGR:", med, " canvas before:",
      np.median(img[cov == 0].reshape(-1, 3), axis=0))
img[cov == 0] = med.astype(np.uint8)
cv2.imwrite(png, img)
print("uncovered canvas repainted to paper median "
      f"({100.0*(cov == 0).mean():.2f}% of the frame)")
