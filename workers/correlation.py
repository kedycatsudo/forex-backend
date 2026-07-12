from __future__ import annotations

import uuid
from contextlib import contextmanager
from typing import Generator

from app.core.logging import request_id_ctx


@contextmanager
def bind_correlation(
    incoming_request_id: str | None = None,
) -> Generator[dict[str, str | None], None, None]:
    """
    Bind correlation ID into request_id context for worker message processing.

    Behavior:
    - If incoming_request_id exists: use it as request_id, no job_id generated.
    - If missing: generate UUID and use it as both request_id and job_id.
    - Always resets context after the block.
    """
    job_id: str | None = None
    request_id = incoming_request_id

    if not request_id:
        job_id = str(uuid.uuid4())
        request_id = job_id

    token = request_id_ctx.set(request_id)
    try:
        yield {
            "request_id": request_id,
            "job_id": job_id,
        }
    finally:
        request_id_ctx.reset(token)
