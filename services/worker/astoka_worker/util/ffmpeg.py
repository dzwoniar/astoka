"""FFmpeg/FFprobe helpers (subprocess wrappers — no python ffmpeg lib needed)."""

import json
import subprocess
from pathlib import Path
from typing import Any


def ffprobe_metadata(input_path: str) -> dict[str, Any]:
    """Run ffprobe and return parsed JSON metadata."""
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-print_format",
        "json",
        "-show_format",
        "-show_streams",
        input_path,
    ]
    out = subprocess.check_output(cmd, text=True, timeout=120)
    return json.loads(out)


def extract_basic_metadata(probe: dict[str, Any]) -> dict[str, Any]:
    """Pull canonical fields from ffprobe output for SourceMaterial columns."""
    fmt = probe.get("format", {})
    streams = probe.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_streams = [s for s in streams if s.get("codec_type") == "audio"]

    duration = float(fmt.get("duration", 0)) if fmt.get("duration") else None
    bytes_size = int(fmt.get("size", 0)) if fmt.get("size") else None

    width = video.get("width") if video else None
    height = video.get("height") if video else None
    fps: float | None = None
    if video and video.get("r_frame_rate"):
        try:
            num, den = video["r_frame_rate"].split("/")
            fps = float(num) / float(den) if float(den) > 0 else None
        except (ValueError, ZeroDivisionError):
            fps = None

    detected_language = None
    for s in audio_streams:
        lang = (s.get("tags") or {}).get("language")
        if lang and lang != "und":
            detected_language = lang
            break

    return {
        "duration_s": duration,
        "width": width,
        "height": height,
        "fps": fps,
        "bytes_size": bytes_size,
        "detected_language": detected_language,
        "audio_streams": len(audio_streams),
    }


def make_proxy_preview(input_path: str, output_path: str) -> None:
    """Encode a 480p H.264 proxy for fast UI playback.

    Uses libx264 (CPU). NVENC could be substituted later if GPU is available; for now
    we trade speed for portability — proxy is a small file, around realtime on modest CPU.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        input_path,
        "-vf",
        "scale=-2:480",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        output_path,
    ]
    subprocess.run(cmd, check=True, capture_output=True, timeout=3600)
