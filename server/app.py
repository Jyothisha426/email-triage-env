# server/app.py
# Required entry point for OpenEnv multi-mode deployment spec.
# Imports and re-exports the FastAPI app from main.py.
from main import app

__all__ = ["app"]
