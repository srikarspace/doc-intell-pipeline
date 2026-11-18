"""JSON logs: one object per line, with the request_id of the request it belongs to."""

import structlog


def setup_logging() -> None:
    """Call once, when the app starts."""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # adds request_id, set by the middleware
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )
