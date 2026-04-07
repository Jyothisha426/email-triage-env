# Dockerfile
# ─────────────────────────────────────────────────────────────
# Using public.ecr.aws instead of docker.io/library because
# the validator's network blocks/rate-limits Docker Hub.
# public.ecr.aws is Amazon's free public mirror — no auth,
# no rate limits, same official Python image.
# ─────────────────────────────────────────────────────────────

FROM public.ecr.aws/docker/library/python:3.11-slim

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
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860", "--workers", "1"]