#!/usr/bin/env python3
"""Install managed assets without overwriting local customizations."""
import argparse
import hashlib
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

SOURCE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SOURCE / "assets/scripts"))
from pm_runtime import VERSION, atomic_write, create_config


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def install(root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    manifest_path = root / ".pm-workflow/installed.json"
    previous = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    tracked = previous.get("files", {})
    mapping = {}
    for folder, target in [("workflows", ".agents/workflows"), ("references", ".agents/references"),
                           ("scripts", "scripts"), ("templates", "templates")]:
        for path in (SOURCE / "assets" / folder).glob("*"):
            if not path.is_file(): continue
            dest = str(Path(target) / path.name)
            if path.name == "启动原型导出服务.command": dest = path.name
            if path.name == "pencil-draw-prompt.md": dest = "scripts/" + path.name
            if path.name == "关键点.md": dest = path.name
            mapping[dest] = path
    mapping[".mcp.json.example"] = SOURCE / "assets/config/mcp.json.example"
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    conflicts = []
    for rel, src in mapping.items():
        dest = root / rel
        current, incoming = digest(dest), digest(src)
        if current == incoming:
            tracked[rel] = incoming
            continue
        if current is not None and current != tracked.get(rel):
            proposal = root / ".pm-workflow/updates" / rel
            proposal.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, proposal)
            conflicts.append(rel)
            continue
        if current is not None:
            backup = root / ".handoff/skill-backups" / stamp / rel
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(dest, backup)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        tracked[rel] = incoming
    atomic_write(manifest_path, json.dumps({"version": VERSION, "files": tracked,
                                           "pending_updates": conflicts}, ensure_ascii=False, indent=2))
    ignore = root / ".gitignore"
    text = ignore.read_text(encoding="utf-8") if ignore.exists() else ""
    for entry in ["/.pm-workflow/", "/scripts/pm-runtime-config.js", "/scripts/.venv/", "/.handoff/"]:
        if entry not in text.splitlines(): text = text.rstrip() + "\n" + entry + "\n"
    atomic_write(ignore, text)
    config = create_config(root)
    print(f"PM Workflow {VERSION} 已初始化，项目 {config['project_id']}")
    if conflicts:
        print("保留本地定制文件，新版本放在 .pm-workflow/updates/，请对照合并：")
        for item in conflicts: print("  " + item)
    print("环境检查：python3 scripts/start_service.py --check")
    print("首次安装：python3 scripts/start_service.py --install")
    print("启动预览：python3 scripts/start_service.py --serve")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", default=".")
    install(parser.parse_args().project)
