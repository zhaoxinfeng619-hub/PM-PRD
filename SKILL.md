---
name: edu-pm-workflow
description: "Product management workflow for demand discovery, HTML PRDs, interactive prototypes, flowcharts, acceptance checklists, and data reports. Use for product requirements and continuing these PM deliverables."
---

# PM Workflow Skill

Turn product requirements into reviewable artifacts across business domains. Preserve the user's scope and confirmed decisions.

## Start and route

1. Check the requested project's `.agents/workflows/` and `.pm-workflow/installed.json`. Read only the workflow needed below. Existing files alone do not prove that required helpers are present.
2. If the project has not been initialized or required helpers are missing, run this skill's `scripts/initialize.py --project <project-directory>` with Python 3.9+. The shell wrapper `scripts/init.sh` uses the current directory.
3. Updates preserve local customizations and place incoming alternatives in `.pm-workflow/updates/`. Report pending merges. Read project-specific overrides in `.agents/workflows/local-overrides.md` when present.
4. Initialization does not install browser dependencies or a background service. Follow the README for environment checking and explicit setup when screenshots or local saving are needed.

| Task | Workflow installed in the project | Output |
|---|---|---|
| Demand discovery | `.agents/workflows/edu-pm-demand.md` | `[需求名]/需求挖掘/[需求名]-需求洞察.html` |
| PRD, prototype, flowcharts, iteration | `.agents/workflows/edu-pm-prd.md` | HTML files in `需求文档/`, `原型/`, `流程图/` |
| Acceptance checklist | `.agents/workflows/edu-pm-acceptance.md` | `[需求名]/验收清单/[需求名]-验收清单.html` |
| Data analysis | `.agents/workflows/edu-pm-data-analysis.md` | `[需求名]/数据分析/[需求名]-数据分析.html` |

## Shared rules

- Reuse one top-level directory per requirement, with the same name across stages. Create only needed output subdirectories, including `流程图截图/` when exporting flowcharts.
- Keep shared tooling in `scripts/`, workflow definitions in `.agents/workflows/`, implementation references in `.agents/references/`, and local runtime state in `.pm-workflow/`.
- Use HTML unless the user requests another format. Preserve actual product terminology, platform, assets and visual conventions.
- Distinguish verified facts, user reports, hypotheses and explicitly authorized demo data. Never invent feedback, data sources or market statistics to fill a report.
- Ask about missing decisions that affect scope, behavior or acceptance. Previously confirmed decisions stay confirmed.
- Keep PRD, prototypes and flowcharts consistent. Check downstream acceptance items and metric definitions when their source requirements change.
- Preserve source documents and personal screenshots. Never delete a diagram to hide rendering errors, discard missing images silently, or overwrite a guessed target.
- Use the shared document runtime and screenshot service. Copying to external documents depends on their paste behavior; verify the first target used.
- Save success means the local file was written and backed up. Ask the assistant to read the saved file before claiming related artifacts have been synchronized.
- Verify changed interactions and report what was actually exercised. Do not claim a workflow is complete based only on HTML existence or a button label.

## Optional references

The PRD workflow links to `pm-artifacts.md` for the shared editor, preview, copy and export contract, `pm-diagrams.md` for screenflow and sequence diagrams, and `pm-pencil.md` only when Pencil design is requested. Do not load optional design tooling for ordinary document work.

## Customization

Edit the skill's `assets/workflows/` or shared components only when updating the reusable skill itself. Keep project preferences in `.agents/workflows/local-overrides.md`; upgrades leave this file untouched. Local runtime configuration contains credentials and must not be published.
