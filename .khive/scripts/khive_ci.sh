#!/bin/sh

set -e  # Exit immediately if a command exits with a non-zero status

echo "🔧 Running pytest..."
uv run pytest tests
