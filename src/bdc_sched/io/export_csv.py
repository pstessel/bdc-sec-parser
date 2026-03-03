from __future__ import annotations

from pathlib import Path

import pandas as pd


def rows_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    return pd.DataFrame(rows)


def rows_to_csv(rows: list[dict], path: str | Path) -> pd.DataFrame:
    df = rows_to_dataframe(rows)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(p, index=False)
    return df


def maybe_write_parquet(df: pd.DataFrame, path: str | Path) -> bool:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        df.to_parquet(p, index=False)
    except Exception as exc:
        msg = str(exc).lower()
        if "pyarrow" in msg or "fastparquet" in msg or "engine" in msg:
            print(f"parquet skipped: optional dependency not available ({exc})")
            return False
        print(f"parquet skipped: {exc}")
        return False
    return True
