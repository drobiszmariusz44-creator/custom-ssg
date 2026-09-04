"""Parsing converted HTML for metadata and custom filtering."""

from __future__ import annotations

import html
import subprocess
import sys

import xml.etree.ElementTree as ET

import html5lib
import yaml


class ParsedFragment:
    """Convert the file from markdown to html and collect metadata."""

    def __init__(self, source: str):
        metadata, markdown = self._split_on_metadata_boundary(source)

        self.metadata = yaml.load(metadata, Loader=yaml.Loader)
        if self.metadata is None:
            self.metadata = {}
        elif not isinstance(self.metadata, dict):
            print("Waring: metadata should be a dictionary!")
            self.metadata = {}

        # No need to give Pandoc the metadata. We are not using its template
        # system.
        self.element: ET.Element = html5lib.parseFragment(
            self._convert_markdown(markdown),
            treebuilder="etree",
            namespaceHTMLElements=False,
            container="body",
        )

    def _convert_markdown(self, source: str) -> str:
        """Invoke pandoc on markdown source."""
        result = subprocess.run(
            [
                "pandoc",
                "-f",
                "markdown-smart+tex_math_dollars",
                "-t",
                "html",
                "--mathml",
            ],
            capture_output=True,
            check=False,
            encoding="UTF-8",
            input=source,
        )

        print(result.stderr, file=sys.stderr, end="")

        if result.returncode != 0:
            print(
                "Pandoc failed.",
                file=sys.stderr,
            )
            output = f"<code><pre>{html.escape(result.stderr, True)}<pre></code>"
        else:
            output = result.stdout

        return output

    def _split_on_metadata_boundary(self, source):
        """Carve out the YAML frontmatter if there is any."""
        if source.startswith("---"):
            split_result = source[3:].split("---", 1)
            return split_result[0], split_result[1]

        return "", source

    def _extract_itemprops(self, root_element: ET.Element) -> dict:
        is_scope = root_element.get("itemscope")

        if is_scope:
            pass

        print("TODO: itemprop extraction", file=sys.stderr)

        return {}
