#!/usr/bin/env python3
"""robobase logsviz - Timeline visualization for DataChannel and ActionsQueue logs.

Usage:
    python viz.py -d /path/to/logs/2026-02-14T12:43:05 -p 5555
"""

import argparse
import json
import os
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import numpy as np

_state = {
    "logs_dir": None,
    "html_path": Path(__file__).parent / "index.html",
    "cache": {"DataChannel": {}, "ActionsQueue": {}},
}


def scan_logs(after=None):  # pylint: disable=too-many-branches
    """Scan log directories and return cached entries, optionally filtered by timestamp."""
    logs_dir = _state["logs_dir"]
    cache = _state["cache"]
    dc_dir = logs_dir / "DataChannel"
    aq_dir = logs_dir / "ActionsQueue"

    if dc_dir.exists():
        for entry in os.scandir(dc_dir):
            if not entry.name.endswith(".npz") or not entry.is_file():
                continue
            stem = entry.name[:-4]
            if stem in cache["DataChannel"]:
                continue
            try:
                data = np.load(entry.path, allow_pickle=True).item()
                keys = sorted(data.keys())
            except Exception:
                keys = []
            cache["DataChannel"][stem] = {
                "timestamp": stem,
                "keys": keys,
            }

    if aq_dir.exists():
        for entry in os.scandir(aq_dir):
            if not entry.name.endswith(".npz") or not entry.is_file():
                continue
            stem = entry.name[:-4]
            if stem in cache["ActionsQueue"]:
                continue
            try:
                data = np.load(entry.path, allow_pickle=True).item()
                action = data.get("action")
                action_name = (
                    str(action.name) if hasattr(action, "name") else str(action)
                )
                data_ts = data.get("data_ts")
                action_params = {}
                if hasattr(action, "parameters") and action.parameters is not None:
                    if isinstance(action.parameters, dict):
                        action_params = {
                            str(k): str(v) for k, v in action.parameters.items()
                        }
                    else:
                        action_params = str(action.parameters)
                cache["ActionsQueue"][stem] = {
                    "timestamp": stem,
                    "keys": sorted(data.keys()),
                    "action_name": action_name,
                    "action_params": action_params,
                    "data_ts": data_ts,
                }
            except Exception:
                cache["ActionsQueue"][stem] = {
                    "timestamp": stem,
                    "keys": [],
                    "action_name": "?",
                    "action_params": {},
                    "data_ts": None,
                }

    dc_items = cache["DataChannel"].values()
    aq_items = cache["ActionsQueue"].values()

    if after:
        dc_items = [e for e in dc_items if e["timestamp"] > after]
        aq_items = [e for e in aq_items if e["timestamp"] > after]

    return {
        "session": str(logs_dir),
        "DataChannel": sorted(dc_items, key=lambda x: x["timestamp"]),
        "ActionsQueue": sorted(aq_items, key=lambda x: x["timestamp"]),
    }


class Handler(BaseHTTPRequestHandler):
    """HTTP request handler for the logsviz web UI."""

    def do_GET(self):  # pylint: disable=invalid-name
        """Serve the HTML UI and the JSON data API."""
        parsed = urlparse(self.path)

        if parsed.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(_state["html_path"].read_bytes())

        elif parsed.path == "/api/data":
            params = parse_qs(parsed.query)
            after = params.get("after", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
            result = scan_logs(after=after)
            self.wfile.write(json.dumps(result).encode())

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, fmt, *args):  # pylint: disable=arguments-renamed,arguments-differ
        """Suppress default request logging."""


def main():
    """Parse arguments and start the logsviz HTTP server."""
    parser = argparse.ArgumentParser(description="robobase logsviz")
    parser.add_argument("-d", "--dir", required=True, help="Logs directory path")
    parser.add_argument("-p", "--port", type=int, default=5555, help="Server port")
    args = parser.parse_args()

    _state["logs_dir"] = Path(args.dir)

    if not _state["logs_dir"].exists():
        print(f"error: {_state['logs_dir']} does not exist")
        return

    server = HTTPServer(("localhost", args.port), Handler)
    print(f"logsviz running at http://localhost:{args.port}")
    print(f"watching: {_state['logs_dir']}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nshutting down")
        server.shutdown()


if __name__ == "__main__":
    main()
