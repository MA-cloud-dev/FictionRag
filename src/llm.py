"""OpenAI-compatible chat completion client."""

from __future__ import annotations

import time
from typing import Any

import requests

from .config import LLMConfig
from .embeddings import APIError
from .prompts import SYSTEM_PROMPT


class LLMClient:
    def __init__(self, config: LLMConfig) -> None:
        self.config = config

    def answer(self, user_prompt: str) -> str:
        return self.chat(SYSTEM_PROMPT, user_prompt, temperature=0)

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0) -> str:
        payload = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
        }
        if self.config.extra_body:
            payload.update(self.config.extra_body)
        response = self._post("/chat/completions", payload)
        try:
            content = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise APIError("LLM API response has invalid chat completion data") from exc
        return str(content).strip()

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
                    raise APIError(f"LLM API request failed: {exc}") from exc
                time.sleep(attempt)
        else:
            raise APIError(f"LLM API request failed: {last_error}")

        try:
            body = response.json()
        except ValueError as exc:
            raise APIError("LLM API response is not valid JSON") from exc
        if not isinstance(body, dict):
            raise APIError("LLM API response JSON must be an object")
        return body
