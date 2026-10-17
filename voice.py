"""Voice input (Groq Whisper) aur voice output (gTTS)."""

import io
import os
import re

STT_MODEL = os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo")
MAX_SPOKEN_CHARS = 1200


def transcribe(groq_client, audio_bytes: bytes) -> str:
    """Awaaz ko text mein badalta hai. Zubaan khud detect hoti hai."""
    result = groq_client.audio.transcriptions.create(
        file=("voice.wav", audio_bytes),
        model=STT_MODEL,
    )
    return (result.text or "").strip()


def _clean_for_speech(text: str) -> str:
    text = re.sub(r"```.*?```", " code block ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)  # markdown links
    text = re.sub(r"[*_#>|~-]{1,}", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:MAX_SPOKEN_CHARS]


def speak(text: str, lang: str = "en") -> bytes:
    """Text ko MP3 audio bytes mein badalta hai (internet chahiye)."""
    from gtts import gTTS

    clean = _clean_for_speech(text)
    if not clean:
        raise ValueError("bolne ke liye text nahi hai")
    buffer = io.BytesIO()
    gTTS(text=clean, lang=lang).write_to_fp(buffer)
    return buffer.getvalue()