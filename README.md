# WAKE FM: your personal morning podcast

Two AI radio hosts banter through **your** weather, calendar and news headlines every morning.
Gemini writes the script and [Gemini TTS](https://ai.google.dev/gemini-api/docs/speech-generation) performs it with two voices, using a delivery direction on every line ("excited, fast-paced", "dry and deadpan", …).

> **Max:** Rise and shine, superstar! It is Tuesday, and you are tuned in live to the one and only morning show broadcast exclusively to your ears!
> **June:** Good morning. Max has had three espressos already. Please send help.

Each episode runs 2–5 minutes, plays in a small radio-style web app with a live transcript, and is saved to an archive.

## Quick start

You need Python 3.11+ and a free [Gemini API key](https://aistudio.google.com/apikey).

```bash
git clone https://github.com/ThisIsJohnnyt/morning-podcast.git
cd morning-podcast
pip install -r requirements.txt
```

Add your API key in one of these ways:

- Copy `.env.example` to `.env` and fill in `GEMINI_API_KEY`, or
- Set `GEMINI_API_KEY` as an environment variable.

Start the app:

```bash
python -m uvicorn app.main:app --port 8000
```

Open **http://localhost:8000**, click **⚙ Settings**, make it yours, then hit **Tune in**. 📻

## Make it yours (all in ⚙ Settings)

| Setting | Notes |
|---|---|
| **Your name** | What the hosts call you |
| **City** | Click *Find* to look it up. Weather comes from [Open-Meteo](https://open-meteo.com/) (no key needed) |
| **Calendar** | Your Google Calendar's *secret iCal address*: Google Calendar → ⚙ Settings → (your calendar) → Integrate calendar → **Secret address in iCal format**. Treat it like a password. Any other `.ics` URL works too |
| **News topics** | Broad topics (`top`, `world`, `business`, `technology`, `science`, `health`, `sports`, `entertainment`) use Google News sections. Anything else (for example `Formula 1` or `Seattle`) searches the last day's news |
| **Hosts** | Names, personalities and voices. Choose from 30 built-in Gemini voices or your own custom voice (see below) |
| **Show length** | 2–5 minutes |

Settings are saved to `config.json`, which is created from [`config.example.json`](config.example.json) on first run. `config.json`, `.env` and your generated episodes in `shows/` are git-ignored, so your personal info stays on your machine.

### Custom voices

Voices you make in Google AI Studio with **Voice Design** or **Voice Replication** show up under "My AI Studio voices" in the voice dropdown. You can also choose "Paste a voice ID…" and enter a `voice_…` or `voicekey_…` ID. The voice must be in the same AI Studio project as your API key.

Gemini's two-speaker mode only supports built-in voices, so a show that uses a custom voice is recorded one line at a time and then joined. That's a little slower, and the hosts' timing is slightly less natural.

## Have it ready when you wake up

`scripts/generate_today.py` makes today's episode without the web UI. Schedule it to run before you get up, then open the app and press play.

**Windows (Task Scheduler):** in Command Prompt, using your own path:

```bat
schtasks /Create /SC DAILY /ST 06:30 /TN "WAKE FM" /TR "python \"C:\path\to\morning-podcast\scripts\generate_today.py\""
```

**macOS / Linux (cron):** add this with `crontab -e`:

```
30 6 * * * cd /path/to/morning-podcast && GEMINI_API_KEY=your-key python3 scripts/generate_today.py
```

## How it works

```
weather ─┐
calendar ├─> Gemini writes a script ─> Gemini TTS records it ─> shows/YYYY-MM-DD.wav + .json
news ────┘   (JSON: speaker, style, line)
```

If one source fails, such as a broken calendar link or a news timeout, the show still goes on. The hosts just skip that segment (or joke about it).

| File | What it does |
|---|---|
| `app/sources/weather.py` | Open-Meteo forecast |
| `app/sources/calendar.py` | Today's events from an iCal URL, including recurring ones |
| `app/sources/news.py` | Google News RSS headlines per topic |
| `app/script_writer.py` | Has Gemini write the episode as structured JSON |
| `app/tts.py` | Gemini TTS → WAV (`python -m app.tts` runs a quick voice test) |
| `app/shows.py` | Pipeline that saves episodes and tracks progress |
| `app/main.py` | FastAPI server and API |
| `static/` | The web app (plain HTML, CSS and JS, no build step) |

Models are set in `config.json` (`script_model` and `tts_model`). The defaults are `gemini-3.8-flash` and `gemini-3.8-flash-tts`.
