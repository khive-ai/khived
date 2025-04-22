---
title: 'khive Developer Style Guide'
by:     'khive Team'
created: '2025-04-05'
updated: '2025-04-18'
version: '1.6'
description: >
  Practical coding standards for khive (Rust + Tauri backend, React/TS
  frontend).  Designed to be easy to follow from the terminal with the khive
  helper scripts; enforced in Quality Review & CI:
  - ! WARNING---K.D KHIVE-DEV TEAM MUST RETAIN FROM  EDITING THIS DOCUMENT.
  - ! WARNING: THIS DOCUMENT IS READ-ONLY
---

! WARNING: THIS DOCUMENT IS READ-ONLY

## 1 · Why another guide?

Because **consistency beats cleverness.** If everyone writes code, commits, and
PRs the same way, we spend brain-cycles on the product - not on deciphering each
other's styles.

---

## 2 · What matters (and what doesn't)

| ✅ KEEP                                       | ❌ Let go                      |
| --------------------------------------------- | ------------------------------ |
| Readability & small functions                 | “One-liner wizardry”           |
| **>80 pct test coverage**                     | 100 pct coverage perfectionism |
| Conventional Commits                          | Exotic git workflows           |
| Search-driven dev (cite results)              | Coding from memory             |
| Local CLI (`khive *`, `git`, `pnpm`, `cargo`) | Heavy bespoke shell wrappers   |
| Tauri security basics                         | Premature micro-optimisation   |

---

## 4 · Golden-path workflow

1. **Search** - `khive search` → paste IDs/links in docs.
2. **Spec** - `khive new-doc` (architect)
3. **Plan + Tests** - `khive new-doc` (implementer)
4. **Code + Green tests** - local `pnpm test`, `cargo test`, `khive fmt`
5. **Commit** - `khive commit 'feat: cool thing'` (includes mode trailer).
6. **PR** - `khive pr` (fills title/body, adds Mode/Version).
7. **CI** - `khive ci` (coverage & template lint).
8. **Review** - reviewer checks search citations + tests, then approves.
9. **Merge & clean** - orchestrator merges; implementer runs `khive clean`.

That's it - nine steps, every time.

---

## 5 · Code standards (abridged)

### TypeScript / React

- Strict TS (`'strict': true`), no `any` unless unavoidable (and then
  `// FIXME`).
- Functional components, hooks > classes.
- Zustand for state, TanStack Query for data-fetch, shadcn/ui for primitives.
- Tailwind: **apply once, reuse classes** - avoid inline style objects.

### Rust / Tauri

- 2021 edition, stable toolchain.
- `rustfmt` on save; `cargo clippy -- -D warnings` must pass.
- Use `Result<T, anyhow::Error>` for app-level functions.
- Prefer `Arc<Mutex<T>>` only when async channels aren't enough.

---

## 6 · Testing & coverage

| Stack    | Test cmd                  | Coverage file                                  | Notes              |
| -------- | ------------------------- | ---------------------------------------------- | ------------------ |
| Frontend | `pnpm test -- --coverage` | `apps/khive-ui/coverage/coverage-summary.json` | Vitest + RTL       |
| Backend  | `cargo test`              | tarpaulin JSON                                 | Run via `khive ci` |

Threshold lives in CI (`khive ci --threshold 80`). Local devs just call
`khive ci` before pushing; fail-fast keeps PRs green.

---

## 7 · Git & commit etiquette

- One logical change per commit.
- Conventional Commit format (`<type>(scope): subject`).
- Commit with `khive commit` so the **Mode** trailer (`Mode: implementer`, etc.)
  is added automatically.
- Example:

feat(ui): add dark-mode toggle

Implements switch component & persists pref in localStorage (search: exa-xyz123

- looked up prefers-color-scheme pattern) Closes #42

---

## 8 · Helper scripts you actually need

| Script            | What it does                                                   |
| ----------------- | -------------------------------------------------------------- |
| **khive-init**    | Bootstrap deps, hooks, `.roomodes`. Run once per clone.        |
| **khive search**  | Validates + prints request JSON for Exa/Perplexity.            |
| **khive new-doc** | Copies a template → docs folder, fills dates/IDs.              |
| **khive commit**  | `git add -A`, set identity, conventional commit, add trailers. |
| **khive pr**      | Push branch & open PR with Mode/Version.                       |
| **khive clean**   | Switch to default branch, delete local+remote feature branch.  |
| **khive ci**      | Front+back coverage + template-lint (what CI runs).            |

Each script prints its own `--help`.

---

## 9 · Search-first rule (the only non-negotiable)

If you introduce a new idea, lib, algorithm, or pattern **you must cite at least
one search result ID** (exa-… or pplx-…) in the spec / plan / commit / PR. Tests
& scanners look for that pattern; missing ⇒ reviewer blocks PR.

---

## 10 · FAQ

- **Why isn't X automated?** - Because simpler is faster. We automate only what
  pays its rent in saved time.
- **Can I skip the templates?** - No. They make hand-offs predictable.
- **What if coverage is <80 pct?** - Add tests or talk to the architect to slice
  scope.
- **My search turned up nothing useful.** - Then **cite that**
  (`search:
exa-none - no relevant hits`) so the reviewer knows you looked.

Happy hacking 🐝
