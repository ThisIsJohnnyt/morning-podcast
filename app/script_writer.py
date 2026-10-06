"""Turn today's data into a two-host radio script with Gemini."""
import json
from datetime import datetime

from google import genai
from google.genai import types

WORDS_PER_MINUTE = 150


def write_script(cfg: dict, data: dict) -> dict:
    a, b = cfg["hosts"][0], cfg["hosts"][1]
    minutes = cfg.get("show_minutes", 3)
    now = datetime.now()
    listener = cfg.get("listener_name") or "the listener"

    prompt = f"""You are the writer for a personal morning radio show made for one person: {listener}.
Today is {now:%A, %B %d, %Y}. Write the script for this morning's episode.

HOSTS
- {a['name']}: {a['persona']}
- {b['name']}: {b['persona']}

TODAY'S DATA (JSON). A value of null or an "error" means that data is unavailable; skip that
segment gracefully or make one quick joke about it. Never invent facts that aren't in the data.
{json.dumps(data, indent=2, ensure_ascii=False)}

SHOW FORMAT
1. A cold open with a station-style intro, greeting {listener} and naming the day.
2. Weather: what it means practically (jacket? umbrella? sunglasses?).
3. The day's calendar in time order, with encouragement or teasing about busy stretches. If there are
   no events, celebrate the open day.
4. Headlines: summarize each in one punchy line, with brief banter on the most interesting ones.
5. A sign-off with a short motivating or funny send-off for the day.

STYLE
- Natural back-and-forth with short turns, interruptions and callbacks. It should sound like real
  people talking, not like reading a list.
- Spell out what should be spoken aloud (for example "ten thirty" rather than "10:30", and "degrees").
- Aim for about {minutes * WORDS_PER_MINUTE} spoken words in total (around {minutes} minutes).
- Only {a['name']} and {b['name']} speak.
- For each line, give a short "style" delivery direction (e.g. "excited, fast-paced",
  "dry and deadpan", "laughing", "whispering conspiratorially").
- Also give the episode a funny title.
"""
    client = genai.Client()
    resp = client.models.generate_content(
        model=cfg.get("script_model", "gemini-3.8-flash"),
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema={
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "lines": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "speaker": {"type": "string", "enum": [a["name"], b["name"]]},
                                "style": {"type": "string"},
                                "line": {"type": "string"},
                            },
                            "required": ["speaker", "style", "line"],
                        },
                    },
                },
                "required": ["title", "lines"],
            },
        ),
    )
    return json.loads(resp.text)
