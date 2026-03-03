from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from bs4 import Tag

from bdc_sched.parse.detect import build_soup, find_candidate_tables, find_schedule_headings

_NUM_RE = re.compile(r"[-+]?\d[\d,]*(?:\.\d+)?")

# Heuristics for table relevance
_POSITIVE_TABLE_HINTS = [
    "investment",
    "portfolio company",
    "principal",
    "amortized cost",
    "fair value",
    "% of net assets",
    "maturity",
    "interest",
    "industry",
]
_NEGATIVE_TABLE_HINTS = [
    "exhibit",
    "indenture",
    "notes due",
    "form of",
    "agreement",
    "trustee",
    # non-target financial statements often misdetected as schedule tables
    "consolidated balance sheet",
    "consolidated balance sheets",
    "statements of operations",
    "statement of operations",
    "comprehensive income",
    "statements of cash flows",
    "statement of cash flows",
    "stockholders' equity",
    "changes in stockholders",
    "net increase in net assets resulting from operations",
]


def normalize_text(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def parse_money(value: str) -> float | None:
    if value is None:
        return None
    s = normalize_text(str(value))
    if not s:
        return None

    s = s.replace("$", "").replace("%", "")
    s = s.replace("—", "-").replace("–", "-")

    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1]

    m = _NUM_RE.search(s)
    if not m:
        return None

    raw = m.group(0).replace(",", "")
    try:
        val = float(raw)
    except ValueError:
        return None
    return -val if negative else val


def _table_text(table: Tag) -> str:
    return normalize_text(table.get_text(" ", strip=True)).lower()


def table_looks_like_schedule(table: Tag) -> bool:
    txt = _table_text(table)

    pos = sum(1 for k in _POSITIVE_TABLE_HINTS if k in txt)
    neg = sum(1 for k in _NEGATIVE_TABLE_HINTS if k in txt)

    # Hard-reject obvious non-target financial statements.
    strong_non_target = [
        "consolidated balance sheet",
        "consolidated balance sheets",
        "statements of operations",
        "statement of operations",
        "comprehensive income",
        "statements of cash flows",
        "statement of cash flows",
        "stockholders' equity",
        "changes in stockholders",
    ]
    if any(k in txt for k in strong_non_target):
        return False

    # Require some schedule flavor and avoid obvious exhibit/legal tables.
    if neg >= 2:
        return False
    if pos >= 2:
        return True

    # Fallback: look for multiple rows that contain at least 2 numeric-like values.
    numeric_rows = 0
    for tr in table.find_all("tr")[:120]:
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue
        cell_texts = [normalize_text(c.get_text(" ", strip=True)) for c in cells]
        count = sum(1 for t in cell_texts if parse_money(t) is not None)
        if count >= 2:
            numeric_rows += 1
        if numeric_rows >= 8:
            break

    return numeric_rows >= 8 and neg == 0


def table_to_records(table: Tag, metadata: dict[str, Any], table_index: int = 0) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []

    for row_idx, tr in enumerate(table.find_all("tr")):
        cells = tr.find_all(["td", "th"])
        if not cells:
            continue

        cell_texts = [normalize_text(c.get_text(" ", strip=True)) for c in cells]
        if not any(cell_texts):
            continue

        parsed_numbers = [n for n in (parse_money(t) for t in cell_texts) if n is not None]

        rec: dict[str, Any] = {
            **metadata,
            "table_index": table_index,
            "row_index": row_idx,
            "raw_row_text": " | ".join(cell_texts),
            "cells_json": json.dumps(cell_texts, ensure_ascii=False),
            "numeric_count": len(parsed_numbers),
            "first_numeric": parsed_numbers[0] if parsed_numbers else None,
            "last_numeric": parsed_numbers[-1] if parsed_numbers else None,
        }
        for i, num in enumerate(parsed_numbers[:4], start=1):
            rec[f"numeric_{i}"] = num

        records.append(rec)

    return records


def parse_schedule_rows(html: str, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    soup = build_soup(html)
    heading_nodes = find_schedule_headings(soup)
    heading_text = normalize_text(heading_nodes[0].get_text(" ", strip=True)) if heading_nodes else None

    tables = find_candidate_tables(html)
    all_rows: list[dict[str, Any]] = []
    kept = 0
    for idx, table in enumerate(tables):
        if not table_looks_like_schedule(table):
            continue
        kept += 1
        table_rows = table_to_records(table, {**metadata, "heading": heading_text}, table_index=idx)
        all_rows.extend(table_rows)

    # Safety fallback: only keep first candidate when a schedule heading was found.
    # This avoids pulling random first-table content (e.g., exhibit indexes) in filings
    # that do not appear to contain a schedule of investments section.
    if not all_rows and tables and heading_text:
        table_rows = table_to_records(
            tables[0],
            {**metadata, "heading": heading_text, "filter_fallback": True},
            table_index=0,
        )
        all_rows.extend(table_rows)

    return all_rows


def parse_filing_file(path: Path, metadata: dict[str, Any]) -> list[dict[str, Any]]:
    html = path.read_text(encoding="utf-8", errors="ignore")
    return parse_schedule_rows(html, {**metadata, "source_file": str(path)})
