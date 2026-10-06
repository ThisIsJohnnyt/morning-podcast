"""Pipeline: gather data -> write script -> record audio -> save episode."""
import json
import traceback
from datetime import date, datetime

from app.config import SHOWS_DIR, load_config
from app.script_writer import write_script
from app.sources.calendar import get_events
from app.sources.news import get_headlines
from app.sources.weather import get_weather
from app.tts import synthesize

# Live status for the UI; there's only ever one generation running at a time.
status = {"state": "idle", "step": None, "error": None, "episode": None}


def _set(step: str) -> None:
    status["step"] = step
    print(f"[show] {step}")


def _safe(fn, cfg):
    try:
        return fn(cfg)
    except Exception as e:  # one broken source shouldn't kill the show
        print(f"[show] {fn.__name__} failed: {e}")
        return {"error": str(e)}


def gather(cfg: dict) -> dict:
    data = {"weather": _safe(get_weather, cfg)}
    if cfg.get("ical_url"):
        data["calendar"] = _safe(get_events, cfg)
    else:
        data["calendar"] = None
    data["headlines"] = _safe(get_headlines, cfg)
    return data


def generate(day: date | None = None) -> str:
    day = day or date.today()
    episode_id = day.isoformat()
    cfg = load_config()
    status.update(state="running", error=None, episode=None)
    try:
        _set("Gathering weather, calendar and news")
        data = gather(cfg)

        _set("Writing the script")
        script = write_script(cfg, data)

        _set("Recording in the studio")
        synthesize(script["lines"], cfg["hosts"], cfg["tts_model"], SHOWS_DIR / f"{episode_id}.wav")

        meta = {
            "id": episode_id,
            "title": script["title"],
            "created": datetime.now().isoformat(timespec="seconds"),
            "hosts": [{"name": h["name"], "voice": h["voice"]} for h in cfg["hosts"][:2]],
            "lines": script["lines"],
            "data": data,
        }
        (SHOWS_DIR / f"{episode_id}.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
        status.update(state="done", step="On air!", episode=episode_id)
        return episode_id
    except Exception as e:
        traceback.print_exc()
        status.update(state="error", error=str(e))
        raise


def list_episodes() -> list[dict]:
    eps = []
    for f in sorted(SHOWS_DIR.glob("*.json"), reverse=True):
        meta = json.loads(f.read_text(encoding="utf-8"))
        eps.append({"id": meta["id"], "title": meta["title"], "created": meta["created"]})
    return eps
