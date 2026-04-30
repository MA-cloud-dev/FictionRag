"""DashScope-compatible reranker client."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import requests

from .config import RerankerConfig
from .embeddings import APIError


@dataclass(frozen=True)
class RerankResult:
    index: int
    score: float


class RerankerClient:
    def __init__(self, config: RerankerConfig) -> None:
        self.config = config

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: int | None = None,
        instruction: str | None = None,
    ) -> list[RerankResult]:
        if not query.strip():
            raise ValueError("query cannot be empty")
        if not documents:
            return []
        if top_n is not None and top_n <= 0:
            raise ValueError("top_n must be greater than 0")

        payload: dict[str, Any] = {
            "model": self.config.model,
            "query": query,
            "documents": documents,
        }
        if top_n is not None:
            payload["top_n"] = min(top_n, len(documents))
        if instruction:
            payload["instruct"] = instruction

        response = self._post("/reranks", payload)
        results = response.get("results")
        if not isinstance(results, list):
            raise APIError("Reranker API response missing 'results' list")

        reranked: list[RerankResult] = []
        for item in results:
            try:
                reranked.append(
                    RerankResult(
                        index=int(item["index"]),
                        score=float(item["relevance_score"]),
                    )
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise APIError("Reranker API response has invalid result data") from exc
        return reranked

    def score(self, query: str, documents: list[str]) -> list[float]:
        reranked = self.rerank(query=query, documents=documents, top_n=len(documents))
        scores = [0.0] * len(documents)
        for result in reranked:
            if result.index < 0 or result.index >= len(documents):
                raise APIError("Reranker API returned an out-of-range document index")
            scores[result.index] = result.score
        return scores

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
                    raise APIError(f"Reranker API request failed: {exc}") from exc
                time.sleep(attempt)
        else:
            raise APIError(f"Reranker API request failed: {last_error}")

        try:
            body = response.json()
        except ValueError as exc:
            raise APIError("Reranker API response is not valid JSON") from exc
        if not isinstance(body, dict):
            raise APIError("Reranker API response JSON must be an object")
        return body
