import asyncio
import sys
import asyncpg

# Fix for Python 3.13 + asyncpg on Windows: ProactorEventLoop breaks asyncpg
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

async def test():
    conn = await asyncpg.connect("postgresql://postgres:postgres@localhost:5432/my_lms")
    result = await conn.fetchval("SELECT 1")
    print("Connected! Result:", result)
    await conn.close()

asyncio.run(test())
