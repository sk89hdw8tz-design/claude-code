#!/usr/bin/env python3
"""Regenerate DASHBOARD.html from state/dashboard.json (self-contained, no deps).

    python3 tools/dashboard.py
"""
import json, os, html
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
d = json.load(open(os.path.join(REPO, "state", "dashboard.json")))
p, pr, e, k = d["project"], d["progress"], d["eta"], d["kpi"]
esc = html.escape
def cell(v): return esc("null" if v is None else str(v))
mark = {"PASSED": "✓", "ACTIVE": "→", "QC": "→", "BLOCKED": "✗"}
rows = "".join(
    f"<tr class='{t['status'].replace(' ','_')}'><td>{mark.get(t['status'],'○')} {esc(t['name'])}</td>"
    f"<td>{esc(t['status'])}</td><td><div class='bar'><i style='width:{t['pct']}%'></i></div>{t['pct']}%</td>"
    f"<td>{esc(', '.join(t['deps']) or '—')}</td><td>{esc(t['accept'])}</td></tr>" for t in d["tasks"])
kpis = "".join(f"<tr><td>{esc(kk.replace('_',' '))}</td><td>{cell(v)}</td></tr>" for kk, v in k.items())
agents = "".join(f"<tr><td>{esc(a.get('id',''))}</td><td>{esc(a.get('task',''))}</td><td>{esc(a.get('status',''))}</td>"
                 f"<td>{esc(a.get('start',''))}</td><td>{esc(a.get('end',''))}</td><td>{esc(a.get('evidence',''))}</td><td>{esc(a.get('result',''))}</td></tr>"
                 for a in d["agents"]) or "<tr><td colspan=7>none used</td></tr>"
ms = "".join(f"<li><b>{esc(m['t'])}</b> {esc(m['event'])}</li>" for m in d["milestones"][-10:])
dec = "".join(f"<h4>{esc(kk)}</h4><ul>{''.join(f'<li>{esc(x)}</li>' for x in v)}</ul>" for kk, v in d["decisions"].items())
qc = k.get("qc_pass_rate"); qc = "n/a" if qc is None else f"{qc}%"
out = f"""<!doctype html><html><head><meta charset="utf-8"><title>1912 Galveston Sanborn dashboard</title>
<style>body{{font:14px system-ui,sans-serif;margin:20px;color:#222;background:#faf8f2}}h1{{margin:0 0 4px}}
.hero{{display:flex;gap:30px;font-size:22px;margin:10px 0 18px}}.hero b{{font-size:30px;display:block}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.box{{background:#fff;border:1px solid #ddd;border-radius:6px;padding:12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #eee;padding:4px 6px;text-align:left;vertical-align:top}}
.bar{{display:inline-block;width:80px;height:8px;background:#eee;vertical-align:middle;margin-right:4px}}.bar i{{display:block;height:8px;background:#3a7}}
tr.ACTIVE td{{background:#fff7d6}}tr.PASSED td{{color:#286}}tr.BLOCKED td{{background:#fdd}}.status{{padding:2px 8px;border-radius:4px;background:#ffe08a}}
h4{{margin:8px 0 2px}}ul{{margin:2px 0 6px 18px}}</style></head><body>
<h1>1912 GALVESTON SANBORN <span class="status">{esc(p['status'])}</span></h1>
<div>stage: <b>{esc(p['stage'])}</b> · commit {esc(p['git_commit'])} · started {esc(p['start_time'])} · updated {esc(p['last_update'])}</div>
<div class="hero"><div>overall<b>{pr['overall_pct']}%</b></div><div>ETA<b>{esc(e['range'])}</b>confidence {esc(e['confidence'])}</div><div>QC pass rate<b>{qc}</b></div>
<div>tasks<b>{pr['tasks_done']}/{pr['tasks_total']}</b></div></div>
<div class="grid">
<div class="box"><h3>CURRENT</h3><div><b>objective:</b> {esc(p['objective'])}</div><div><b>current task:</b> {esc(pr['current_task'])} ({pr['stage_pct']}%)</div>
<div><b>next task:</b> {esc(pr['next_task'])}</div><div><b>blockers:</b> {esc(', '.join(pr['blockers']) or 'none')}</div><div><b>ETA note:</b> {esc(e['reason'])}</div>
<div><b>tokens/cost:</b> {esc(d.get('tokens_cost','not available'))}</div></div>
<div class="box"><h3>QUALITY KPIs</h3><table>{kpis}</table></div>
<div class="box" style="grid-column:1/3"><h3>PIPELINE / TASKS</h3><table><tr><th>task</th><th>status</th><th>progress</th><th>depends on</th><th>acceptance</th></tr>{rows}</table></div>
<div class="box"><h3>AGENTS</h3><table><tr><th>id</th><th>task</th><th>status</th><th>start</th><th>end</th><th>evidence</th><th>result</th></tr>{agents}</table></div>
<div class="box"><h3>RECENT MILESTONES</h3><ul>{ms}</ul></div>
<div class="box" style="grid-column:1/3"><h3>DECISIONS / RISKS</h3>{dec}</div>
</div></body></html>"""
open(os.path.join(REPO, "DASHBOARD.html"), "w").write(out)
print("wrote DASHBOARD.html")
