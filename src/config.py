"""Application configuration loaded from environment variables and local .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOK_PATH = PROJECT_ROOT / "data" / "novels" / "book.txt"
DEFAULT_INDEX_PATH = PROJECT_ROOT / "data" / "index" / "chunks.jsonl"
DEFAULT_TOP_K = 5
CHUNK_SIZE = 800
CHUNK_MAX_SIZE = 1000
CHUNK_OVERLAP = 3
DOTENV_PATH = PROJECT_ROOT / ".env"


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class EmbeddingConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 60


@dataclass(frozen=True)
class LLMConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 120


def load_dotenv(path: Path = DOTENV_PATH) -> None:
    """Load simple KEY=VALUE lines into os.environ without overriding existing values."""
    if not path.exists():
        return

    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue

        key, value = stripped.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def _required_env(name: str) -> str:
    load_dotenv()
    value = os.getenv(name)
    if not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value


def _normalize_base_url(value: str) -> str:
    return value.rstrip("/")


def load_embedding_config() -> EmbeddingConfig:
    return EmbeddingConfig(
        api_key=_required_env("EMBEDDING_API_KEY"),
        base_url=_normalize_base_url(_required_env("EMBEDDING_BASE_URL")),
        model=_required_env("EMBEDDING_MODEL"),
    )


def load_llm_config() -> LLMConfig:
    return LLMConfig(
        api_key=_required_env("LLM_API_KEY"),
        base_url=_normalize_base_url(_required_env("LLM_BASE_URL")),
        model=_required_env("LLM_MODEL"),
    )
