import os
import sys
from pathlib import Path

# Make `app` importable when running `pytest` from the backend/ dir.
BACKEND_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(BACKEND_ROOT))

# Use an isolated in-memory-ish sqlite file for any DB-touching tests.
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_football_predictor.db")
os.environ.setdefault("SECRET_KEY", "test-secret-key-please-ignore-1234567890")
