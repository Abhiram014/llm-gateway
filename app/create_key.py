import asyncio
import sys

import asyncpg

from app.auth import create_api_key
from app.config import DATABASE_URL
from app.db import SCHEMA


async def main(name: str, rpm_limit: int) -> None:
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        await conn.execute(SCHEMA)
        key = await create_api_key(conn, name, rpm_limit)
    finally:
        await conn.close()

    print(f"Created key '{name}' ({rpm_limit} requests/min):")
    print(key)
    print("Copy it now. It will not be shown again.")


if __name__ == "__main__":
    name = sys.argv[1] if len(sys.argv) > 1 else "default"
    rpm = int(sys.argv[2]) if len(sys.argv) > 2 else 60
    asyncio.run(main(name, rpm))