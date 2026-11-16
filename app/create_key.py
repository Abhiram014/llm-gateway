import asyncio
import sys

import asyncpg

from app.auth import create_api_key
from app.config import DATABASE_URL
from app.db import SCHEMA


async def main(name: str) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(SCHEMA)
        key = await create_api_key(conn, name)
    finally:
        await conn.close()

    print(f"Created key '{name}':")
    print(key)
    print("Copy it now. It will not be shown again.")


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "default"))