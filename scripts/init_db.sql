-- Run automatically by Docker postgres init on first start
-- Production migrations are handled by Alembic

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";   -- fast LIKE queries
CREATE EXTENSION IF NOT EXISTS "btree_gin"; -- GIN indexes on composite types

-- Partitioned jobs table (monthly)
CREATE TABLE IF NOT EXISTS jobs (
    id              UUID NOT NULL DEFAULT gen_random_uuid(),
    title           TEXT NOT NULL,
    company_name    TEXT NOT NULL DEFAULT '',
    location        TEXT,
    remote_type     TEXT CHECK (remote_type IN ('onsite','hybrid','remote','flexible')),
    salary_min      NUMERIC(12,2),
    salary_max      NUMERIC(12,2),
    salary_currency CHAR(3) DEFAULT 'USD',
    description_text        TEXT NOT NULL DEFAULT '',
    description_compressed  TEXT,
    skills          TEXT[] NOT NULL DEFAULT '{}',
    content_hash    CHAR(64) NOT NULL,
    source_url      TEXT NOT NULL DEFAULT '',
    source_domain   TEXT NOT NULL DEFAULT '',
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_seen_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

CREATE TABLE IF NOT EXISTS jobs_default PARTITION OF jobs DEFAULT;

CREATE UNIQUE INDEX IF NOT EXISTS idx_jobs_content_hash  ON jobs (content_hash);
CREATE        INDEX IF NOT EXISTS idx_jobs_active_recent  ON jobs (is_active, last_seen_at DESC) WHERE is_active = TRUE;
CREATE        INDEX IF NOT EXISTS idx_jobs_skills         ON jobs USING GIN (skills);
CREATE        INDEX IF NOT EXISTS idx_jobs_fts            ON jobs USING GIN (to_tsvector('english', title || ' ' || description_text));

CREATE TABLE IF NOT EXISTS users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           TEXT UNIQUE NOT NULL,
    password_hash   TEXT,
    tier            TEXT NOT NULL DEFAULT 'free' CHECK (tier IN ('free','pro','enterprise')),
    preferences     JSONB NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    last_active_at  TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS resumes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version         INT NOT NULL DEFAULT 1,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    file_key        TEXT NOT NULL,
    file_hash       CHAR(64) NOT NULL,
    parsed_data     JSONB,
    ats_score       SMALLINT,
    ats_issues      JSONB,
    embedding_id    UUID,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(user_id, version)
);

CREATE TABLE IF NOT EXISTS match_results (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    match_id        UUID NOT NULL,
    user_id         UUID NOT NULL REFERENCES users(id),
    resume_id       UUID NOT NULL REFERENCES resumes(id),
    filters         JSONB NOT NULL DEFAULT '{}',
    job_results     JSONB NOT NULL DEFAULT '[]',
    llm_provider    TEXT,
    total_cost_usd  NUMERIC(10,6),
    processing_ms   INT,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_type  TEXT NOT NULL,
    actor_id    UUID,
    resource_id TEXT,
    metadata    JSONB,
    ts          TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
-- Append-only: grant INSERT only, no UPDATE/DELETE to application role
