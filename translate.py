#!/usr/bin/env python3
"""
Auto-translate missing Chinese content in BB Marble HTML files.

Usage:
    python3 translate.py              # translate index.html and projects.html
    python3 translate.py --dry-run    # show what would be translated, don't write
    python3 translate.py index.html   # translate a specific file

Requires: pip3 install anthropic beautifulsoup4 lxml
Requires: ANTHROPIC_API_KEY environment variable set
"""

import json
import os
import re
import sys
from pathlib import Path

import anthropic
from bs4 import BeautifulSoup, NavigableString, Tag

# Each (en_class, zh_class) pair the site uses
PAIRS = [
    ("en", "zh-text"),
    ("en-block", "zh-block"),
    ("en-flex", "zh-flex"),
]

FILES = ["index.html", "projects.html", "blog.html", "blog-choosing-stone-fabricator.html"]

SITE_DIR = Path(__file__).parent


def inner_html(tag: Tag) -> str:
    return "".join(str(c) for c in tag.children)


def is_empty(tag: Tag) -> bool:
    return tag.get_text(strip=True) == ""


def collect_missing(soup: BeautifulSoup) -> list[dict]:
    """Return list of {en_tag, zh_tag, en_html} for every pair missing a translation."""
    missing = []
    for en_class, zh_class in PAIRS:
        for en_tag in soup.find_all(class_=en_class):
            # Look for the immediately following sibling with zh class
            zh_tag = en_tag.find_next_sibling(class_=zh_class)
            if zh_tag is None or is_empty(zh_tag):
                missing.append({
                    "en_tag": en_tag,
                    "zh_tag": zh_tag,
                    "en_html": inner_html(en_tag),
                    "zh_class": zh_class,
                })
    return missing


def translate_batch(items: list[dict], client: anthropic.Anthropic) -> list[str]:
    """
    Send all untranslated strings to Claude in one call.
    Returns list of translated HTML strings in the same order.
    """
    numbered = [
        {"id": i, "html": item["en_html"]}
        for i, item in enumerate(items)
    ]

    prompt = f"""You are translating content for B&B Marble, a premium natural stone fabrication and installation company in the San Francisco Bay Area.

Translate the English HTML snippets below into Simplified Chinese (简体中文).

Rules:
- Preserve ALL HTML tags exactly (e.g. <br>, <em>, <strong>, &amp;, &quot;)
- Use natural, professional Simplified Chinese — not word-for-word literal
- Keep the same tone: luxury, craftsmanship, precision
- For proper nouns (stone names like Calacatta, Statuario, brand names like Cambria/MSI/Silestone/Dekton, place names, licence numbers) keep the original English
- For quotation marks in testimonials, use 「 」 instead of " "
- Return ONLY a JSON array — no explanation, no markdown fences

Input:
{json.dumps(numbered, ensure_ascii=False, indent=2)}

Return format (same length, same order):
[
  {{"id": 0, "zh_html": "..."}},
  {{"id": 1, "zh_html": "..."}},
  ...
]"""

    message = client.messages.create(
        model="claude-opus-4-7",
        max_tokens=8192,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip markdown code fences if Claude adds them anyway
    raw = re.sub(r"^```[a-z]*\n?", "", raw)
    raw = re.sub(r"\n?```$", "", raw)

    results = json.loads(raw)
    # Sort by id to guarantee order
    results.sort(key=lambda x: x["id"])
    return [r["zh_html"] for r in results]


def apply_translations(soup: BeautifulSoup, items: list[dict], translations: list[str]) -> None:
    for item, zh_html in zip(items, translations):
        en_tag: Tag = item["en_tag"]
        zh_tag: Tag | None = item["zh_tag"]
        zh_class: str = item["zh_class"]

        if zh_tag is None:
            # Create a new sibling span right after the en tag
            new_tag = soup.new_tag("span")
            new_tag["class"] = [zh_class]
            en_tag.insert_after(new_tag)
            zh_tag = new_tag

        # Clear existing content and set new translated HTML
        zh_tag.clear()
        frag = BeautifulSoup(zh_html, "lxml").body
        if frag:
            for child in list(frag.children):
                zh_tag.append(child.__copy__() if isinstance(child, Tag) else NavigableString(str(child)))


def process_file(path: Path, client: anthropic.Anthropic, dry_run: bool) -> None:
    print(f"\n{'='*60}")
    print(f"File: {path.name}")

    html = path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "lxml")

    missing = collect_missing(soup)

    if not missing:
        print("  No missing translations — nothing to do.")
        return

    print(f"  Found {len(missing)} span(s) needing translation:")
    for item in missing:
        preview = BeautifulSoup(item["en_html"], "lxml").get_text()[:80]
        print(f"    [{item['zh_class']}] {preview!r}")

    if dry_run:
        print("  (dry-run: skipping API call and file write)")
        return

    print(f"  Translating via Claude API...")
    translations = translate_batch(missing, client)

    apply_translations(soup, missing, translations)

    # Serialise — lxml wraps in <html><body>, strip that back out
    # We want to preserve the original file structure exactly
    output = str(soup)
    # lxml adds <!DOCTYPE html> and wraps — recover the original structure
    # by replacing just the body content
    output = reconstruct_html(html, soup)

    path.write_text(output, encoding="utf-8")
    print(f"  Done. Wrote {len(translations)} translation(s) to {path.name}")


def reconstruct_html(original: str, soup: BeautifulSoup) -> str:
    """
    BeautifulSoup/lxml may mangle the outer HTML structure.
    We serialise each modified tag individually and stitch them back.
    This preserves DOCTYPE, <html lang=...>, scripts, etc.
    """
    # Re-parse with html.parser (less aggressive) for output
    soup2 = BeautifulSoup(original, "html.parser")

    for en_class, zh_class in PAIRS:
        for zh_tag_new in soup.find_all(class_=zh_class):
            new_html = str(zh_tag_new)
            # Find matching tag in soup2 by walking to the same position
            # Match by preceding en sibling text
            en_tag_new = zh_tag_new.find_previous_sibling(class_=en_class)
            if en_tag_new is None:
                continue
            en_text = en_tag_new.get_text(strip=True)[:60]

            # Find the corresponding en tag in soup2
            for en_tag_orig in soup2.find_all(class_=en_class):
                if en_tag_orig.get_text(strip=True)[:60] == en_text:
                    zh_tag_orig = en_tag_orig.find_next_sibling(class_=zh_class)
                    if zh_tag_orig is not None:
                        zh_tag_orig.replace_with(BeautifulSoup(new_html, "html.parser"))
                    else:
                        en_tag_orig.insert_after(BeautifulSoup(new_html, "html.parser"))
                    break

    return str(soup2)


def main() -> None:
    args = sys.argv[1:]
    dry_run = "--dry-run" in args
    args = [a for a in args if a != "--dry-run"]

    # Determine which files to process
    if args:
        targets = [SITE_DIR / a for a in args]
    else:
        targets = [SITE_DIR / f for f in FILES]

    targets = [t for t in targets if t.exists()]
    if not targets:
        print("No HTML files found to process.")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and not dry_run:
        print("Error: ANTHROPIC_API_KEY environment variable is not set.")
        print("Get your key at https://console.anthropic.com/")
        print("Then run:  export ANTHROPIC_API_KEY=sk-ant-...")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key) if api_key else None

    for path in targets:
        process_file(path, client, dry_run)

    print("\nAll done.")


if __name__ == "__main__":
    main()
