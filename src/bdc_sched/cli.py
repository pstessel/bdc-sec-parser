from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

from bdc_sched.config import load_settings
from bdc_sched.io.export_csv import maybe_write_parquet, rows_to_csv, rows_to_dataframe
from bdc_sched.io.manifests import load_manifest, save_manifest
from bdc_sched.normalize.investments import normalize_rows_to_investments
from bdc_sched.parse.schedule import parse_filing_file
from bdc_sched.qa.report import build_qa_report, write_qa_report
from bdc_sched.schema.contracts import validate_csv
from bdc_sched.sec.filings import build_primary_doc_url, download_text
from bdc_sched.sec.submissions import SecClient


def _load_universe(path: str = "configs/universe.yml"):
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f).get("bdcs", [])


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def _build_metadata_index(manifest_dir: Path) -> dict[tuple[str, str], dict]:
    idx: dict[tuple[str, str], dict] = {}
    for mf in sorted(manifest_dir.glob("*_recent.json")):
        try:
            rows = load_manifest(mf)
        except Exception as exc:
            print(f"manifest read failed for {mf}: {exc}")
            continue
        for row in rows:
            key = (str(row.get("ticker", "")).upper(), str(row.get("accessionNo", "")))
            idx[key] = row
    return idx


def cmd_fetch(args):
    settings = load_settings()
    client = SecClient(settings.sec_user_agent, settings.sec_requests_per_sec)
    bdcs = _load_universe(args.universe)

    forms = {f.strip().upper() for f in args.forms.split(",") if f.strip()}
    if args.include_amendments:
        forms = forms | {f"{f}/A" for f in list(forms)}

    cutoff = date.today() - timedelta(days=365 * max(args.years, 0))

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    total = 0
    for bdc in bdcs:
        sub = client.get_submissions(bdc["cik"])
        recent = sub.get("filings", {}).get("recent", {})
        items = []
        forms_arr = recent.get("form", [])
        filing_dates = recent.get("filingDate", [])

        for i, form in enumerate(forms_arr):
            if form.upper() not in forms:
                continue
            filing_date = filing_dates[i] if i < len(filing_dates) else None
            parsed_date = _parse_date(filing_date)
            if parsed_date and parsed_date < cutoff:
                continue

            items.append(
                {
                    "ticker": bdc["ticker"],
                    "cik": bdc["cik"],
                    "accessionNo": recent["accessionNumber"][i],
                    "filingDate": filing_date,
                    "reportDate": recent.get("reportDate", [None] * len(forms_arr))[i],
                    "primaryDocument": recent["primaryDocument"][i],
                    "form": form,
                }
            )
            if args.limit and len(items) >= args.limit:
                break

        save_manifest(out_dir / f"{bdc['ticker']}_recent.json", items)
        print(f"{bdc['ticker']}: wrote {len(items)} records")
        total += len(items)

    print(f"wrote {total} filing metadata records to {out_dir}")


def cmd_download(args):
    settings = load_settings()
    manifest_dir = Path(args.manifests)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    saved = 0
    for mf in sorted(manifest_dir.glob("*_recent.json")):
        rows = load_manifest(mf)
        selected = rows[: args.limit] if args.limit else rows
        for row in selected:
            url = build_primary_doc_url(row["cik"], row["accessionNo"], row["primaryDocument"])
            dest = out_dir / row["ticker"] / f"{row['accessionNo']}.html"
            try:
                download_text(url, settings.sec_user_agent, dest)
                saved += 1
            except Exception as e:
                print(f"download failed for {row['ticker']} {row['accessionNo']}: {e}")
    print(f"downloaded {saved} filing html documents to {out_dir}")


def cmd_parse(args):
    raw_dir = Path(args.raw)
    out_dir = Path(args.out)
    manifest_dir = Path(args.manifests)
    out_dir.mkdir(parents=True, exist_ok=True)

    metadata_index = _build_metadata_index(manifest_dir)

    html_files = sorted(raw_dir.glob("*/*.html"))
    if args.limit:
        html_files = html_files[: args.limit]

    all_rows: list[dict] = []
    parsed_files = 0
    for html_path in html_files:
        ticker = html_path.parent.name.upper()
        accession = html_path.stem
        meta = metadata_index.get((ticker, accession), {})
        metadata = {
            "ticker": ticker,
            "cik": meta.get("cik"),
            "accessionNo": accession,
            "filingDate": meta.get("filingDate"),
            "form": meta.get("form"),
        }

        try:
            rows = parse_filing_file(html_path, metadata)
        except Exception as exc:
            print(f"parse failed for {html_path}: {exc}")
            continue

        parsed_files += 1
        per_file_out = out_dir / ticker / f"{accession}.csv"
        rows_to_csv(rows, per_file_out)
        print(f"{ticker} {accession}: parsed {len(rows)} rows")
        all_rows.extend(rows)

    all_csv = out_dir / "all_rows.csv"
    all_df = rows_to_dataframe(all_rows)
    all_df.to_csv(all_csv, index=False)

    if args.parquet:
        maybe_write_parquet(all_df, out_dir / "all_rows.parquet")

    print(f"parsed {parsed_files} filing(s), wrote {len(all_rows)} total rows to {all_csv}")


def cmd_qa(args):
    parsed_csv = Path(args.input)
    if not parsed_csv.exists():
        raise FileNotFoundError(f"parsed csv not found: {parsed_csv}")

    df = rows_to_dataframe([])
    try:
        import pandas as pd

        df = pd.read_csv(parsed_csv)
    except Exception as exc:
        raise RuntimeError(f"failed reading parsed csv {parsed_csv}: {exc}") from exc

    report = build_qa_report(df)
    out_path = write_qa_report(report, args.out)

    if report.get("status") != "ok":
        print(f"qa failed: {report.get('error')}")
        return

    s = report["summary"]
    print(
        "qa summary: "
        f"rows={s['total_rows']}, filings={s['total_filings']}, "
        f"empty_raw_pct={s['empty_raw_pct']}%, numeric_zero_pct={s['numeric_count_zero_pct']}%, "
        f"duplicates={s['duplicate_key_rows']}, flagged_filings={s['flagged_filings']}"
    )
    print(f"qa report written to {out_path}")


def cmd_normalize(args):
    src = Path(args.input)
    if not src.exists():
        raise FileNotFoundError(f"parsed csv not found: {src}")

    import pandas as pd

    raw_df = pd.read_csv(src)
    norm_df = normalize_rows_to_investments(raw_df)

    if args.min_confidence is not None:
        norm_df = norm_df[norm_df["confidence"] >= float(args.min_confidence)]

    if args.drop_headers:
        norm_df = norm_df[~norm_df["is_header_like"]]

    out_csv = Path(args.out)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    norm_df.to_csv(out_csv, index=False)

    if args.parquet:
        maybe_write_parquet(norm_df, out_csv.with_suffix(".parquet"))

    print(f"normalized {len(norm_df)} rows to {out_csv}")


def cmd_validate(args):
    report = validate_csv(args.input, args.kind)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"schema report written to {out_path}")

    if report.get("status") == "ok":
        print(
            f"schema ok: kind={report['kind']} rows={report['rows']} "
            f"missing_columns={len(report['missing_columns'])} "
            f"type_mismatches={len(report.get('type_mismatches', {}))}"
        )
        return

    err = report.get("error")
    if err:
        print(f"schema validation failed: {err}")
    else:
        print(
            f"schema validation failed: kind={report.get('kind')} "
            f"missing_columns={report.get('missing_columns', [])} "
            f"type_mismatches={report.get('type_mismatches', {})}"
        )


def cmd_profile_layouts(args):
    src = Path(args.input)
    if not src.exists():
        raise FileNotFoundError(f"normalized csv not found: {src}")

    import pandas as pd

    df = pd.read_csv(src)
    if df.empty:
        print("no rows to profile")
        return

    dims = [c for c in ["ticker", "form", "layout_id", "period_focus"] if c in df.columns]
    if not dims:
        raise RuntimeError("normalized csv missing profiling columns")

    profile = (
        df.groupby(dims, dropna=False)
        .agg(
            rows=("row_index", "count"),
            avg_confidence=("confidence", "mean"),
            header_like_rows=("is_header_like", "sum"),
            total_rows=("is_total_row", "sum"),
            pipe_rows=("has_pipe_artifacts", "sum"),
        )
        .reset_index()
        .sort_values(["rows", "avg_confidence"], ascending=[False, False])
    )

    out_csv = Path(args.out)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    profile.to_csv(out_csv, index=False)
    print(f"wrote layout profile: {out_csv} ({len(profile)} groups)")


def main():
    ap = argparse.ArgumentParser("bdc-sched")
    sub = ap.add_subparsers(dest="cmd", required=True)

    f = sub.add_parser("fetch")
    f.add_argument("--universe", default="configs/universe.yml")
    f.add_argument("--forms", default="10-Q,10-K")
    f.add_argument("--include-amendments", action=argparse.BooleanOptionalAction, default=True)
    f.add_argument("--years", type=int, default=5)
    f.add_argument("--limit", type=int, default=0, help="0 means no per-file limit")
    f.add_argument("--out", default="out/manifests")
    f.set_defaults(func=cmd_fetch)

    d = sub.add_parser("download")
    d.add_argument("--manifests", default="out/manifests")
    d.add_argument("--out", default="out/raw_filings")
    d.add_argument("--limit", type=int, default=0, help="0 means no per-file limit")
    d.set_defaults(func=cmd_download)

    p = sub.add_parser("parse")
    p.add_argument("--raw", default="out/raw_filings")
    p.add_argument("--manifests", default="out/manifests")
    p.add_argument("--out", default="out/parsed")
    p.add_argument("--limit", type=int, default=0)
    p.add_argument("--parquet", action=argparse.BooleanOptionalAction, default=True)
    p.set_defaults(func=cmd_parse)

    q = sub.add_parser("qa")
    q.add_argument("--input", default="out/parsed/all_rows.csv")
    q.add_argument("--out", default="out/parsed/qa_report.json")
    q.set_defaults(func=cmd_qa)

    n = sub.add_parser("normalize")
    n.add_argument("--input", default="out/parsed/all_rows.csv")
    n.add_argument("--out", default="out/normalized/investments.csv")
    n.add_argument("--min-confidence", type=float, default=0.4)
    n.add_argument("--drop-headers", action=argparse.BooleanOptionalAction, default=True)
    n.add_argument("--parquet", action=argparse.BooleanOptionalAction, default=True)
    n.set_defaults(func=cmd_normalize)

    v = sub.add_parser("validate")
    v.add_argument("--kind", choices=["parsed", "normalized"], default="parsed")
    v.add_argument("--input", default="out/parsed/all_rows.csv")
    v.add_argument("--out", default="")
    v.set_defaults(func=cmd_validate)

    lp = sub.add_parser("profile-layouts")
    lp.add_argument("--input", default="out/normalized/investments.csv")
    lp.add_argument("--out", default="out/normalized/layout_profile.csv")
    lp.set_defaults(func=cmd_profile_layouts)

    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
