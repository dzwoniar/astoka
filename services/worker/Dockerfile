# Astoka worker — runs ML pipelines on GPU.
# Base: NVIDIA CUDA 12.4 runtime (matches RTX 4090 driver expectations + faster-whisper/CTranslate2).
# Sprint 0 ships skeleton only — heavy ML deps wire in Sprint 2.

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

WORKDIR /app
COPY pyproject.toml ./
RUN uv pip install --system --no-cache .

COPY . /app

CMD ["celery", "-A", "astoka_worker.celery_app", "worker", "--loglevel=info", "--concurrency=2"]
