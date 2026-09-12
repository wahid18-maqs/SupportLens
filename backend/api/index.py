import sys
from pathlib import Path

# Vercel's Python runtime treats api/ as the function's own root, so the
# sibling backend modules (main.py, agent.py, retrieval.py, ...) at the
# project root need to be added to sys.path explicitly to import cleanly.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import app  # noqa: E402
