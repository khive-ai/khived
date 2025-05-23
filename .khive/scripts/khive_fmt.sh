#!/bin/sh

set -e  # Exit immediately if a command exits with a non-zero status

echo "🔧 Running isort on src..."
uv run isort src

echo "🎨 Running black on src..."
uv run black src

echo "🧹 Running ruff format..."
uv run ruff format

echo "🛠️  Running pre-commit (1st attempt)..."
if uv run pre-commit run --all-files; then
  echo "✅ Pre-commit passed on first attempt."
else
  echo "🔁 Running pre-commit (2nd attempt)..."
  if uv run pre-commit run --all-files; then
    echo "✅ Pre-commit passed on second attempt."
  else
    echo "❌ Pre-commit failed after two attempts."
    exit 1
  fi
fi

echo "🏁 All steps completed successfully."
