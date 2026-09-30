#!/usr/bin/env python3
"""Run The Truman Show simulation with a live dashboard.

Examples:
  python run.py                                 # SDK backend, 8 days, dashboard at http://127.0.0.1:8765
  python run.py --backend cli                   # use the Claude Code CLI as the model backend
  python run.py --backend mock --rounds 4       # offline smoke test
  python run.py --replay runs/episode.jsonl     # re-watch a finished episode
"""
from __future__ import annotations

import argparse
import asyncio
import os
import threading
import time
import webbrowser

from truman_show.backends import make_backend
from truman_show.bus import EventBus
from truman_show.engine import Config, Episode
from truman_show.server import serve


def main() -> None:
    ap = argparse.ArgumentParser(description="The Truman Show, with AI agents.")
    ap.add_argument("--backend", choices=["sdk", "cli", "mock"], default="sdk")
    ap.add_argument("--rounds", type=int, default=Config.rounds, help="days in the season")
    ap.add_argument("--turns", type=int, default=Config.turns_per_scene, help="dialogue turns per scene")
    ap.add_argument("--threshold", type=int, default=Config.threshold, help="suspicion needed for a declaration to count")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--log", default=None, help="events.jsonl path (default runs/<timestamp>.jsonl)")
    ap.add_argument("--replay", default=None, help="serve a finished events.jsonl instead of running")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--no-server", action="store_true", help="run headless, just write the log")
    args = ap.parse_args()

    if args.replay:
        bus = EventBus()
        bus.load(args.replay)
        serve(bus, args.host, args.port, replay=True)
        url = f"http://{args.host}:{args.port}/"
        print(f"Replaying {args.replay} at {url}")
        if not args.no_browser:
            webbrowser.open(url)
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            return

    os.makedirs("runs", exist_ok=True)
    log = args.log or os.path.join("runs", time.strftime("%Y%m%d-%H%M%S") + ".jsonl")
    bus = EventBus(log)
    if not args.no_server:
        serve(bus, args.host, args.port)
        url = f"http://{args.host}:{args.port}/"
        print(f"Dashboard: {url}")
        if not args.no_browser:
            threading.Timer(0.8, lambda: webbrowser.open(url)).start()
    print(f"Event log: {log}")

    backend = make_backend(args.backend)
    episode = Episode(backend, bus, Config(rounds=args.rounds, turns_per_scene=args.turns, threshold=args.threshold))
    asyncio.run(episode.run())
    print("Done. Re-watch with: python run.py --replay", log)
    if not args.no_server:
        print("Dashboard stays up; Ctrl-C to quit.")
        try:
            while True:
                time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
