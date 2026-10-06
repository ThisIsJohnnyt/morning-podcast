"""Multi-speaker Gemini TTS -> WAV."""
import wave
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from google import genai
from google.genai import types

SAMPLE_RATE = 24000
MAX_CHARS_PER_CALL = 3000
TURN_GAP = bytes(2 * int(SAMPLE_RATE * 0.25))  # pause between separately-recorded turns
PARALLEL_TURNS = 4

VOICES = [
    "Zephyr", "Puck", "Charon", "Kore", "Fenrir", "Leda", "Orus", "Aoede",
    "Callirrhoe", "Autonoe", "Enceladus", "Iapetus", "Umbriel", "Algieba",
    "Despina", "Erinome", "Algenib", "Rasalgethi", "Laomedeia", "Achernar",
    "Alnilam", "Schedar", "Gacrux", "Pulcherrima", "Achird", "Zubenelgenubi",
    "Vindemiatrix", "Sadachbia", "Sadaltager", "Sulafat",
]


def is_custom(voice: str) -> bool:
    """Voice Design / Voice Replication IDs from AI Studio, as opposed to prebuilt names."""
    return voice.startswith(("voice_", "voicekey_"))


def list_custom_voices() -> list[dict]:
    """Custom voices (designed or replicated) stored in the API key's project."""
    resp = genai.Client().voices.list(type_=["prompted", "replicated"])
    return [
        {"id": v.id, "name": v.display_name or v.id, "type": v.type, "description": v.description}
        for v in resp.voices or []
    ]


def _chunks(lines: list[dict]) -> list[list[dict]]:
    """Split the script at speaker turns so each TTS call stays a manageable size."""
    chunks, current, size = [], [], 0
    for line in lines:
        n = len(line["line"]) + len(line["speaker"]) + 2
        if current and size + n > MAX_CHARS_PER_CALL:
            chunks.append(current)
            current, size = [], 0
        current.append(line)
        size += n
    if current:
        chunks.append(current)
    return chunks


def _speak_chunk(client, model: str, hosts: list[dict], lines: list[dict]) -> bytes:
    # Newer TTS models take one text part per line, tagged with its speaker and delivery style.
    parts = [
        types.Part(
            text=l["line"],
            speech_metadata=types.SpeechMetadata(speaker=l["speaker"], style=l.get("style") or None),
        )
        for l in lines
    ]
    resp = client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=parts)],
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(
                multi_speaker_voice_config=types.MultiSpeakerVoiceConfig(
                    speaker_voice_configs=[
                        types.SpeakerVoiceConfig(
                            speaker=h["name"],
                            voice_config=types.VoiceConfig(
                                prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=h["voice"])
                            ),
                        )
                        for h in hosts[:2]
                    ]
                )
            ),
        ),
    )
    return b"".join(
        p.inline_data.data for p in resp.candidates[0].content.parts if p.inline_data
    )


def _speak_turn(client, model: str, voice: str, line: dict) -> bytes:
    # Custom voices can't be used in multi-speaker requests, so each turn is its own call.
    try:
        resp = _generate_turn(client, model, voice, line)
    except genai.errors.ClientError as e:
        if e.code == 404 and is_custom(voice):
            raise RuntimeError(
                f"Custom voice '{voice}' wasn't found. Check the ID, and make sure the voice was "
                "created in the same Google AI Studio project as your GEMINI_API_KEY."
            ) from e
        raise
    return b"".join(p.inline_data.data for p in resp.candidates[0].content.parts if p.inline_data)


def _generate_turn(client, model: str, voice: str, line: dict):
    return client.models.generate_content(
        model=model,
        contents=[types.Content(role="user", parts=[
            types.Part(text=line["line"], speech_metadata=types.SpeechMetadata(style=line.get("style") or None))
        ])],
        config=types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=types.SpeechConfig(voice_config=_voice_config(voice)),
        ),
    )


def _voice_config(voice: str) -> types.VoiceConfig:
    if is_custom(voice):
        return types.VoiceConfig(voice=voice)
    return types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=voice))


def synthesize(lines: list[dict], hosts: list[dict], model: str, out_path: Path) -> Path:
    client = genai.Client()
    if any(is_custom(h["voice"]) for h in hosts[:2]):
        voices = {h["name"]: h["voice"] for h in hosts[:2]}
        with ThreadPoolExecutor(PARALLEL_TURNS) as pool:
            turns = list(pool.map(lambda l: _speak_turn(client, model, voices[l["speaker"]], l), lines))
        pcm = TURN_GAP.join(turns)
    else:
        pcm = b"".join(_speak_chunk(client, model, hosts, chunk) for chunk in _chunks(lines))
    with wave.open(str(out_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm)
    return out_path


if __name__ == "__main__":
    from app.config import SHOWS_DIR, load_config

    cfg = load_config()
    a, b = cfg["hosts"][0]["name"], cfg["hosts"][1]["name"]
    test = [
        {"speaker": a, "style": "excited, booming radio voice", "line": "Gooood morning! This is a test of the emergency banter system!"},
        {"speaker": b, "style": "flat, deadpan, unimpressed", "line": "It's working. Unfortunately."},
    ]
    out = synthesize(test, cfg["hosts"], cfg["tts_model"], SHOWS_DIR / "_tts_test.wav")
    print("wrote", out, out.stat().st_size, "bytes")
    print("custom voices in this project:", list_custom_voices())
