import httpx

from app.providers.base import Provider
from app.schemas import ChatCompletionRequest, ChatCompletionResponse


class OpenAICompatibleProvider(Provider):
    """Any provider that already speaks OpenAI's format: OpenAI, Ollama, Groq..."""

    def __init__(self, name: str, base_url: str, api_key: str | None = None, transport=None):
        self.name = name
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self.client = httpx.AsyncClient(
            base_url=base_url, headers=headers, timeout=120.0, transport=transport
        )

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        payload = request.model_dump(exclude_none=True)
        payload["model"] = request.model.removeprefix(f"{self.name}/")
        payload["stream"] = False

        response = await self.client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()
        return ChatCompletionResponse.model_validate(response.json())