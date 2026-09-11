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

"""Tests for the CLI."""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import cast

import mkdocstrings_handlers
import pytest
from griffe import Class, Docstring, Function, Module
from markdown import Markdown
from mkdocstrings_handlers.python import PythonHandler
from zensical.compat import mkdocstrings as zensical_mkdocstrings
from zensical.config import parse_config

from venv_doc import main
from venv_doc._internal import debug
from venv_doc._internal.cli import (
    _load_packages,
    _preparse_docstrings,
    _venv_packages,
    _venv_python,
)
from venv_doc._internal.sphinx_roles import _SphinxRolesExtension


def test_main(monkeypatch: pytest.MonkeyPatch) -> None:
    """Generate module pages without starting a web server."""
    generated = {}
    discovered_pythons = []
    reset_mkdocstrings = zensical_mkdocstrings.reset

    def _serve(config_path: str, options: dict) -> None:
        root = Path(config_path).parent
        generated["config"] = Path(config_path).read_text()
        generated["options"] = options
        generated["pages"] = {page.name: page.read_text() for page in root.joinpath("docs").glob("*.md")}
        config = parse_config(config_path)
        html = Markdown(
            extensions=config["markdown_extensions"],
            extension_configs=config["mdx_configs"],
        ).convert(":class:`mkdocstrings_handlers.python.PythonHandler`")
        assert html == (
            '<p><autoref identifier="mkdocstrings_handlers.python.PythonHandler">'
            "mkdocstrings_handlers.python.PythonHandler</autoref></p>"
        )
        handlers = zensical_mkdocstrings.HANDLERS
        assert handlers is not None
        zensical_mkdocstrings.reset()
        assert zensical_mkdocstrings.HANDLERS is handlers
        zensical_mkdocstrings.get_mkdocstrings_extension(
            **config["plugins"]["mkdocstrings"]["config"],
            config=config,
        )
        python_handler = cast("PythonHandler", handlers.get_handler("python"))
        assert python_handler._modules_collection["mkdocstrings_handlers.python"].is_module

    monkeypatch.setattr("venv_doc._internal.cli.serve", _serve)
    monkeypatch.setattr(
        "venv_doc._internal.cli._venv_packages",
        lambda python: (
            discovered_pythons.append(python)
            or (
                ["mkdocstrings_handlers"],
                [str(Path(mkdocstrings_handlers.__path__[0]).parent)],
            )
        ),
    )
    assert (
        main(
            ["serve", "--dev-addr", "127.0.0.1:9000", "--open", "--strict"],
        )
        == 0
    )
    assert zensical_mkdocstrings.reset is reset_mkdocstrings
    assert discovered_pythons == [Path(".venv/bin/python")]
    assert generated["options"] == {
        "dev_addr": "127.0.0.1:9000",
        "open": True,
        "strict": True,
    }
    assert "mkdocstrings_handlers.md" in generated["pages"]
    assert "mkdocstrings_handlers.python.md" in generated["pages"]
    assert "show_submodules: false" in generated["pages"]["mkdocstrings_handlers.python.md"]

    assert '"mkdocstrings_handlers" = [' in generated["config"]
    assert '"mkdocstrings_handlers.md",' in generated["config"]
    assert "pycon = {}" in generated["config"]
    assert '"venv_doc._internal.sphinx_roles:_SphinxRolesExtension" = {}' in generated["config"]
    assert '"Overview"' not in generated["config"]
    assert '"navigation.expand"' not in generated["config"]
    assert '"mkdocstrings_handlers.python" = "mkdocstrings_handlers.python.md"' in generated["config"]


def test_self(monkeypatch: pytest.MonkeyPatch) -> None:
    """Use venv-doc's own interpreter when requested."""
    discovered_pythons = []
    monkeypatch.setattr(
        "venv_doc._internal.cli._venv_packages",
        lambda python: discovered_pythons.append(python) or ([], []),
    )
    monkeypatch.setattr("venv_doc._internal.cli.serve", lambda *args: None)

    assert main(["--self", "serve"]) == 0
    assert discovered_pythons == [Path(sys.executable)]


def test_build(monkeypatch: pytest.MonkeyPatch) -> None:
    """Build generated documentation with the requested options."""
    built = {}

    def _build(config_path: str, options: dict) -> None:
        built["config"] = Path(config_path).read_text()
        built["options"] = options

    monkeypatch.setattr("venv_doc._internal.cli.build", _build)
    monkeypatch.setattr(
        "venv_doc._internal.cli._venv_packages",
        lambda python: ([], []),
    )

    assert main(["build", "--clean", "--strict"]) == 0
    assert 'site_name = "API docs"' in built["config"]
    assert built["options"] == {"clean": True, "strict": True}


def test_load_packages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Load all packages into shared collections before resolving aliases once."""
    modules = {}
    lines = object()
    loaded = []
    resolved = []
    loader_options = {}
    extensions = object()
    configured_extensions = []
    options = SimpleNamespace(
        allow_inspection=True,
        docstring_options=None,
        docstring_style=None,
        extensions=["extension"],
        find_stubs_package=True,
        force_inspection=False,
        preload_modules=["preloaded"],
    )
    handler = SimpleNamespace(
        _lines_collection=lines,
        _modules_collection=modules,
        _paths=["search-path"],
        config=SimpleNamespace(load_external_modules=True),
        get_options=lambda local_options: options,
        normalize_extension_paths=lambda configured: ["normalized-extension"],
    )

    class _Loader:
        def __init__(self, **kwargs: object) -> None:
            loader_options.update(kwargs)

        def load(self, package: str, **kwargs: object) -> Module:
            loaded.append((package, kwargs))
            module = Module(package)
            modules[package] = module
            return module

        def resolve_aliases(self, **kwargs: object) -> tuple[set[str], int]:
            resolved.append(kwargs)
            return set(), 1

    monkeypatch.setattr("venv_doc._internal.cli.GriffeLoader", _Loader)

    def _load_extensions(*configured: object) -> object:
        configured_extensions.append(configured)
        return extensions

    monkeypatch.setattr(
        "venv_doc._internal.cli.load_extensions",
        _load_extensions,
    )

    root_modules = _load_packages(handler, ["package_a", "package_b"])

    assert list(root_modules) == ["package_a", "package_b"]
    assert root_modules["package_a"] is modules["package_a"]
    assert configured_extensions == [("normalized-extension",)]
    assert loaded == [
        ("preloaded", {"try_relative_path": False, "find_stubs_package": True}),
        ("package_a", {"try_relative_path": False, "find_stubs_package": True}),
        ("package_b", {"try_relative_path": False, "find_stubs_package": True}),
    ]
    assert resolved == [{"implicit": False, "external": True}]
    assert loader_options == {
        "allow_inspection": True,
        "docstring_options": None,
        "docstring_parser": None,
        "extensions": extensions,
        "force_inspection": False,
        "lines_collection": lines,
        "modules_collection": modules,
        "search_paths": ["search-path"],
    }


def test_preparse_docstrings() -> None:
    """Parse and cache only docstrings rendered by the generated pages."""
    module_docstring = Docstring("Module documentation.")
    class_docstring = Docstring("Class documentation.")
    method_docstring = Docstring("Method documentation.")
    private_docstring = Docstring("Private documentation.")
    module = Module("package", docstring=module_docstring)
    public_class = Class("Public", docstring=class_docstring)
    public_class.set_member("method", Function("method", docstring=method_docstring))
    module.set_member("Public", public_class)
    module.set_member("_private", Function("_private", docstring=private_docstring))

    assert _preparse_docstrings([module, module]) == 3
    assert "parsed" in module_docstring.__dict__
    assert "parsed" in class_docstring.__dict__
    assert "parsed" in method_docstring.__dict__
    assert "parsed" not in private_docstring.__dict__


def test_venv_packages() -> None:
    """Read importable packages from another virtual environment."""
    packages, paths = _venv_packages(_venv_python(Path(".venv")))

    assert "mkdocstrings_handlers" in packages
    assert str(Path(mkdocstrings_handlers.__path__[0]).parent) in paths


def test_sphinx_roles_extension() -> None:
    """Convert all supported Python-domain roles into mkdocs-autorefs markers."""
    html = Markdown(extensions=[_SphinxRolesExtension()]).convert(
        " ".join(
            f":{role}:`package.symbol`"
            for role in (
                "attr",
                "class",
                "const",
                "data",
                "deco",
                "exc",
                "func",
                "meth",
                "mod",
                "obj",
                "type",
            )
        ),
    )

    assert html == (
        '<p><autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">@package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref> '
        '<autoref identifier="package.symbol">package.symbol</autoref></p>'
    )


def test_sphinx_roles_extension_supports_qualified_roles_and_modifiers() -> None:
    """Convert qualified roles and apply Sphinx cross-reference modifiers."""
    html = Markdown(extensions=[_SphinxRolesExtension()]).convert(
        ":py:meth:`~package.Class.method` and "
        ":py:class:`a title <package.Class>` and "
        ":func:`.package.function()` and "
        ":py:func:`!package.function`",
    )

    assert html == (
        '<p><autoref identifier="package.Class.method">method</autoref> and '
        '<autoref identifier="package.Class">a title</autoref> and '
        '<autoref identifier="package.function">package.function()</autoref> and '
        "<code>package.function</code></p>"
    )


def test_sphinx_roles_extension_leaves_non_python_roles_unchanged() -> None:
    """Do not alter roles outside the Python domain."""
    html = Markdown(extensions=[_SphinxRolesExtension()]).convert(":ref:`some-label`")

    assert html == "<p>:ref:<code>some-label</code></p>"


def test_show_help(capsys: pytest.CaptureFixture) -> None:
    """Show help.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    with pytest.raises(SystemExit):
        main(["-h"])
    captured = capsys.readouterr()
    assert "venv-doc" in captured.out


def test_show_version(capsys: pytest.CaptureFixture) -> None:
    """Show version.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    with pytest.raises(SystemExit):
        main(["-V"])
    captured = capsys.readouterr()
    assert debug._get_version() in captured.out


def test_show_debug_info(capsys: pytest.CaptureFixture) -> None:
    """Show debug information.

    Parameters:
        capsys: Pytest fixture to capture output.
    """
    with pytest.raises(SystemExit):
        main(["--debug-info"])
    captured = capsys.readouterr().out.lower()
    assert "python" in captured
    assert "system" in captured
    assert "environment" in captured
    assert "packages" in captured
