import httpx

from app.providers.base import Provider
from app.schemas import ChatCompletionRequest, ChatCompletionResponse


class OllamaProvider(Provider):
    name = "ollama"

    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=120.0)

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        # "ollama/qwen2.5:0.5b" -> "qwen2.5:0.5b" (Ollama only knows the model's own name)
        model = request.model.removeprefix("ollama/")

        payload = request.model_dump(exclude_none=True)
        payload["model"] = model
        payload["stream"] = False  # streaming comes in Week 2

        response = await self.client.post("/v1/chat/completions", json=payload)
        response.raise_for_status()

        return ChatCompletionResponse.model_validate(response.json())