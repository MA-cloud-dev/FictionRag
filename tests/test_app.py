import sqlite3

from src.app import create_app
from src.chunker import Chunk
from src.embeddings import APIError
from src.rag_service import RagAnswer
from src.retriever import RetrievalResult
from src.visitor_store import VisitorStore


def make_result() -> RetrievalResult:
    chunk = Chunk(
        id="book-000001",
        book_name="book",
        chunk_index=1,
        start=0,
        end=10,
        text="原文片段",
        embedding=[1.0, 0.0],
    )
    return RetrievalResult(
        chunk_id=chunk.id,
        score=0.99,
        text=chunk.text,
        chunk=chunk,
    )


def make_app(tmp_path):
    return create_app(visitor_store=VisitorStore(tmp_path / "visitor_usage.sqlite3"))


def stored_queries(store: VisitorStore) -> list[tuple[str, str, str, int]]:
    with sqlite3.connect(store.db_path) as connection:
        return connection.execute(
            """
            SELECT visitor_id, question, answer, used_custom_api_key
            FROM visitor_queries
            ORDER BY id
            """
        ).fetchall()


def test_ask_requires_question(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/ask", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "question is required"


def test_serves_frontend_index(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"FictionRag" in response.data
    assert b"app.js" in response.data


def test_books_returns_index_stats(monkeypatch, tmp_path):
    monkeypatch.setattr(
        "src.app.list_book_stats",
        lambda: {
            "index_path": "data/index/chunks.jsonl",
            "total_books": 1,
            "total_chunks": 2,
            "books": [{"book_name": "第一卷", "chunk_count": 2}],
        },
    )
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.get("/api/books")

    assert response.status_code == 200
    assert response.get_json() == {
        "index_path": "data/index/chunks.jsonl",
        "total_books": 1,
        "total_chunks": 2,
        "books": [{"book_name": "第一卷", "chunk_count": 2}],
    }


def test_ask_rejects_blank_question(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/ask", json={"question": "   "})

    assert response.status_code == 400
    assert response.get_json()["error"] == "question is required"


def test_ask_rejects_missing_visitor_id(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/ask", json={"question": "问题？"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "visitor_id is required"


def test_visitor_usage_endpoint_returns_current_quota(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/api/visitor/usage", json={"visitor_id": "visitor-one"})

    assert response.status_code == 200
    assert response.get_json() == {"quota": 5, "used": 0, "remaining": 5}


def test_ask_returns_answer_json_and_records_free_usage(monkeypatch, tmp_path):
    def fake_answer_question(question: str, top_k: int, model_configs=None):
        assert question == "问题？"
        assert top_k == 3
        assert model_configs is None
        return RagAnswer(
            question=question,
            answer="答案",
            contexts=[make_result()],
        )

    monkeypatch.setattr("src.app.answer_question", fake_answer_question)
    store = VisitorStore(tmp_path / "visitor_usage.sqlite3")
    app = create_app(visitor_store=store)
    client = app.test_client()

    response = client.post(
        "/ask",
        json={"question": " 问题？ ", "top_k": 3, "visitor_id": "visitor-one"},
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["question"] == "问题？"
    assert body["answer"] == "答案"
    assert body["usage"] == {"quota": 5, "used": 1, "remaining": 4}
    assert body["used_custom_api_key"] is False
    assert body["contexts"] == [
        {
            "rank": 1,
            "book_name": "book",
            "chunk_id": "book-000001",
            "score": 0.99,
            "text": "原文片段",
        }
    ]
    assert stored_queries(store) == [("visitor-one", "问题？", "答案", 0)]


def test_ask_rejects_invalid_top_k(tmp_path):
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post(
        "/ask",
        json={"question": "问题？", "visitor_id": "visitor-one", "top_k": 0},
    )

    assert response.status_code == 400
    assert response.get_json()["error"] == "top_k must be a positive integer"


def test_free_quota_blocks_sixth_successful_request(monkeypatch, tmp_path):
    calls = 0

    def fake_answer_question(question: str, top_k: int, model_configs=None):
        nonlocal calls
        calls += 1
        return RagAnswer(question=question, answer=f"答案{calls}", contexts=[make_result()])

    monkeypatch.setattr("src.app.answer_question", fake_answer_question)
    app = make_app(tmp_path)
    client = app.test_client()

    for _ in range(5):
        response = client.post(
            "/ask",
            json={"question": "问题？", "visitor_id": "visitor-one"},
        )
        assert response.status_code == 200

    response = client.post(
        "/ask",
        json={"question": "问题？", "visitor_id": "visitor-one"},
    )

    assert calls == 5
    assert response.status_code == 429
    assert response.get_json()["usage"] == {"quota": 5, "used": 5, "remaining": 0}


def test_custom_api_key_bypasses_quota_and_is_not_stored(monkeypatch, tmp_path):
    def fake_answer_question(question: str, top_k: int, model_configs=None):
        assert model_configs is not None
        assert model_configs.llm.api_key == "sk-custom"
        assert model_configs.llm.model == "qwen3.5-flash"
        assert model_configs.llm.extra_body == {"enable_thinking": False}
        assert model_configs.embedding.model == "text-embedding-v4"
        assert model_configs.reranker.model == "qwen3-rerank"
        return RagAnswer(question=question, answer="自定义答案", contexts=[make_result()])

    monkeypatch.setattr("src.app.answer_question", fake_answer_question)
    store = VisitorStore(tmp_path / "visitor_usage.sqlite3")
    for _ in range(5):
        store.increment_usage("visitor-one")
    app = create_app(visitor_store=store)
    client = app.test_client()

    response = client.post(
        "/ask",
        json={
            "question": "问题？",
            "visitor_id": "visitor-one",
            "api_key": "sk-custom",
        },
    )

    assert response.status_code == 200
    body = response.get_json()
    assert body["answer"] == "自定义答案"
    assert body["usage"] == {"quota": 5, "used": 5, "remaining": 0}
    assert body["used_custom_api_key"] is True
    assert stored_queries(store) == [("visitor-one", "问题？", "自定义答案", 1)]
    with sqlite3.connect(store.db_path) as connection:
        rows = connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    assert "sk-custom" not in repr(rows + stored_queries(store))


def test_custom_key_test_endpoint_success(monkeypatch, tmp_path):
    class FakeLLMClient:
        def __init__(self, config):
            self.config = config

        def chat(self, system_prompt, user_prompt, temperature=0):
            assert self.config.api_key == "sk-custom"
            return "OK"

    class FakeEmbeddingClient:
        def __init__(self, config):
            self.config = config

        def embed_text(self, text):
            assert self.config.api_key == "sk-custom"
            return [1.0]

    class FakeRerankerClient:
        def __init__(self, config):
            self.config = config

        def score(self, query, documents):
            assert self.config.api_key == "sk-custom"
            return [1.0]

    monkeypatch.setattr("src.app.LLMClient", FakeLLMClient)
    monkeypatch.setattr("src.app.EmbeddingClient", FakeEmbeddingClient)
    monkeypatch.setattr("src.app.RerankerClient", FakeRerankerClient)
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/api/custom-key/test", json={"api_key": "sk-custom"})

    assert response.status_code == 200
    assert response.get_json() == {"ok": True}


def test_custom_key_test_endpoint_reports_failed_stage(monkeypatch, tmp_path):
    class FailingLLMClient:
        def __init__(self, config):
            self.config = config

        def chat(self, system_prompt, user_prompt, temperature=0):
            raise APIError("bad key")

    monkeypatch.setattr("src.app.LLMClient", FailingLLMClient)
    app = make_app(tmp_path)
    client = app.test_client()

    response = client.post("/api/custom-key/test", json={"api_key": "sk-bad"})

    assert response.status_code == 400
    assert response.get_json() == {"ok": False, "error": "LLM test failed: bad key"}
