import asyncio
import logging
from typing import Coroutine

logger = logging.getLogger("main_api")

# asyncio.create_task() only holds a *weak* reference to the task it returns;
# if nothing else references it, the task can be garbage-collected before it
# finishes running (a bare `asyncio.create_task(send_audit_log(...))` with the
# result discarded is exactly this pattern). Keeping every in-flight task in
# this set until it completes prevents that, and the done-callback logs any
# exception that would otherwise vanish silently (a fire-and-forget audit log
# or alert that fails without a trace defeats its own purpose).
_background_tasks: set[asyncio.Task] = set()


def fire_and_forget(coro: Coroutine) -> asyncio.Task:
    task = asyncio.create_task(coro)
    _background_tasks.add(task)

    def _on_done(t: asyncio.Task) -> None:
        _background_tasks.discard(t)
        if t.cancelled():
            return
        exc = t.exception()
        if exc:
            logger.error(f"Background task {t.get_coro()} failed: {exc}", exc_info=exc)

    task.add_done_callback(_on_done)
    return task
