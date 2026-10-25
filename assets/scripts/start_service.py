#!/usr/bin/env python3
"""Cross-platform dependency check, explicit installation and service start."""
import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from urllib.request import urlopen
from pm_runtime import load_config

ROOT = Path(__file__).resolve().parent.parent
PYTHON = ROOT / "scripts/.venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
PLAYWRIGHT_VERSION = "1.60.0"
CHECK = 'from playwright.sync_api import sync_playwright\nwith sync_playwright() as p:\n b=p.chromium.launch(headless=True); b.close()'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--install", action="store_true")
    parser.add_argument("--serve", action="store_true")
    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()
    if sys.version_info < (3, 9): raise SystemExit("需要 Python 3.9 或更高版本")
    config = load_config(ROOT)
    if args.install:
        if not PYTHON.exists(): subprocess.run([sys.executable, "-m", "venv", str(PYTHON.parent.parent)], check=True)
        print("正在安装截图依赖，首次下载 Chromium 可能需要数分钟", flush=True)
        subprocess.run([str(PYTHON), "-m", "pip", "install", "playwright==" + PLAYWRIGHT_VERSION], check=True)
        subprocess.run([str(PYTHON), "-m", "playwright", "install", "chromium"], check=True)
    if not PYTHON.exists(): raise SystemExit("缺少截图环境，请运行 python3 scripts/start_service.py --install")
    result = subprocess.run([str(PYTHON), "-c", CHECK], capture_output=True, text=True)
    if result.returncode:
        print(result.stderr, file=sys.stderr)
        raise SystemExit("浏览器未就绪，请重新运行 --install；Linux 可能需要安装浏览器系统依赖")
    if not args.serve:
        print("环境检查通过：Python、Playwright、Chromium 均可运行")
        return
    try:
        with urlopen(f"http://127.0.0.1:{config['port']}/api/health", timeout=1) as r: health = json.load(r)
    except Exception:
        health = None
    if health:
        if (health.get("project_id") != config["project_id"] or health.get("read_only") != args.read_only):
            raise SystemExit("端口被其他项目或不同运行模式占用，请先停止对应服务")
        print("当前项目服务已经运行")
        return
    if args.host not in ("127.0.0.1", "localhost", "::1") and not args.read_only:
        raise SystemExit("局域网监听只允许 --read-only 模式")
    env = dict(os.environ, PM_SERVER_HOST=args.host, PM_READ_ONLY="1" if args.read_only else "0")
    os.execve(str(PYTHON), [str(PYTHON), str(ROOT / "scripts/prototype_server.py")], env)


if __name__ == "__main__": main()
