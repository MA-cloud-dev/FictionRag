from src.app import create_app
from src.chunker import Chunk
from src.rag_service import RagAnswer
from src.retriever import RetrievalResult


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


def test_ask_requires_question():
    app = create_app()
    client = app.test_client()

    response = client.post("/ask", json={})

    assert response.status_code == 400
    assert response.get_json()["error"] == "question is required"


def test_serves_frontend_index():
    app = create_app()
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    assert b"FictionRag" in response.data
    assert b"app.js" in response.data


def test_books_returns_index_stats(monkeypatch):
    monkeypatch.setattr(
        "src.app.list_book_stats",
        lambda: {
            "index_path": "data/index/chunks.jsonl",
            "total_books": 1,
            "total_chunks": 2,
            "books": [{"book_name": "第一卷", "chunk_count": 2}],
        },
    )
    app = create_app()
    client = app.test_client()

    response = client.get("/api/books")

    assert response.status_code == 200
    assert response.get_json() == {
        "index_path": "data/index/chunks.jsonl",
        "total_books": 1,
        "total_chunks": 2,
        "books": [{"book_name": "第一卷", "chunk_count": 2}],
    }


def test_ask_rejects_blank_question():
    app = create_app()
    client = app.test_client()

    response = client.post("/ask", json={"question": "   "})

    assert response.status_code == 400
    assert response.get_json()["error"] == "question is required"


def test_ask_returns_answer_json(monkeypatch):
    def fake_answer_question(question: str, top_k: int):
        assert question == "问题？"
        assert top_k == 3
        return RagAnswer(
            question=question,
            answer="答案",
            contexts=[make_result()],
        )

    monkeypatch.setattr("src.app.answer_question", fake_answer_question)
    app = create_app()
    client = app.test_client()

    response = client.post("/ask", json={"question": " 问题？ ", "top_k": 3})

    assert response.status_code == 200
    body = response.get_json()
    assert body["question"] == "问题？"
    assert body["answer"] == "答案"
    assert body["contexts"] == [
        {
            "rank": 1,
            "book_name": "book",
            "chunk_id": "book-000001",
            "score": 0.99,
            "text": "原文片段",
        }
    ]


def test_ask_rejects_invalid_top_k():
    app = create_app()
    client = app.test_client()

    response = client.post("/ask", json={"question": "问题？", "top_k": 0})

    assert response.status_code == 400
    assert response.get_json()["error"] == "top_k must be a positive integer"
