#!/usr/bin/env python3
"""Regenerate DASHBOARD.html from state/dashboard.json (self-contained, no deps).

    python3 tools/dashboard.py

Coordinator utilities (update state and re-render in one command):

    python3 tools/dashboard.py --set-limits FIVE_HOUR WEEKLY
        FIVE_HOUR / WEEKLY are each either an integer token ceiling
        (e.g. 500000) or a percentage already used (e.g. 35%), or
        "null" to clear. Writes tokens.limits and recomputes
        tokens.used_pct.

    python3 tools/dashboard.py --wave ID --status STATUS \
        [--running N] [--done N] [--rejected N] [--gate TEXT]
        Updates one row in team.waves (status: planned|running|done|
        rejected). Stamps "started" the first time a wave goes to
        running, and "finished" the first time it goes to done or
        rejected.
"""
import argparse
import datetime
import html
import json
import os

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATE_PATH = os.path.join(REPO, "state", "dashboard.json")
OUT_PATH = os.path.join(REPO, "DASHBOARD.html")

esc = html.escape

STATUS_CHIP = {
    "planned": "#eee",
    "running": "#ffe08a",
    "done": "#bfe6cc",
    "rejected": "#f7b8b8",
}


def now_utc():
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%MZ"
    )


def load_data():
    with open(STATE_PATH) as f:
        return json.load(f)


def save_data(d):
    with open(STATE_PATH, "w") as f:
        json.dump(d, f, indent=1, ensure_ascii=False)
        f.write("\n")


def cell(v):
    return esc("null" if v is None else str(v))


def render_tasks(tasks):
    mark = {"PASSED": "✓", "ACTIVE": "→", "QC": "→", "BLOCKED": "✗"}
    rows = []
    for t in tasks:
        rows.append(
            f"<tr class='{t['status'].replace(' ', '_')}'>"
            f"<td>{mark.get(t['status'], '○')} {esc(t['name'])}</td>"
            f"<td>{esc(t['status'])}</td>"
            f"<td><div class='bar'><i style='width:{t['pct']}%'></i></div>"
            f"{t['pct']}%</td>"
            f"<td>{esc(', '.join(t['deps']) or '—')}</td>"
            f"<td>{esc(t['accept'])}</td></tr>"
        )
    return "".join(rows)


def render_kpis(k):
    return "".join(
        f"<tr><td>{esc(kk.replace('_', ' '))}</td><td>{cell(v)}</td></tr>"
        for kk, v in k.items()
    )


def render_agents(agents):
    rows = "".join(
        f"<tr><td>{esc(a.get('id', ''))}</td><td>{esc(a.get('task', ''))}"
        f"</td><td>{esc(a.get('status', ''))}</td>"
        f"<td>{esc(a.get('start', ''))}</td><td>{esc(a.get('end', ''))}</td>"
        f"<td>{esc(a.get('evidence', ''))}</td>"
        f"<td>{esc(a.get('result', ''))}</td></tr>"
        for a in agents
    )
    return rows or "<tr><td colspan=7>none used</td></tr>"


def render_milestones(milestones):
    return "".join(
        f"<li><b>{esc(m['t'])}</b> {esc(m['event'])}</li>"
        for m in milestones[-10:]
    )


def render_decisions(decisions):
    return "".join(
        f"<h4>{esc(kk)}</h4><ul>"
        f"{''.join(f'<li>{esc(x)}</li>' for x in v)}</ul>"
        for kk, v in decisions.items()
    )


def render_team(team):
    """Task board: one row per wave, with a status chip."""
    if not team:
        return ""
    waves = team.get("waves", [])
    rows = []
    for w in waves:
        status = w.get("status", "")
        chip_color = STATUS_CHIP.get(status, "#eee")
        workers = ", ".join(
            f"{esc(str(m))}×{n}" for m, n in w.get("workers", {}).items()
        ) or "—"
        chip = (
            f"<span class='chip' style='background:{chip_color}'>"
            f"{esc(status)}</span>"
        )
        rows.append(
            "<tr>"
            f"<td>{esc(w.get('id', ''))}</td>"
            f"<td>{esc(w.get('name', ''))}</td>"
            f"<td>{chip}</td>"
            f"<td>{esc(w.get('lead_model', ''))}</td>"
            f"<td>{workers}</td>"
            f"<td>{esc(w.get('auditor_model', ''))}</td>"
            f"<td>{w.get('running', 0)}/{w.get('done', 0)}/"
            f"{w.get('rejected', 0)}</td>"
            f"<td>{esc(w.get('gate', '') or '—')}</td>"
            f"<td>{esc(w.get('started', '') or '—')}</td>"
            f"<td>{esc(w.get('finished', '') or '—')}</td>"
            "</tr>"
        )
    body = "".join(rows) or "<tr><td colspan=10>no waves</td></tr>"
    return f"""<div class="box" style="grid-column:1/3">
<h3>TEAM / TASK BOARD</h3>
<div><b>director:</b> {esc(team.get('director', ''))}</div>
<table><tr><th>wave</th><th>name</th><th>status</th><th>lead</th>
<th>workers</th><th>auditor</th><th>running/done/rejected</th>
<th>gate</th><th>started</th><th>finished</th></tr>{body}</table>
</div>"""


def render_eta_chain(eta):
    """Small per-wave estimate table plus a headline, if per_wave is set."""
    per_wave = eta.get("per_wave") if eta else None
    if not per_wave:
        return ""
    rows = "".join(
        f"<tr><td>{esc(w.get('id', ''))}</td>"
        f"<td>{w.get('estimate_min', '')} min</td>"
        f"<td>{esc(w.get('basis', '') or '—')}</td></tr>"
        for w in per_wave
    )
    chain = eta.get("chain_remaining_min")
    finish = eta.get("finish_utc", "")
    headline = (
        f"<b>{cell(chain)} min remaining</b> · finish ~"
        f"{esc(finish or 'n/a')} · confidence {esc(eta.get('confidence', ''))}"
    )
    return f"""<div class="box"><h3>ETA CHAIN</h3>
<div>{headline}</div>
<table><tr><th>wave</th><th>estimate</th><th>basis</th></tr>{rows}</table>
</div>"""


def millions(n):
    if n is None:
        return "n/a"
    return f"{n / 1_000_000:.1f}M"


def render_pct_bar(label, used_pct, limit, total):
    if limit is None:
        return f"<div><b>{esc(label)}:</b> limit not set</div>"
    pct = used_pct if used_pct is not None else 0
    pct_disp = min(max(pct, 0), 100)
    return (
        f"<div><b>{esc(label)}:</b> {millions(total)} / "
        f"{millions(limit)} tokens "
        f"<div class='bar wide'><i style='width:{pct_disp}%'></i></div>"
        f"{cell(used_pct)}%</div>"
    )


def render_tokens(tokens):
    if not tokens:
        return ""
    by_wave = tokens.get("by_wave", [])
    rows = "".join(
        f"<tr><td>{esc(w.get('id', ''))}</td>"
        f"<td>{esc(w.get('model_mix', ''))}</td>"
        f"<td>{millions(w.get('subagent_tokens'))}</td></tr>"
        for w in by_wave
    )
    limits = tokens.get("limits", {}) or {}
    used_pct = tokens.get("used_pct", {}) or {}
    total = tokens.get("total")
    note = limits.get("note")
    note_html = f"<div class='note'>{esc(note)}</div>" if note else ""
    return f"""<div class="box" style="grid-column:1/3">
<h3>TOKENS</h3>
<div class="hero" style="font-size:16px">
<div>total<b>{millions(total)}</b></div>
<div>director context<b>{millions(tokens.get('director_context_tokens'))}</b>
</div></div>
{render_pct_bar('5-hour window', used_pct.get('five_hour'),
                limits.get('five_hour'), total)}
{render_pct_bar('weekly window', used_pct.get('weekly'),
                limits.get('weekly'), total)}
{note_html}
<table><tr><th>wave</th><th>model mix</th><th>subagent tokens</th></tr>
{rows}</table>
</div>"""


def build_html(d):
    p, pr, e, k = d["project"], d["progress"], d["eta"], d["kpi"]
    rows = render_tasks(d["tasks"])
    kpis = render_kpis(k)
    agents = render_agents(d["agents"])
    ms = render_milestones(d["milestones"])
    dec = render_decisions(d["decisions"])
    team_html = render_team(d.get("team"))
    eta_chain_html = render_eta_chain(e)
    tokens_html = render_tokens(d.get("tokens"))
    qc = k.get("qc_pass_rate")
    qc = "n/a" if qc is None else f"{qc}%"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>1912 Galveston Sanborn dashboard</title>
<style>body{{font:14px system-ui,sans-serif;margin:20px;color:#222;background:#faf8f2}}h1{{margin:0 0 4px}}
.hero{{display:flex;gap:30px;font-size:22px;margin:10px 0 18px}}.hero b{{font-size:30px;display:block}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}.box{{background:#fff;border:1px solid #ddd;border-radius:6px;padding:12px}}
table{{border-collapse:collapse;width:100%;font-size:13px}}td,th{{border-bottom:1px solid #eee;padding:4px 6px;text-align:left;vertical-align:top}}
.bar{{display:inline-block;width:80px;height:8px;background:#eee;vertical-align:middle;margin-right:4px}}.bar i{{display:block;height:8px;background:#3a7}}
.bar.wide{{width:160px}}
tr.ACTIVE td{{background:#fff7d6}}tr.PASSED td{{color:#286}}tr.BLOCKED td{{background:#fdd}}.status{{padding:2px 8px;border-radius:4px;background:#ffe08a}}
.chip{{padding:1px 8px;border-radius:10px;font-size:12px}}
.note{{color:#777;font-size:12px;margin:4px 0}}
h4{{margin:8px 0 2px}}ul{{margin:2px 0 6px 18px}}</style></head><body>
<h1>1912 GALVESTON SANBORN <span class="status">{esc(p['status'])}</span></h1>
<div>stage: <b>{esc(p['stage'])}</b> · commit {esc(p['git_commit'])} · started {esc(p['start_time'])} · updated {esc(p['last_update'])}</div>
<div class="hero"><div>overall<b>{pr['overall_pct']}%</b></div><div>ETA<b>{esc(e['range'])}</b>confidence {esc(e['confidence'])}</div><div>QC pass rate<b>{qc}</b></div>
<div>tasks<b>{pr['tasks_done']}/{pr['tasks_total']}</b></div></div>
<div class="grid">
<div class="box"><h3>CURRENT</h3><div><b>objective:</b> {esc(p['objective'])}</div><div><b>current task:</b> {esc(pr['current_task'])} ({pr['stage_pct']}%)</div>
<div><b>next task:</b> {esc(pr['next_task'])}</div><div><b>blockers:</b> {esc(', '.join(pr['blockers']) or 'none')}</div><div><b>ETA note:</b> {esc(e['reason'])}</div>
<div><b>tokens/cost:</b> {esc(d.get('tokens_cost', 'not available'))}</div></div>
<div class="box"><h3>QUALITY KPIs</h3><table>{kpis}</table></div>
<div class="box" style="grid-column:1/3"><h3>PIPELINE / TASKS</h3><table><tr><th>task</th><th>status</th><th>progress</th><th>depends on</th><th>acceptance</th></tr>{rows}</table></div>
<div class="box"><h3>AGENTS</h3><table><tr><th>id</th><th>task</th><th>status</th><th>start</th><th>end</th><th>evidence</th><th>result</th></tr>{agents}</table></div>
<div class="box"><h3>RECENT MILESTONES</h3><ul>{ms}</ul></div>
{team_html}
{eta_chain_html}
{tokens_html}
<div class="box" style="grid-column:1/3"><h3>DECISIONS / RISKS</h3>{dec}</div>
</div></body></html>"""


def write_html(d):
    with open(OUT_PATH, "w") as f:
        f.write(build_html(d))
    print("wrote DASHBOARD.html")


def parse_limit_arg(value, total):
    """Return (limit_tokens, used_pct) for one --set-limits argument."""
    if value.lower() in ("null", "none", "-"):
        return None, None
    if value.endswith("%"):
        return None, float(value[:-1])
    limit = int(value)
    used_pct = round(total / limit * 100, 1) if limit else None
    return limit, used_pct


def cmd_set_limits(d, five_hour_arg, weekly_arg):
    tokens = d.setdefault("tokens", {})
    total = tokens.get("total", 0)
    limits = tokens.setdefault("limits", {})
    used_pct = tokens.setdefault("used_pct", {})
    five_limit, five_pct = parse_limit_arg(five_hour_arg, total)
    week_limit, week_pct = parse_limit_arg(weekly_arg, total)
    limits["five_hour"] = five_limit
    limits["weekly"] = week_limit
    used_pct["five_hour"] = five_pct
    used_pct["weekly"] = week_pct
    return d


def cmd_update_wave(d, wave_id, status, running, done, rejected, gate):
    team = d.setdefault("team", {"director": "", "waves": []})
    waves = team.setdefault("waves", [])
    wave = next((w for w in waves if w.get("id") == wave_id), None)
    if wave is None:
        raise SystemExit(f"no wave with id {wave_id!r} in team.waves")
    if status is not None:
        wave["status"] = status
        if status == "running" and not wave.get("started"):
            wave["started"] = now_utc()
        if status in ("done", "rejected") and not wave.get("finished"):
            wave["finished"] = now_utc()
    if running is not None:
        wave["running"] = running
    if done is not None:
        wave["done"] = done
    if rejected is not None:
        wave["rejected"] = rejected
    if gate is not None:
        wave["gate"] = gate
    return d


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--set-limits", nargs=2, metavar=("FIVE_HOUR", "WEEKLY"))
    parser.add_argument("--wave", metavar="ID")
    parser.add_argument("--status", choices=["planned", "running", "done", "rejected"])
    parser.add_argument("--running", type=int)
    parser.add_argument("--done", type=int)
    parser.add_argument("--rejected", type=int)
    parser.add_argument("--gate")
    return parser.parse_args()


def main():
    args = parse_args()
    d = load_data()
    changed = False
    if args.set_limits:
        d = cmd_set_limits(d, args.set_limits[0], args.set_limits[1])
        changed = True
    if args.wave:
        d = cmd_update_wave(
            d, args.wave, args.status, args.running, args.done,
            args.rejected, args.gate,
        )
        changed = True
    if changed:
        save_data(d)
    write_html(d)


if __name__ == "__main__":
    main()
