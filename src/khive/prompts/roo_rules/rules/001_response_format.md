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

## Response Structure

Every response must begin with a structured reasoning format:

<multi_reasoning> To increase our reasoning context, Let us think through with 5
random perspectives in random order: [^...] Reason / Action / Reflection /
Expected Outcome [^...] Reason / Action / Reflection / Expected Outcome ...
</multi_reasoning>

---

Then move onto answering the prompt.

- Creative Thinking [^Creative]: Generate innovative ideas and unconventional
  solutions beyond traditional boundaries.

- Critical Thinking [^Critical]: Analyze problems from multiple perspectives,
  question assumptions, and evaluate evidence using logical reasoning.

- Systems Thinking [^System]: Consider problems as part of larger systems,
  identifying underlying causes, feedback loops, and interdependencies.

- Reflective Thinking [^Reflect]: Step back to examine personal biases,
  assumptions, and mental models, learning from past experiences.

- Risk Analysis [^Risk]: Evaluate potential risks, uncertainties, and trade-offs
  associated with different solutions.

- Stakeholder Analysis [^Stakeholder]: Consider human behavior aspects, affected
  individuals, perspectives, needs, and required resources.

- Problem Specification [^Specification]: Identify technical requirements,
  expertise needed, and success metrics.

- Alternative Solutions [^New]: Challenge existing solutions and propose
  entirely new approaches.

- Solution Modification [^Edit]: Analyze the problem type and recommend
  appropriate modifications to current solutions.

- Problem Decomposition [^Breakdown]: Break down complex problems into smaller,
  more manageable components.

- Simplification [^Simplify]: Review previous approaches and simplify problems
  to make them more tractable.

- Analogy [^Analogy]: Use analogies to draw parallels between different domains,
  facilitating understanding and generating new ideas.

- Brainstorming [^Brainstorm]: Generate a wide range of ideas and possibilities
  without immediate judgment or evaluation.

- Mind Mapping [^Map]: Visualize relationships between concepts, ideas, and
  information, aiding in organization and exploration of complex topics.

- Scenario Planning [^Scenario]: Explore potential future scenarios and their
  implications, helping to anticipate challenges and opportunities.

- SWOT Analysis [^SWOT]: Assess strengths, weaknesses, opportunities, and
  threats related to a project or idea, providing a structured framework for
  evaluation.

- Design Thinking [^Design]: Empathize with users, define problems, ideate
  solutions, prototype, and test, focusing on user-centered design principles.

- Lean Thinking [^Lean]: Emphasize efficiency, waste reduction, and continuous
  improvement in processes, products, and services.

- Agile Thinking [^Agile]: Embrace flexibility, adaptability, and iterative
  development, allowing for rapid response to changing requirements and
  feedback.
