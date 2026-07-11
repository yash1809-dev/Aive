CREATE TABLE IF NOT EXISTS items (
    id                TEXT PRIMARY KEY,
    title             TEXT NOT NULL,
    source            TEXT,
    source_url        TEXT,
    type              TEXT NOT NULL,
    raw_text          TEXT,
    summary           TEXT,
    problem           TEXT,
    solution          TEXT,
    technology        TEXT,
    keywords          TEXT,
    industry          TEXT,
    impact            TEXT,
    beneficiaries     TEXT,
    year              TEXT,
    extracted_at      TEXT,
    extraction_status TEXT DEFAULT 'pending',
    ko_type           TEXT DEFAULT 'document',
    confidence        REAL DEFAULT 0.5,
    version           INTEGER DEFAULT 1,
    provenance        TEXT,  -- JSON object
    validation_state  TEXT DEFAULT 'unvalidated',
    reasoning_refs    TEXT,  -- JSON array
    discovery_refs    TEXT   -- JSON array
);

CREATE TABLE IF NOT EXISTS nodes (
    id           TEXT PRIMARY KEY,
    label        TEXT NOT NULL,
    node_type    TEXT NOT NULL,
    source_items TEXT
);

CREATE TABLE IF NOT EXISTS edges (
    id           TEXT PRIMARY KEY,
    from_node    TEXT REFERENCES nodes(id),
    to_node      TEXT REFERENCES nodes(id),
    relationship TEXT NOT NULL,
    weight       REAL DEFAULT 0.7,
    evidence     TEXT  -- JSON array of source item IDs
);

CREATE TABLE IF NOT EXISTS workspaces (
    id             TEXT PRIMARY KEY,
    name           TEXT NOT NULL,
    status         TEXT DEFAULT 'active', -- active, archived
    created_at     TEXT NOT NULL,
    updated_at     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workspace_history (
    id             TEXT PRIMARY KEY,
    workspace_id   TEXT REFERENCES workspaces(id),
    version        INTEGER NOT NULL,
    snapshot_data  TEXT, -- JSON snapshot of graph/items state
    created_at     TEXT NOT NULL,
    created_by     TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS opportunities (
    id                   TEXT PRIMARY KEY,
    title                TEXT,
    problem              TEXT,
    technology           TEXT,
    market               TEXT,
    timing_signal        TEXT,
    problem_node         TEXT REFERENCES nodes(id),
    technology_node      TEXT REFERENCES nodes(id),
    market_node          TEXT REFERENCES nodes(id),
    reasoning            TEXT,
    evidence             TEXT,
    existing_competitors TEXT,
    novelty_score        INTEGER,
    timing_score         INTEGER,
    market_score         INTEGER,
    feasibility          INTEGER,
    confidence_score     INTEGER,
    edge_confidence      REAL,
    source_papers        TEXT,
    source_patents       TEXT,
    source_startups      TEXT,
    critic_verdict       TEXT DEFAULT 'pending',
    critic_notes         TEXT,
    created_at           TEXT
);

CREATE TABLE IF NOT EXISTS opportunity_feedback (
    id             TEXT PRIMARY KEY,
    opportunity_id TEXT REFERENCES opportunities(id),
    human_rating   INTEGER,
    novel          INTEGER,
    feasible       INTEGER,
    valuable       INTEGER,
    surprising     INTEGER,
    would_build    INTEGER DEFAULT 0,
    notes          TEXT,
    created_at     TEXT
);

CREATE TABLE IF NOT EXISTS rejected_ideas (
    id             TEXT PRIMARY KEY,
    opportunity_id TEXT REFERENCES opportunities(id),
    reason         TEXT,
    rejected_at    TEXT
);
