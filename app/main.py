from contextlib import asynccontextmanager

import asyncpg
import httpx
import redis.asyncio as redis
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from app.config import (
    ANTHROPIC_API_KEY,
    ANTHROPIC_BASE_URL,
    DATABASE_URL,
    OLLAMA_URL,
    OPENAI_API_KEY,
    OPENAI_BASE_URL,
    REDIS_URL,
)
from app.providers.anthropic import AnthropicProvider
from app.providers.base import Provider
from app.providers.mock import MockProvider
from app.providers.openai_compatible import OpenAICompatibleProvider
from app.schemas import ChatCompletionRequest, ChatCompletionResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Runs once when the server starts
    app.state.db = await asyncpg.create_pool(DATABASE_URL)
    app.state.redis = redis.from_url(REDIS_URL)
    yield  # the app handles requests while paused here
    # Runs once when the server shuts down
    await app.state.db.close()
    await app.state.redis.aclose()


app = FastAPI(title="LLM Gateway", lifespan=lifespan)


@app.get("/health")
async def health():
    status = {}

    try:
        async with app.state.db.acquire() as conn:
            await conn.fetchval("SELECT 1")
        status["postgres"] = "ok"
    except Exception as e:
        status["postgres"] = f"error: {e}"

    try:
        await app.state.redis.ping()
        status["redis"] = "ok"
    except Exception as e:
        status["redis"] = f"error: {e}"

    healthy = all(v == "ok" for v in status.values())
    return JSONResponse(status, status_code=200 if healthy else 503)


PROVIDERS: dict[str, Provider] = {
    "mock": MockProvider(),
    "ollama": OpenAICompatibleProvider("ollama", OLLAMA_URL),
    "openai": OpenAICompatibleProvider("openai", OPENAI_BASE_URL, OPENAI_API_KEY),
    "anthropic": AnthropicProvider(ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL),
}


def get_provider(model: str) -> Provider:
    if model.startswith("mock"):
        return PROVIDERS["mock"]
    prefix, slash, _ = model.partition("/")  # "anthropic/claude-x" -> ("anthropic", "/", "claude-x")
    if slash and prefix in PROVIDERS:
        return PROVIDERS[prefix]
    raise HTTPException(status_code=400, detail=f"Unknown model: {model}")


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    provider = get_provider(request.model)
    try:
        return await provider.chat(request)
    except httpx.HTTPError as e:
        raise HTTPException(
            status_code=502,
            detail=f"Provider '{provider.name}' failed: {e}",
        )