from __future__ import annotations
from pathlib import Path
import requests

ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"


def build_primary_doc_url(cik: str, accession_no: str, primary_doc: str) -> str:
    cik_nozeros = str(int(str(cik)))
    accession_nodash = accession_no.replace("-", "")
    return f"{ARCHIVES_BASE}/{cik_nozeros}/{accession_nodash}/{primary_doc}"


def download_text(url: str, user_agent: str, out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    r = requests.get(url, headers={"User-Agent": user_agent}, timeout=45)
    r.raise_for_status()
    out_path.write_text(r.text, encoding="utf-8", errors="ignore")
    return out_path
