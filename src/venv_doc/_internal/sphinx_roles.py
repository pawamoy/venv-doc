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
# ACTION OF CONTRACT, NEGLIGENCE OR OTHERWISE ARISING IN ANY WAY OUT OF THE
# USE OR PERFORMANCE OF THIS SOFTWARE.

from __future__ import annotations

from re import fullmatch
from typing import TYPE_CHECKING
from xml.etree.ElementTree import Element

from markdown import Markdown
from markdown.extensions import Extension
from markdown.inlinepatterns import InlineProcessor

if TYPE_CHECKING:
    from re import Match


_PYTHON_ROLES = "attr|class|const|data|deco|exc|func|meth|mod|obj|type"
"""Python-domain cross-reference roles supported by Sphinx."""

_SPHINX_ROLE_RE = rf"(?<![\w`]):(?:py:)?(?P<role>{_PYTHON_ROLES}):`(?P<content>[^`\n]+)`(?!`)"
"""Match a supported short or qualified Python-domain Sphinx role."""

_PYTHON_IDENTIFIER_RE = r"[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*"
"""Match the dotted Python object identifiers that mkdocs-autorefs can resolve."""

_EXPLICIT_TITLE_RE = r"(?P<title>.+?)\s*<(?P<target>[^<>]+)>"
"""Match Sphinx's ``title <target>`` cross-reference syntax."""


class _SphinxRoleInlineProcessor(InlineProcessor):
    """Turn supported Python-domain Sphinx roles into mkdocs-autorefs markers."""

    def handleMatch(self, m: Match[str], data: str) -> tuple[Element, int, int]:
        """Create an ``autoref`` element for a Sphinx role where possible."""
        role = m.group("role")
        content = m.group("content")

        # ``!`` explicitly disables linking in Sphinx. It must not become an
        # autoref marker because a resolvable marker would create a link again.
        if content.startswith("!"):
            element = Element("code")
            element.text = content[1:]
            return element, m.start(0), m.end(0)

        explicit_title = fullmatch(_EXPLICIT_TITLE_RE, content)
        if explicit_title:
            title = explicit_title.group("title")
            identifier = explicit_title.group("target")
        else:
            title = content
            identifier = content

        # Sphinx uses a leading ``~`` only to shorten an implicit title, and a
        # leading ``.`` only to affect lookup precedence. Autorefs has no
        # equivalent contextual lookup, so resolve the unprefixed identifier.
        if not explicit_title:
            title = title.lstrip(".")
            if title.startswith("~"):
                title = title[1:].rsplit(".", maxsplit=1)[-1]
        identifier = identifier.strip().lstrip("~.").removesuffix("()")

        if not fullmatch(_PYTHON_IDENTIFIER_RE, identifier):
            # Leave syntax that cannot name an mkdocs-autorefs object to
            # Markdown's normal handling rather than making an invalid marker.
            element = Element("code")
            element.text = content
            return element, m.start(0), m.end(0)

        if role == "deco":
            title = f"@{title}"

        element = Element("autoref", {"identifier": identifier})
        element.text = title
        return element, m.start(0), m.end(0)


class _SphinxRolesExtension(Extension):
    """Convert Python-domain Sphinx roles to auto-references."""

    name = "venv-doc-sphinx-roles"

    def extendMarkdown(self, md: Markdown) -> None:
        """Register the role processor before Markdown's code-span processor."""
        md.inlinePatterns.register(
            _SphinxRoleInlineProcessor(_SPHINX_ROLE_RE, md),
            self.name,
            priority=191,
        )
