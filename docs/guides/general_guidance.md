---
title: 'khive General Guidance'
by:   'khive Team'
created: '2025-04-05'
updated: '2025-04-18'
version: '2.4'
description: >
  Authoritative principles and workflow for khive, emphasising autonomous roles,
  Tauri architecture, CLI-first development, mandatory search citation,
  standardised templates, and rigorous quality gates:
---

```WARNING!!!
K.D KHIVE-DEV TEAM **MUST RETAIN FROM** EDITING THE FOLLOWING FOLDERS: 'docs/`
```

! WARNING: THIS DOCUMENT IS READ-ONLY

# project: lionagi

- _GitHub Owner:_ **khive-ai**
- _Repository:_ **khive.d**

---

# Team k.d

- _Orchestrator:_ **@khive-orchestrator**
- _Architect:_ **@khive-architect**
- _Researcher:_ **@khive-researcher**
- _Implementer:_ **@khive-implementer**
- _Quality Reviewer:_ **@khive-quality-reviewer**
- _Documenter:_ **@khive-documenter**

## Core Principles

1. **Autonomy & Specialisation** - each agent sticks to its stage of the golden
   path.
2. **Search-Driven Development (MANDATORY)** - run `khive search` **before**
   design/impl _Cite result IDs / links in specs, plans, PRs, commits._
3. **TDD & Quality** - >80 pct combined coverage (`khive ci --threshold 80` in
   CI).
4. **Clear Interfaces** - `shared-protocol` defines Rust ↔ TS contracts; Tauri
   commands/events are the API.
5. **GitHub Orchestration** - Issues & PRs are the single source of truth.
6. **Use local read/edit** - use native roo tools for reading and editing files
7. **Local CLI First** - prefer plain `git`, `gh`, `pnpm`, `cargo`, plus helper
   scripts (`khive-*`).
8. **Standardised Templates** - Create via CLI (`khive new-doc`) and should be
   **filled** and put under `docs/reports/...`
9. **Quality Gates** - CI + reviewer approval before merge.
10. **Know your issue** - always check the issue you are working on, use github
    intelligently, correct others mistakes and get everyone on the same page.

| code | template         | description           | folder         |
| ---- | ---------------- | --------------------- | -------------- |
| RR   | `RR-<issue>.md`  | Research Report       | `reports/rr/`  |
| TDS  | `TDS-<issue>.md` | Technical Design Spec | `reports/tds/` |
| IP   | `IP-<issue>.md`  | Implementation Plan   | `reports/ip/`  |
| TI   | `TI-<issue>.md`  | Test Implementation   | `reports/ti/`  |
| CRR  | `CRR-<pr>.md`    | Code Review Report    | `reports/crr/` |

if it's an issue needing zero or one pr, don't need to add suffix

**Example**

> khive new-doc RR 123 # RR = Research Report, this ->
> docs/reports/research/RR-123.md

if you are doing multiple pr's for the same issue, you need to add suffix

> _issue 150_ khive new-doc ID 150-pr1 # ID = Implementation plans, this ->
> docs/reports/plans/ID-150-pr1.md

> khive new-doc TDS 150-pr2

11. **Docs Mirror Reality** - update docs **after** Quality Review passes.

---

## Golden Path & Roles

| Stage          | Role                     | Primary Artifacts (template)                 | Search citation |
| -------------- | ------------------------ | -------------------------------------------- | --------------- |
| Research       | `khive-researcher`       | `RR-<issue>.md`                              | ✅              |
| Design         | `khive-architect`        | `TDS-<issue>.md`                             | ✅              |
| Implement      | `khive-implementer`      | `IP-<issue>.md`, `TI-<issue>.md`, code+tests | ✅              |
| Quality Review | `khive-quality-reviewer` | `CRR-<pr>.md` (optional) + GH review         | verifies        |
| Document       | `khive-documenter`       | Updated READMEs / guides                     | N/A             |

Each artifact must be committed before hand-off to the next stage.

## Team Roles

researcher · architect · implementer · quality-reviewer · documenter ·
orchestrator

## Golden Path

1. Research → 2. Design → 3. Implement → 4. Quality-Review → 5. Document → Merge

## Tooling Matrix

| purpose                   | local CLI                                 | GitHub MCP                                                                |
| ------------------------- | ----------------------------------------- | ------------------------------------------------------------------------- |
| clone / checkout / rebase | `git`                                     | —                                                                         |
| multi-file commit         | `git add -A && git commit`                | `mcp: github.push_files` (edge cases)                                     |
| open PR                   | `gh pr create` _or_ `create_pull_request` | `mcp: github.create_pull_request`                                         |
| comment / review          | `gh pr comment` _or_ `add_issue_comment`  | `mcp: github.add_issue_comment`, `mcp: github.create_pull_request_review` |
| CI status                 | `gh pr checks`                            | `mcp: github.get_pull_request_status`                                     |

_(CLI encouraged; MCP always available)_

## Validation Gates

- spec committed → CI green
- PR → Quality-Reviewer approves in coomments
- Orchestrator merges & tags

---

## Quality Gates (CI + Reviewer)

1. **Design approved** - TDS committed, search cited.
2. **Implementation ready** - IP & TI committed, PR opened, local tests pass.
3. **Quality review** - Reviewer approves, coverage ≥ 80 pct, citations
   verified.
4. **Docs updated** - Documenter syncs docs.
5. **Merge & clean** - PR merged, issue closed, branch deleted.

---
