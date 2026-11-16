from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException

from app.providers.base import Provider
from app.providers.mock import MockProvider
from app.schemas import ChatCompletionRequest, ChatCompletionResponse
import asyncpg
import redis.asyncio as redis

from fastapi.responses import JSONResponse

from app.config import DATABASE_URL, REDIS_URL


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
}


def get_provider(model: str) -> Provider:
    # For now: any model name starting with "mock" goes to the Mock provider.
    # Day 3 adds real routing for OpenAI, Anthropic and Ollama.
    if model.startswith("mock"):
        return PROVIDERS["mock"]
    raise HTTPException(status_code=400, detail=f"Unknown model: {model}")


@app.post("/v1/chat/completions", response_model=ChatCompletionResponse)
async def chat_completions(request: ChatCompletionRequest):
    provider = get_provider(request.model)
    return await provider.chat(request)