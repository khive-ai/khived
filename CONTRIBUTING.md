# Contributing to Khive

Thank you for your interest in contributing to Khive! This document provides
guidelines and instructions for contributing to the project.

## Table of Contents

1. [Code of Conduct](#code-of-conduct)
2. [Getting Started](#getting-started)
3. [Development Workflow](#development-workflow)
4. [Coding Standards](#coding-standards)
5. [Testing](#testing)
6. [Documentation](#documentation)
7. [Pull Request Process](#pull-request-process)
8. [Release Process](#release-process)

## Code of Conduct

By participating in this project, you agree to abide by our
[Code of Conduct](CODE_OF_CONDUCT.md). Please read it before contributing.

## Getting Started

### Prerequisites

Before you begin, ensure you have the following installed:

- Python 3.11+
- [uv](https://github.com/astral-sh/uv)
- Rust toolchain (`cargo`, `rustc`, `rustfmt`)
- Node.js and pnpm
- Deno ≥ 1.42
- Git and GitHub CLI (`gh`)
- jq

### Setting Up the Development Environment

1. Fork the repository on GitHub
2. Clone your fork locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/khive.git
   cd khive
   ```
3. Install the project in development mode:
   ```bash
   uv pip install -e .
   ```
4. Initialize the development environment:
   ```bash
   khive init -v
   ```

## Development Workflow

1. Create a new branch for your feature or bugfix:
   ```bash
   git checkout -b feat/your-feature-name
   # or
   git checkout -b fix/your-bugfix-name
   ```

2. Make your changes, following the [coding standards](#coding-standards)

3. Run the formatter and linters:
   ```bash
   khive fmt
   ```

4. Run the tests:
   ```bash
   khive ci --check
   ```

5. Commit your changes using the Conventional Commits format:
   ```bash
   khive commit "feat(component): add new feature"
   # or
   khive commit "fix(component): fix bug"
   ```

6. Push your branch to GitHub:
   ```bash
   git push -u origin feat/your-feature-name
   ```

7. Create a pull request using:
   ```bash
   khive pr
   ```

## Coding Standards

Khive uses several tools to enforce coding standards:

- **Python**: [ruff](https://github.com/astral-sh/ruff) for linting and
  formatting
- **Rust**: `rustfmt` for formatting
- **Markdown**: Deno's markdown formatter
- **TypeScript/JavaScript**: Deno's formatter

Run `khive fmt` to automatically format your code according to the project's
standards.

### Conventional Commits

We follow the [Conventional Commits](https://www.conventionalcommits.org/)
specification for commit messages. This enables automatic versioning and
changelog generation.

Format: `<type>(<scope>): <description>`

Types:

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Changes that do not affect the meaning of the code
- `refactor`: Code changes that neither fix a bug nor add a feature
- `perf`: Performance improvements
- `test`: Adding or correcting tests
- `build`: Changes to the build system or dependencies
- `ci`: Changes to CI configuration files and scripts
- `chore`: Other changes that don't modify src or test files

Use the `khive commit` command to help format your commits correctly.

## Testing

Khive uses pytest for testing. Run the tests with:

```bash
khive ci --check
```

When adding new features, please include appropriate tests.

## Documentation

Documentation is crucial for Khive. When adding or modifying features, please
update the relevant documentation:

- Update the README.md if necessary
- Update or add documentation in the docs/ directory
- Include docstrings in your code
- Update the CHANGELOG.md in the [Unreleased] section

Use `khive new-doc` to create new documentation files from templates.

## Pull Request Process

1. Ensure your code passes all tests and linting checks
2. Update documentation as necessary
3. Create a pull request using `khive pr`
4. The PR title should follow the Conventional Commits format
5. Wait for code review and address any feedback
6. Once approved, your PR will be merged

## Release Process

Khive follows semantic versioning and uses an automated release process:

1. Merged PRs with Conventional Commits automatically determine the next version
2. The release process generates a changelog and creates a new version tag
3. The package is automatically published to PyPI

## Questions?

If you have any questions or need help, please open an issue on GitHub.

Thank you for contributing to Khive!
