# server/app.py
# Required entry point for OpenEnv multi-mode deployment spec.
# Imports and re-exports the FastAPI app from main.py.
import uvicorn
from main import app  # noqa: F401


def main():
    uvicorn.run("main:app", host="0.0.0.0", port=7860)


if __name__ == "__main__":
    main()
