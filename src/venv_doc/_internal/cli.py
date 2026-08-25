# SPDX-License-Identifier: ISC
#
# ISC License
#
# Copyright (c) 2025, Timothée Mazzucotelli and contributors
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

# Why does this file exist, and why not put this in `__main__`?
#
# You might be tempted to import things from `__main__` later,
# but that will cause problems: the code will get executed twice:
#
# - When you run `python -m venv_doc` python will execute
#   `__main__.py` as a script. That means there won't be any
#   `venv_doc.__main__` in `sys.modules`.
# - When you import `__main__` it will get executed again (as a module) because
#   there's no `venv_doc.__main__` in `sys.modules`.

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from importlib import import_module, metadata
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Any

from packaging.requirements import Requirement

from venv_doc._internal import debug

# YORE: EOL 3.10: Replace block with line 2.
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib


class _DebugInfo(argparse.Action):
    def __init__(self, nargs: int | str | None = 0, **kwargs: Any) -> None:
        super().__init__(nargs=nargs, **kwargs)

    def __call__(self, *args: Any, **kwargs: Any) -> None:  # noqa: ARG002
        debug._print_debug_info()
        sys.exit(0)


def get_parser() -> argparse.ArgumentParser:
    """Return the CLI argument parser.

    Returns:
        An argparse parser.
    """
    parser = argparse.ArgumentParser(prog="venv-doc")
    parser.add_argument("-V", "--version", action="version", version=f"%(prog)s {debug._get_version()}")
    parser.add_argument("--debug-info", action=_DebugInfo, help="Print debug information.")
    return parser


def _norm_name(name: str) -> str:
    return name.replace("_", "-").replace(".", "-").lower()


def _requirements(deps: list[str]) -> dict[str, Requirement]:
    return {_norm_name((req := Requirement(dep)).name): req for dep in deps}


def main(args: list[str] | None = None) -> int:  # noqa: ARG001
    """Run the main program.

    This function is executed when you type `venv-doc` or `python -m venv_doc`.

    Parameters:
        args: Arguments passed from the command line.

    Returns:
        An exit code.
    """
    installed = defaultdict(list)
    for pkg, dists in metadata.packages_distributions().items():
        for dist in dists:
            installed[dist].append(pkg)

    project_dir = Path()
    with project_dir.joinpath("pyproject.toml").open("rb") as pyproject_file:
        pyproject = tomllib.load(pyproject_file)
    dependencies = _requirements(pyproject["project"].get("dependencies", []))

    package_paths = []
    package_names = []
    for dependency in dependencies:
        for package in installed[dependency]:
            module = import_module(package)
            module_path = module.__file__
            if module_path:
                package_path = Path(module_path)
                if package_path.is_file():
                    package_path = package_path.parent
                if not package_path.name.startswith("_"):
                    package_paths.append(str(package_path))
                    package_names.append(package)
            else:
                print(f"Warning: {package} has no __file__ attribute")

    packages = sorted(set(package_names))
    nav = ",\n                ".join(
        f"{{ {json.dumps(package)} = {json.dumps(f'{package}.md')} }}" for package in packages
    )

    with TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        tmppath.joinpath("docs").mkdir()
        config = dedent(
            f"""\
            [project]
            site_name = "API docs"
            nav = [
                {{ "API docs" = [
                    {{ "Overview" = "index.md" }},
                    {nav}
                ] }},
            ]

            [project.theme]
            features = [
                "announce.dismiss",
                "content.action.edit",
                "content.action.view",
                "content.code.annotate",
                "content.code.copy",
                "content.tooltips",
                "navigation.expand",
                "navigation.footer",
                "navigation.indexes",
                "navigation.instant.preview",
                "navigation.path",
                "navigation.top",
                "search.highlight",
                "search.suggest",
                "toc.follow",
            ]

            [[project.theme.palette]]
            media = "(prefers-color-scheme)"
            toggle.icon = "material/brightness-auto"
            toggle.name = "Switch to light mode"

            [[project.theme.palette]]
            media = "(prefers-color-scheme: light)"
            scheme = "default"
            primary = "teal"
            accent = "purple"
            toggle.icon = "material/weather-sunny"
            toggle.name = "Switch to dark mode"

            [[project.theme.palette]]
            media = "(prefers-color-scheme: dark)"
            scheme = "slate"
            primary = "black"
            accent = "lime"
            toggle.icon = "material/weather-night"
            toggle.name = "Switch to system preference"

            [project.markdown_extensions.toc]
            permalink = true

            [project.plugins.mkdocstrings.handlers.python]
            inventories = ["https://docs.python.org/3/objects.inv"]
            paths = {json.dumps(sorted(set(package_paths)))}

            [project.plugins.mkdocstrings.handlers.python.options]
            docstring_options = {{ per_style_options = {{ google = {{ ignore_init_summary = true }}, numpy = {{ ignore_init_summary = true }} }} }}
            docstring_section_style = "list"
            docstring_style = "auto"
            filters = "public"
            heading_level = 1
            inherited_members = true
            merge_init_into_class = true
            separate_signature = true
            show_root_heading = true
            show_root_full_path = false
            show_signature_annotations = true
            show_source = true
            show_submodules = true
            show_symbol_type_heading = true
            show_symbol_type_toc = true
            signature_crossrefs = true
            summary = true
            """,
        )
        tmppath.joinpath("zensical.toml").write_text(config)
        tmppath.joinpath("docs", "index.md").write_text(
            "# API docs\n\nSelect a package from the navigation to view its API reference.\n",
        )
        for package in packages:
            tmppath.joinpath("docs", f"{package}.md").write_text(
                f"---\ntitle: {package}\n---\n\n::: {package}\n",
            )
        run([sys.executable, "-m", "zensical", "serve"], cwd=tmppath, check=False)

    return 0
