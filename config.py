"""Project configuration for TeacherEdLab.

Values can be overridden with environment variables (see config.example.env).
"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent


class Config:
    DATABASE = os.environ.get("TEDLAB_DB", str(BASE_DIR / "instance" / "teacheredlab.sqlite3"))
    # Key required for researcher-only actions (CSV import / export).
    # CHANGE THIS before any use beyond local demonstration.
    RESEARCHER_KEY = os.environ.get("TEDLAB_RESEARCHER_KEY", "demo-researcher-key")
    MAX_CONTENT_LENGTH = 2 * 1024 * 1024          # 2 MB upload / request limit
    MAX_IMPORT_ROWS = 2000
    MAX_OPEN_TEXT_CHARS = 1000
    SUBMIT_LIMIT_PER_MINUTE = 20                  # per client address, in-memory
    JSON_SORT_KEYS = False
    TESTING = False


class TestConfig(Config):
    """Tests override DATABASE with a temporary file (see tests/test_app.py)."""
    TESTING = True
    RESEARCHER_KEY = "test-key"
