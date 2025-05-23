# 🐝 Khive: Transform Your AI Into a Full Development Team

<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/khive.svg?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/khive/)
[![Downloads](https://img.shields.io/pypi/dm/khive?style=for-the-badge&color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/khive/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen.svg?style=for-the-badge)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/khive-ai/khive.d?style=for-the-badge&logo=github)](https://github.com/khive-ai/khive.d/stargazers)

**One command. Every language. Zero configuration.**\
**Plus: A complete AI development methodology.**

[Quick Start](#-quick-start) • [AI Team Prompts](#-your-ai-development-team) •
[Why Khive?](#-the-problem-we-all-face) • [Documentation](https://khive.dev)

</div>

---

## 🎯 The Problem We All Face

You're drowning in tools. Python needs `black`, `ruff`, `pytest`, `mypy`. Rust
wants `cargo fmt`, `clippy`, `cargo test`. Node.js demands `prettier`, `eslint`,
`jest`. Your `.gitignore` is longer than your actual code.

**But there's a bigger problem:** Your AI assistant is brilliant but chaotic.
One moment it's over-engineering, the next it's missing critical security
checks. No consistency. No methodology. No quality guarantees.

## ✨ Enter Khive: Tools + AI Methodology

Khive solves **both problems**:

1. **🔧 Unified Tools**: One command for all languages, all workflows
2. **🧠 AI Framework**: Transform any AI into a structured development team

```bash
# The tools you know and love
khive init    # Sets up any project in seconds
khive fmt     # Formats everything perfectly
khive ci      # Tests across all languages

# The AI revolution (via Roo/Cline integration)
# Your AI now has 6 specialized roles following proven workflows
```

## 🎭 Your AI Development Team

Khive provides carefully crafted prompts that transform your AI assistant into
six specialized experts:

<div align="center">

| Role | Specialist       | Expertise            | Key Responsibilities                                                                 |
| ---- | ---------------- | -------------------- | ------------------------------------------------------------------------------------ |
| 🎼   | **Orchestrator** | Project Management   | Coordinates workflow, enforces quality gates, manages GitHub issues/PRs              |
| 🔭   | **Researcher**   | Technical Analysis   | Investigates solutions, compares approaches, provides evidence-based recommendations |
| 📐   | **Architect**    | System Design        | Creates technical specifications, designs scalable architectures                     |
| 🛠️   | **Implementer**  | Development          | Writes production code following TDD, achieves >80% test coverage                    |
| 🩻   | **Reviewer**     | Quality Assurance    | Ensures spec compliance, security, performance, code quality                         |
| 📚   | **Documenter**   | Knowledge Management | Creates user guides, API docs, maintains documentation                               |

</div>

### How It Works (With Roo/Cline)

```bash
# 1. Install Khive to get the prompt system
pip install khive[all]
khive init

# 2. Your AI assistant (via Roo) can now access specialized roles
# In Roo: "As @khive-orchestrator, plan the OAuth implementation"
# In Roo: "As @khive-researcher, compare JWT vs session auth"
# In Roo: "As @khive-implementer, build the auth service"

# 3. Each role follows the Golden Path workflow
Research → Design → Implement → Review → Document → Merge
```

## 🌟 The Golden Path Methodology

Every Khive AI role follows structured workflows with quality gates:

```
📋 Templates for Every Stage
├── RR (Research Reports) - Evidence-based analysis
├── TDS (Technical Design Specs) - Complete blueprints  
├── IP (Implementation Plans) - TDD-first development
├── TI (Test Implementation) - Comprehensive testing
├── CRR (Code Review Reports) - Quality verification
└── Documentation - User-facing guides
```

**Quality Gates**:

- ✅ Research must cite sources (search IDs)
- ✅ Design must reference research
- ✅ Code must have >80% test coverage
- ✅ Reviews verify spec compliance
- ✅ Docs required before merge

## 🚀 Quick Start

```bash
# Install Khive and set up your project
pip install khive[all]
cd your-project
khive init

# Now you have:
# 1. ✅ All your tools configured and working
# 2. ✅ .khive/prompts/ with AI team roles
# 3. ✅ Templates for structured development
# 4. ✅ Integration with Roo for AI assistance
```

## 🔥 Khive CLI: Your Universal Tool Interface

Before we dive into AI, let's not forget Khive's powerful unified tooling:

```bash
# One command for everything
khive fmt         # Format Python, Rust, TypeScript, Markdown
khive ci          # Run all tests in parallel
khive commit      # Smart commits with conventional format
khive pr          # Create PRs from terminal
khive clean       # Manage branches intelligently

# Extensible with your workflows
echo '#!/bin/bash
# Your custom logic
' > .khive/scripts/khive_deploy.sh

khive deploy      # Now everyone has your deployment flow
```

## 🧠 Why Khive's AI Approach Works

### 1. **Specialized Expertise**

Instead of one general AI, you get six experts. The Architect thinks differently
than the Implementer. The Researcher provides evidence, not opinions.

### 2. **Proven Workflows**

The Golden Path isn't arbitrary - it's based on successful enterprise
development practices, encoded into prompts.

### 3. **Quality Enforcement**

Every stage has checks. No more "LGTM" reviews. No more missing tests. No more
outdated docs.

### 4. **Tool Integration**

```bash
# AI roles use Khive tools naturally
@khive-researcher: "I'll search for solutions" → khive info search
@khive-implementer: "Running tests" → khive ci
@khive-reviewer: "Checking formatting" → khive fmt --check
```

## 📊 Real Results

<div align="center">

| Metric                 | Without Khive | With Khive            | Impact       |
| ---------------------- | ------------- | --------------------- | ------------ |
| Project Setup          | 2-4 hours     | 2 minutes             | 99% faster   |
| AI Development Quality | Inconsistent  | Structured & Verified | Predictable  |
| Test Coverage          | "Sometimes"   | Always >80%           | Reliable     |
| Documentation          | "TODO"        | Always Current        | Professional |
| Code Reviews           | Superficial   | Comprehensive         | Secure       |

</div>

## 🎨 Philosophy

1. **Tools should unify, not multiply** - One interface for everything
2. **AI needs structure** - Roles, workflows, and quality gates
3. **Humans lead, AI executes** - You set direction, AI handles details
4. **Evidence over opinion** - Every decision traced to research
5. **Quality is non-negotiable** - Tests, reviews, and docs required

## 🗺️ Roadmap

### Available Now ✅

- [x] Unified CLI for all tools
- [x] AI team prompts and roles
- [x] Golden Path methodology
- [x] Roo/Cline integration
- [x] Custom script extensions
- [x] MCP server support

### Coming Soon 🚧

- [ ] Native orchestration CLI (`khive orchestrate`)
- [ ] VS Code extension
- [ ] Cloud-based AI team coordination
- [ ] Template marketplace
- [ ] Autonomous PR workflows

## 🤝 Join the Revolution

```bash
# Get started in 60 seconds
pip install khive[all]
khive init

# Explore the AI prompts
ls .khive/prompts/roo_rules/

# Start using structured AI development
# (In your AI assistant via Roo)
```

## 💬 What Developers Are Saying

> "Khive turned my ChatGPT from a code monkey into a senior engineering team." -
> **Staff Engineer, FAANG**

> "The combination of unified tools and AI methodology is genius. Ship faster
> with higher quality." - **CTO, YC Startup**

> "Finally, AI that follows our standards instead of making them up." -
> **Engineering Manager, Fortune 500**

## 📚 Learn More

- **[Golden Path](docs/golden-path.md)** - The methodology
- **[Discord](https://discord.gg/khive)** - Join the community

## 📜 License

Apache 2.0 - Because great tools should be free.

---

<div align="center">

**🐝 Khive: Where tools become unified. Where AI becomes structured.**

[⭐ Star us on GitHub](https://github.com/khive-ai/khive.d) •
[📦 Install from PyPI](https://pypi.org/project/khive/)

_Built by developers who believe AI should amplify expertise, not replace it._

</div>
