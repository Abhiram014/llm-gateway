import time

import httpx

from app.providers.base import Provider
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    Usage,
)

# Anthropic's stop reasons -> OpenAI's finish reasons
FINISH_REASONS = {
    "end_turn": "stop",
    "stop_sequence": "stop",
    "max_tokens": "length",
}


def to_anthropic(request: ChatCompletionRequest) -> dict:
    """Translate OUR (OpenAI-style) request into Anthropic's format."""
    system_parts = [m.content for m in request.messages if m.role == "system"]
    messages = [
        {"role": m.role, "content": m.content}
        for m in request.messages
        if m.role != "system"
    ]

    body = {
        "model": request.model.removeprefix("anthropic/"),
        "messages": messages,
        "max_tokens": request.max_tokens or 1024,  # required by Anthropic
    }
    if system_parts:
        body["system"] = "\n\n".join(system_parts)
    if request.temperature is not None:
        body["temperature"] = request.temperature
    return body


def from_anthropic(data: dict) -> ChatCompletionResponse:
    """Translate Anthropic's answer back into OUR (OpenAI-style) format."""
    text = "".join(block["text"] for block in data["content"] if block["type"] == "text")
    usage = data["usage"]

    return ChatCompletionResponse(
        id=data["id"],
        created=int(time.time()),
        model=data["model"],
        choices=[
            Choice(
                index=0,
                message=Message(role="assistant", content=text),
                finish_reason=FINISH_REASONS.get(data["stop_reason"], "stop"),
            )
        ],
        usage=Usage(
            prompt_tokens=usage["input_tokens"],
            completion_tokens=usage["output_tokens"],
            total_tokens=usage["input_tokens"] + usage["output_tokens"],
        ),
    )


class AnthropicProvider(Provider):
    name = "anthropic"

    def __init__(self, api_key: str | None, base_url: str = "https://api.anthropic.com", transport=None):
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={"x-api-key": api_key or "", "anthropic-version": "2023-06-01"},
            timeout=120.0,
            transport=transport,
        )

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        response = await self.client.post("/v1/messages", json=to_anthropic(request))
        response.raise_for_status()
        return from_anthropic(response.json())