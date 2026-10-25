#!/usr/bin/env python3
"""Project-specific optional launcher; dependencies must be installed explicitly."""
import json
import os
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.request import urlopen
from pm_runtime import load_config, origin_allowed, valid_token

PROJECT_DIR = Path(os.environ.get("PROTOTYPE_PROJECT_DIR") or Path(__file__).resolve().parent.parent).resolve()
CONFIG = load_config(PROJECT_DIR)
PORT = CONFIG["launcher_port"]
PYTHON = PROJECT_DIR / "scripts/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
process = None


def launch():
    global process
    try:
        with urlopen(f"http://127.0.0.1:{CONFIG['port']}/api/health", timeout=1) as response: state = json.load(response)
    except Exception:
        state = None
    if state:
        if state.get("project_id") != CONFIG["project_id"] or state.get("read_only"):
            raise RuntimeError("端口对应其他项目或只读模式")
        return "already-running"
    if process and process.poll() is None: return "launching"
    if not PYTHON.exists(): raise RuntimeError("依赖未安装，请先运行 python3 scripts/start_service.py --install")
    log = PROJECT_DIR / ".pm-workflow/service.log"
    with log.open("ab") as stream:
        process = subprocess.Popen([str(PYTHON), str(PROJECT_DIR / "scripts/start_service.py"), "--serve"],
                                   cwd=PROJECT_DIR, stdout=stream, stderr=stream)
    time.sleep(.2)
    if process.poll() not in (None, 0): raise RuntimeError("启动失败，详见 .pm-workflow/service.log")
    return "launching"


class Handler(BaseHTTPRequestHandler):
    def allowed_origin(self):
        return origin_allowed(self.headers.get("Origin"), PORT) or self.headers.get("Origin") in (
            f"http://127.0.0.1:{CONFIG['port']}", f"http://localhost:{CONFIG['port']}")

    def reply(self, data, code=200):
        raw = json.dumps(data).encode()
        self.send_response(code)
        origin = self.headers.get("Origin")
        if origin and self.allowed_origin(): self.send_header("Access-Control-Allow-Origin", origin)
        self.send_header("Access-Control-Allow-Headers", "Content-Type, X-PM-Project, X-PM-Token")
        self.send_header("Access-Control-Allow-Methods", "POST, OPTIONS")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers(); self.wfile.write(raw)

    def do_OPTIONS(self): self.reply({}, 200 if self.allowed_origin() else 403)

    def do_POST(self):
        if self.path != "/api/launch" or not self.allowed_origin() or not valid_token(self.headers, CONFIG):
            self.reply({"error":"项目身份校验失败"}, 403); return
        try:
            self.reply({"ok":True, "status":launch(), "project_id":CONFIG["project_id"]})
        except Exception as exc: self.reply({"error":str(exc)}, 400)


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", PORT), Handler).serve_forever()
