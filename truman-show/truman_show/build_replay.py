"""Bake an events.jsonl file into a single self-contained replay HTML file."""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


def build(events_path: str, out_path: str) -> None:
    events = [json.loads(l) for l in open(events_path, encoding="utf-8") if l.strip()]
    html = open(os.path.join(HERE, "dashboard.html"), encoding="utf-8").read()
    payload = json.dumps(events, ensure_ascii=False).replace("<", "\\u003c")  # no '<' can end or reopen the script
    html = html.replace("<!--TRUMAN_MODE-->", f"<script>window.__TRUMAN_REPLAY__=true;window.__TRUMAN_EVENTS__={payload}</script>")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("<!doctype html>\n" + html)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("usage: python -m truman_show.build_replay events.jsonl replay.html")
        sys.exit(1)
    build(sys.argv[1], sys.argv[2])
    print("wrote", sys.argv[2])
