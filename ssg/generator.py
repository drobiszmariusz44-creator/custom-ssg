"""The generator logic."""

import configparser
import os
import sys
import xml.etree.ElementTree as ET

import html5lib

from ssg.parser import ParsedFragment
from ssg.assets import AssetManager
from ssg.document import Document


class Generator:
    """A self-contained generator with an input path."""

    def __init__(self, input_path):
        self.input_path = input_path
        config = configparser.ConfigParser()
        config.read(os.path.join(input_path, "config.ini"))

        self.output_path = os.path.abspath(
            os.path.join(
                input_path,
                config.get(
                    "ssg",
                    "output",
                    fallback="public",
                ),
            )
        )
        self.site_lang = config.get("ssg", "lang", fallback=None)
        self.content_dir = os.path.join(input_path, "content")
        self.asset_manager = AssetManager(self.content_dir, self.output_path)

    def build(self, /):
        """Walk the content directory and convert everything."""

        document = self._build_dir(self.content_dir)

        print("Finalizing...")
        document.finalize()
        document.write()

        self.asset_manager.clean_up()

    def _get_output_path(self, input_path):
        return os.path.join(
            self.output_path,
            input_path.removeprefix(self.content_dir + os.path.sep).removesuffix(".md")
            + ".html",
        )

    def _build_dir(self, path: str) -> Document:
        result = self._build_one(os.path.join(path, "index.md"))

        for item in os.listdir(path):
            if item == "index.md":
                continue

            item = os.path.join(path, item)
            if os.path.islink(item):
                print(
                    "Warning: No symlinks allowed in the content directory!",
                    file=sys.stderr,
                )
            else:
                child = None
                if os.path.isdir(item):
                    child = self._build_dir(item)
                elif os.path.isfile(item):
                    if item.endswith(".md"):
                        child = self._build_one(item)
                else:
                    print(f"Warning: Ignored irregular file {item}.")

                if child is not None:
                    child.parent = result
                    result.children.append(child)

        return result

    def _get_html_fragment(self, file_path: str) -> ParsedFragment:
        """Perform the markdown conversion for a single file."""
        if not os.path.isfile(file_path):
            print(f"Error: {file_path} doesn't exist!")
            return None

        with open(file_path, "r", encoding="UTF-8") as f:
            source = f.read()
        return ParsedFragment(source)

    def _create_empty_document(self) -> ET.ElementTree:
        """Create an empty document node to insert generated content into."""
        return ET.ElementTree(
            html5lib.parse(
                f"""
                <!DOCTYPE html>
                <html lang={self.site_lang}>
                    <head>
                        <meta name="viewport" content="width=device-width,initial-scale=1" />
                    </head>
                    <body><main><article></article></main></body>
                </html>
                """,
                treebuilder="etree",
                namespaceHTMLElements=False,
            )
        )

    def _build_one(self, source) -> Document:
        """
        Convert a single file from markdown to html and write the output to
        disk.
        """

        print(f"{os.path.relpath(source, self.content_dir)}")

        fragment = self._get_html_fragment(source)
        document = None

        if fragment is not None:
            document = self._create_empty_document()

            if self.site_lang is not None:
                document.getroot().set("lang", self.site_lang)

            head = document.find("head")

            article = document.find(".//body/main/article")
            article.append(fragment.element)
            if "lang" in fragment.metadata:
                article.set("lang", fragment.metadata["lang"])

            title_element = ET.SubElement(head, "title")
            title = fragment.metadata.get("title", None)

            if title is None:
                heading = fragment.element.find("h1")
                if heading is not None:
                    title = "".join(heading.itertext())

            if title is None:
                print(
                    "Warning: No title found. "
                    "You should add a level 1 heading or title metadata key.",
                    file=sys.stderr,
                )
                title = ""

            title_element.text = title

            for link in fragment.metadata.get("links", []):
                link_element = ET.SubElement(head, "link")
                if "rel" in link:
                    link_element.set("rel", link["rel"])
                if "href" in link:
                    link_element.set(
                        "href",
                        "/"
                        + self.asset_manager.translate(
                            os.path.join(os.path.dirname(source), link["href"]),
                        ),
                    )
                if "data-inherit" in link:
                    if link["data-inherit"] is True:
                        link_element.set("data-inherit", ".//head")
                    else:
                        link_element.set("data-inherit", link["data-inherit"])

            for script in fragment.metadata.get("scripts", []):
                script_element = ET.SubElement(head, "script")

                if "type" in script:
                    script_element.set("type", script["type"])
                if "src" in script:
                    if script.get("type", None) == "text/python":
                        script_element.set(
                            "src",
                            os.path.join(os.path.dirname(source), script["src"]),
                        )
                    else:
                        script_element.set(
                            "src",
                            "/"
                            + self.asset_manager.translate(
                                os.path.join(os.path.dirname(source), script["src"]),
                            ),
                        )
                if "data-inherit" in script:
                    if script["data-inherit"] is True:
                        script_element.set("data-inherit", ".//head")
                    else:
                        script_element.set("data-inherit", script["data-inherit"])

            for meta_name, meta_content in fragment.metadata.get("meta", {}).items():
                meta_element = ET.SubElement(head, "meta")
                meta_element.set("name", meta_name)
                meta_element.set("content", meta_content)

        print()
        return Document(
            source_path=source,
            content_dir=self.content_dir,
            dest_path=self._get_output_path(source),
            tree=document,
            metadata=fragment.metadata if fragment is not None else {},
            output_dir=self.output_path,
        )
