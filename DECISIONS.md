# Design Decisions

Why the project is built the way it is. Written as I build it.

## Day 1: Infrastructure

**Postgres and Redis run in Docker Compose, not installed locally.**
One command (`docker compose up -d`) gives anyone the same setup. No version conflicts.

**Using the pgvector image from the start.**
The semantic cache (Week 2) needs vector search. Starting with it avoids switching images later.

**Postgres is exposed on laptop port 5433, not 5432.**
A local Windows Postgres already uses 5432. Inside the container it's still 5432.

**Database connections are opened once at startup, in a pool (asyncpg).**
Opening a connection per request costs tens of ms. A gateway's job is low overhead, so requests borrow pooled connections instead.

**Async everywhere (asyncpg, redis.asyncio, httpx).**
A gateway spends most of its time waiting on LLM providers. Async lets one process handle many waiting requests at once.

**/health returns 503 when a dependency is down.**
Load balancers and hosting platforms read the status code, not the body, to decide if the service is healthy.

**Config and secrets live in .env, never in code or git.**

## Day 2: Chat endpoint

**The API copies OpenAI's chat format exactly.**
It's the industry standard, so any OpenAI client can use the gateway by changing only the base URL. Verified with the official OpenAI Python SDK.

**Providers follow one interface (adapter pattern).**
Each provider implements `chat(request) -> response` and hides its own API. The endpoint never knows which provider it's calling, so adding a provider never touches the endpoint.

**A Mock provider for tests and load testing.**
Free, instant and predictable. Real providers are slow, cost money and give different answers.

**Unknown model = 400, invalid body = 422.**
Both are client mistakes, so they're 4xx errors.

## Day 3: Real providers

**Models are named `provider/model` (e.g. `ollama/qwen2.5:0.5b`).**
The prefix picks the provider and is stripped before calling it. Same convention as OpenRouter and LiteLLM.

**Ollama runs locally in Docker for free real-model testing.**
A tiny model (qwen2.5 0.5B) is enough to test the gateway without paying for API calls.

**One reusable httpx.AsyncClient per provider, with a 120s timeout.**
Reusing connections avoids reconnect cost; the timeout stops a stuck provider from hanging requests forever.

**Provider failures return 502 Bad Gateway.**
4xx = the client's mistake, 502 = the provider behind the gateway failed.