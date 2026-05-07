# Dev Setup — pełny przewodnik

## Wymagania

| Tool | Min version | Sprawdź |
|---|---|---|
| Docker | 24+ | `docker --version` |
| Docker Compose | 2.20+ | `docker compose version` |
| Node | 20 | `node -v` |
| pnpm | 9.12 | `pnpm -v` |
| Python | 3.11 | `python --version` |
| uv | latest | `uv --version` |
| NVIDIA Container Toolkit | latest | `docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi` |

### NVIDIA Container Toolkit (Linux)

```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
  sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker
```

## Pierwsze uruchomienie

```bash
git clone git@github.com:dzwoniar/astoka.git
cd astoka
cp .env.example .env

# Generate API_SECRET_KEY
openssl rand -hex 32
# Wklej do .env

make bootstrap
make up
```

Pierwszy `make up` pobierze ~5GB Llama 3.3 8B przez Ollama — może chwilę potrwać.

## Hosts file (HTTPS via Traefik)

Dodaj do `/etc/hosts`:

```
127.0.0.1 astoka.local flower.astoka.local minio.astoka.local
```

Wygeneruj cert dla `astoka.local`:

```bash
brew install mkcert  # lub apt install mkcert
mkcert -install
cd infra/traefik/certs
mkcert -cert-file astoka.local.pem -key-file astoka.local.key astoka.local "*.astoka.local"
```

## Daily workflow

```bash
make up                    # rano
make logs                  # kiedy coś nie działa
# edytuj kod — hot reload działa dla web + api
make test                  # przed PR
make lint type-check       # przed PR
make down                  # wieczorem (lub zostaw)
```

## Debugowanie

| Problem | Rozwiązanie |
|---|---|
| `make up` wisi na Ollama healthcheck | Pierwsze pobranie modelu trwa kilka minut. Sprawdź `make logs` na ollama. |
| `docker: Error response from daemon: could not select device driver "nvidia"` | Zainstaluj NVIDIA Container Toolkit (powyżej). |
| Worker crashes z `CUDA out of memory` | Sprzętowo: tylko 24 GB VRAM. Ogranicz concurrent jobs (`--concurrency=1` w `infra/docker-compose.yml` worker.command). |
| `psql: FATAL: database "astoka" does not exist` | `make down-volumes && make up` (DESTRUCTIVE — tylko świeży repo). |
| Web nie widzi API | Sprawdź `NEXT_PUBLIC_API_URL` w `.env` i sieć dockera (`make ps`). |

## Lokalny dev bez Dockera (opcjonalny, Sprint 0+)

Jeśli chcesz iterować na pythonie z lepszym debuggerem:

```bash
# Postgres + Redis + MinIO + Ollama nadal w docker-compose:
docker compose -f infra/docker-compose.yml --env-file .env up -d postgres redis minio ollama

# API lokalnie:
cd services/api
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"
uvicorn astoka_api.main:app --reload

# Worker lokalnie (Sprint 1+):
cd services/worker
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
celery -A astoka_worker.celery_app worker --loglevel=info
```

## Następny krok

Po setup'ie:
1. Przeczytaj [`PRD-Astoka.md`](../PRD-Astoka.md).
2. Uruchom Faza 0 ASR spike (zob. README → "Faza 0").
3. Zacznij Sprint 1.
