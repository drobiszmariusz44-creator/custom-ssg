"""A document representation."""

import copy
import os
import sys
import xml.etree.ElementTree as ET

import html5lib


class Document:
    """A fully built document with all the metadata resolved."""

    QUOTES = {"en-US": "\u201C\u201D", "cs-CZ": "\u201E\u201C"}
    RAW_ELEMENTS = ("script", "style", "code")

    def __init__(
        self,
        /,
        source_path: str,
        dest_path,
        output_dir,
        content_dir,
        metadata: dict,
        tree: ET.ElementTree | None,
    ):
        self.source_path = source_path
        self.dest_path = dest_path
        self.output_dir = output_dir
        self.content_dir = content_dir
        self.metadata = metadata
        self.tree = tree
        self.children: list[Document] = []
        self.parent = None

        if self.tree is not None:
            Document._apply_ligatures(self.tree.getroot())

    def finalize(self):
        """Propagate inherited links and scripts and run python scripts."""

        inherited_elements = []
        if self.tree is not None:
            inherited_elements.extend(self.tree.findall(".//*[@data-inherit]"))

        for child in self.children:
            if child.tree is not None:
                for element in inherited_elements:
                    element = copy.deepcopy(element)
                    child.tree.find(element.get("data-inherit")).append(element)
        for element in inherited_elements:
            element.attrib.pop("data-inherit")

        if self.tree is None:
            return

        for link in self.tree.findall(".//link"):
            link.set("href", self._relativize(link.get("href")))

        for script in self.tree.findall(".//script"):
            if script.get("type", None) == "text/python":
                if "src" in script.attrib:
                    with open(script.get("src"), "r", encoding="UTF-8") as f:
                        code = f.read()
                else:
                    code = script.text

                exec(code, {"document": self})  # pylint: disable=exec-used

            else:
                if "src" in script:
                    script.set("src", self._relativize(script.get("src")))

        for anchor in self.tree.findall(".//a"):
            if "href" in anchor.attrib:  # Anchors don't have to link anywhere.
                anchor.set("href", self._relativize(anchor.get("href")))

        for parent in self.tree.findall('.//script[@type="text/python"]/..'):
            for script in parent.findall('./script[@type="text/python"]'):
                parent.remove(script)

        for child in self.children:
            child.finalize()

    def _relativize(self, absolute_path):
        """
        Generate a relative path that uses slashes instead of the OS specific
        separator.
        """

        if absolute_path.startswith("http://") or absolute_path.startswith("https://"):
            return absolute_path
        if not absolute_path.startswith("/"):
            return absolute_path

        split_result = absolute_path.split("#", 1)
        if len(split_result) == 2:
            absolute_path, fragment = split_result
        else:
            fragment = None

        if absolute_path.endswith(".md"):
            absolute_path = absolute_path.removesuffix(".md") + ".html"

        relative_path = os.path.relpath(
            os.path.join(self.output_dir, absolute_path.removeprefix("/")),
            os.path.dirname(self.dest_path),
        )
        result = ""
        while relative_path != "":
            relative_path, basename = os.path.split(relative_path)

            if result == "":
                result = basename
            else:
                result = basename + "/" + result

        if fragment is not None:
            return "#".join((result, fragment))
        return result

    def write(self):
        """Write self and all children to disk."""
        for child in self.children:
            child.write()

        if self.tree is None:
            return

        result = b"<!DOCTYPE html>" + html5lib.serialize(
            self.tree.getroot(),
            "etree",
            encoding="UTF-8",
            quote_attr_values="spec",
            strip_whitespace=True,
            omit_optional_tags=False,  # No, they are not optional for **serializers**
            inject_meta_charset=True,
        )

        os.makedirs(os.path.dirname(self.dest_path), exist_ok=True)
        with open(self.dest_path, "w", encoding="UTF-8") as f:
            f.write(result.decode("UTF-8"))

    @staticmethod
    def _apply_ligatures(
        element: ET.Element,
        /,
        inside_quotes: bool = False,
        lang: str | None = None,
    ) -> None:
        if "lang" in element.attrib:
            if inside_quotes and element.get("lang") != lang:
                print(
                    'Error: unmatched " character. Conversion will break.',
                    file=sys.stderr,
                )
                inside_quotes = False
            lang = element.get("lang")

        if lang is None:
            print("Warning: unset language. Quotes will be left alone.")

        def normalize_text(text: str) -> str:
            return (
                text.replace("---", "\u2014")
                .replace("--", "\u2013")
                .replace("...", "\u2026")
            )

        def resolve_quotes(
            text: str, inside_quotes: bool, /, tail: bool = False
        ) -> tuple[str, bool]:
            if lang is None or (not tail and element.tag in Document.RAW_ELEMENTS):
                return text, inside_quotes
            result = ""
            for c in text:
                if c == '"':
                    result += Document.QUOTES[lang][1 if inside_quotes else 0]
                    inside_quotes = not inside_quotes
                else:
                    result += c
            return result, inside_quotes

        if element.text is not None and element.tag not in Document.RAW_ELEMENTS:
            element.text, inside_quotes = resolve_quotes(
                normalize_text(element.text), inside_quotes
            )

        for child in element.findall("./*"):
            Document._apply_ligatures(child, lang=lang, inside_quotes=inside_quotes)

        if element.tail is not None:
            element.tail, inside_quotes = resolve_quotes(
                normalize_text(element.tail), inside_quotes, tail=True
            )
