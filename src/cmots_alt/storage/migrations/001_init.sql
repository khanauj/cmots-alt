-- 001_init.sql — base schema for cmots-alt
-- Tables:
--   company                : canonical equity master (ISIN-keyed)
--   identifier_crosswalk   : ISIN ↔ NSE symbol ↔ BSE code ↔ AMFI code
--   co_code_sequence       : single-row autoincrementing surrogate
--   ingest_manifest        : audit row per bronze write

CREATE TABLE IF NOT EXISTS company (
    isin            TEXT PRIMARY KEY,
    co_code         INTEGER NOT NULL UNIQUE,
    nse_symbol      TEXT UNIQUE,
    bse_code        INTEGER UNIQUE,
    legal_name      TEXT NOT NULL,
    short_name      TEXT NOT NULL,
    category        TEXT NOT NULL,
    sector_code     INTEGER,
    sector_name     TEXT,
    mcap_class      TEXT,
    bse_group       TEXT,
    nse_listed      INTEGER NOT NULL,
    bse_listed      INTEGER NOT NULL,
    listing_date    TEXT,
    face_value      REAL,
    first_seen_at   TEXT NOT NULL,
    last_seen_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS identifier_crosswalk (
    isin       TEXT NOT NULL,
    id_type    TEXT NOT NULL,
    id_value   TEXT NOT NULL,
    source     TEXT NOT NULL,
    confidence REAL NOT NULL,
    seen_at    TEXT NOT NULL,
    PRIMARY KEY (isin, id_type, id_value)
);

CREATE TABLE IF NOT EXISTS co_code_sequence (
    next_value INTEGER NOT NULL
);
INSERT INTO co_code_sequence (next_value)
SELECT 100001 WHERE NOT EXISTS (SELECT 1 FROM co_code_sequence);

CREATE TABLE IF NOT EXISTS ingest_manifest (
    run_id     TEXT PRIMARY KEY,
    source     TEXT NOT NULL,
    artifact   TEXT NOT NULL,
    partition  TEXT NOT NULL,
    raw_path   TEXT NOT NULL,
    sha256     TEXT NOT NULL,
    rows       INTEGER,
    started_at TEXT NOT NULL,
    ended_at   TEXT NOT NULL,
    status     TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_manifest_source_part
    ON ingest_manifest(source, artifact, partition);
