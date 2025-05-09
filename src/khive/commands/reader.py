#!/usr/bin/env python3

from __future__ import annotations

from khive.cli.khive_reader import main as original_main


def cli_entry() -> None:
    original_main()


if __name__ == "__main__":
    cli_entry()
