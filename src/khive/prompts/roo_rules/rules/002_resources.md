# Khive Resources & Tooling Cheat-Sheet

> **Use Khive’s own tools first.** Workflow order of preference: **Roo internal
> helpers → Khive CLI → Essential CLI → MCP helpers → External CLI.** prefer
> khive command over `gh`, `git`, and prefer cli over `mcp`

---

## 1 • Core Stack Overview

| Layer                 | What it is                                     | Why it matters                                                             |
| --------------------- | ---------------------------------------------- | -------------------------------------------------------------------------- |
| Roo runtime           | Orchestration engine with `vscode` integration | allows for sub-task delegation, context injection, and agent orchestration |
| Khive CLI (`khive …`) | Single entry-point for all local/dev/CI tasks  | keeps dev rituals uniform; CI calls the exact same code                    |
| Essential CLI         | `uv`, `deno`, `pytest`, `docker`, etc.         | avoids tool sprawl; ensures the Golden Path stays authoritative            |
| MCP helpers           | We have `github` MCP helpers                   | Integrations                                                               |
| External CLI          | `git`, `gh`                                    | still available but invoked through Khive commands where possible.         |
