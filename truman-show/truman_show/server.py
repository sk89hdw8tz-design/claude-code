"""Tiny stdlib web server: serves the dashboard and streams events over Server-Sent Events."""
from __future__ import annotations

import json
import os
import queue
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .bus import EventBus

HERE = os.path.dirname(os.path.abspath(__file__))
DASHBOARD = os.path.join(HERE, "dashboard.html")


def make_handler(bus: EventBus, replay: bool):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *a):  # quiet
            pass

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                body = b"<!doctype html>\n" + open(DASHBOARD, "rb").read()
                if replay:
                    body = body.replace(b"<!--TRUMAN_MODE-->", b"<script>window.__TRUMAN_REPLAY__=true</script>")
                self._send(200, "text/html; charset=utf-8", body)
            elif self.path == "/events.jsonl":
                data = "\n".join(json.dumps(e, ensure_ascii=False) for e in bus.events)
                self._send(200, "application/x-ndjson; charset=utf-8", data.encode())
            elif self.path.startswith("/events"):
                self._sse()
            else:
                self._send(404, "text/plain", b"not found")

        def _send(self, code, ctype, body):
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _sse(self):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            past, q = bus.subscribe()
            try:
                for ev in past:
                    self._write(ev)
                while True:
                    try:
                        ev = q.get(timeout=15)
                        self._write(ev)
                    except queue.Empty:
                        self.wfile.write(b": keepalive\n\n")
                        self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError, OSError):
                pass
            finally:
                bus.unsubscribe(q)

        def _write(self, ev):
            self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()

    return Handler


def serve(bus: EventBus, host: str = "127.0.0.1", port: int = 8765, replay: bool = False) -> ThreadingHTTPServer:
    srv = ThreadingHTTPServer((host, port), make_handler(bus, replay))
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv
