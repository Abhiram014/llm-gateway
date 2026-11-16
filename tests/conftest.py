import asyncio

import asyncpg
import pytest
from fastapi.testclient import TestClient

from app.auth import create_api_key
from app.config import DATABASE_URL
from app.main import app


def run_db(func):
    """Run an async database function with its own short-lived connection."""
    async def _run():
        conn = await asyncpg.connect(DATABASE_URL)
        try:
            return await func(conn)
        finally:
            await conn.close()
    return asyncio.run(_run())


@pytest.fixture
def client():
    with TestClient(app) as c:   # starts the app, which creates the tables
        yield c


@pytest.fixture
def api_key(client):
    return run_db(lambda conn: create_api_key(conn, "test"))


@pytest.fixture
def auth_headers(api_key):
    return {"Authorization": f"Bearer {api_key}"}

@pytest.fixture
def db():
    """Lets a test run a database command: db(lambda conn: conn.execute(...))."""
    return run_db