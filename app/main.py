import json
import threading

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app import shows
from app.config import SHOWS_DIR, STATIC_DIR, load_config, save_config
from app.tts import VOICES, is_custom, list_custom_voices

app = FastAPI(title="Morning Radio Show")
_lock = threading.Lock()


def _run():
    with _lock:
        try:
            shows.generate()
        except Exception:
            pass  # error already recorded in shows.status


@app.post("/api/shows/generate")
def generate_show():
    if shows.status["state"] == "running":
        raise HTTPException(409, "A show is already being produced")
    shows.status.update(state="running", step="Warming up the microphones", error=None)
    threading.Thread(target=_run, daemon=True).start()
    return shows.status


@app.get("/api/status")
def get_status():
    return shows.status


@app.get("/api/shows")
def list_shows():
    return shows.list_episodes()


@app.get("/api/shows/{episode_id}")
def get_show(episode_id: str):
    f = SHOWS_DIR / f"{episode_id}.json"
    if not f.is_file() or f.parent != SHOWS_DIR:
        raise HTTPException(404)
    return json.loads(f.read_text(encoding="utf-8"))


@app.get("/audio/{episode_id}.wav")
def get_audio(episode_id: str):
    f = SHOWS_DIR / f"{episode_id}.wav"
    if not f.is_file() or f.parent != SHOWS_DIR:
        raise HTTPException(404)
    return FileResponse(f, media_type="audio/wav")


@app.get("/api/config")
def get_config():
    try:
        custom = list_custom_voices()
    except Exception as e:  # listing is a nicety; manual IDs still work
        print(f"[config] couldn't list custom voices: {e}")
        custom = []
    return {"config": load_config(), "voices": VOICES, "custom_voices": custom}


@app.put("/api/config")
def put_config(cfg: dict):
    if len(cfg.get("hosts", [])) < 2:
        raise HTTPException(400, "Need two hosts")
    if cfg["hosts"][0]["name"].strip() == cfg["hosts"][1]["name"].strip():
        raise HTTPException(400, "Hosts need different names")
    for h in cfg["hosts"][:2]:
        v = h.get("voice", "").strip()
        if not (v in VOICES or is_custom(v)):
            raise HTTPException(400, f"{h['name']}: voice must be a built-in voice or a voice_... / voicekey_... ID")
    save_config(cfg)
    return {"ok": True}


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
