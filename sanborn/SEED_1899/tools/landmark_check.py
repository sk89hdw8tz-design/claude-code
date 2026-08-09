"""Independent registration check — the anti-circular gate.

Given ground-truth landmarks (the SAME physical object located in two
sheets' native pixel frames) and a build's per-sheet transforms, map each
landmark through both transforms and compare. The disagreement IS that
pair's registration error at that point.

Why this and not fit residuals: a uniform per-sheet bias is absorbed by the
translation term, so residuals stay small while the sheet's content sits far
out of place. In the prior 1899 build residuals stayed under 15 px while a
sheet's content was 114 px out, and every automated gate passed. This check
cannot be fooled that way because it never consults the fit's own objective —
only where real ink lands.

Usage:
    python3 landmark_check.py landmarks.json registration.json [--max 8]

registration.json must supply, per unit, piecewise knots:
    units[key]["knots"] = {"xkn": [...], "xkg": [...],
                           "ykn": [...], "ykg": [...]}
where *kn are native positions and *kg the global positions they map to.
A build using a pure similarity transform can emit two knots per axis.
"""
import json
import sys


def pw_fwd(v, native, glob):
    """Piecewise-linear map native -> global, extrapolating on end slopes."""
    if len(native) < 2:
        raise ValueError("need >= 2 knots per axis")
    pairs = sorted(zip(native, glob))
    n = [p[0] for p in pairs]
    g = [p[1] for p in pairs]
    out = []
    for x in v:
        if x <= n[0]:
            s = (g[1] - g[0]) / (n[1] - n[0])
            out.append(g[0] + (x - n[0]) * s)
        elif x >= n[-1]:
            s = (g[-1] - g[-2]) / (n[-1] - n[-2])
            out.append(g[-1] + (x - n[-1]) * s)
        else:
            for i in range(len(n) - 1):
                if n[i] <= x <= n[i + 1]:
                    t = (x - n[i]) / (n[i + 1] - n[i])
                    out.append(g[i] + t * (g[i + 1] - g[i]))
                    break
    return out


def to_global(unit, xy):
    k = unit["knots"]
    gx = pw_fwd([xy[0]], k["xkn"], k["xkg"])[0]
    gy = pw_fwd([xy[1]], k["ykn"], k["ykg"])[0]
    return gx, gy


def main(landmarks_path, reg_path, max_ok=8.0):
    lm = json.load(open(landmarks_path))
    reg = json.load(open(reg_path))
    units = reg["units"]
    rows, missing = [], []
    for f in lm["features"]:
        a, b = f["sheet_a"], f["sheet_b"]
        if a not in units or b not in units:
            missing.append(f["id"])
            continue
        ax, ay = to_global(units[a], f["a_xy"])
        bx, by = to_global(units[b], f["b_xy"])
        dx, dy = bx - ax, by - ay
        rows.append({"id": f["id"], "pair": f"{a}|{b}",
                     "boundary": f.get("boundary", ""),
                     "dx": round(dx, 1), "dy": round(dy, 1),
                     "step": round((dx * dx + dy * dy) ** 0.5, 1),
                     "confidence": f.get("confidence", "")})
    rows.sort(key=lambda r: -r["step"])
    print(f"{'landmark':28} {'pair':8} {'dx':>8} {'dy':>8} {'step':>8}")
    for r in rows:
        flag = "  <== OVER" if r["step"] > max_ok else ""
        print(f"{r['id'][:28]:28} {r['pair']:8} {r['dx']:8.1f} {r['dy']:8.1f} "
              f"{r['step']:8.1f}{flag}")
    if rows:
        steps = sorted(r["step"] for r in rows)
        med = steps[len(steps) // 2]
        over = sum(1 for s in steps if s > max_ok)
        print(f"\nlandmarks: {len(rows)}   median step {med:.1f} px   "
              f"max {steps[-1]:.1f} px   over {max_ok:g} px: {over}")
        # per-pair summary: a whole-pair offset means that pair is misregistered
        by_pair = {}
        for r in rows:
            by_pair.setdefault(r["pair"], []).append(r)
        print("\nper pair (a consistent dx/dy across a pair's landmarks means")
        print("that pair carries a rigid offset — the fixable kind):")
        for p, rs in sorted(by_pair.items()):
            mdx = sum(r["dx"] for r in rs) / len(rs)
            mdy = sum(r["dy"] for r in rs) / len(rs)
            spread = max(r["step"] for r in rs) - min(r["step"] for r in rs)
            print(f"  {p:8} n={len(rs)}  mean dx={mdx:+7.1f} dy={mdy:+7.1f}  "
                  f"spread={spread:5.1f}")
    if missing:
        print(f"\nlandmarks skipped (unit not in this build): {missing}")
    return 0 if rows and max(r["step"] for r in rows) <= max_ok else 1


if __name__ == "__main__":
    mx = 8.0
    if "--max" in sys.argv:
        mx = float(sys.argv[sys.argv.index("--max") + 1])
    sys.exit(main(sys.argv[1], sys.argv[2], mx))
