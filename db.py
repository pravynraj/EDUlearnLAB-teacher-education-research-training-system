"""SQLite persistence layer: schema, initialisation and insert helpers."""
import sqlite3
from datetime import datetime, timezone
from flask import current_app, g

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS import_batches (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    filename    TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    rows_read   INTEGER NOT NULL,
    rows_saved  INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS respondents (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at       TEXT NOT NULL,
    source           TEXT NOT NULL CHECK (source IN ('collected','synthetic','imported')),
    category         TEXT NOT NULL,
    practicum_status TEXT NOT NULL,
    ai_exposure      TEXT NOT NULL,
    consent_given    INTEGER NOT NULL CHECK (consent_given IN (0,1)),
    consent_version  TEXT NOT NULL,
    batch_id         INTEGER REFERENCES import_batches(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS item_responses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    respondent_id INTEGER NOT NULL REFERENCES respondents(id) ON DELETE CASCADE,
    item_code     TEXT NOT NULL,
    domain_code   TEXT NOT NULL,
    score         INTEGER NOT NULL CHECK (score BETWEEN 1 AND 5),
    UNIQUE (respondent_id, item_code)
);

CREATE TABLE IF NOT EXISTS open_responses (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    respondent_id INTEGER NOT NULL REFERENCES respondents(id) ON DELETE CASCADE,
    question_code TEXT NOT NULL,
    response_text TEXT NOT NULL,
    UNIQUE (respondent_id, question_code)
);

CREATE INDEX IF NOT EXISTS idx_items_respondent ON item_responses(respondent_id);
CREATE INDEX IF NOT EXISTS idx_items_domain ON item_responses(domain_code);
CREATE INDEX IF NOT EXISTS idx_resp_source ON respondents(source);
"""


def _connect(path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    if "db" not in g:
        g.db = _connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()


def init_db(path):
    """Create all tables if they do not exist (idempotent)."""
    conn = _connect(path)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()


def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def insert_respondent(conn, clean, source, consent_version, batch_id=None, created_at=None):
    """Insert one validated respondent with item and open responses (caller commits)."""
    cur = conn.execute(
        "INSERT INTO respondents (created_at, source, category, practicum_status, ai_exposure,"
        " consent_given, consent_version, batch_id) VALUES (?,?,?,?,?,1,?,?)",
        (created_at or now_iso(), source, clean["category"], clean["practicum_status"],
         clean["ai_exposure"], consent_version, batch_id))
    rid = cur.lastrowid
    conn.executemany(
        "INSERT INTO item_responses (respondent_id, item_code, domain_code, score) VALUES (?,?,?,?)",
        [(rid, code, code[:3], score) for code, score in clean["answers"].items()])
    if clean.get("open"):
        conn.executemany(
            "INSERT INTO open_responses (respondent_id, question_code, response_text) VALUES (?,?,?)",
            [(rid, q, t) for q, t in clean["open"].items()])
    return rid
