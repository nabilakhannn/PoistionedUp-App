FROM python:3.11-slim

WORKDIR /app

# System deps: ffmpeg for yt-dlp/Whisper audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Railway/Render set PORT env var. Default to 8000 for local.
ENV PORT=8000

# Default: run the API server
# To run the worker instead, override CMD:
#   CMD ["python3", "-m", "worker.main"]
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
