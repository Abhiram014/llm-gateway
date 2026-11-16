import time
import uuid

from app.providers.base import Provider
from app.schemas import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    Choice,
    Message,
    Usage,
)


class MockProvider(Provider):
    name = "mock"

    async def chat(self, request: ChatCompletionRequest) -> ChatCompletionResponse:
        last_message = request.messages[-1].content
        reply = f"Mock response to: {last_message}"

        # Rough token count (word count). Real token counting comes on Day 7.
        prompt_tokens = sum(len(m.content.split()) for m in request.messages)
        completion_tokens = len(reply.split())

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex}",
            created=int(time.time()),
            model=request.model,
            choices=[
                Choice(
                    index=0,
                    message=Message(role="assistant", content=reply),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )