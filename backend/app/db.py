import os
from typing import Any, AsyncGenerator, Optional

from surrealdb import AsyncSurreal


SURREAL_URL = os.getenv("SURREAL_URL", "http://localhost:8000")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS = os.getenv("SURREAL_NS", "hackathon")
SURREAL_DB = os.getenv("SURREAL_DB", "agentic_auditor")


class SurrealClient:
    def __init__(self) -> None:
        self._client: Optional[AsyncSurreal] = None

    async def connect(self) -> AsyncSurreal:
        if self._client is None:
            self._client = AsyncSurreal(SURREAL_URL)
            await self._client.connect()
            await self._client.signin({"user": SURREAL_USER, "pass": SURREAL_PASS})
            await self._client.use(SURREAL_NS, SURREAL_DB)
        return self._client

    async def query(self, sql: str, vars: Optional[dict[str, Any]] = None) -> Any:
        client = await self.connect()
        return await client.query(sql, vars or {})

    async def close(self) -> None:
        if self._client is not None:
            await self._client.close()
            self._client = None


surreal_client = SurrealClient()


async def get_db() -> AsyncGenerator[SurrealClient, None]:
    try:
        yield surreal_client
    finally:
        # Single shared client; do not close per-request.
        pass

