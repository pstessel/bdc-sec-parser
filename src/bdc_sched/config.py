from __future__ import annotations
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    sec_user_agent: str
    sec_requests_per_sec: float = 5.0


def _load_dotenv_if_present(path: str = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        os.environ.setdefault(k, v)


def load_settings() -> Settings:
    _load_dotenv_if_present()
    ua = os.getenv("SEC_USER_AGENT", "").strip()
    if not ua:
        raise RuntimeError("SEC_USER_AGENT is not set")
    rps = float(os.getenv("SEC_REQUESTS_PER_SEC", "5"))
    return Settings(sec_user_agent=ua, sec_requests_per_sec=rps)
