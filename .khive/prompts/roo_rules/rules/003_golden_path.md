---
title: 'khive Developer Style Guide'
by:     'khive Team'
created: '2025-04-05'
updated: '2025-05-09'
version: '1.7'
description: >
  Practical coding standards for khive. Designed to be easy to follow from the terminal with the khive helper scripts; enforced in Quality Review & CI.
---

ALWAYS CHECK WHICH BRANCH YOU ARE ON !!! ALWAYS CHECK THE ISSUE YOU ARE WORKING
ON !!!

- `git branch` - check which branch you are on
- `git checkout <branch>` - switch to the branch you want to work on
- `git checkout -b <branch>` - create a new branch and switch to it

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
| Info-driven dev (cite results)                | Coding from memory             |
| Local CLI (`khive *`, `git`, `pnpm`, `cargo`) | Heavy bespoke shell wrappers   |
| Tauri security basics                         | Premature micro-optimisation   |

---

## 4 · Golden-path workflow

1. **Must Info** - `khive info search` → paste IDs/links in docs.
   `khive info consult` when need sanity check, rule of thumb: if you tried 3-4
   times on the same topic, ask!
2. **Spec** - `khive new-doc`
3. **Plan + Tests** - `khive new-doc`
4. **Code + Green tests** - `khive init`, code, then local `pnpm test`,
   `cargo test`
5. **Lint** - should make a pre-commit, and do
   `uv run pre-commit run --all-files`, or language specific linting, such as
   `cargo fmt`, `ruff`, `black`, etc. SUPER IMPORTANT !!!!
6. **Commit** - `khive commit --type xx ... --by "khive-abc"` (includes mode
   trailer).
7. **PR** - `khive pr` (fills title/body, adds Mode/Version).
8. **Review** - reviewer checks search citations + tests, then approves.
9. **Merge & clean** - orchestrator merges; implementer runs `khive clean`.

That's it - nine steps, every time.

## 5 · Git & commit etiquette

- must use `uv run pre-commit` until no problems before commit
- One logical change per commit.
- Conventional Commit format (`<type>(scope): subject`).
- Commit with `khive commit` with structured input, use `--by` to set the author
  slug.

## 6 · Search-first rule (the only non-negotiable)

always use `khive info` extensively for up to date best practcies and sanity
check.

If you introduce a new idea, lib, algorithm, or pattern **you must cite at least
one search result ID** (exa-… or pplx-…) in the spec / plan / commit / PR. Tests
& scanners look for that pattern; missing ⇒ reviewer blocks PR.

---

## 7 · FAQ

- **Why isn't X automated?** - Because simpler is faster. We automate only what
  pays its rent in saved time.
- **Can I skip the templates?** - No. They make hand-offs predictable.
- **What if coverage is <80 pct?** - Add tests or talk to the architect to slice
  scope.
- **My search turned up nothing useful.** - Then **cite that**
  (`search:exa-none - no relevant hits`) so the reviewer knows you looked.

Happy hacking 🐝
