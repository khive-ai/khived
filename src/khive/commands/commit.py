# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
commit.py - Create Conventional Commits with staging and push options.

This is an adapter module that delegates to the original implementation
in khive.cli.khive_commit.
"""

from __future__ import annotations

# Import the original implementation
from khive.cli.khive_commit import main as original_main


def cli_entry() -> None:
    """
    Entry point for the commit command.

    This function delegates to the original implementation.
    """
    original_main()


if __name__ == "__main__":
    cli_entry()
