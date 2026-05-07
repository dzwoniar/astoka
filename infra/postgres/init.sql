-- Initial Postgres setup. Runs once on first container start.
-- Schema is owned by Alembic migrations (Sprint 1+); this file only enables extensions.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- pgvector reserved for Sprint 1.5+ (semantic transcript search). Enable now to avoid migration churn.
CREATE EXTENSION IF NOT EXISTS "vector";
