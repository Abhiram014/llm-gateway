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

**One OpenAICompatibleProvider class serves OpenAI and Ollama.**
Both speak OpenAI's format, so one class configured twice avoids duplicate code. It will also cover Groq, Together, vLLM, etc.

**The Anthropic adapter translates both ways.**
Going in: system messages move to a separate `system` field, and `max_tokens` defaults to 1024 (Anthropic requires it). Coming out: content blocks are joined into one string, `stop_reason` maps to `finish_reason`, and `input/output_tokens` map to `prompt/completion_tokens`.

**Translators are pure functions, tested without a network.**
Provider classes accept an httpx transport, so tests use MockTransport to simulate OpenAI and Anthropic: real adapter code, no API keys, no cost.

**Routing reads the prefix before "/" and looks it up in a dictionary.**
Adding a provider = one line in PROVIDERS. `get_provider` never changes.

**All provider URLs come from config, with the real addresses as defaults.**
Lets a provider be pointed at a proxy or another host without code changes.

**No paid API keys yet.**
OpenAI and Anthropic adapters are verified with mocked responses; real calls only need a key in .env, no code changes.

## Day 4: API keys

**Keys are stored as SHA-256 hashes, never in plain text.**
A stolen database doesn't leak usable keys. The real key is shown once at creation.

**SHA-256, not bcrypt.**
Keys are 32 random bytes, so they can't be guessed, and a fast hash is safe. Slow hashes like bcrypt are for low-entropy human passwords. Keys are checked on every request, so speed matters.

**Keys are revoked (revoked_at), not deleted.**
Keeps history for usage logs and audits.

**A key_prefix (first 10 chars) is stored for display.**
Lets people recognize a key without exposing it.

**Auth is a FastAPI dependency (`Depends(require_api_key)`).**
One reusable check; it returns the key's id so rate limiting and cost tracking know who is calling. /health stays public for load balancers.

**Parameterized SQL ($1, $2) everywhere.**
Prevents SQL injection.

**Tables are created at startup with CREATE TABLE IF NOT EXISTS.**
Simple for now; a migration tool (Alembic) would be the next step as the schema grows.

## Day 5: Rate limiting

**Token bucket algorithm, per API key.**
Allows short bursts but caps the average rate. Fixed windows allow 2x bursts at window edges; sliding logs cost more memory.

**State lives in Redis, not in the app's memory.**
All gateway instances share one bucket per key, and Redis answers in well under 1 ms.

**The check runs as a Lua script, so it's atomic.**
Prevents race conditions where two simultaneous requests both spend the last token.

**Redis's own clock (TIME) is used, not each server's.**
Gateway instances with slightly different clocks still agree.

**Buckets expire automatically (EXPIRE).**
Idle keys don't leave data in Redis forever.

**429 with a Retry-After header.**
Standard "slow down" response; clients like the OpenAI SDK back off automatically.

**Fail open if Redis is down.**
Briefly losing rate limits is better than blocking all traffic. (A payments system would fail closed.)

**Per-key limits stored in Postgres (rpm_limit, default 60).**
Added with ALTER TABLE ... ADD COLUMN IF NOT EXISTS, because CREATE TABLE IF NOT EXISTS doesn't change existing tables; a migration tool would handle this as the schema grows.

**Tokens-per-minute limits come after real token counting (Day 7).**