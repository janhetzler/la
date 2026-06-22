"""
Audio recorder for meetings.

Captures the microphone (your voice) and BlackHole (the others) in parallel,
mixes both into a mono 16 kHz WAV file ready for Whisper.

Usage (CLI):
    python recorder.py start [--project P] [--topic T] [--name N]

Stop signals:
    - SIGINT  (Ctrl+C)        — interactive use
    - SIGTERM (kill <pid>)    — programmatic use (e.g., from the meeting agent)

When stopped, the recorder automatically triggers process.py on the WAV file
to generate the transcript + structured summary + Qdrant indexing.
"""
import argparse
import queue
import signal
import subprocess
import sys
import threading
from datetime import datetime
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf


# ===== Configuration =====
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
RECORDINGS_DIR = PROJECT_ROOT / "data" / "recordings"
RECORDINGS_DIR.mkdir(parents=True, exist_ok=True)

# Device indices (verify with sd.query_devices())
MIC_INDEX = 2          # MacBook Air built-in microphone
BLACKHOLE_INDEX = 1    # BlackHole 2ch

# Audio settings
SAMPLE_RATE = 16000    # what Whisper expects
BLOCK_SIZE = 1600      # 100 ms per chunk
CHANNELS = 1           # mono for Whisper

# Shared queue for audio chunks
audio_queue: queue.Queue = queue.Queue()
stop_event = threading.Event()


def mic_callback(indata, frames, time, status):
    """Microphone callback: pushes samples into the queue."""
    if status:
        print(f"⚠️  Mic status: {status}", file=sys.stderr)
    audio_queue.put(("mic", indata.copy().flatten()))


def blackhole_callback(indata, frames, time, status):
    """BlackHole callback: averages the 2 channels into mono."""
    if status:
        print(f"⚠️  BlackHole status: {status}", file=sys.stderr)
    mono = indata.mean(axis=1) if indata.ndim > 1 else indata.flatten()
    audio_queue.put(("blackhole", mono))


def mixer_thread(output_path: Path):
    """Mix incoming chunks and write them to the WAV file."""
    mic_buf = np.zeros(0, dtype=np.float32)
    bh_buf = np.zeros(0, dtype=np.float32)

    with sf.SoundFile(
        str(output_path),
        mode="w",
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        subtype="PCM_16",
    ) as out:
        while not stop_event.is_set() or not audio_queue.empty():
            try:
                source, chunk = audio_queue.get(timeout=0.5)
            except queue.Empty:
                continue

            if source == "mic":
                mic_buf = np.concatenate([mic_buf, chunk])
            else:
                bh_buf = np.concatenate([bh_buf, chunk])

            # When both buffers have data, mix and write
            n = min(len(mic_buf), len(bh_buf))
            if n > 0:
                mixed = (mic_buf[:n] + bh_buf[:n]) * 0.5
                mixed = np.clip(mixed, -1.0, 1.0)
                out.write(mixed.astype(np.float32))
                mic_buf = mic_buf[n:]
                bh_buf = bh_buf[n:]

        # Flush remaining buffers
        if len(mic_buf) > 0:
            out.write(np.clip(mic_buf, -1.0, 1.0).astype(np.float32))
        if len(bh_buf) > 0:
            out.write(np.clip(bh_buf, -1.0, 1.0).astype(np.float32))


def install_signal_handlers():
    """Install handlers for SIGINT (Ctrl+C) and SIGTERM (programmatic stop)."""
    def stop_handler(sig, frame):
        sig_name = "SIGINT" if sig == signal.SIGINT else "SIGTERM"
        print(f"\n⏹️  Received {sig_name}, stopping...", flush=True)
        stop_event.set()

    signal.signal(signal.SIGINT, stop_handler)
    signal.signal(signal.SIGTERM, stop_handler)


def trigger_post_processing(audio_path: Path, project: str, topic: str | None):
    """Run process.py on the recorded WAV (transcript + summary + indexing)."""
    print(f"\n🚀 Launching post-processing on {audio_path.name}...")
    process_script = Path(__file__).parent / "process.py"

    cmd = [sys.executable, str(process_script), str(audio_path), project]
    if topic:
        cmd.append(topic)

    try:
        # Inherit stdout/stderr so the user sees progress
        result = subprocess.run(cmd, check=False)
        if result.returncode == 0:
            print(f"✅ Post-processing finished successfully.")
        else:
            print(f"⚠️  Post-processing exited with code {result.returncode}")
    except Exception as e:
        print(f"❌ Could not launch post-processing: {e}")


def record(
    name: str | None = None,
    project: str = "default",
    topic: str | None = None,
):
    """Run the capture loop until SIGINT/SIGTERM, then trigger post-processing."""
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    session_name = f"{timestamp}_{name}" if name else timestamp
    output_path = RECORDINGS_DIR / f"{session_name}.wav"

    print(f"🎙️  Recording starts: {output_path.name}")
    print(f"   Project: {project}")
    print(f"   Topic:   {topic or '(none)'}")
    print(f"   Mic:        {sd.query_devices(MIC_INDEX)['name']}")
    print(f"   BlackHole:  {sd.query_devices(BLACKHOLE_INDEX)['name']}")
    print(f"   → Stop with Ctrl+C (or kill <pid> from another agent)\n", flush=True)

    # Mixer thread
    mixer = threading.Thread(target=mixer_thread, args=(output_path,))
    mixer.start()

    # Audio streams
    mic_stream = sd.InputStream(
        device=MIC_INDEX,
        channels=1,
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        callback=mic_callback,
    )
    bh_stream = sd.InputStream(
        device=BLACKHOLE_INDEX,
        channels=2,
        samplerate=SAMPLE_RATE,
        blocksize=BLOCK_SIZE,
        callback=blackhole_callback,
    )

    install_signal_handlers()

    mic_stream.start()
    bh_stream.start()

    try:
        elapsed = 0
        while not stop_event.is_set():
            sd.sleep(1000)
            elapsed += 1
            if elapsed % 60 == 0:
                mins = elapsed // 60
                print(f"   ... {mins} min elapsed", flush=True)
    finally:
        mic_stream.stop()
        bh_stream.stop()
        mic_stream.close()
        bh_stream.close()
        mixer.join()

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"\n✅ Recording complete: {output_path}")
    print(f"   Size: {size_mb:.1f} MB")

    # Auto-trigger post-processing
    trigger_post_processing(output_path, project, topic)

    return output_path


def main():
    parser = argparse.ArgumentParser(description="Meeting audio recorder")
    parser.add_argument("command", choices=["start"], help="Action to perform")
    parser.add_argument("--name", default=None, help="Optional session name")
    parser.add_argument("--project", default="default", help="Project tag")
    parser.add_argument("--topic", default=None, help="Meeting topic")
    args = parser.parse_args()

    if args.command == "start":
        record(name=args.name, project=args.project, topic=args.topic)


if __name__ == "__main__":
    main()