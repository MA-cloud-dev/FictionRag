"""Minimal Flask API for FictionRag."""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .config import DEFAULT_TOP_K, ConfigError, build_bailian_model_configs
from .embeddings import APIError, EmbeddingClient
from .index_store import IndexStoreError
from .llm import LLMClient
from .rag_service import RagAnswer, answer_question, list_book_stats
from .reranker import RerankerClient
from .visitor_store import VisitorStore


def create_app(visitor_store: VisitorStore | None = None) -> Flask:
    app = Flask(__name__)
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"
    store = visitor_store or VisitorStore()

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/api/books")
    def books():
        try:
            return jsonify(list_book_stats())
        except (OSError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.post("/api/visitor/usage")
    def visitor_usage():
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON"}), 400

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        try:
            visitor_id = _parse_visitor_id(payload.get("visitor_id"))
            return jsonify(store.get_usage(visitor_id))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        except sqlite3.Error as exc:
            return jsonify({"error": str(exc)}), 500

    @app.post("/api/custom-key/test")
    def custom_key_test():
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON"}), 400

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        try:
            api_key = _parse_api_key(payload.get("api_key"))
            _test_bailian_api_key(api_key)
            return jsonify({"ok": True})
        except (ConfigError, APIError, ValueError) as exc:
            return jsonify({"ok": False, "error": str(exc)}), 400

    @app.post("/ask")
    def ask():
        if not request.is_json:
            return jsonify({"error": "Request body must be JSON"}), 400

        payload = request.get_json(silent=True)
        if not isinstance(payload, dict):
            return jsonify({"error": "Request body must be a JSON object"}), 400

        question = payload.get("question")
        if not isinstance(question, str) or not question.strip():
            return jsonify({"error": "question is required"}), 400

        try:
            visitor_id = _parse_visitor_id(payload.get("visitor_id"))
            api_key = _parse_optional_api_key(payload.get("api_key"))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        try:
            top_k = _parse_top_k(payload.get("top_k", DEFAULT_TOP_K))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        try:
            usage = store.get_usage(visitor_id)
            model_configs = None
            used_custom_api_key = bool(api_key)
            if api_key:
                model_configs = build_bailian_model_configs(api_key)
            elif usage["remaining"] <= 0:
                return jsonify({"error": "今日免费体验次数已用完", "usage": usage}), 429

            result = answer_question(
                question=question.strip(),
                top_k=top_k,
                model_configs=model_configs,
            )
            store.save_query(
                visitor_id=visitor_id,
                question=result.question,
                answer=result.answer,
                used_custom_api_key=used_custom_api_key,
            )
            if not used_custom_api_key:
                usage = store.increment_usage(visitor_id)

            body = _answer_to_dict(result)
            body["usage"] = usage
            body["used_custom_api_key"] = used_custom_api_key
            return jsonify(body)
        except (ConfigError, APIError, IndexStoreError, OSError, sqlite3.Error, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.get("/<path:filename>")
    def frontend_asset(filename: str):
        return send_from_directory(frontend_dir, filename)

    return app


def _parse_top_k(value: object) -> int:
    if isinstance(value, bool):
        raise ValueError("top_k must be a positive integer")
    try:
        top_k = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("top_k must be a positive integer") from exc
    if top_k <= 0:
        raise ValueError("top_k must be a positive integer")
    return top_k


def _parse_visitor_id(value: object) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("visitor_id is required")
    visitor_id = value.strip()
    if len(visitor_id) > 200:
        raise ValueError("visitor_id is too long")
    return visitor_id


def _parse_optional_api_key(value: object) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError("api_key must be a string")
    api_key = value.strip()
    return api_key or None


def _parse_api_key(value: object) -> str:
    api_key = _parse_optional_api_key(value)
    if not api_key:
        raise ValueError("api_key is required")
    return api_key


def _test_bailian_api_key(api_key: str) -> None:
    configs = build_bailian_model_configs(api_key)
    try:
        LLMClient(configs.llm).chat("你是 API Key 测试助手。", "请只回复 OK。", temperature=0)
    except (APIError, ValueError) as exc:
        raise APIError(f"LLM test failed: {exc}") from exc

    try:
        EmbeddingClient(configs.embedding).embed_text("API Key 测试")
    except (APIError, ValueError) as exc:
        raise APIError(f"Embedding test failed: {exc}") from exc

    try:
        RerankerClient(configs.reranker).score("API Key 测试", ["API Key 测试文档"])
    except (APIError, ValueError) as exc:
        raise APIError(f"Rerank test failed: {exc}") from exc


def _answer_to_dict(result: RagAnswer) -> dict[str, object]:
    return {
        "question": result.question,
        "answer": result.answer,
        "rerank_enabled": result.rerank_enabled,
        "rerank_candidate_count": result.rerank_candidate_count,
        "used_rewrite": result.used_rewrite,
        "rewritten_queries": result.rewritten_queries,
        "answerability": result.answerability,
        "contexts": [
            {
                "rank": rank,
                "book_name": context.chunk.book_name,
                "chunk_id": context.chunk_id,
                "score": context.score,
                "text": context.text,
            }
            for rank, context in enumerate(result.contexts, start=1)
        ],
    }


app = create_app()


if __name__ == "__main__":
    host = os.getenv("FICTIONRAG_HOST", "127.0.0.1")
    port = int(os.getenv("FICTIONRAG_PORT", "5000"))
    app.run(host=host, port=port)
