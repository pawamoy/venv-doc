"""venv-doc package.

Like `cargo doc` for Python venvs.
"""

from __future__ import annotations

from venv_doc._internal.cli import get_parser, main

__all__: list[str] = ["get_parser", "main"]
