#!/bin/bash
set -euo pipefail
SKILL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
python3 "$SKILL_SCRIPT_DIR/initialize.py" --project "$PWD"
if [ "${EDU_PM_INSTALL_EXPORT_WATCHER:-0}" = "1" ] && [ "${EDU_PM_SKIP_EXPORT_WATCHER:-0}" != "1" ]; then
  bash scripts/setup_prototype_export_watcher.sh "$PWD"
fi
