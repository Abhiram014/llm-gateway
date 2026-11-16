import hashlib
import secrets

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

KEY_PREFIX = "gw-"


def generate_key() -> str:
    return KEY_PREFIX + secrets.token_urlsafe(32)


def hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


async def create_api_key(db, name: str) -> str:
    """Create a key, store only its hash, return the real key (shown once)."""
    key = generate_key()
    await db.execute(
        "INSERT INTO api_keys (name, key_hash, key_prefix) VALUES ($1, $2, $3)",
        name, hash_key(key), key[:10],
    )
    return key


bearer = HTTPBearer(auto_error=False)


async def require_api_key(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
) -> dict:
    """Runs before protected endpoints. Returns the key's info, or rejects with 401."""
    if credentials is None:
        raise HTTPException(status_code=401, detail="Missing API key",
                            headers={"WWW-Authenticate": "Bearer"})

    row = await request.app.state.db.fetchrow(
        "SELECT id, name FROM api_keys WHERE key_hash = $1 AND revoked_at IS NULL",
        hash_key(credentials.credentials),
    )
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid API key",
                            headers={"WWW-Authenticate": "Bearer"})
    return dict(row)