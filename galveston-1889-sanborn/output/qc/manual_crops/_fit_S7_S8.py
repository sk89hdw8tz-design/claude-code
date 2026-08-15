#!/usr/bin/env python
"""Fit a 4-parameter similarity to the S7|S8 manual correspondences and emit JSON."""
import json, math
import numpy as np

W8 = 212.7  # sheet-8 pixels for a 70-ft avenue (mean of 6 measurements on Av. E and Av. F)

# name, a_x (S7 AvD west property line), a_y (S7 street prop line),
#       s8 AvD east property line x, b_y (S8 street prop line)
ROWS = [
    ('19th St N', 3119.12, 132.50, 296.44, 103.34, 4.5, 'high'),
    ('19th St S', 3119.98, 379.59, 294.40, 349.05, 5.0, 'high'),
    ('20th St N', 3117.73, 1299.30, 294.97, 1275.01, 5.0, 'high'),
    ('21st St N', 3102.60, 2457.02, 293.06, 2439.05, 4.5, 'high'),
    ('21st St S', 3099.49, 2699.28, 294.47, 2685.99, 5.0, 'high'),
    ('22nd St N', 3095.30, 3617.60, 293.55, 3606.94, 6.5, 'medium'),
    ('22nd St S', 3092.83, 3862.05, 293.94, 3852.55, 5.0, 'medium'),
]

A = np.array([[r[1], r[2]] for r in ROWS], float)
B = np.array([[r[3] - W8, r[4]] for r in ROWS], float)
sig = np.array([r[5] for r in ROWS], float)

# weighted 4-parameter similarity  b = s*R*a + t
w = 1.0 / sig ** 2
M, rhs = [], []
for (ax, ay), (bx, by), wi in zip(A, B, w):
    s = math.sqrt(wi)
    M.append([ax * s, -ay * s, s, 0]); rhs.append(bx * s)
    M.append([ay * s, ax * s, 0, s]); rhs.append(by * s)
p, *_ = np.linalg.lstsq(np.array(M), np.array(rhs), rcond=None)
a, b, tx, ty = p
scale = math.hypot(a, b)
rot = math.degrees(math.atan2(b, a))
pred = np.stack([a * A[:, 0] - b * A[:, 1] + tx, b * A[:, 0] + a * A[:, 1] + ty], 1)
res = np.linalg.norm(pred - B, axis=1)
print('scale %.6f  rot %.4f deg  tx %.2f  ty %.2f' % (scale, rot, tx, ty))
print('rms %.2f  max %.2f' % (math.sqrt((res ** 2).mean()), res.max()))
for r, rr, pr, bb in zip(ROWS, res, pred, B):
    print('  %-10s resid %5.2f  (%.1f sigma)   pred(%.1f,%.1f) obs(%.1f,%.1f)'
          % (r[0], rr, rr / r[5], pr[0], pr[1], bb[0], bb[1]))

# water-main check under this fit
for nm, ay, by in (('20th St 10in W.P.', 1375.71, 1381.13), ('22nd St W.P.', 3730.07, 3748.35)):
    py = b * 3200.0 + a * ay + ty
    print('%s: S7 y=%.1f -> pred S8 y=%.1f, observed %.1f, resid %+.1f'
          % (nm, ay, py, by, by - py))
