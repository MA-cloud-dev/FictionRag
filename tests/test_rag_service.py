from pathlib import Path

from src.chunker import Chunk
from src.rag_service import answer_question


class FakeEmbeddingClient:
    queries: list[str] = []
    embeddings: dict[str, list[float]] = {"问题？": [1.0, 0.0]}

    def __init__(self, config) -> None:
        self.config = config

    def embed_text(self, text: str) -> list[float]:
        FakeEmbeddingClient.queries.append(text)
        return FakeEmbeddingClient.embeddings[text]


class FakeLLMClient:
    chat_responses: list[str] = []
    answer_response = "答案"
    chats: list[tuple[str, str, float]] = []
    answer_prompts: list[str] = []

    def __init__(self, config) -> None:
        self.config = config

    def chat(self, system_prompt: str, user_prompt: str, temperature: float = 0) -> str:
        FakeLLMClient.chats.append((system_prompt, user_prompt, temperature))
        return FakeLLMClient.chat_responses.pop(0)

    def answer(self, user_prompt: str) -> str:
        FakeLLMClient.answer_prompts.append(user_prompt)
        return FakeLLMClient.answer_response


def reset_fakes() -> None:
    FakeEmbeddingClient.queries = []
    FakeEmbeddingClient.embeddings = {"问题？": [1.0, 0.0]}
    FakeLLMClient.chat_responses = []
    FakeLLMClient.answer_response = "答案"
    FakeLLMClient.chats = []
    FakeLLMClient.answer_prompts = []


def patch_clients(monkeypatch, chunks: list[Chunk]) -> None:
    monkeypatch.setattr("src.rag_service.load_chunks", lambda path: chunks)
    monkeypatch.setattr("src.rag_service.load_embedding_config", lambda: object())
    monkeypatch.setattr("src.rag_service.EmbeddingClient", FakeEmbeddingClient)
    monkeypatch.setattr("src.rag_service.load_llm_config", lambda: object())
    monkeypatch.setattr("src.rag_service.LLMClient", FakeLLMClient)


def test_answer_question_retrieves_context_and_calls_llm(monkeypatch):
    reset_fakes()
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
    FakeLLMClient.chat_responses = [
        '{"answerable": true, "missing_info": [], '
        '"rewrite_queries": [], "clarification_questions": []}'
    ]
    patch_clients(monkeypatch, chunks)

    result = answer_question("问题？", top_k=1, index_path=Path("index.jsonl"))

    assert result.question == "问题？"
    assert result.answer == "答案"
    assert [context.chunk_id for context in result.contexts] == ["hit"]
    assert result.used_rewrite is False
    assert result.rewritten_queries == []
    assert result.answerability is not None
    assert result.answerability["answerable"] is True
    assert FakeEmbeddingClient.queries == ["问题？"]
    assert len(FakeLLMClient.chats) == 1
    assert len(FakeLLMClient.answer_prompts) == 1
    assert "命中的原文" in FakeLLMClient.answer_prompts[0]
    assert "问题？" in FakeLLMClient.answer_prompts[0]


def test_answer_question_rewrites_and_answers_with_second_context(monkeypatch):
    reset_fakes()
    FakeEmbeddingClient.embeddings = {
        "问题？": [0.8, 0.2],
        "改写问题": [0.0, 1.0],
    }
    chunks = [
        Chunk(
            id="first",
            book_name="book",
            chunk_index=1,
            start=0,
            end=10,
            text="第一次召回原文",
            embedding=[1.0, 0.0],
        ),
        Chunk(
            id="rewrite",
            book_name="book",
            chunk_index=2,
            start=11,
            end=20,
            text="二次召回原文",
            embedding=[0.0, 1.0],
        ),
    ]
    FakeLLMClient.chat_responses = [
        '{"answerable": false, "missing_info": ["当前片段不足以回答"], '
        '"rewrite_queries": ["改写问题"], '
        '"clarification_questions": ["他是谁？"]}',
        '{"answerable": true, "missing_info": [], '
        '"rewrite_queries": [], "clarification_questions": []}',
    ]
    FakeLLMClient.answer_response = "二次答案"
    patch_clients(monkeypatch, chunks)
    monkeypatch.setattr("src.rag_service.generate_entity_rewrites", lambda question: ["改写问题"])

    result = answer_question("问题？", top_k=2, index_path=Path("index.jsonl"))

    assert result.answer == "二次答案"
    assert result.used_rewrite is True
    assert result.rewritten_queries == ["改写问题"]
    assert "rewrite" in [context.chunk_id for context in result.contexts]
    assert FakeEmbeddingClient.queries == ["问题？", "改写问题"]
    assert len(FakeLLMClient.chats) == 2
    assert len(FakeLLMClient.answer_prompts) == 1
    assert "二次召回原文" in FakeLLMClient.answer_prompts[0]


def test_answer_question_retries_with_rewrite_when_answer_is_unhelpful(monkeypatch):
    reset_fakes()
    FakeEmbeddingClient.embeddings = {
        "问题？": [0.8, 0.2],
        "改写问题": [0.0, 1.0],
    }
    chunks = [
        Chunk(
            id="first",
            book_name="book",
            chunk_index=1,
            start=0,
            end=10,
            text="第一次召回原文",
            embedding=[1.0, 0.0],
        ),
        Chunk(
            id="rewrite",
            book_name="book",
            chunk_index=2,
            start=11,
            end=20,
            text="二次召回原文",
            embedding=[0.0, 1.0],
        ),
    ]
    FakeLLMClient.chat_responses = [
        '{"answerable": true, "missing_info": [], "clarification_questions": []}',
        '{"answerable": true, "missing_info": [], "clarification_questions": []}',
        "澄清建议",
    ]
    FakeLLMClient.answer_response = "目前原文片段中没有足够信息确认答案。"
    patch_clients(monkeypatch, chunks)
    monkeypatch.setattr("src.rag_service.generate_entity_rewrites", lambda question: ["改写问题"])

    result = answer_question("问题？", top_k=2, index_path=Path("index.jsonl"))

    assert result.used_rewrite is True
    assert result.rewritten_queries == ["改写问题"]
    assert result.answer == "澄清建议"
    assert FakeEmbeddingClient.queries == ["问题？", "改写问题"]
    assert len(FakeLLMClient.chats) == 3
    assert len(FakeLLMClient.answer_prompts) == 2


def test_answer_question_rewrites_then_returns_clarification(monkeypatch):
    reset_fakes()
    FakeEmbeddingClient.embeddings = {
        "问题？": [0.8, 0.2],
        "改写问题": [0.0, 1.0],
    }
    chunks = [
        Chunk(
            id="first",
            book_name="book",
            chunk_index=1,
            start=0,
            end=10,
            text="第一次召回原文",
            embedding=[1.0, 0.0],
        ),
        Chunk(
            id="rewrite",
            book_name="book",
            chunk_index=2,
            start=11,
            end=20,
            text="二次召回原文",
            embedding=[0.0, 1.0],
        ),
    ]
    FakeLLMClient.chat_responses = [
        '{"answerable": false, "missing_info": ["证据不足"], '
        '"rewrite_queries": ["改写问题"], '
        '"clarification_questions": []}',
        '{"answerable": false, "missing_info": ["原文未提供"], '
        '"rewrite_queries": [], '
        '"clarification_questions": ["请补充事件"]}',
        "澄清建议",
    ]
    patch_clients(monkeypatch, chunks)
    monkeypatch.setattr("src.rag_service.generate_entity_rewrites", lambda question: ["改写问题"])

    result = answer_question("问题？", top_k=2, index_path=Path("index.jsonl"))

    assert result.answer == "澄清建议"
    assert result.used_rewrite is True
    assert result.rewritten_queries == ["改写问题"]
    assert result.answerability is not None
    assert result.answerability["answerable"] is False
    assert FakeEmbeddingClient.queries == ["问题？", "改写问题"]
    assert len(FakeLLMClient.chats) == 3
    assert FakeLLMClient.answer_prompts == []


def test_answer_question_invalid_answerability_json_falls_back_to_original_flow(monkeypatch):
    reset_fakes()
    chunks = [
        Chunk(
            id="hit",
            book_name="book",
            chunk_index=1,
            start=0,
            end=10,
            text="命中的原文",
            embedding=[1.0, 0.0],
        )
    ]
    FakeLLMClient.chat_responses = ["不是 JSON"]
    FakeLLMClient.answer_response = "降级答案"
    patch_clients(monkeypatch, chunks)

    result = answer_question("问题？", top_k=1, index_path=Path("index.jsonl"))

    assert result.answer == "降级答案"
    assert result.answerability is None
    assert result.used_rewrite is False
    assert result.rewritten_queries == []
    assert FakeEmbeddingClient.queries == ["问题？"]
    assert len(FakeLLMClient.chats) == 1
    assert len(FakeLLMClient.answer_prompts) == 1


def test_answer_question_unanswerable_without_entity_rewrite_returns_clarification(monkeypatch):
    reset_fakes()
    chunks = [
        Chunk(
            id="hit",
            book_name="book",
            chunk_index=1,
            start=0,
            end=10,
            text="命中的原文",
            embedding=[1.0, 0.0],
        )
    ]
    FakeLLMClient.chat_responses = [
        '{"answerable": false, "missing_info": ["当前片段不足"], '
        '"clarification_questions": ["请补充人物"]}',
        "澄清建议",
    ]
    patch_clients(monkeypatch, chunks)
    monkeypatch.setattr("src.rag_service.generate_entity_rewrites", lambda question: [])

    result = answer_question("问题？", top_k=1, index_path=Path("index.jsonl"))

    assert result.answer == "澄清建议"
    assert result.used_rewrite is False
    assert result.rewritten_queries == []
    assert FakeEmbeddingClient.queries == ["问题？"]
    assert len(FakeLLMClient.chats) == 2
    assert FakeLLMClient.answer_prompts == []


def test_answer_question_unanswerable_always_rewrites_once(monkeypatch):
    reset_fakes()
    FakeEmbeddingClient.embeddings = {
        "问题？": [1.0, 0.0],
        "改写问题": [0.0, 1.0],
    }
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
            id="rewrite",
            book_name="book",
            chunk_index=2,
            start=11,
            end=20,
            text="二次召回原文",
            embedding=[0.0, 1.0],
        )
    ]
    FakeLLMClient.chat_responses = [
        '{"answerable": false, "missing_info": ["当前片段不足"], '
        '"rewrite_queries": ["改写问题"], '
        '"clarification_questions": ["请补充人物"]}',
        '{"answerable": false, "missing_info": ["仍然不足"], '
        '"rewrite_queries": ["不应再次使用"], '
        '"clarification_questions": ["请补充人物"]}',
        "澄清建议",
    ]
    patch_clients(monkeypatch, chunks)
    monkeypatch.setattr("src.rag_service.generate_entity_rewrites", lambda question: ["改写问题"])

    result = answer_question("问题？", top_k=1, index_path=Path("index.jsonl"))

    assert result.answer == "澄清建议"
    assert result.used_rewrite is True
    assert result.rewritten_queries == ["改写问题"]
    assert result.answerability is not None
    assert result.answerability["answerable"] is False
    assert FakeEmbeddingClient.queries == ["问题？", "改写问题"]
    assert len(FakeLLMClient.chats) == 3
