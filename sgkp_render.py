"""Render source Markdown as a restricted HTML fragment for entry details."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser
from urllib.parse import urlsplit

import markdown
from markdown.extensions.tables import TableExtension


TABLE_SEPARATOR = re.compile(r"\|\s*:?-{3,}:?\s*\|")
TABLE_ROW_BOUNDARY = re.compile(r"(?<=\|) (?=\|)")
ALLOWED_TAGS = frozenset({
    "a", "b", "blockquote", "br", "code", "del", "em", "h1", "h2", "h3", "h4", "h5", "h6",
    "hr", "i", "li", "ol", "p", "pre", "strong", "sub", "sup", "table", "tbody", "td",
    "tfoot", "th", "thead", "tr", "ul",
})
VOID_TAGS = frozenset({"br", "hr"})
DROP_CONTENT = frozenset({"script", "style", "iframe", "object", "embed", "svg", "math", "template"})


def normalize_tables(source: str) -> str:
    """Restore row breaks lost when OCR flattened a pipe table onto one line."""
    lines = []
    for line in source.splitlines():
        if line.lstrip().startswith("|") and "| |" in line and TABLE_SEPARATOR.search(line):
            line = TABLE_ROW_BOUNDARY.sub("\n", line)
        lines.append(line)
    return "\n".join(lines)


class _SafeFragment(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.open_tags: list[str] = []
        self.blocked: list[str] = []

    def handle_starttag(self, tag, attrs):
        if self.blocked:
            if tag in DROP_CONTENT:
                self.blocked.append(tag)
            return
        if tag in DROP_CONTENT:
            self.blocked.append(tag)
            return
        if tag not in ALLOWED_TAGS:
            return
        safe_attrs = []
        if tag == "a":
            href = next((value for name, value in attrs if name == "href"), None)
            if href:
                try:
                    url = urlsplit(href.strip())
                except ValueError:
                    url = None
                if url and url.scheme in ("http", "https") and url.netloc:
                    safe_attrs = [("href", href.strip()), ("target", "_blank"), ("rel", "noopener noreferrer")]
        elif tag in ("th", "td"):
            align = next((value for name, value in attrs if name == "align"), None)
            if align in ("left", "center", "right"):
                safe_attrs = [("align", align)]
        attributes = "".join(f' {name}="{html.escape(value, quote=True)}"' for name, value in safe_attrs)
        self.parts.append(f"<{tag}{attributes}>")
        if tag not in VOID_TAGS:
            self.open_tags.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_TAGS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.blocked:
            if tag == self.blocked[-1]:
                self.blocked.pop()
            return
        if tag in self.open_tags:
            while self.open_tags:
                current = self.open_tags.pop()
                self.parts.append(f"</{current}>")
                if current == tag:
                    break

    def handle_data(self, data):
        if not self.blocked:
            self.parts.append(html.escape(data))

    def render(self, source: str) -> str:
        self.feed(source)
        self.close()
        while self.open_tags:
            self.parts.append(f"</{self.open_tags.pop()}>")
        return "".join(self.parts)


def render_entry_markdown(source: str) -> str:
    rendered = markdown.markdown(normalize_tables(source), extensions=[TableExtension(use_align_attribute=True)])
    return _SafeFragment().render(rendered)
