#!/bin/sh

set -e  # Exit immediately if a command exits with a non-zero status

echo "🔧 Installing python via uv with all optional dependencies..."
uv sync --extra all
