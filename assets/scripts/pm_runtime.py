"""Project-scoped configuration shared by the preview server and launcher."""
import hashlib
import json
import os
import secrets
import socket
import tempfile
from pathlib import Path

VERSION = "3.0.0"


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix="." + path.name + ".", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(content)
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def load_config(root):
    config = json.loads((Path(root) / ".pm-workflow/runtime.json").read_text(encoding="utf-8"))
    if Path(config["root"]).resolve() != Path(root).resolve():
        raise RuntimeError("项目目录已移动，请重新运行 Skill 初始化脚本")
    return config


def create_config(root):
    root = Path(root).resolve()
    path = root / ".pm-workflow/runtime.json"
    if path.exists():
        config = json.loads(path.read_text(encoding="utf-8"))
    else:
        config = {}
    if config.get("root") != str(root):
        with socket.socket() as a, socket.socket() as b:
            a.bind(("127.0.0.1", 0)); b.bind(("127.0.0.1", 0))
            ports = (a.getsockname()[1], b.getsockname()[1])
        config = {"root": str(root), "project_id": hashlib.sha256(str(root).encode()).hexdigest()[:16],
                  "token": secrets.token_urlsafe(32), "port": ports[0], "launcher_port": ports[1]}
    config["version"] = VERSION
    atomic_write(path, json.dumps(config, ensure_ascii=False, indent=2))
    path.chmod(0o600)
    browser = {"projectId": config["project_id"], "token": config["token"],
               "server": "http://127.0.0.1:" + str(config["port"]),
               "launcher": "http://127.0.0.1:" + str(config["launcher_port"])}
    atomic_write(root / "scripts/pm-runtime-config.js", "window.PM_RUNTIME = " + json.dumps(browser) + ";\n")
    return config


def origin_allowed(origin, port):
    return origin in (None, "null", "http://127.0.0.1:" + str(port), "http://localhost:" + str(port))


def valid_token(headers, config):
    return (headers.get("X-PM-Project") == config["project_id"] and
            secrets.compare_digest(headers.get("X-PM-Token", ""), config["token"]))
