"""OpenAI-compatible embedding client."""

from __future__ import annotations

import time
from typing import Any

import requests

from .config import EmbeddingConfig


class APIError(RuntimeError):
    """Raised when an external API call fails or returns an invalid payload."""


class EmbeddingClient:
    def __init__(self, config: EmbeddingConfig) -> None:
        self.config = config

    def embed_text(self, text: str) -> list[float]:
        return self._embed_batch([text])[0]

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        embeddings: list[list[float]] = []
        batch_size = 10 if self.config.model == "qwen3-vl-embedding" else 1
        for start in range(0, len(texts), batch_size):
            embeddings.extend(self._embed_batch(texts[start : start + batch_size]))
        return embeddings

    def _embed_batch(self, texts: list[str]) -> list[list[float]]:
        if self.config.model == "qwen3-vl-embedding":
            return self._embed_dashscope_multimodal(texts)

        payload = {
            "model": self.config.model,
            "input": texts,
        }
        response = self._post("/embeddings", payload)
        data = response.get("data")
        if not isinstance(data, list):
            raise APIError("Embedding API response missing 'data' list")

        try:
            sorted_data = sorted(data, key=lambda item: item.get("index", 0))
            embeddings = [item["embedding"] for item in sorted_data]
        except (KeyError, TypeError) as exc:
            raise APIError("Embedding API response has invalid embedding data") from exc

        if len(embeddings) != len(texts):
            raise APIError(
                f"Embedding API returned {len(embeddings)} embeddings for {len(texts)} inputs"
            )
        return embeddings

    def _embed_dashscope_multimodal(self, texts: list[str]) -> list[list[float]]:
        payload = {
            "model": self.config.model,
            "input": {
                "contents": [{"text": text} for text in texts],
            },
        }
        response = self._post(self._dashscope_multimodal_path(), payload)
        try:
            data = response["output"]["embeddings"]
            sorted_data = sorted(data, key=lambda item: item.get("index", 0))
            embeddings = [item["embedding"] for item in sorted_data]
        except (KeyError, TypeError) as exc:
            raise APIError("DashScope multimodal embedding response is invalid") from exc

        if len(embeddings) != len(texts):
            raise APIError(
                f"Embedding API returned {len(embeddings)} embeddings for {len(texts)} inputs"
            )
        return embeddings

    def _dashscope_multimodal_path(self) -> str:
        compatible_suffix = "/compatible-mode/v1"
        native_endpoint = "/api/v1/services/embeddings/multimodal-embedding/multimodal-embedding"
        if self.config.base_url.endswith(native_endpoint):
            return ""
        if self.config.base_url.endswith(compatible_suffix):
            self.config = type(self.config)(
                api_key=self.config.api_key,
                base_url=self.config.base_url[: -len(compatible_suffix)],
                model=self.config.model,
                timeout_seconds=self.config.timeout_seconds,
            )
        return native_endpoint

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = f"{self.config.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        last_error: requests.RequestException | None = None
        for attempt in range(1, 4):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.config.timeout_seconds,
                )
                response.raise_for_status()
                break
            except requests.RequestException as exc:
                last_error = exc
                status_code = exc.response.status_code if exc.response is not None else None
                if attempt == 3 or (status_code is not None and status_code < 500):
                    raise APIError(f"Embedding API request failed: {exc}") from exc
                time.sleep(attempt)
        else:
            raise APIError(f"Embedding API request failed: {last_error}")

        try:
            body = response.json()
        except ValueError as exc:
            raise APIError("Embedding API response is not valid JSON") from exc
        if not isinstance(body, dict):
            raise APIError("Embedding API response JSON must be an object")
        return body
