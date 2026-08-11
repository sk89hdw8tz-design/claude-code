"""Edge-knot audit for 1889 (playbook s3), pitch fixed at the edition
nominal, phase anchored on each unit's interior lines."""
import sys, json
sys.path.insert(0, "/home/user/claude-code/sanborn")
import numpy as np
import config, coverage_prior as cov, run_build as rb, registration as reg

YEAR = "1889"
ed = config.EDITIONS[YEAR]
config.STREET_ORIGIN = ed["street_origin"]
k = config.DETECT_WIDTH / ed["native_size"][0]
config.PITCH_AV_DETECT = ed["pitch_av"] * k
config.PITCH_ST_DETECT = ed["pitch_st"] * k
NOM = {"x": ed["pitch_av"], "y": ed["pitch_st"]}
prop, raw = {}, {}
for key, unit in cov.COVERAGE[YEAR].items():
    path = rb.sheet_path(YEAR, unit["file"])
    dreg = unit.get("detect_region") or unit["region"]
    want_v, want_h = cov.expected_detect_lines(YEAR, key)
    det = reg.detect_sheet_grid(path, region=dreg,
                               want_v=len(want_v), want_h=len(want_h))
    raw[key] = {}
    for axis, dkey, ids in (("x", "v_lines_native", want_v),
                            ("y", "h_lines_native", want_h)):
        pos = list(det.get(dkey) or [])
        raw[key][axis] = {"ids": ids, "pos": [round(p, 1) for p in pos]}
        if len(pos) != len(ids) or len(ids) < 3:
            print(f"  {key:>3} {axis}: {len(pos)} lines vs {len(ids)} ids — skip")
            continue
        idsA = np.array(ids, float); posA = np.array(pos, float)
        inner = list(range(1, len(ids) - 1))
        off = float(np.mean(posA[inner] - NOM[axis] * idsA[inner]))
        sp = np.diff(posA) / np.diff(idsA)
        out = f"  {key:>3} {axis}: spacings {[round(float(s)) for s in sp]} |"
        for i in (0, len(ids) - 1):
            pred = off + NOM[axis] * idsA[i]
            bias = pos[i] - pred
            tag = "OVERRIDE" if abs(bias) > 12 else "ok"
            out += f" id{ids[i]} det {pos[i]:7.1f} pred {pred:7.1f} bias {bias:+6.1f}[{tag}]"
            if abs(bias) > 12:
                prop.setdefault(key, {}).setdefault(axis, {})[str(ids[i])] = round(pred, 1)
        print(out)
json.dump(prop, open("proposed_overrides.json", "w"), indent=1)
json.dump(raw, open("edge_audit_raw.json", "w"), indent=1)
n = sum(len(v) for u in prop.values() for v in u.values())
print(f"\n{n} overrides across {len(prop)} units")
print(json.dumps(prop, indent=1))
