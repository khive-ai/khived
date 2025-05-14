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

## 7 · Common pitfalls and how to avoid them

- 7.0 Not using Khive Tools.

we have our own cli tooling, and we should use them well, otherwise, are we
still the khive team? Also the creator is always the the human, khive team may
not claim to be the originator of the project. Should be absolutely clear who
did what, hugely important for our khive system iterations.

- 7.1 Wrong directory

a common mistake is to run command line without regard of the current directory,
for example if you have already done `cd src/abc && pnpm install` and now you
want to test them, the correct command is to directly to `pnpm test` in the
`src/abc` directory, not `cd src/abc && pnpm test`, because you are already
there.

- 7.2 Wrong branch

It's common to blindly work on the current branch, and overlook the bigger
picture or plans. Doing so will mess up entire development flow, and ruin the
work of your collegues. Always check the branch you are working, use
`git branch`, read issues via mcp ...etc to verify

- 7.3 Wrong MCP formatting the MCP formating is

very important, because it uses json structure, and is easy to mess up
formatting. the correct format is`{json stuff}`, and the wrong format
is`{json stuff}</use_mcp_tool>`

- 7.4 Neglect Templates

Also, commonly, khive team members forget to use the `khive new-doc` and Write
report without using templates, This will lead to inconsistent formatting and
structure. potentially ruining front matter metadata or content parsing for
downstream data analysis. Please always use `khive new-doc` to create the
report, with correct code and formatting. should be
`khive new-doc <type> <issue_number> ...`

- 7.5 Overconfidence

Note that you are based in LLM, and your knowledge limited to your training
data. So don't get stuck in the "I know this, I can do it myself" mindset, if
encountering problems, have doubts, stuck on a same mistake 3-4 times, always
use `khive info` to help you out. Always try best efforts, but remember,
crucially, you are allowed to give up and report back to orchestrator,
suggesting alternative approaches or further research, redesign...etc Because
getting stuck on a problem for too long is not productive, and can lead to
burnout or frustration, and slows down the entire team.

- 7.6 Poor Github Ettiquette

Should always use `khive commit` to commit the changes, must add `--by` flag to
set the author slug, so we know who did what, and can refine our approaches.
It's also common to neglect the various options, please make use of them, they
will help you and the khive team in maintaining the codebase. For example, you
can use `--type` to specify the type of change you are making, such as `feat`,
`fix`, or `docs`. You can also use `--scope` to specify the scope of the change,
such as `ui`, `api`, or `db`. This will help us understand the context of your
changes and make it easier to review and merge them.

- 7.7 Overly ambitious code editing

break down large tasks into smaller, manageable chunks. for example, never edit
more than 300 lines at once, if certain file is very long, always append to the
bottom. For example, when writing reports with templates, you should read the
created report template to make sure you understand it, then rewrite this file
from scratch for about 300-500 lines (which should overwrite all the template
text) append new sections to the bottom of the file, so you don't write 900
lines and then make one error and waste all efforts. Use your best judgement on
this, and balance correctness and efficiency, do not do 50 API calls when you
can solve it in 10, (use khive cli well, we can save a lot of time and token
expenses)

- final words

please always use issue number as the identifier, and use `khive new-doc` to
create the report. The official location of the reports is `.khive/reports/`,
and typically we recommend add `.khive` to .gitignore, so your prompts, configs
won't be in repo, unless you intend to version control them or share them with
others. If `.khive` is already in .gitignore, you don't need to commit the
report.

---

## 8 · FAQ

- **Why isn't X automated?** - Because simpler is faster. We automate only what
  pays its rent in saved time.
- **Can I skip the templates?** - No. They make hand-offs predictable.
- **What if coverage is <80 pct?** - Add tests or talk to the architect to slice
  scope.
- **My search turned up nothing useful.** - Then **cite that**
  (`search:exa-none - no relevant hits`) so the reviewer knows you looked.

Happy hacking 🐝
