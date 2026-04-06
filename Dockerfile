# Dockerfile
# ─────────────────────────────────────────────────────────────
# WHY THIS FILE EXISTS:
#   Hugging Face Spaces runs your environment inside Docker.
#   This file tells Docker exactly how to:
#     1. Set up a Python environment
#     2. Install your dependencies
#     3. Start your FastAPI server
#
#   The evaluator also does `docker build` on your repo —
#   if this fails, you're disqualified. Keep it simple.
#
#   Port 7860 is the REQUIRED port for HF Spaces.
# ─────────────────────────────────────────────────────────────

FROM python:3.11-slim

# Set working directory inside the container
WORKDIR /app

# Copy requirements first (Docker caches this layer — faster rebuilds)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy all project files into the container
COPY . .

# Expose port 7860 (mandatory for Hugging Face Spaces)
EXPOSE 7860

# Start the FastAPI server
# host 0.0.0.0 = accept connections from outside the container
# workers 1 = single worker (we have global state, so only 1!)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]
