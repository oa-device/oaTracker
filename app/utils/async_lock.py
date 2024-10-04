import asyncio
from concurrent.futures import ThreadPoolExecutor
import contextlib


_pool = ThreadPoolExecutor()

@contextlib.asynccontextmanager
async def async_lock(lock):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_pool, lock.acquire)
    try:
        yield  # the lock is held
    finally:
        lock.release()