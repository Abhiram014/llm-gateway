import asyncio
import json

import httpx

from app.providers.anthropic import AnthropicProvider, from_anthropic, to_anthropic
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.schemas import ChatCompletionRequest

# What a real Anthropic answer looks like
FAKE_ANTHROPIC_RESPONSE = {
    "id": "msg_123",
    "type": "message",
    "role": "assistant",
    "model": "claude-test",
    "content": [{"type": "text", "text": "Hello from Claude"}],
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 10, "output_tokens": 4},
}


def make_request(model: str) -> ChatCompletionRequest:
    return ChatCompletionRequest(
        model=model,
        messages=[
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "Hi"},
        ],
    )


# ---- Unit tests: the translators alone (no network at all) ----

def test_to_anthropic_moves_system_message_out():
    body = to_anthropic(make_request("anthropic/claude-test"))
    assert body["model"] == "claude-test"            # prefix stripped
    assert body["system"] == "Be brief."             # system moved to its own field
    assert body["messages"] == [{"role": "user", "content": "Hi"}]  # system removed from list
    assert body["max_tokens"] == 1024                # default added


def test_from_anthropic_builds_openai_format():
    result = from_anthropic(FAKE_ANTHROPIC_RESPONSE)
    assert result.choices[0].message.content == "Hello from Claude"
    assert result.choices[0].finish_reason == "stop"  # end_turn -> stop
    assert result.usage.prompt_tokens == 10
    assert result.usage.completion_tokens == 4
    assert result.usage.total_tokens == 14


# ---- Provider tests: real adapter code, fake server ----

def test_anthropic_provider_sends_correct_request():
    def fake_anthropic(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/messages"
        assert request.headers["x-api-key"] == "test-key"
        assert request.headers["anthropic-version"] == "2023-06-01"
        assert json.loads(request.content)["system"] == "Be brief."
        return httpx.Response(200, json=FAKE_ANTHROPIC_RESPONSE)

    provider = AnthropicProvider("test-key", transport=httpx.MockTransport(fake_anthropic))
    result = asyncio.run(provider.chat(make_request("anthropic/claude-test")))

    assert result.choices[0].message.content == "Hello from Claude"


def test_openai_provider_sends_bearer_key():
    def fake_openai(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1/chat/completions"
        assert request.headers["authorization"] == "Bearer test-key"
        assert json.loads(request.content)["model"] == "gpt-test"  # prefix stripped
        return httpx.Response(200, json={
            "id": "chatcmpl-1", "object": "chat.completion", "created": 1, "model": "gpt-test",
            "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hi from OpenAI"},
                         "finish_reason": "stop"}],
            "usage": {"prompt_tokens": 3, "completion_tokens": 3, "total_tokens": 6},
        })

    provider = OpenAICompatibleProvider(
        "openai", "https://api.openai.com", "test-key", transport=httpx.MockTransport(fake_openai)
    )
    result = asyncio.run(provider.chat(make_request("openai/gpt-test")))

    assert result.choices[0].message.content == "Hi from OpenAI"