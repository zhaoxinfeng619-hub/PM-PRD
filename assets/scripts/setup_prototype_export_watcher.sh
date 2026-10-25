#!/bin/bash
set -euo pipefail
PROJECT_PATH="$PWD"
if [ "$#" -gt 0 ]; then PROJECT_PATH="$1"; fi
if [ "$(uname -s)" != "Darwin" ]; then
  echo "自动启动器仅支持 macOS，其他系统请手动运行 start_service.py --serve"
  exit 0
fi
python3 - "$PROJECT_PATH" <<'PY'
import json, pathlib, plistlib, subprocess, sys
root = pathlib.Path(sys.argv[1]).resolve()
cfg = json.loads((root / '.pm-workflow/runtime.json').read_text())
label = 'com.pm-workflow.launcher.' + cfg['project_id']
destination = pathlib.Path.home() / 'Library/Application Support/pm-workflow' / cfg['project_id']
destination.mkdir(parents=True, exist_ok=True)
for name in ['prototype_launcher.py', 'pm_runtime.py']:
    (destination / name).write_bytes((root / 'scripts' / name).read_bytes())
plist = pathlib.Path.home() / 'Library/LaunchAgents' / (label + '.plist')
plist.parent.mkdir(parents=True, exist_ok=True)
settings = {'Label': label, 'ProgramArguments': [sys.executable, str(destination / 'prototype_launcher.py')],
            'EnvironmentVariables': {'PROTOTYPE_PROJECT_DIR': str(root)}, 'RunAtLoad': True,
            'KeepAlive': True, 'ThrottleInterval': 30,
            'StandardOutPath': str(destination / 'launcher.log'),
            'StandardErrorPath': str(destination / 'launcher-error.log')}
plist.write_bytes(plistlib.dumps(settings))
uid = subprocess.check_output(['id', '-u'], text=True).strip()
subprocess.run(['launchctl', 'bootout', 'gui/' + uid, str(plist)], capture_output=True)
subprocess.run(['launchctl', 'bootstrap', 'gui/' + uid, str(plist)], check=True)
print('已安装当前项目启动器：' + label)
print('停用命令：launchctl bootout gui/' + uid + ' "' + str(plist) + '"')
PY
