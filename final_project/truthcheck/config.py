"""Runtime configuration loaded from environment variables."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, replace
from pathlib import Path


def _load_dotenv(env_path: Path) -> None:
    """Minimal .env loader — no external dependency required."""
    if not env_path.is_file():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


@dataclass(frozen=True)
class Config:
    gemini_api_key: str
    model: str = "gemini-1.5-pro"
    log_level: str = "INFO"

    @classmethod
    def from_env(cls) -> Config:
        _load_dotenv(Path(__file__).parent.parent / ".env")

        key = os.getenv("GEMINI_API_KEY")
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. "
                "Add it to your .env file or export it in your shell."
            )

        return cls(
            gemini_api_key=key,
            model=os.getenv("TRUTHCHECK_MODEL", "gemini-1.5-pro"),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )

    def with_log_level(self, level: str) -> Config:
        return replace(self, log_level=level)

    def configure_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, self.log_level.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
