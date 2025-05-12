# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

"""
roo.py - Legacy ROO mode generator.

This is an adapter module that delegates to the original implementation
in khive.cli.khive_roo.
"""

from __future__ import annotations

# Import the original implementation
from khive.cli.khive_roo import main as original_main


def cli_entry() -> None:
    """
    Entry point for the roo command.

    This function delegates to the original implementation.
    """
    original_main()


if __name__ == "__main__":
    cli_entry()
