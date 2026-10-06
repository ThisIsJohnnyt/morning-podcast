"""Generate today's episode without the UI (for Windows Task Scheduler)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.shows import generate  # noqa: E402

if __name__ == "__main__":
    print("Episode ready:", generate())
