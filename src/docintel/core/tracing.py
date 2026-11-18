"""Send spans to the local Phoenix, and trace every OpenAI call on its own."""

from phoenix.otel import register

from docintel.core.config import get_settings


def setup_tracing() -> None:
    """Call once, when the app starts. With TRACING=false, spans cost nothing and go nowhere."""
    if get_settings().tracing:
        register(project_name="docintel", auto_instrument=True, batch=True)
