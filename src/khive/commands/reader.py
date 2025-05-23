# Copyright (c) 2025, HaiyangLi <quantocean.li at gmail dot com>
#
# SPDX-License-Identifier: Apache-2.0

from __future__ import annotations

from khive.cli.khive_reader import main


def cli_entry() -> None:
    # The Typer app instance is callable.
    # Typer handles sys.argv internally when app() is called.
    main()


if __name__ == "__main__":
    cli_entry()
