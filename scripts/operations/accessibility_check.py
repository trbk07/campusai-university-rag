"""Static accessibility smoke check for the dependency-free demo UI."""

from __future__ import annotations

import argparse
from html.parser import HTMLParser
from pathlib import Path


class AccessibilityParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.tags: list[str] = []
        self.ids: set[str] = set()
        self.labels_for: set[str] = set()
        self.aria_live = False
        self.lang = False
        self.viewport = False
        self.headings = 0
        self.buttons = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.tags.append(tag)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "label" and values.get("for"):
            self.labels_for.add(values["for"])
        if tag == "html" and values.get("lang"):
            self.lang = True
        if tag == "meta" and values.get("name") == "viewport":
            self.viewport = True
        if values.get("aria-live"):
            self.aria_live = True
        if tag in {"h1", "h2"}:
            self.headings += 1
        if tag == "button":
            self.buttons += 1


def check(html: str) -> list[str]:
    parser = AccessibilityParser()
    parser.feed(html)
    errors = []
    if not parser.lang:
        errors.append("html_lang_missing")
    if not parser.viewport:
        errors.append("viewport_missing")
    if parser.headings < 2:
        errors.append("heading_structure_missing")
    if not parser.aria_live:
        errors.append("status_live_region_missing")
    for control_id in {"question"}:
        if control_id not in parser.labels_for:
            errors.append(f"label_missing_{control_id}")
    if parser.buttons < 1:
        errors.append("submit_control_missing")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path)
    args = parser.parse_args()
    if args.html:
        html = args.html.read_text(encoding="utf-8")
    else:
        from campusai.web import INDEX_HTML
        html = INDEX_HTML
    errors = check(html)
    print({"status": "pass" if not errors else "fail", "errors": errors})
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
