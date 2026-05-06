from src.config import LLMConfig
from src.llm import LLMClient


def test_llm_client_merges_extra_body_into_chat_payload(monkeypatch):
    client = LLMClient(
        LLMConfig(
            api_key="test-key",
            base_url="https://example.test",
            model="qwen3.5-flash",
            extra_body={"enable_thinking": False},
        )
    )

    def fake_post(path, payload):
        assert path == "/chat/completions"
        assert payload["model"] == "qwen3.5-flash"
        assert payload["enable_thinking"] is False
        return {"choices": [{"message": {"content": "OK"}}]}

    monkeypatch.setattr(client, "_post", fake_post)

    assert client.chat("system", "user") == "OK"
