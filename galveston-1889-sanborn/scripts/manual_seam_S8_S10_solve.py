#!/usr/bin/env python3
"""Assemble the S8|S10 seam measurements and run the similarity self-check."""
import numpy as np
from manual_profile_s8_s10 import profile, peaks

STEP = 120


def scan_line(sheet, y0, y1, prom, pick, skip_x=()):
    """Return [(x_mid, y)] for the chosen printed line in each x window."""
    out = []
    for x in range(200, 3160, STEP):
        xm = x + STEP // 2
        if any(a <= xm <= b for a, b in skip_x):
            continue
        b_, v = profile(sheet, "row", x, x + STEP, y0, y1)
        p = peaks(b_, v, prom)
        y = pick(p)
        if y is not None:
            out.append((float(xm), float(y)))
    return out


def strongest(p):
    return max(p, key=lambda t: t[1])[0] if p else None


def outermost_strong(p, thr=55):
    q = [t for t in p if t[1] >= thr]
    return max(q, key=lambda t: t[0])[0] if q else None


def fitline(pts):
    x = np.array([p[0] for p in pts])
    y = np.array([p[1] for p in pts])
    A = np.vstack([x - x.mean(), np.ones(len(x))]).T
    sol, *_ = np.linalg.lstsq(A, y, rcond=None)
    resid = y - A @ sol
    return dict(slope=float(sol[0]), y0=float(sol[1]), xm=float(x.mean()),
                rms=float(np.sqrt((resid ** 2).mean())), n=len(x),
                maxres=float(np.abs(resid).max()))


def ev(f, x):
    return f["y0"] + f["slope"] * (x - f["xm"])


# Avenue corridors are excluded: no block frontage is drawn there.
AV_S8 = [(1085, 1299), (2086, 2300)]
AV_S10 = [(1093, 1308), (2104, 2320)]

lines = {}
lines["s8_north"] = fitline(scan_line("8", 3596, 3630, 35, outermost_strong, AV_S8))
lines["s8_south"] = fitline(scan_line("8", 3838, 3878, 60, strongest))
lines["s10_north"] = fitline(scan_line("10", 80, 120, 60, strongest))
lines["s10_south"] = fitline(scan_line("10", 328, 360, 35,
                                        lambda p: strongest([t for t in p if 339 <= t[0] <= 348]),
                                        AV_S10))

print("--- seam line fits (y = y0 + slope*(x - xm)) ---")
for k, f in lines.items():
    print(f"  {k:10s} n={f['n']:3d} y@x0={ev(f,0):9.2f} slope={f['slope']:+.5f} "
          f"rms={f['rms']:.2f} max={f['maxres']:.2f}")
print("  22nd St width S8  @x=500 :", round(ev(lines['s8_south'], 500) - ev(lines['s8_north'], 500), 2),
      " @x=2900 :", round(ev(lines['s8_south'], 2900) - ev(lines['s8_north'], 2900), 2))
print("  22nd St width S10 @x=500 :", round(ev(lines['s10_south'], 500) - ev(lines['s10_north'], 500), 2),
      " @x=2900 :", round(ev(lines['s10_south'], 2900) - ev(lines['s10_north'], 2900), 2))

# ---- vertical lines: x at the two seam latitudes (from manual_vline fits) ----
VLINES = {  # name: (s8 x@north, s8 x@south, s10 x@north, s10 x@south)
    "AvD_E":   (292.10, 291.44, 294.14, 296.18),
    "alDE_W":  (659.05, 658.51, 665.41, 665.34),
    "alDE_tee": (687.76, 685.88, 690.21, 691.25),
    "alDE_E":  (719.41, 719.24, 724.12, 725.46),
    "AvE_W":   (1085.33, 1085.17, 1090.89, 1092.11),
    "AvE_E":   (1298.44, 1298.34, 1306.89, 1307.58),
    "alEF_W":  (1662.16, 1661.51, 1676.47, 1676.40),
    "alEF_E":  (1724.60, 1724.78, 1737.16, 1737.54),
    "AvF_W":   (2085.83, 2084.84, 2104.14, 2104.15),
    "AvF_E":   (2300.38, 2300.80, 2320.50, 2320.35),
    "alFG_W":  (2662.63, 2662.28, 2687.81, 2687.55),
    "alFG_E":  (2723.65, 2723.61, 2743.05, 2744.38),
    "AvG_W":   (3087.10, 3087.11, 3108.14, 3109.52),
}


def corner(name, side):
    a8, s8, a10, s10 = VLINES[name]
    if side == "N":
        return (a8, ev(lines["s8_north"], a8)), (a10, ev(lines["s10_north"], a10))
    return (s8, ev(lines["s8_south"], s8)), (s10, ev(lines["s10_south"], s10))


def umeyama(A, B, w):
    """Similarity mapping B -> A (b on sheet 10 -> a on sheet 8), weighted."""
    w = np.asarray(w, float)
    w = w / w.sum()
    ma = (A * w[:, None]).sum(0)
    mb = (B * w[:, None]).sum(0)
    Ac, Bc = A - ma, B - mb
    C = (Bc * w[:, None]).T @ Ac
    U, S, Vt = np.linalg.svd(C)
    d = np.sign(np.linalg.det(U @ Vt))
    R = (U @ np.diag([1, d]) @ Vt).T
    varb = (w[:, None] * Bc ** 2).sum()
    s = (S[0] + d * S[1]) / varb
    t = ma - s * (R @ mb)
    return s, R, t


if __name__ == "__main__":
    import sys
    sel = eval(sys.argv[1]) if len(sys.argv) > 1 else None
    if sel:
        A, B, W, N = [], [], [], []
        for nm, side, unc in sel:
            (ax, ay), (bx, by) = corner(nm, side)
            A.append([ax, ay]); B.append([bx, by]); W.append(1.0 / unc ** 2)
            N.append(f"{nm}-{side}")
            print(f"{nm:9s} {side}  A=({ax:8.2f},{ay:8.2f})  B=({bx:8.2f},{by:8.2f})  u={unc}")
        A, B = np.array(A), np.array(B)
        s, R, t = umeyama(A, B, W)
        pred = (s * (R @ B.T).T) + t
        res = np.linalg.norm(pred - A, axis=1)
        rot = np.degrees(np.arctan2(R[1, 0], R[0, 0]))
        print(f"\nscale={s:.5f} rot={rot:+.4f} deg  t=({t[0]:.2f},{t[1]:.2f})")
        print(f"rms={np.sqrt((res**2).mean()):.2f}  max={res.max():.2f}")
        for n, r, u in zip(N, res, [x[2] for x in sel]):
            flag = "  <== OUTLIER" if r > 3 * u else ""
            print(f"   {n:14s} resid {r:5.2f} (stated {u}){flag}")
