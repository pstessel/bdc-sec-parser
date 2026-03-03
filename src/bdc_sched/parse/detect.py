from __future__ import annotations

import re
import warnings
from typing import Iterable

from bs4 import BeautifulSoup, Tag, XMLParsedAsHTMLWarning

HEADING_RE = re.compile(r"consolidated\s+schedule(?:s)?\s+of\s+investments?", re.I)


def build_soup(document: str) -> BeautifulSoup:
    # SEC primary docs are usually HTML; some filings arrive as XML/XBRL-like content.
    # Parse XML-ish content with XML parser to avoid noisy warnings and improve reliability.
    snippet = document.lstrip()[:400].lower()
    parser = "xml" if snippet.startswith("<?xml") or "<xbrl" in snippet else "lxml"
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)
        return BeautifulSoup(document, parser)


def find_schedule_headings(soup: BeautifulSoup) -> list[Tag]:
    hits = soup.find_all(string=HEADING_RE)
    out: list[Tag] = []
    for h in hits:
        parent = getattr(h, "parent", None)
        if isinstance(parent, Tag):
            out.append(parent)
    return out


def _iter_next_tables(node: Tag, max_tables: int = 3) -> Iterable[Tag]:
    found = 0
    for nxt in node.find_all_next("table"):
        if not isinstance(nxt, Tag):
            continue
        yield nxt
        found += 1
        if found >= max_tables:
            break


def find_candidate_tables(html: str, max_tables_per_heading: int = 2) -> list[Tag]:
    soup = build_soup(html)
    candidates: list[Tag] = []
    seen: set[int] = set()

    for heading in find_schedule_headings(soup):
        for table in _iter_next_tables(heading, max_tables=max_tables_per_heading):
            table_id = id(table)
            if table_id in seen:
                continue
            seen.add(table_id)
            candidates.append(table)

    # Fallback for filings where heading text differs or is outside nearby table structure.
    if not candidates:
        all_tables = [t for t in soup.find_all("table") if isinstance(t, Tag)]
        all_tables.sort(key=lambda t: len(t.get_text(" ", strip=True)), reverse=True)
        for table in all_tables[:40]:
            table_id = id(table)
            if table_id in seen:
                continue
            seen.add(table_id)
            candidates.append(table)

    return candidates
