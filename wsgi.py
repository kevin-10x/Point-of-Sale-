"""WSGI entrypoint — used by gunicorn, Railway, Render, and `flask` CLI."""
from run import app  # noqa: F401  re-export the app instance

__all__ = ["app"]
