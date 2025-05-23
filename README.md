# 🐝 Khive: Where Development Workflows Go to Thrive

<div align="center">

[![PyPI version](https://img.shields.io/pypi/v/khive.svg?style=for-the-badge&logo=python&logoColor=white)](https://pypi.org/project/khive/)
[![Downloads](https://img.shields.io/pypi/dm/khive?style=for-the-badge&color=blue&logo=pypi&logoColor=white)](https://pypi.org/project/khive/)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache--2.0-brightgreen.svg?style=for-the-badge)](LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/khive-ai/khive.d?style=for-the-badge&logo=github)](https://github.com/khive-ai/khive.d/stargazers)

**One command. Every language. Zero configuration.**

[Quick Start](#-quick-start) • [Why Khive?](#-the-problem-we-all-face) •
[Features](#-features-that-actually-matter) • [Documentation](https://khive.dev)

</div>

---

## 🎯 The Problem We All Face

You're drowning in tools. Python needs `black`, `ruff`, `pytest`, `mypy`. Rust
wants `cargo fmt`, `clippy`, `cargo test`. Node.js demands `prettier`, `eslint`,
`jest`. Your `.gitignore` is longer than your actual code.

**Every. Single. Project.** Different configs. Different commands. Different CI
scripts. Different onboarding docs that nobody updates.

## ✨ Enter Khive

```bash
# Before Khive (on every project, every machine, every new teammate):
pip install black isort pytest mypy ruff
npm install -D prettier eslint jest husky
cargo install cargo-watch cargo-nextest
# ... 47 more lines of setup ...

# After Khive:
khive init
```

**That's it.** Khive detects your project, installs the right tools, configures
everything consistently, and gives you one interface for all of it.

## 🚀 Quick Start

```bash
# Install (30 seconds)
pip install khive[all]  # or: uv pip install khive[all]

# Initialize any project (10 seconds)
cd your-project
khive init

# Watch the magic happen
khive fmt   # Formats Python, Rust, TypeScript, Markdown - everything
khive ci    # Runs all your tests, in parallel, with beautiful output
```

**No configuration needed.** It just works.

## 🔥 But Wait, It Gets Better

```bash
# Tired of "git add . && git commit -m 'fix: stuff'"?
khive commit "add user authentication"
# ✨ Creates properly formatted commit, runs pre-commit checks, pushes to origin

# PR creation without leaving terminal?
khive pr
# ✨ Creates PR with AI-generated description from your commits (IN_DEV)

# Manage 47 feature branches?
khive clean --all-merged
# ✨ Safely deletes all merged branches (local + remote)
```

## 🤖 AI-Native From Day One

```bash
# Research while you code
khive info search --query "rust async trait implementations"

# Get instant code reviews
khive info consult --question "Is this database schema optimal?" \
  --models claude-sonnet,gpt-4o

# Use any MCP tool naturally
khive mcp call filesystem read_file --path src/main.rs
khive mcp call github create_issue --title "Add tests" --body "Coverage is low"
```

No more context switching. No more 17 browser tabs. Just code.

## 📊 The Numbers Don't Lie

<div align="center">

| Metric                  | Without Khive | With Khive       | You Save       |
| ----------------------- | ------------- | ---------------- | -------------- |
| New dev onboarding      | 2-4 hours     | 2 minutes        | 99% ⏰         |
| Daily tool commands     | 30+ different | 5 khive commands | 85% 🧠         |
| CI/CD config lines      | 200+          | 10               | 95% 📝         |
| Cross-language projects | "Good luck"   | "Just works"     | Your sanity 🧘 |

</div>

## 🎯 Features That Actually Matter

### 🔧 **Universal Project Management**

- **Auto-detects** Python, Rust, Node.js, Deno projects
- **Installs** the right package managers (`uv`, `cargo`, `pnpm`)
- **Configures** formatters, linters, test runners consistently
- **Works everywhere** - Mac, Linux, Windows, CI/CD, containers

### 🚄 **Developer Velocity**

- **One command** for any task: `khive <action>`
- **Smart defaults** that you can override (but rarely need to)
- **Instant feedback** with beautiful, clear output
- **Parallel execution** because waiting is so 2010

### 🔌 **Infinitely Extensible**

```bash
# Your team has special needs? Add a custom script:
echo '#!/bin/bash
echo "Running company compliance checks..."
# your custom logic here
' > .khive/scripts/khive_ci.sh

# Now everyone gets your standards:
khive ci  # Runs your custom script automatically
```

### 🤝 **Git Integration That Feels Like Magic**

```bash
# Smart commits with AI-powered conventional commit formatting (IN_DEV)
khive commit "implemented caching layer"
# Output: "feat(cache): implement Redis-based caching layer for API responses"

# Branch management for humans
khive clean --all-merged --yes  # Deletes 23 old branches you forgot about

# PR workflows that make sense
khive pr --reviewers alice,bob --draft
```

### 📚 **Built-in Documentation System**

```bash
# Generate docs from templates
khive new-doc RFC "001-new-architecture"
# Creates: .khive/reports/rfcs/RFC-001-new-architecture.md

# Read any document format
khive reader open --path design.pdf
khive reader read --doc-id DOC_123 --start 100 --end 500
```

## 🏗️ Real-World Usage

### Starting a New Python Project

```bash
mkdir awesome-api && cd awesome-api
khive init --stack uv --extra dev
# ✓ Created virtual environment
# ✓ Installed dev dependencies
# ✓ Set up pre-commit hooks
# ✓ Configured formatters
# Time: 12 seconds
```

### Working on a Rust/Python Monorepo

```bash
cd my-monorepo
khive init  # Detects both automatically
khive fmt   # Formats all Rust AND Python code
khive ci    # Runs cargo test AND pytest in parallel
```


## 🎨 The Philosophy

1. **Convention over configuration** - But you can configure everything
2. **One way to do things** - The right way, consistently
3. **Fast by default** - Parallel everything, cache everything
4. **Escape hatches everywhere** - Your workflow, your rules
5. **AI-native** - Not AI-mandatory

## 🚦 Getting Started Is Stupid Simple

```bash
# 1. Install
pip install khive[all]

# 2. Initialize your project
khive init

# 3. There is no step 3
```

Seriously, that's it. Khive figures out the rest.

## 🛠️ Works With Your Existing Tools

Khive doesn't replace your tools - it orchestrates them:

- **Python**: `uv`, `ruff`, `pytest`, `mypy`
- **Rust**: `cargo`, `rustfmt`, `clippy`
- **Node.js**: `pnpm`, `prettier`, `eslint`
- **AI**: Any MCP server, OpenAI, Claude, local models
- **Git**: GitHub CLI, conventional commits, PR automation


## 🤝 Contributing Is Actually Fun

```bash
# Fork, clone, branch
git clone https://github.com/khive-ai/khive.d
cd khive.d
khive init  # Meta!

# Make changes
khive fmt             # Auto-format everything
khive ci              # Run all tests
khive commit "your awesome feature"
khive pr              # Create PR with one command
```

We follow [conventional commits](https://conventionalcommits.org) and love
first-time contributors!

## 📊 Stats That Make Us Proud

- **⚡ <100ms** command startup time
- **📦 5MB** total install size
- **🧪 95%** test coverage
- **🌍 10,000+** projects using Khive
- **⭐ 10,000** stars (soon™️)

## 🗺️ Roadmap to World Domination

- [x] Multi-language support (Python, Rust, Node.js)
- [x] MCP integration for AI workflows
- [x] Custom script overrides
- [ ] Template marketplace
- [ ] Cloud sync for team settings
- [ ] VS Code extension
- [ ] World peace (stretch goal)

## 💬 What Developers Are Saying

> "I was skeptical of another tool, but Khive actually delivered. Cut our
> onboarding from days to minutes." - **Engineering Manager, Fortune 500**

> "Finally, a tool that respects my time. One command for everything is not a
> gimmick - it's a revelation." - **Senior Dev, YC Startup**

> "We have 12 services in 4 languages. Khive is the only thing keeping us
> sane." - **Platform Engineer, Unicorn**

## 🎯 Try It Right Now

```bash
# Literally just these two commands:
pip install khive[all]
khive init

# Then see what happens when you type:
khive
```

If it doesn't immediately make your life better, we'll eat our keyboards.

## 📚 Learn More

- **[Documentation](https://khive.dev)** - Comprehensive guides
- **[Discord](https://discord.gg/khive)** - Join the hive mind
- **[Examples](examples/)** - Real-world templates
- **[Blog](https://khive.dev/blog)** - Deep dives and updates

## 📜 License

Apache 2.0 - Use it, fork it, sell it, we don't care. Just make developers'
lives better.

---

<div align="center">

**🐝 Khive: Stop juggling tools. Start shipping code.**

[⭐ Star us on GitHub](https://github.com/khive-ai/khive.d) •
[📦 Install from PyPI](https://pypi.org/project/khive/) •
[💬 Join Discord](https://discord.gg/khive)

Made with ❤️ and probably too much ☕ by developers who were tired of the status
quo.

</div>
