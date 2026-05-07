# Astoka

Self-hosted narzędzie Akademii 100k do automatycznej produkcji shortów (long-form → 9:16 z polskimi captions). Działa lokalnie na localhost lub na pojedynczej stacji z RTX 4090.

📖 **Dokumenty źródłowe:**
- [`PRD-Astoka.md`](./PRD-Astoka.md) — Product Requirements Document v0.1
- [`RESEARCH-Highlight-Detection.md`](./RESEARCH-Highlight-Detection.md) — Załącznik techniczny do Sprint 4

---

## Quick Start (one command)

```bash
git clone git@github.com:dzwoniar/astoka.git
cd astoka
make install
```

`make install` (~5 min):
1. Sprawdza Docker + Docker Compose
2. Generuje `.env` z losowym `API_SECRET_KEY`
3. Buduje obrazy Docker
4. Stawia Postgres, Redis, MinIO i czeka aż będą zdrowe
5. Uruchamia migracje DB
6. Tworzy użytkownika `admin/admin`
7. Stawia API + worker + web

Po zakończeniu: otwórz **http://localhost:3000**, login `admin/admin`.

### GPU mode (Ollama dla LLM reranking highlightów)

```bash
make install-gpu
```

Wymaga NVIDIA Container Toolkit. Bez `--gpu` highlight detection jedzie w trybie heurystycznym (bez LLM).

### Tylko Phase A (auth + projekty, bez worker'ów)

```bash
make install-no-worker
```

Najszybszy start — pozwala przetestować login + projects CRUD bez czekania na build worker'a.

---

## Status implementacji

Sprint 1 ("Demo Backbone") jest w trakcie — zob. plan w `/root/.claude/plans/...`.

| Phase | Status | Co działa |
|---|---|---|
| Sprint 0 | ✅ Done | Docker stack, healthcheck, ASR spike, vendor extracts (chunking + dedupe + prompt) |
| Phase A.1 | ✅ Done | Pełen DB schema + Alembic 0001 |
| Phase A.2 | ✅ Done | Auth: bcrypt + JWT cookie + seed CLI |
| Phase A.3 | ✅ Done | Projects CRUD API |
| Phase A.5 | ✅ Done | Web: login + projects list + new + detail |
| Phase E.2/E.3 | ✅ Done | docker-compose.dev.yml + `make install` |
| Phase B | 🚧 In progress | Ingest API + workers (upload, yt-dlp, probe, proxy) |
| Phase C | ⏳ Pending | ASR pipeline (faster-whisper) |
| Phase D | ⏳ Pending | Highlight detection (heuristics + Ollama LLM) |
| Phase E.1 | ⏳ Pending | TanStack Query + SSE for live status |
| Phase E.5 | ⏳ Pending | Playwright E2E |

**Co możesz przetestować TERAZ (po `make install`):**
- Login admin/admin
- Tworzenie projektów (z opcjonalnym polem klient)
- Lista projektów z sortowaniem i filtrem (aktywne/zarchiwizowane/wszystkie)
- Soft-delete (archiwizacja) + restore + hard-delete

**Co jeszcze nie działa:**
- Upload pliku / YouTube URL (Phase B)
- ASR / transkrypcja (Phase C)
- Highlight detection (Phase D)

---

## Stack

```
Frontend:   Next.js 14 + TypeScript + Tailwind + shadcn/ui
Backend:    FastAPI (Python 3.11) + Pydantic + SQLAlchemy 2.0
Workers:    Celery 5 + Redis
DB:         Postgres 16 + pgvector
Storage:    MinIO (S3-compatible) lokalnie
ASR:        faster-whisper (model TBD po Faza 0 spike)
LLM:        Llama 3.3 8B Q4_K_M przez Ollama (z heuristic fallback)
Render:     FFmpeg 7 (NVENC)  ← Sprint 5
Hardware:   1× RTX 4090 (rec.) lub CPU dla developmentu
```

---

## Repo layout

```
astoka/
├── apps/web/                      # Next.js 14 App Router
├── services/
│   ├── api/                       # FastAPI backend
│   │   ├── astoka_api/
│   │   │   ├── auth/              # bcrypt + JWT + cookie
│   │   │   ├── cli/               # seed.py
│   │   │   ├── db/models/         # ORM (full MVP schema)
│   │   │   ├── routers/           # /auth, /projects, /health
│   │   │   ├── schemas/           # Pydantic
│   │   │   └── services/          # Business logic
│   │   └── alembic/versions/      # Migrations
│   ├── worker/                    # Celery workers
│   └── highlight/                 # ML pipeline + vendor/samurai/
├── infra/
│   ├── docker-compose.dev.yml     # Default for `make install` — localhost ports, no Traefik
│   ├── docker-compose.yml         # Production-style — Traefik + TLS
│   └── ...
├── scripts/
│   ├── install.sh                 # One-shot installer
│   └── asr_spike.py               # Faza 0 ASR baseline
└── docs/
```

---

## Common commands

```bash
make help           # List all targets
make install        # One-shot install (CPU mode)
make install-gpu    # Install with Ollama (GPU required)
make up             # Start dev stack (after install)
make down           # Stop stack (preserves data)
make logs           # Tail logs
make ps             # Service status
make migrate        # Apply Alembic migrations
make seed           # Re-seed admin user
make test           # Run all tests
make lint           # Lint Python + Web
make type-check     # mypy + tsc
make api-shell      # Bash inside api container
make db-shell       # psql to Postgres
```

---

## Try this (after Phase B/C/D land)

Once ingest + ASR + highlights are wired:

1. Login admin/admin
2. **Nowy projekt** → wpisz nazwę + kliknij Utwórz
3. Wybierz źródło: **upload pliku** lub **YouTube URL**
4. Zaczekaj na pipeline: download → probe → transcribe → highlights (~5-10 min dla 5-min wideo na GPU)
5. Zobacz transkrypcję klikalną word-by-word
6. Akceptuj/odrzucaj propozycje highlightów

Test YouTube URL (gdy Phase B będzie gotowy): _TBD — Janek wpisze tu URL._

---

## Faza 0 — ASR baseline gate

Krytyczne przed produkcyjnym dev: PRD MET-06 wymaga WER ≤10% na PL.

```bash
# 1. Wrzuć 5 nagrań Akademii do scripts/data/akademia_samples/
#    sample_01.mp4 + sample_01.txt (ground truth)
# 2. Uruchom spike (wymaga --profile worker + GPU)
make asr-spike
# 3. Przeczytaj raport
cat docs/asr-baseline.md
```

Decyzja gate (zielony/żółty/czerwony) udokumentowana w raporcie.

---

## Decyzje architektoniczne

| Decyzja | Rationale |
|---|---|
| Monorepo (pnpm workspace + Python services) | Jeden codegen, spójne CI, Janek solo-dev |
| Selective copy z SamurAIGPT, nie submodule | Clean namespace, łatwa modyfikacja promptów PL |
| pgvector on Day 1 | Unika migration churn — Faza 2 semantic search dostaje pole gotowe |
| Single docker-compose.dev.yml dla install | "Make install" UX > production parity dla MVP |
| Minimal auth admin/admin w Sprint 1, full w Sprint 6 | Demo działa Day 1, multi-user gdy stać |
| Heuristic fallback gdy brak Ollama | Demo działa nawet bez GPU |
| Manual TS types (zamiast OpenAPI codegen) | Mniej infrastruktury w Sprint 1 |

---

## Troubleshooting

| Problem | Rozwiązanie |
|---|---|
| `make install` zawiesza się na "Building images" | Pierwsza kompilacja faster-whisper deps (~3-5 min). Sprawdź `docker compose logs`. |
| `docker: Error response from daemon: could not select device driver "nvidia"` | Brak NVIDIA Container Toolkit. Użyj `make install` zamiast `make install-gpu`. |
| Worker crashes z `CUDA out of memory` | Tylko 24 GB VRAM. Ogranicz concurrent jobs lub przerwij równoległe runy. |
| `psql: FATAL: database "astoka" does not exist` | `make down-volumes && make install` (DESTRUCTIVE — usuwa dane). |
| Web nie widzi API | Sprawdź `NEXT_PUBLIC_API_URL=http://localhost:8000` w `.env`. |
| `make install` mówi "ports already allocated" | Inny serwis używa 3000/8000/5432. Zmień w `.env` lub zatrzymaj kolidujący serwis. |

---

## License

Proprietary (Akademia 100k internal). Vendor extracts — zob. `services/highlight/astoka_highlight/vendor/samurai/LICENSE`.
