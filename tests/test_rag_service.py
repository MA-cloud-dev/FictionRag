from pathlib import Path

from src.chunker import Chunk
from src.rag_service import answer_question


class FakeEmbeddingClient:
    def __init__(self, config) -> None:
        self.config = config

    def embed_text(self, text: str) -> list[float]:
        assert text == "问题？"
        return [1.0, 0.0]


class FakeLLMClient:
    prompt: str | None = None

    def __init__(self, config) -> None:
        self.config = config

    def answer(self, user_prompt: str) -> str:
        FakeLLMClient.prompt = user_prompt
        return "答案"


def test_answer_question_retrieves_context_and_calls_llm(monkeypatch):
    chunks = [
        Chunk(
            id="hit",
            book_name="book",
            chunk_index=1,
            start=0,
            end=10,
            text="命中的原文",
            embedding=[1.0, 0.0],
        ),
        Chunk(
            id="miss",
            book_name="book",
            chunk_index=2,
            start=11,
            end=20,
            text="无关原文",
            embedding=[0.0, 1.0],
        ),
    ]

    monkeypatch.setattr("src.rag_service.load_chunks", lambda path: chunks)
    monkeypatch.setattr("src.rag_service.load_embedding_config", lambda: object())
    monkeypatch.setattr("src.rag_service.EmbeddingClient", FakeEmbeddingClient)
    monkeypatch.setattr("src.rag_service.load_llm_config", lambda: object())
    monkeypatch.setattr("src.rag_service.LLMClient", FakeLLMClient)

    result = answer_question("问题？", top_k=1, index_path=Path("index.jsonl"))

    assert result.question == "问题？"
    assert result.answer == "答案"
    assert [context.chunk_id for context in result.contexts] == ["hit"]
    assert FakeLLMClient.prompt is not None
    assert "命中的原文" in FakeLLMClient.prompt
    assert "问题？" in FakeLLMClient.prompt
