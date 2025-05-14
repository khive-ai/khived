---
title: "Roo Lite"
version: "1.1"
scope:  "project"
created: "2025-05-05"
updated: "2025-05-09"
description: >
  A lightweight, tool-agnostic response scaffold that forces broad reasoning
  (3-6 perspectives) before action while reserving tokens for the real answer.
---

## 1 • Purpose & Rule (of one)

> **Always** start with a `<multi-reasoning>` block (≈3-5 bullets). After that,
> answer freely or layer a task-specific template.

```text
<multi-reasoning>
1. [^Spec]  Reason | Action | Outcome
2. [^Impl]  …
3. [^Validation] …
</multi-reasoning>

<main answer here>
```

### Why bother?

- Ensures broad thinking first.
- Stays cheap (≈70-120 tokens).
- Remains tool-agnostic, so CI/YAML can wrap it later.

---

## 2 • Perspective tags

| Tag                                  | Use-case                           | Sample prompt stub           |
| ------------------------------------ | ---------------------------------- | ---------------------------- |
| **[^Spec]**                          | clarify requirements & constraints | “What does _done_ mean?”     |
| **[^Impl]**                          | algorithms, code shape             | “How will we build it?”      |
| **[^Validation]**                    | tests & edge cases                 | “How will we know it works?” |
| **Optional lenses**<br>(pick any ≤3) |                                    |                              |
| [^Risk]                              | failure modes & security           | “What can break?”            |
| [^System]                            | external deps & feedback loops     | “How does it fit in?”        |
| [^Efficiency]                        | speed / cost trim                  | “Can we do it leaner?”       |
| [^User]                              | human impact & UX                  | “Who touches this?”          |

> Minimum: **Spec + Impl + Validation**. Feel free to swap or add up to **three
> optional lenses**.

---

## 3 • Extended lens glossary (reference only)

Use these if the task demands deeper exploration; otherwise ignore to save
tokens.

| Tag            | Lens                  | One-liner                        |
| -------------- | --------------------- | -------------------------------- |
| [^Creative]    | Creative thinking     | novel, unconstrained ideas       |
| [^Critical]    | Critical thinking     | challenge assumptions with logic |
| [^Reflect]     | Reflective thinking   | surface biases & past lessons    |
| [^Stakeholder] | Stakeholder analysis  | align needs & resources          |
| [^Breakdown]   | Problem decomposition | split into tractable parts       |
| [^Simplify]    | Simplification        | strip to essentials              |
| [^Analogy]     | Analogy               | cross-domain parallels           |
| [^Scenario]    | Scenario planning     | future implications              |
| [^SWOT]        | SWOT analysis         | strengths / weaknesses / etc.    |
| [^Design]      | Design thinking       | empathise-ideate-prototype cycle |
| [^Lean]        | Lean thinking         | waste reduction                  |
| [^Agile]       | Agile thinking        | iterative adaptability           |

---

## 4 • Bullet micro-syntax

```text
[^Tag] Reason: … | Action: … | Outcome: …
```

Keep sentences short; trim filler adverbs. The goal is clarity, not prose.
