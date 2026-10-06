import json
import shutil
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.json"
EXAMPLE_CONFIG_PATH = ROOT / "config.example.json"
SHOWS_DIR = ROOT / "shows"
STATIC_DIR = ROOT / "static"

load_dotenv(ROOT / ".env")
SHOWS_DIR.mkdir(exist_ok=True)


def load_config() -> dict:
    # First run: start from the example settings; the real file stays out of git.
    if not CONFIG_PATH.exists():
        shutil.copy(EXAMPLE_CONFIG_PATH, CONFIG_PATH)
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
