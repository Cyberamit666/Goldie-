import asyncpg

class Database:
    def __init__(self, dsn: str):
        self._dsn = dsn
        self.pool = None

    async def initialize(self):
        self.pool = await asyncpg.create_pool(dsn=self._dsn)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    uid BIGINT PRIMARY KEY,
                    bal BIGINT DEFAULT 0,
                    xp INT DEFAULT 0
                );
            """)

    async def execute(self, query: str, *args):
        return await self.pool.execute(query, *args)

    async def fetchrow(self, query: str, *args):
        return await self.pool.fetchrow(query, *args)