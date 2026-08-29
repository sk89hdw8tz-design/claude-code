#!/usr/bin/env python3
"""Hook target for .claude/settings.json (SubagentStart/SubagentStop):
appends one JSON line per event to state/events.jsonl, rolled at 5 MB per
the cloud addendum. Safe to call with anything: never fails the hook.

    python tools/ledger.py event start|stop
"""
import json
import os
import sys
import time

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PATH = os.path.join(REPO, "state", "events.jsonl")

def main():
    try:
        os.makedirs(os.path.dirname(PATH), exist_ok=True)
        if os.path.exists(PATH) and os.path.getsize(PATH) > 5_000_000:
            os.replace(PATH, PATH + ".1")      # single-generation roll
        payload = ""
        if not sys.stdin.isatty():
            try:
                payload = sys.stdin.read(4000)
            except Exception:
                payload = ""
        rec = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "argv": sys.argv[1:], }
        if payload:
            try:
                rec["hook"] = json.loads(payload)
            except Exception:
                rec["raw"] = payload[:500]
        with open(PATH, "a") as f:
            f.write(json.dumps(rec) + "\n")
    except Exception:
        pass
    return 0

if __name__ == "__main__":
    sys.exit(main())
