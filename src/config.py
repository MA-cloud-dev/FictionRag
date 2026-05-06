"""Application configuration loaded from environment variables and local .env."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_BOOK_PATH = PROJECT_ROOT / "data" / "novels" / "book.txt"
DEFAULT_INDEX_PATH = PROJECT_ROOT / "data" / "index" / "chunks.jsonl"
DEFAULT_ENTITIES_PATH = PROJECT_ROOT / "data" / "entities" / "entities.json"
DEFAULT_VISITOR_DB_PATH = PROJECT_ROOT / "data" / "visitor_usage.sqlite3"
DEFAULT_TOP_K = 5
VISITOR_DAILY_QUOTA = 5
CHUNK_SIZE = 800
CHUNK_MAX_SIZE = 1000
CHUNK_OVERLAP = 3
DOTENV_PATH = PROJECT_ROOT / ".env"
BAILIAN_COMPATIBLE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
BAILIAN_RERANKER_BASE_URL = "https://dashscope.aliyuncs.com/compatible-api/v1"
BAILIAN_LLM_MODEL = "qwen3.5-flash"
BAILIAN_EMBEDDING_MODEL = "text-embedding-v4"
BAILIAN_RERANKER_MODEL = "qwen3-rerank"


class ConfigError(RuntimeError):
    """Raised when required runtime configuration is missing."""


@dataclass(frozen=True)
class EmbeddingConfig:
    api_key: str
    base_url: str
    model: str
    timeout_seconds: int = 60


@dataclass(frozen=True)
class RerankerConfig:
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
    extra_body: dict[str, Any] | None = None


@dataclass(frozen=True)
class ModelRuntimeConfigs:
    embedding: EmbeddingConfig
    reranker: RerankerConfig
    llm: LLMConfig


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


def load_reranker_config() -> RerankerConfig:
    load_dotenv()
    api_key = os.getenv("RERANKER_API_KEY") or _required_env("EMBEDDING_API_KEY")
    base_url = os.getenv("RERANKER_BASE_URL") or _reranker_base_url_from_embedding(
        _required_env("EMBEDDING_BASE_URL")
    )
    model = os.getenv("RERANKER_MODEL") or "qwen3-rerank"
    return RerankerConfig(
        api_key=api_key,
        base_url=_normalize_base_url(base_url),
        model=model,
    )


def _reranker_base_url_from_embedding(embedding_base_url: str) -> str:
    normalized = _normalize_base_url(embedding_base_url)
    compatible_mode_suffix = "/compatible-mode/v1"
    if normalized.endswith(compatible_mode_suffix):
        return normalized[: -len(compatible_mode_suffix)] + "/compatible-api/v1"
    return normalized


def load_llm_config() -> LLMConfig:
    return LLMConfig(
        api_key=_required_env("LLM_API_KEY"),
        base_url=_normalize_base_url(_required_env("LLM_BASE_URL")),
        model=_required_env("LLM_MODEL"),
    )


def build_bailian_model_configs(api_key: str) -> ModelRuntimeConfigs:
    normalized_key = api_key.strip()
    if not normalized_key:
        raise ConfigError("api_key is required")
    return ModelRuntimeConfigs(
        embedding=EmbeddingConfig(
            api_key=normalized_key,
            base_url=BAILIAN_COMPATIBLE_BASE_URL,
            model=BAILIAN_EMBEDDING_MODEL,
        ),
        reranker=RerankerConfig(
            api_key=normalized_key,
            base_url=BAILIAN_RERANKER_BASE_URL,
            model=BAILIAN_RERANKER_MODEL,
        ),
        llm=LLMConfig(
            api_key=normalized_key,
            base_url=BAILIAN_COMPATIBLE_BASE_URL,
            model=BAILIAN_LLM_MODEL,
            extra_body={"enable_thinking": False},
        ),
    )
