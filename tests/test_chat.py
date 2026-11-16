from fastapi.testclient import TestClient

from app.main import app


def test_mock_chat_returns_openai_format(client, auth_headers):
    response = client.post(
        "/v1/chat/completions",
        json={"model": "mock-1", "messages": [{"role": "user", "content": "Hi"}]},
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["object"] == "chat.completion"
    assert body["choices"][0]["message"]["content"] == "Mock response to: Hi"
    assert body["usage"]["total_tokens"] > 0


def test_unknown_model_returns_400(client, auth_headers):
    response = client.post(
        "/v1/chat/completions",
        json={"model": "gpt-99", "messages": [{"role": "user", "content": "Hi"}]},
        headers=auth_headers,
    )
    assert response.status_code == 400


def test_empty_messages_returns_422(client, auth_headers):
    response = client.post(
        "/v1/chat/completions",
        json={"model": "mock-1", "messages": []},
        headers=auth_headers,
    )
    assert response.status_code == 422