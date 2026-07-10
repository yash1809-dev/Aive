CREATE TABLE IF NOT EXISTS test_runs (
    run_id       TEXT PRIMARY KEY,
    label        TEXT,
    created_at   TEXT,
    total_tests  INTEGER,
    passed       INTEGER,
    failed       INTEGER,
    errored      INTEGER
);

CREATE TABLE IF NOT EXISTS test_results (
    id              TEXT PRIMARY KEY,
    run_id          TEXT REFERENCES test_runs(run_id),
    test_id         TEXT NOT NULL,
    test_name       TEXT,
    passed          INTEGER NOT NULL,
    scores_json     TEXT,
    threshold_json  TEXT,
    details_json    TEXT,
    error           TEXT,
    created_at      TEXT,
    UNIQUE(run_id, test_id)
);

CREATE TABLE IF NOT EXISTS novelty_cache (
    opportunity_id         TEXT PRIMARY KEY,
    verdict                TEXT,
    matching_products_json TEXT,
    search_queries_json    TEXT,
    confidence             REAL,
    cached_at              TEXT
);
