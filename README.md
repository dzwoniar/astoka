# Astoka

Wewnętrzne narzędzie Akademii 100k do automatycznej produkcji shortów (long-form → 9:16 z polskimi captions). Self-hosted, działa lokalnie na pojedynczej stacji z RTX 4090.

📖 **Dokumenty źródłowe (w roocie repo):**
- [`PRD-Astoka.md`](./PRD-Astoka.md) — Product Requirements Document v0.1
- [`RESEARCH-Highlight-Detection.md`](./RESEARCH-Highlight-Detection.md) — załącznik techniczny do Sprint 4

## Stack (PRD §8)

```
Frontend:   Next.js 14 + TypeScript + Tailwind + shadcn/ui
Backend:    FastAPI (Python 3.11) + Pydantic + SQLAlchemy 2.0
Workers:    Celery 5 + Redis
DB:         Postgres 16 + pgvector
Storage:    MinIO (S3-compatible) lokalnie
ASR:        faster-whisper + WhisperX (model TBD po Faza 0 spike)
LLM:        Llama 3.3 8B Q4_K_M przez Ollama
Render:     FFmpeg 7 (NVENC) + format ASS dla captions
Hardware:   1× RTX 4090, 64 GB RAM, 12-core CPU, 1 TB NVMe
```

## Repo layout

```
astoka/
├── apps/
│   └── web/                    # Next.js 14 App Router
├── services/
│   ├── api/                    # FastAPI backend
│   ├── worker/                 # Celery workers (ASR, render, highlight)
│   └── highlight/              # ML pipeline modules + vendor/samurai/
├── packages/
│   └── shared/                 # generated TS types from Pydantic OpenAPI
├── infra/
│   ├── docker-compose.yml      # main stack
│   ├── postgres/               # init.sql (extensions)
│   ├── ollama/                 # custom image with Llama 3.3 pre-pull
│   └── traefik/                # reverse proxy + TLS
├── scripts/
│   ├── asr_spike.py            # Faza 0 ASR baseline
│   └── data/akademia_samples/  # ground truth (not committed)
├── docs/
│   └── asr-baseline.md         # Faza 0 report (filled by spike)
└── PRD-Astoka.md               # source of truth
```

## Quick start (dev)

**Wymagania:**
- Docker + Docker Compose v2
- NVIDIA Container Toolkit (jeśli chcesz odpalić ML pipeliny lokalnie)
- Node 20 + pnpm 9
- Python 3.11 + [`uv`](https://github.com/astral-sh/uv)

```bash
# 1. Setup .env
cp .env.example .env
# Edytuj .env — szczególnie API_SECRET_KEY (otwórz `openssl rand -hex 32`).

# 2. Bootstrap (instaluje Node + Python deps lokalnie)
make bootstrap

# 3. Start stack
make up

# 4. Status / logi
make ps
make logs
```

**URLs (po starcie):**
- Web: http://localhost:3000
- API: http://localhost:8000 (`/health`, `/docs`)
- MinIO console: http://localhost:9001
- Flower (Celery monitoring): http://localhost:5555
- Traefik dashboard: http://localhost:8080
- Ollama: http://localhost:11434

Z `astoka.local` w `/etc/hosts` (zob. `infra/traefik/certs/README.md`) dostajesz HTTPS przez Traefik.

## Faza 0 — ASR baseline gate

**Krytyczne:** zanim ruszysz z Sprint 1, musisz mieć zmierzony WER na 5 realnych nagraniach Akademii. PRD MET-06 wymaga ≤10%.

```bash
# 1. Wrzuć 5 nagrań + ground truth do scripts/data/akademia_samples/
#    sample_01.mp4 + sample_01.txt
#    ...
# 2. Uruchom spike
make asr-spike
# 3. Przeczytaj raport
cat docs/asr-baseline.md
```

Decyzja gate (zielony/żółty/czerwony) udokumentowana w raporcie.

## Roadmap (z planu Sprint 0–9)

Plan implementacyjny: zob. `/root/.claude/plans/przeczytaj-prd-astoka-md-oraz-research-h-enumerated-sparrow.md` (developer-side) lub PRD §Appendix A.

| Sprint | Cel |
|---|---|
| 0 (this) | Setup + Faza 0 ASR spike |
| 1 | DB schema + minimal auth + project management |
| 2 | Ingest + ASR pipeline |
| 3 | Text-based editing + filler removal |
| 4 | Highlight detection (HIGH-XX + RESEARCH §1–6) |
| 5 | Reframe 9:16 |
| 6 | Captions |
| 7 | Render + Export + Batch |
| 8 | Prompt-driven edit + full Auth + polish |
| 9 | User testing + bug bash + DR + go/no-go |

## Common dev tasks

```bash
make help                       # lista komend
make migrate                    # apply Alembic migrations
make migrate-create MSG="add foo bar"
make seed                       # tworzy admina (Sprint 1+)
make test                       # pełne testy
make lint type-check            # CI parity locally
make codegen                    # regenerate TS types from API
make down                       # zatrzymaj stack
make down-volumes               # ⚠ DESTRUCTIVE — usuwa też dane
```

## Decyzje architektoniczne

| Decyzja | Rationale |
|---|---|
| Monorepo (pnpm workspace + Python services) | jeden codegen, spójne CI, Janek solo-dev |
| Selective copy z SamurAIGPT, nie submodule | clean namespace, łatwa modyfikacja promptów PL — zob. `services/highlight/vendor/samurai/ATTRIBUTION.md` |
| pgvector on Day 1 | unika migration churn — Faza 2 semantic search dostaje pole gotowe |
| Single docker-compose, no K8s | overkill dla 1 serwera (PRD §8) |
| Minimal auth w Sprint 1, full w Sprint 8 | PRD AUTH-XX odłożone, ale projekty potrzebują ownera Day 1 |

## License

Proprietary (Akademia 100k internal). Vendor extracts pod ich własnymi licencjami — zob. `services/highlight/vendor/samurai/LICENSE`.
