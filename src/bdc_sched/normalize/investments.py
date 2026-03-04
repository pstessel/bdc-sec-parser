from __future__ import annotations

import json
import re
from typing import Any

import pandas as pd

_TOTAL_RE = re.compile(r"\btotal\b", re.I)
_HEADER_RE = re.compile(r"schedule\s+of\s+investments?|consolidated", re.I)
_FOOTNOTE_RE = re.compile(r"\(([a-z0-9]{1,3})\)", re.I)
_PERIOD_PRIOR_RE = re.compile(r"\b(prior|previous|12/31|year\s*end|fiscal\s*year\s*end)\b", re.I)
_PERIOD_CURRENT_RE = re.compile(r"\b(current|three\s+months\s+ended|quarter\s+ended|as\s+of)\b", re.I)


NUMERICISH_RE = re.compile(r"[-$(),.%0-9\s]+")


def _safe_list_from_json(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(x) for x in value]
    s = str(value).strip()
    if not s:
        return []
    try:
        parsed = json.loads(s)
        if isinstance(parsed, list):
            return [str(x) for x in parsed]
    except Exception:
        pass
    return [s]


def _clean_cell_text(text: str) -> str:
    t = str(text or "").replace("\xa0", " ")
    t = re.sub(r"\s*\|\s*", " | ", t)
    t = re.sub(r"\s+", " ", t).strip(" |")
    return t.strip()


def _expand_pipe_cells(cells: list[str], raw_row_text: str) -> list[str]:
    base = cells or []
    if not base and raw_row_text:
        base = [raw_row_text]

    out: list[str] = []
    for c in base:
        cleaned = _clean_cell_text(c)
        if not cleaned:
            continue
        if "|" in cleaned:
            parts = [p.strip() for p in cleaned.split("|")]
            out.extend([p for p in parts if p])
        else:
            out.append(cleaned)
    return out


def _extract_issuer(cells: list[str], raw_row_text: str) -> str | None:
    for cell in cells:
        c = str(cell).strip()
        if c and not NUMERICISH_RE.fullmatch(c):
            return c
    txt = str(raw_row_text).strip()
    return txt[:180] if txt else None


def _extract_business_description(cells: list[str], layout_id: str) -> str | None:
    if layout_id in {"arcc_sched_v1", "main_sched_v1"} and len(cells) >= 2:
        c = str(cells[1]).strip()
        return c or None
    return None


def _extract_instrument_text(cells: list[str], layout_id: str) -> str | None:
    # ARCC/MAIN dominant layouts generally place investment/instrument text in col 3.
    if layout_id in {"arcc_sched_v1", "main_sched_v1"} and len(cells) >= 3:
        c = str(cells[2]).strip()
        return c or None
    return None


def _extract_industry_group(cells: list[str], is_header_like: bool, numeric_count: int) -> str | None:
    # Best-effort: header-like row with little/no numeric data and short text often indicates group bucket.
    if not is_header_like or numeric_count > 0:
        return None
    if len(cells) == 1:
        c = str(cells[0]).strip()
        if c and len(c) <= 80 and "schedule" not in c.lower() and "investments" not in c.lower():
            return c
    return None


def _confidence(numeric_count: int, is_header_like: bool, is_total_row: bool, has_pipe_artifacts: bool) -> float:
    score = 0.2
    if numeric_count >= 2:
        score += 0.5
    elif numeric_count == 1:
        score += 0.25
    if is_header_like:
        score -= 0.35
    if is_total_row:
        score -= 0.2
    if has_pipe_artifacts:
        score -= 0.05
    return max(0.0, min(1.0, round(score, 3)))


def _derive_layout_id(text: str, ticker: str = "") -> str:
    t = (text or "").lower()
    tk = (ticker or "").upper()

    # issuer-specific dominant layouts
    if tk == "ARCC" and all(k in t for k in ["portfolio company", "business description", "type of investment", "amortized cost", "fair value"]):
        return "arcc_sched_v1"
    if tk == "MAIN" and all(k in t for k in ["portfolio company", "business", "type of investment", "cost", "fair value"]):
        return "main_sched_v1"

    has_rate = any(k in t for k in ["interest", "rate", "spread", "cash", "pik"])
    has_maturity = "maturity" in t
    has_cost = any(k in t for k in ["amortized cost", "amortised cost", "cost"])  # UK spelling safety
    has_fv = any(k in t for k in ["fair value", "market value"])

    if has_rate and has_maturity and has_cost and has_fv:
        return "sched_v1_rate_maturity_cost_fv"
    if has_cost and has_fv and has_maturity:
        return "sched_v2_maturity_cost_fv"
    if has_cost and has_fv:
        return "sched_v3_cost_fv"
    if has_maturity and has_fv:
        return "sched_v4_maturity_fv"
    return "sched_unknown"


def _period_focus(raw: str, form: str | None, table_text: str = "") -> str:
    text = f"{raw or ''} {table_text or ''}".lower()
    has_prior = bool(_PERIOD_PRIOR_RE.search(text))
    has_current = bool(_PERIOD_CURRENT_RE.search(text))
    if has_prior and has_current:
        return "comparative"
    if has_prior:
        return "prior"
    if has_current:
        return "current"

    f = (form or "").upper()
    if f.startswith("10-Q"):
        return "quarterly"
    if f.startswith("10-K"):
        return "annual"
    return "unknown"


def _table_key(row: dict[str, Any]) -> tuple[str, str, str, str]:
    return (
        str(row.get("ticker", "")),
        str(row.get("accessionNo", "")),
        str(row.get("source_file", "")),
        str(row.get("table_index", "")),
    )


def normalize_rows_to_investments(df: pd.DataFrame) -> pd.DataFrame:
    prep: list[dict[str, Any]] = []
    table_header_text: dict[tuple[str, str, str, str], list[str]] = {}

    for _, row in df.iterrows():
        raw = str(row.get("raw_row_text", "") or "").strip()
        numeric_count = int(pd.to_numeric(row.get("numeric_count"), errors="coerce") or 0)

        source_cells = _safe_list_from_json(row.get("cells_json"))
        cells = _expand_pipe_cells(source_cells, raw)
        has_pipe_artifacts = "|" in raw or any("|" in str(c) for c in source_cells)

        is_total_row = bool(_TOTAL_RE.search(raw))
        is_header_like = bool(_HEADER_RE.search(raw)) or (numeric_count == 0)

        rec = {
            "row": row,
            "raw": raw,
            "cells": cells,
            "numeric_count": numeric_count,
            "has_pipe_artifacts": has_pipe_artifacts,
            "is_total_row": is_total_row,
            "is_header_like": is_header_like,
            "key": _table_key(row),
        }
        prep.append(rec)

        if is_header_like or numeric_count <= 1:
            joined = " ; ".join(cells) if cells else raw
            if joined:
                table_header_text.setdefault(rec["key"], []).append(joined)

    table_profile: dict[tuple[str, str, str, str], dict[str, str]] = {}
    for key, parts in table_header_text.items():
        table_text = " | ".join(parts)
        table_profile[key] = {
            "layout_id": _derive_layout_id(table_text, key[0]),
            "table_text": table_text,
        }

    out: list[dict[str, Any]] = []
    for item in prep:
        row = item["row"]
        raw = item["raw"]
        cells = item["cells"]
        numeric_count = item["numeric_count"]
        is_total_row = item["is_total_row"]
        is_header_like = item["is_header_like"]
        has_pipe_artifacts = item["has_pipe_artifacts"]

        nums = []
        for k in ["numeric_1", "numeric_2", "numeric_3", "numeric_4", "first_numeric", "last_numeric"]:
            v = pd.to_numeric(row.get(k), errors="coerce")
            if pd.notna(v):
                nums.append(float(v))

        principal_estimate = nums[0] if nums else None
        cost_estimate = nums[-2] if len(nums) >= 2 else (nums[0] if len(nums) == 1 else None)
        fair_value_estimate = nums[-1] if nums else None

        footnotes = sorted(set(m.group(1) for m in _FOOTNOTE_RE.finditer(raw)))
        profile = table_profile.get(item["key"], {"layout_id": "sched_unknown", "table_text": ""})

        row_layout = _derive_layout_id(" ".join(cells + [raw]), str(row.get("ticker", "")))
        final_layout = profile["layout_id"] if profile["layout_id"] != "sched_unknown" else row_layout

        out.append(
            {
                "ticker": row.get("ticker"),
                "cik": row.get("cik"),
                "accessionNo": row.get("accessionNo"),
                "filingDate": row.get("filingDate"),
                "form": row.get("form"),
                "source_file": row.get("source_file"),
                "table_index": row.get("table_index"),
                "row_index": row.get("row_index"),
                "issuer_name": _extract_issuer(cells, raw),
                "business_description": _extract_business_description(cells, final_layout),
                "instrument_text": _extract_instrument_text(cells, final_layout),
                "industry_group": _extract_industry_group(cells, is_header_like, numeric_count),
                "raw_row_text": raw,
                "clean_row_text": " ; ".join(cells),
                "cells_json": json.dumps(cells, ensure_ascii=False),
                "numeric_count": numeric_count,
                "principal_estimate": principal_estimate,
                "cost_estimate": cost_estimate,
                "fair_value_estimate": fair_value_estimate,
                "is_total_row": is_total_row,
                "is_header_like": is_header_like,
                "has_pipe_artifacts": has_pipe_artifacts,
                "layout_id": final_layout,
                "period_focus": _period_focus(raw, row.get("form"), profile.get("table_text", "")),
                "footnote_refs": ",".join(footnotes) if footnotes else None,
                "confidence": _confidence(numeric_count, is_header_like, is_total_row, has_pipe_artifacts),
            }
        )

    return pd.DataFrame(out)
