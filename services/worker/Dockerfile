# Astoka worker — runs ML pipelines on GPU.
# Base: NVIDIA CUDA 12.4 runtime (matches RTX 4090 driver expectations + faster-whisper/CTranslate2).
#
# Build context: `services/` (parent dir), NOT `services/worker/`. This is
# enforced by infra/docker-compose.dev.yml so we can COPY sibling packages
# (api/, highlight/) needed by worker's path deps in pyproject.toml.
#
# Layout inside container:
#   /app/api/         — astoka-api package (ORM models, schemas, services)
#   /app/highlight/   — astoka-highlight package (vendor extracts + ML pipeline)
#   /app/worker/      — this service (Celery tasks)

FROM nvidia/cuda:12.4.1-cudnn-runtime-ubuntu22.04

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    DEBIAN_FRONTEND=noninteractive \
    PATH="/usr/local/bin:$PATH"

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3.11 python3.11-venv python3-pip python3.11-dev \
        ffmpeg curl ca-certificates build-essential \
    && rm -rf /var/lib/apt/lists/* \
    && update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1 \
    && update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

RUN pip install --no-cache-dir uv

# Copy sibling packages FIRST so worker's path deps can resolve them.
WORKDIR /app
COPY api /app/api
COPY highlight /app/highlight
COPY worker /app/worker

# Install worker (resolves astoka-api + astoka-highlight from /app/api + /app/highlight
# via [tool.uv.sources] in worker/pyproject.toml).
WORKDIR /app/worker
RUN uv pip install --system --no-cache .

CMD ["celery", "-A", "astoka_worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
