#!/usr/bin/env python3
"""Simple MP3/MP4 converter with multi-bitrate and resolution support."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise SystemExit(
            "ffmpeg is required but was not found on PATH. Please install ffmpeg."
        )


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_mp3_commands(
    input_path: Path,
    output_dir: Path,
    bitrates: list[str],
) -> list[list[str]]:
    commands: list[list[str]] = []
    for bitrate in bitrates:
        output_path = output_dir / f"{input_path.stem}_{bitrate}.mp3"
        commands.append(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-vn",
                "-b:a",
                bitrate,
                str(output_path),
            ]
        )
    return commands


def build_mp4_commands(
    input_path: Path,
    output_dir: Path,
    resolutions: list[str],
    video_bitrate: str,
    audio_bitrate: str,
) -> list[list[str]]:
    commands: list[list[str]] = []
    for resolution in resolutions:
        output_path = output_dir / f"{input_path.stem}_{resolution}.mp4"
        commands.append(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(input_path),
                "-vf",
                f"scale={resolution}",
                "-b:v",
                video_bitrate,
                "-b:a",
                audio_bitrate,
                str(output_path),
            ]
        )
    return commands


def run_commands(commands: list[list[str]]) -> None:
    for command in commands:
        subprocess.run(command, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Convert media into MP3 or MP4 variants using ffmpeg."
    )
    parser.add_argument("input", type=Path, help="Path to the source media file.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory where converted files will be stored.",
    )

    subparsers = parser.add_subparsers(dest="mode", required=True)

    mp3_parser = subparsers.add_parser("mp3", help="Create MP3 variants.")
    mp3_parser.add_argument(
        "--bitrates",
        type=parse_csv,
        default=["128k", "192k", "320k"],
        help="Comma-separated list of MP3 bitrates (e.g. 128k,192k,320k).",
    )

    mp4_parser = subparsers.add_parser("mp4", help="Create MP4 variants.")
    mp4_parser.add_argument(
        "--resolutions",
        type=parse_csv,
        default=["1920:1080", "1280:720", "854:480"],
        help="Comma-separated list of resolutions in WIDTH:HEIGHT format.",
    )
    mp4_parser.add_argument(
        "--video-bitrate",
        default="2000k",
        help="Target video bitrate (e.g. 2500k).",
    )
    mp4_parser.add_argument(
        "--audio-bitrate",
        default="128k",
        help="Target audio bitrate (e.g. 128k).",
    )

    args = parser.parse_args()

    ensure_ffmpeg()

    args.output_dir.mkdir(parents=True, exist_ok=True)

    if args.mode == "mp3":
        commands = build_mp3_commands(args.input, args.output_dir, args.bitrates)
    else:
        commands = build_mp4_commands(
            args.input,
            args.output_dir,
            args.resolutions,
            args.video_bitrate,
            args.audio_bitrate,
        )

    run_commands(commands)


if __name__ == "__main__":
    main()
