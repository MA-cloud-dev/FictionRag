from src.config import _reranker_base_url_from_embedding
from src.config import RerankerConfig
from src.reranker import RerankerClient


def test_reranker_base_url_uses_dashscope_compatible_api_endpoint():
    assert (
        _reranker_base_url_from_embedding(
            "https://dashscope.aliyuncs.com/compatible-mode/v1"
        )
        == "https://dashscope.aliyuncs.com/compatible-api/v1"
    )


def test_reranker_score_maps_scores_back_to_original_document_order(monkeypatch):
    client = RerankerClient(
        RerankerConfig(
            api_key="test-key",
            base_url="https://example.test",
            model="qwen3-rerank",
        )
    )

    def fake_post(path, payload):
        assert path == "/reranks"
        assert payload["model"] == "qwen3-rerank"
        assert payload["query"] == "question"
        assert payload["documents"] == ["a", "b", "c"]
        return {
            "results": [
                {"index": 2, "relevance_score": 0.9},
                {"index": 0, "relevance_score": 0.5},
                {"index": 1, "relevance_score": 0.1},
            ]
        }

    monkeypatch.setattr(client, "_post", fake_post)

    assert client.score("question", ["a", "b", "c"]) == [0.5, 0.1, 0.9]
