"""Minimal Flask API for FictionRag."""

from __future__ import annotations

import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from .config import DEFAULT_TOP_K, ConfigError
from .embeddings import APIError
from .index_store import IndexStoreError
from .rag_service import RagAnswer, answer_question, list_book_stats


def create_app() -> Flask:
    app = Flask(__name__)
    frontend_dir = Path(__file__).resolve().parent.parent / "frontend"

    @app.get("/")
    def index():
        return send_from_directory(frontend_dir, "index.html")

    @app.get("/api/books")
    def books():
        try:
            return jsonify(list_book_stats())
        except (OSError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

    @app.get("/<path:filename>")
    def frontend_asset(filename: str):
        return send_from_directory(frontend_dir, filename)

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
            top_k = _parse_top_k(payload.get("top_k", DEFAULT_TOP_K))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400

        try:
            result = answer_question(question=question.strip(), top_k=top_k)
        except (ConfigError, APIError, IndexStoreError, OSError, ValueError) as exc:
            return jsonify({"error": str(exc)}), 500

        return jsonify(_answer_to_dict(result))

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


def _answer_to_dict(result: RagAnswer) -> dict[str, object]:
    return {
        "question": result.question,
        "answer": result.answer,
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
