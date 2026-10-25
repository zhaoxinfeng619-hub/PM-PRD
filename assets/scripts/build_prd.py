#!/usr/bin/env python3
"""Assemble a PRD from actual content and reusable document components."""
import argparse
import json
import shutil
import uuid
from pathlib import Path
from pm_runtime import atomic_write

ROOT = Path(__file__).resolve().parent.parent


def build(content, pages, output, overwrite=False):
    output = Path(output).resolve()
    output.relative_to(ROOT)
    if output.parent.name != "需求文档": raise ValueError("输出必须位于需求文档目录")
    seen = set()
    for page in pages:
        if page["value"] in seen: raise ValueError("页面编号重复")
        seen.add(page["value"])
        if page["w"] <= 0 or page["h"] <= 0: raise ValueError("页面尺寸必须大于零")
        if not isinstance(page["url"], str) or not page["url"].startswith("../原型/"):
            raise ValueError("页面应使用同需求原型的相对路径")
        target = (output.parent / page["url"].split("#")[0].split("?")[0]).resolve()
        target.relative_to(output.parent.parent)
        if not target.is_file(): raise FileNotFoundError(str(target))
    template = (ROOT / "templates/prd-shell.html").read_text(encoding="utf-8")
    values = {"CONTENT": content, "PAGES": json.dumps(pages, ensure_ascii=False).replace("<", "\\u003c"),
              "SERVICE": (ROOT / "scripts/prototype-export-client.js").read_text(encoding="utf-8"),
              "DOCUMENT": (ROOT / "scripts/pm-document.js").read_text(encoding="utf-8")}
    for key, value in values.items(): template = template.replace("{{" + key + "}}", value)
    if output.exists():
        if not overwrite: raise FileExistsError("文件已存在，复核后使用 --overwrite，覆盖前自动备份")
        backup = ROOT / ".handoff/build-backups" / uuid.uuid4().hex / output.name
        backup.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(output, backup)
    atomic_write(output, template)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--content", required=True)
    parser.add_argument("--pages", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(build(Path(args.content).read_text(encoding="utf-8"), json.loads(Path(args.pages).read_text(encoding="utf-8")), args.output, args.overwrite))
