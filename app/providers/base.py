from abc import ABC, abstractmethod

from app.schemas import ChatCompletionRequest, ChatCompletionResponse


class Provider(ABC):
    name: str

    @abstractmethod
    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        """Send a chat request to the provider and return an OpenAI-format response."""