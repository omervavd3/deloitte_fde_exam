"""Dev entrypoint.

Windows defaults to ProactorEventLoop, which async psycopg cannot use.
Selecting the policy here happens before uvicorn creates its loop.
Not needed in Docker; the Dockerfile calls uvicorn directly.
"""

import asyncio
import sys
import warnings

if sys.platform == "win32":
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import uvicorn  # noqa: E402

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
