import pyttsx3
import threading
import re


def _normalize_for_tts(text: str) -> str:
    """
    Clean up formatting so TTS
    pronounces them naturally.
    """
    if not text:
        return text

    # Numeric cleanup
    # Handles: 3.0, 3. 0, 3 .0, 3 . 0  -> 3
    text = re.sub(
        r"\b(\d+)\s*\.\s*0\b",
        r"\1",
        text
    )

    # Compound units

    # 3m/s or 3 m/s -> 3 meters per second
    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*m\s*/\s*s\b",
        r"\1 meters per second",
        text
    )

    # 15km/h or 15 km/h -> 15 kilometers per hour
    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*km\s*/\s*h\b",
        r"\1 kilometers per hour",
        text
    )

    # Simple units 

    # 175m or 175 m -> 175 meters
    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*m\b",
        r"\1 meters",
        text
    )

    # 2km or 2 km -> 2 kilometers
    text = re.sub(
        r"\b(\d+(?:\.\d+)?)\s*km\b",
        r"\1 kilometers",
        text
    )

    return text



def _speak_blocking(text: str):
    try:
        engine = pyttsx3.init()

        voices = engine.getProperty("voices")
        if isinstance(voices, list):
            for v in voices:
                if "zira" in getattr(v, "name", "").lower():
                    engine.setProperty("voice", v.id)
                    break

        engine.setProperty("rate", 174)  
        engine.setProperty("volume", 1.0)

        engine.say(text)
        engine.runAndWait()
        engine.stop()

    except Exception as e:
        print("[TTS ERROR]", e)


def speak(text: str):
    """
    Each utterance runs in its own thread.
    """
    if not text or not text.strip():
        return

    text = _normalize_for_tts(text)

    threading.Thread(
        target=_speak_blocking,
        args=(text,),
        daemon=True
    ).start()
