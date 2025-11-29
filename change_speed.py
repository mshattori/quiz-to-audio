#!/usr/bin/env uv run
"""Command line tool to change playback speed of an audio file.

The script always preserves the original pitch by using FFmpeg's `atempo`
filter chain and optionally applies an extra pitch shift in semitones so you
can fine-tune the voice after speeding up or slowing down the playback.
"""

from __future__ import annotations

import argparse
import math
import shutil
import subprocess
from pathlib import Path
from typing import Iterable, List

from pydub.utils import mediainfo


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Change the playback speed of an audio file with optional pitch control.",
    )
    parser.add_argument("input", type=Path, help="Input audio file (any format FFmpeg supports)")
    parser.add_argument(
        "--speed",
        type=float,
        required=True,
        help="Playback speed multiplier (e.g. 1.5 for 1.5x, 0.7 for slower)",
    )
    parser.add_argument(
        "--output-directory",
        type=Path,
        required=True,
        help="Directory to place the processed file. The filename matches the input filename.",
    )
    parser.add_argument(
        "--pitch-shift",
        type=float,
        default=0.0,
        help="Apply an additional pitch shift in semitones after the speed change.",
    )
    parser.add_argument(
        "--ffmpeg",
        default="ffmpeg",
        help="FFmpeg binary to use (defaults to `ffmpeg` on PATH).",
    )
    return parser.parse_args()


def ensure_ffmpeg(binary: str) -> None:
    if shutil.which(binary) is None:
        raise SystemExit(
            f"FFmpeg binary '{binary}' was not found. Install FFmpeg or pass --ffmpeg with the correct path."
        )


def read_sample_rate(path: Path) -> int:
    info = mediainfo(str(path))
    if "sample_rate" not in info:
        raise SystemExit(f"Could not determine sample rate for {path} via ffprobe.")
    return int(info["sample_rate"])


def _split_tempo_factor(value: float) -> List[float]:
    if value <= 0:
        raise ValueError("Tempo factor must be greater than zero.")
    factors: List[float] = []
    remaining = value
    # Keep factors inside the allowed FFmpeg atempo range [0.5, 2.0].
    while remaining > 2.0:
        factors.append(2.0)
        remaining /= 2.0
    while remaining < 0.5:
        factors.append(0.5)
        remaining /= 0.5
    if not math.isclose(remaining, 1.0, rel_tol=1e-9):
        factors.append(remaining)
    return factors


def build_speed_filters(speed: float) -> List[str]:
    if speed <= 0:
        raise SystemExit("--speed must be greater than 0.")
    return [f"atempo={f:.8f}" for f in _split_tempo_factor(speed)] or ["atempo=1.0"]


def build_pitch_filters(pitch_shift: float, sample_rate: int) -> List[str]:
    if math.isclose(pitch_shift, 0.0, abs_tol=1e-9):
        return []
    pitch_factor = 2 ** (pitch_shift / 12.0)
    filters: List[str] = [f"asetrate={sample_rate * pitch_factor:.6f}", f"aresample={sample_rate}"]
    tempo_comp = 1.0 / pitch_factor
    filters.extend(f"atempo={f:.8f}" for f in _split_tempo_factor(tempo_comp))
    return filters


def run_ffmpeg(ffmpeg_binary: str, input_path: Path, output_path: Path, filters: Iterable[str]) -> None:
    filter_arg = ",".join(filters)
    cmd = [
        ffmpeg_binary,
        "-hide_banner",
        "-loglevel",
        "info",
        "-y",
        "-i",
        str(input_path),
        "-filter:a",
        filter_arg,
        str(output_path),
    ]
    subprocess.run(cmd, check=True)


def main() -> None:
    args = parse_args()
    ensure_ffmpeg(args.ffmpeg)

    input_path = args.input
    if not input_path.exists():
        raise SystemExit(f"Input file {input_path} does not exist.")

    sample_rate = read_sample_rate(input_path)
    output_dir = args.output_directory
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / input_path.name

    filters: List[str] = []
    filters.extend(build_speed_filters(args.speed))
    filters.extend(build_pitch_filters(args.pitch_shift, sample_rate))
    run_ffmpeg(args.ffmpeg, input_path, output_path, filters)
    print(
        f"Created {output_path} (speed={args.speed}, preserve_pitch=True, pitch_shift={args.pitch_shift})"
    )


if __name__ == "__main__":
    main()
