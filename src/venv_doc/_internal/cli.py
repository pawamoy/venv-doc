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
import os
import sys
from pathlib import Path
from subprocess import run
from tempfile import TemporaryDirectory
from textwrap import dedent
from typing import Any, cast

from griffe import AliasResolutionError, Module
from zensical import serve
from zensical.compat import mkdocstrings as zensical_mkdocstrings
from zensical.config import parse_config

from venv_doc._internal import debug


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
    parser.add_argument(
        "-V", "--version", action="version", version=f"%(prog)s {debug._get_version()}"
    )
    parser.add_argument(
        "--debug-info", action=_DebugInfo, help="Print debug information."
    )
    parser.add_argument(
        "--self",
        action="store_true",
        help="Document packages from the environment running venv-doc instead of .venv.",
    )
    return parser


_VENV_INFO_SCRIPT = """\
import json
from importlib.metadata import packages_distributions
from importlib.util import find_spec
from pathlib import Path

package_names = []
package_paths = set()
for package in packages_distributions():
    if package.startswith("_") or not package.isidentifier():
        continue
    spec = find_spec(package)
    if spec is None:
        continue
    package_names.append(package)
    if spec.submodule_search_locations:
        package_paths.update(str(Path(path).parent) for path in spec.submodule_search_locations)
    elif spec.origin:
        package_paths.add(str(Path(spec.origin).parent))

print(json.dumps({"packages": sorted(package_names), "paths": sorted(package_paths)}))
"""


def _venv_python(venv_path: Path) -> Path:
    """Return the Python interpreter in a virtual environment."""
    candidates = (
        (venv_path / "Scripts" / "python.exe", venv_path / "Scripts" / "python")
        if os.name == "nt"
        else (venv_path / "bin" / "python",)
    )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    msg = f"Could not find a Python interpreter in {venv_path}"
    raise FileNotFoundError(msg)


def _venv_packages(python: Path) -> tuple[list[str], list[str]]:
    """Return public packages and their import roots from a Python interpreter."""
    result = run(
        [str(python), "-c", _VENV_INFO_SCRIPT],
        capture_output=True,
        check=True,
        text=True,
    )
    info = json.loads(result.stdout)
    return info["packages"], info["paths"]


def _public_modules(module: Module) -> list[Module]:
    """Return the public modules below a module, in declaration order."""
    modules = []
    for member in module.members.values():
        if member.is_alias:
            continue
        try:
            if not member.is_module or not member.is_public:
                continue
        except AliasResolutionError:
            continue
        public_module = cast(Module, member)
        modules.append(public_module)
        modules.extend(_public_modules(public_module))
    return modules


def _write_page(path: Path, identifier: str) -> None:
    """Write an API documentation page for an identifier."""
    path.write_text(
        f"---\ntitle: {identifier}\n---\n\n::: {identifier}\n    options:\n        show_submodules: false\n",
    )


def _get_python_handler(config_path: Path) -> Any:
    """Return Zensical's shared Python handler for a documentation build."""
    config = parse_config(str(config_path))
    zensical_mkdocstrings.reset()
    zensical_mkdocstrings.get_mkdocstrings_extension(
        **config["plugins"]["mkdocstrings"]["config"],
        config=config,
    )
    handlers = zensical_mkdocstrings.HANDLERS
    assert handlers is not None
    return handlers.get_handler("python")


def main(args: list[str] | None = None) -> int:
    """Run the main program.

    This function is executed when you type `venv-doc` or `python -m venv_doc`.

    Parameters:
        args: Arguments passed from the command line.

    Returns:
        An exit code.
    """
    parsed_args = get_parser().parse_args(args)
    python = Path(sys.executable) if parsed_args.self else _venv_python(Path(".venv"))
    packages, package_paths = _venv_packages(python)

    with TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        tmppath.joinpath("docs").mkdir()
        config = dedent(
            f"""\
            [project]
            site_name = "API docs"
            nav = [
                {{ "API docs" = [
                    "index.md",
                    # {{packages}}
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

            [project.markdown_extensions]
            pycon = {{}}
            "venv_doc._internal.sphinx_roles:_SphinxRolesExtension" = {{}}

            [project.plugins.mkdocstrings.handlers.python]
            inventories = ["https://docs.python.org/3/objects.inv"]
            paths = {json.dumps(package_paths)}

            [project.plugins.mkdocstrings.handlers.python.options]
            docstring_options = {{ per_style_options = {{ google = {{ ignore_init_summary = true }}, numpy = {{ ignore_init_summary = true }} }} }}
            docstring_section_style = "list"
            docstring_style = "auto"
            filters = "public"
            heading_level = 1
            inherited_members = true
            merge_init_into_class = true
            scoped_crossrefs = false
            separate_signature = true
            show_if_no_docstring = true
            show_root_heading = true
            show_root_full_path = false
            show_signature_annotations = true
            show_source = true
            show_submodules = false
            show_symbol_type_heading = true
            show_symbol_type_toc = true
            signature_crossrefs = true
            summary = true
            """,
        )
        config_path = tmppath.joinpath("zensical.toml")
        config_path.write_text(config)
        tmppath.joinpath("docs", "index.md").write_text(
            "# API docs\n\nSelect a package from the navigation to view its API reference.\n",
        )
        handler = _get_python_handler(config_path)
        package_modules = {}
        for package in packages:
            root_module = handler.collect(package, handler.get_options({}))
            package_modules[package] = _public_modules(root_module)
            _write_page(tmppath.joinpath("docs", f"{package}.md"), package)
            for module in package_modules[package]:
                _write_page(tmppath.joinpath("docs", f"{module.path}.md"), module.path)

        nav = ",\n                    ".join(
            "{ "
            + json.dumps(package)
            + " = [\n                        "
            + json.dumps(f"{package}.md")
            + ",\n                        "
            + ",\n                        ".join(
                f"{{ {json.dumps(module.path)} = {json.dumps(f'{module.path}.md')} }}"
                for module in modules
            )
            + "\n                    ] }"
            for package, modules in package_modules.items()
        )
        config_path.write_text(config.replace("# {packages}", nav))
        serve(str(config_path), {"dev_addr": None, "open": False, "strict": False})

    return 0
