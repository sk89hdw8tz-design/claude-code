#!/usr/bin/env python3
"""Render this project's Claude Code session transcript as a PDF.

    python3 tools/transcript.py --jsonl <session>.jsonl --out transcript.pdf

The session log interleaves four things: what the human typed, what the
assistant wrote back, the 636 tool calls between them, and a large volume of
automated traffic (tool results, hook feedback, task notifications, system
reminders). Reproducing all of it is neither readable nor useful -- the tool
results alone are 37 MB -- so this keeps the conversation and reduces the
machinery to one line per call, and labels the automated messages rather than
passing them off as things the user said.
"""
import argparse
import datetime
import html
import json
import os
import re
import subprocess
import sys

CHROME = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"

# a user record is not necessarily a person talking
AUTOMATED = [
    (re.compile(r"^\s*<command-name>", re.S), "slash command"),
    (re.compile(r"<local-command-caveat>", re.S), "local command output"),
    (re.compile(r"Stop hook feedback", re.S), "stop hook"),
    (re.compile(r"<task-notification>", re.S), "background task"),
    (re.compile(r"^\s*<system-reminder>", re.S), "system reminder"),
    (re.compile(r"Caveat: The messages below", re.S), "local command output"),
]


def blocks(m):
    c = m.get("content")
    if isinstance(c, str):
        return [{"type": "text", "text": c}]
    return [b for b in (c or []) if isinstance(b, dict)]


def classify(text):
    for rx, label in AUTOMATED:
        if rx.search(text):
            return label
    return None


def strip_noise(text):
    text = re.sub(r"<system-reminder>.*?</system-reminder>", "", text, flags=re.S)
    text = re.sub(r"<local-command-[a-z]+>.*?</local-command-[a-z]+>", "",
                  text, flags=re.S)
    return text.strip()


def tool_line(b):
    """One readable line for a tool call."""
    name = b.get("name", "?")
    i = b.get("input") or {}
    for key in ("command", "file_path", "pattern", "prompt", "description",
                "skill", "query", "url"):
        if key in i and isinstance(i[key], str):
            v = " ".join(i[key].split())
            if len(v) > 160:
                v = v[:157] + "..."
            return name, v
    return name, ""


def md(text):
    import markdown
    return markdown.markdown(text, extensions=["fenced_code", "tables",
                                               "sane_lists", "nl2br"])


def when(ts):
    if not ts:
        return ""
    try:
        d = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        return d.strftime("%d %b %Y, %H:%M UTC")
    except Exception:
        return ts


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--jsonl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--title", default="Galveston Sanborn mosaics")
    a = ap.parse_args()

    turns, stamps = [], []
    n_tools = 0
    with open(a.jsonl) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                d = json.loads(line)
            except Exception:
                continue
            if d.get("type") not in ("user", "assistant"):
                continue
            m = d.get("message") or {}
            ts = d.get("timestamp")
            if ts:
                stamps.append(ts)
            bs = blocks(m)
            if m.get("role") == "user":
                if any(b.get("type") == "tool_result" for b in bs):
                    continue
                raw = "\n".join(b.get("text", "") for b in bs
                                if b.get("type") == "text")
                if not raw.strip():
                    continue
                label = classify(raw)
                body = strip_noise(raw)
                if not body:
                    continue
                turns.append(("user", label, body, ts))
            else:
                for b in bs:
                    if b.get("type") == "text" and b.get("text", "").strip():
                        turns.append(("assistant", None, b["text"], ts))
                    elif b.get("type") == "tool_use":
                        n_tools += 1
                        turns.append(("tool",) + tool_line(b) + (ts,))

    # collapse runs of tool calls into one block
    out, run = [], []
    for t in turns:
        if t[0] == "tool":
            run.append(t)
        else:
            if run:
                out.append(("tools", run))
                run = []
            out.append(t)
    if run:
        out.append(("tools", run))

    parts = []
    said = sum(1 for t in turns if t[0] == "user" and t[1] is None)
    parts.append(f"""<div class="cover">
      <div class="kicker">Claude Code session transcript</div>
      <h1>{html.escape(a.title)}</h1>
      <p class="sub">Full-city Sanborn fire-insurance mosaics of Galveston,
      Texas, 1899 and 1912</p>
      <table class="meta">
        <tr><td>Session</td><td>{html.escape(os.path.basename(a.jsonl).replace('.jsonl',''))}</td></tr>
        <tr><td>Period</td><td>{when(min(stamps))} &ndash; {when(max(stamps))}</td></tr>
        <tr><td>Messages from the user</td><td>{said}</td></tr>
        <tr><td>Replies</td><td>{sum(1 for t in turns if t[0]=='assistant')}</td></tr>
        <tr><td>Tool calls</td><td>{n_tools}</td></tr>
      </table>
      <p class="note"><strong>What this contains.</strong> Every message the
      user sent and every reply, in order. Tool calls are listed one line each,
      by name and argument. What is <em>not</em> here: the output those calls
      returned, which runs to 37&nbsp;MB and is machine traffic rather than
      conversation. Messages generated by the harness rather than typed by the
      user &mdash; hook feedback, background-task notifications, slash commands
      &mdash; are kept in place and labelled as such.</p>
    </div><div class="pb"></div>""")

    last_day = None
    for item in out:
        if item[0] == "tools":
            rows = "".join(
                f'<div class="t"><span class="tn">{html.escape(n)}</span>'
                f'<span class="tv">{html.escape(v)}</span></div>'
                for _k, n, v, _ts in item[1])
            parts.append(f'<div class="tools"><div class="tools-h">'
                         f'{len(item[1])} tool call{"s" if len(item[1])>1 else ""}'
                         f'</div>{rows}</div>')
            continue
        role, label, body, ts = item
        day = (ts or "")[:10]
        if day and day != last_day:
            parts.append(f'<div class="day">{html.escape(day)}</div>')
            last_day = day
        if role == "user":
            tag = ("<span class='auto'>" + html.escape(label) + "</span>"
                   if label else "<span class='who'>User</span>")
            cls = "msg user" + (" automated" if label else "")
            parts.append(f'<div class="{cls}"><div class="hd">{tag}'
                         f'<span class="ts">{when(ts)}</span></div>'
                         f'<div class="bd">{md(body)}</div></div>')
        else:
            parts.append(f'<div class="msg asst"><div class="hd">'
                         f'<span class="who">Claude</span>'
                         f'<span class="ts">{when(ts)}</span></div>'
                         f'<div class="bd">{md(body)}</div></div>')

    css = """
    @page { size: A4; margin: 16mm 15mm 18mm; }
    body { font: 10.5pt/1.55 "DejaVu Serif", Georgia, serif; color:#1b1b1b;
           margin:0; }
    .pb { page-break-after: always; }
    .cover { padding-top: 38mm; }
    .cover .kicker { font: 600 9pt/1 "DejaVu Sans", sans-serif;
        letter-spacing:.16em; text-transform:uppercase; color:#8a6d3b; }
    .cover h1 { font: 700 30pt/1.15 "DejaVu Serif", Georgia, serif;
        margin:.35em 0 .1em; }
    .cover .sub { font-size:12pt; color:#555; margin:0 0 2.2em; }
    table.meta { border-collapse:collapse; font: 9.5pt/1.5 "DejaVu Sans",sans-serif;
        margin-bottom:2.4em; }
    table.meta td { border-top:1px solid #ddd; padding:.42em 1.6em .42em 0; }
    table.meta td:first-child { color:#777; white-space:nowrap; }
    .cover .note { font-size:9.5pt; color:#444; background:#faf7f0;
        border-left:3px solid #c9a227; padding:.9em 1.1em; }
    .day { font: 600 8.5pt/1 "DejaVu Sans",sans-serif; letter-spacing:.14em;
        color:#999; text-transform:uppercase; margin:2.2em 0 .9em;
        border-bottom:1px solid #e6e6e6; padding-bottom:.5em; }
    .msg { margin:0 0 1.35em; page-break-inside:auto; }
    .hd { font:600 8.5pt/1 "DejaVu Sans",sans-serif; letter-spacing:.06em;
        margin-bottom:.5em; }
    .who { color:#1a5490; text-transform:uppercase; letter-spacing:.12em; }
    .msg.asst .who { color:#8a6d3b; }
    .auto { color:#999; text-transform:uppercase; letter-spacing:.12em;
        font-weight:600; }
    .ts { color:#bbb; font-weight:400; margin-left:.9em; letter-spacing:0; }
    .msg.user > .bd { background:#f2f6fa; border-left:3px solid #1a5490;
        padding:.75em 1em; border-radius:2px; }
    .msg.automated > .bd { background:#f7f7f7; border-left:3px solid #d5d5d5;
        color:#666; font-size:9.5pt; padding:.6em .9em; }
    .bd > *:first-child { margin-top:0; } .bd > *:last-child { margin-bottom:0; }
    .bd h1,.bd h2,.bd h3 { font-size:12pt; margin:1.1em 0 .45em; }
    .bd p { margin:.55em 0; } .bd li { margin:.25em 0; }
    .bd code { font:9pt "DejaVu Sans Mono",monospace; background:#f0f0f0;
        padding:.08em .3em; border-radius:2px; }
    .bd pre { background:#f6f6f4; border:1px solid #e6e6e2; border-radius:3px;
        padding:.7em .85em; overflow-wrap:break-word; white-space:pre-wrap;
        page-break-inside:avoid; }
    .bd pre code { background:none; padding:0; font-size:8.5pt; }
    .bd table { border-collapse:collapse; font-size:9pt; margin:.7em 0;
        width:100%; }
    .bd th,.bd td { border:1px solid #ddd; padding:.34em .55em; text-align:left; }
    .bd th { background:#f4f4f2; }
    .tools { margin:0 0 1.35em; padding:.5em .8em; background:#fcfcfa;
        border:1px solid #ececE6; border-radius:3px; page-break-inside:avoid; }
    .tools-h { font:600 7.5pt/1 "DejaVu Sans",sans-serif; letter-spacing:.13em;
        text-transform:uppercase; color:#aaa; margin-bottom:.45em; }
    .t { font:8.5pt/1.45 "DejaVu Sans Mono",monospace; color:#666;
         overflow-wrap:anywhere; }
    .tn { color:#8a6d3b; font-weight:700; margin-right:.6em; }
    """
    doc = ("<!doctype html><html><head><meta charset='utf-8'>"
           f"<title>{html.escape(a.title)}</title><style>{css}</style>"
           "</head><body>" + "".join(parts) + "</body></html>")

    htmlpath = os.path.splitext(a.out)[0] + ".html"
    open(htmlpath, "w").write(doc)
    print(f"wrote {htmlpath} ({os.path.getsize(htmlpath)/1e6:.1f} MB)")

    r = subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-sandbox",
                        "--no-pdf-header-footer",
                        f"--print-to-pdf={a.out}", "file://" + os.path.abspath(htmlpath)],
                       capture_output=True, text=True)
    if not os.path.exists(a.out):
        sys.exit("chrome failed:\n" + r.stderr[-2000:])
    print(f"wrote {a.out} ({os.path.getsize(a.out)/1e6:.1f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
