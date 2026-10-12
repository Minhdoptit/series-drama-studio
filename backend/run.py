"""
run.py — Windows-safe uvicorn entry point
Chạy: python run.py
"""
import sys, asyncio, selectors

# Fix Windows psycopg ProactorEventLoop error TRUOC khi uvicorn khoi dong
if sys.platform == "win32":
    loop = asyncio.SelectorEventLoop(selectors.SelectSelector())
    asyncio.set_event_loop(loop)

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        loop="asyncio",          # force asyncio (SelectorEventLoop)
    )
