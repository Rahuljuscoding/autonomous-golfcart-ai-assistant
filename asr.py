import sounddevice as sd
import numpy as np
import queue
import keyboard
import time
from faster_whisper import WhisperModel


SAMPLE_RATE = 16000
CHANNELS = 1
BLOCKSIZE = 1024
MODEL_SIZE = "small"   


model = WhisperModel(
    MODEL_SIZE,
    device="cpu",
    compute_type="int8"
)


_audio_queue = queue.Queue()

def _audio_callback(indata, frames, time_info, status):
    _audio_queue.put(indata.copy())



def listen_once(on_start=None, on_end=None) -> str:
    """
    Push-to-talk ASR with optional start / end callbacks.
    Blocks until user presses and releases SPACE.
    """

    _audio_queue.queue.clear()

    keyboard.wait("space")

    if on_start:
        on_start()

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        blocksize=BLOCKSIZE,
        dtype="float32",
        callback=_audio_callback
    ):
        while keyboard.is_pressed("space"):
            sd.sleep(50)

    if on_end:
        on_end()

    frames = []
    while not _audio_queue.empty():
        frames.append(_audio_queue.get())

    if not frames:
        return ""

    audio = np.concatenate(frames, axis=0).squeeze()

    segments, _ = model.transcribe(
        audio,
        language="en",
        vad_filter=True,
        beam_size=1,
        temperature=0.0
    )

    text = " ".join(
        seg.text.strip()
        for seg in segments
        if seg.text.strip()
    )

    time.sleep(0.25)  # debounce
    return text.strip()
