#!/usr/bin/env python3
"""Flask web app for multi-bitrate MP3 and multi-resolution MP4 conversions."""

from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
DOWNLOAD_DIR = BASE_DIR / "downloads"
OUTPUT_DIR = BASE_DIR / "output"
ALLOWED_EXTENSIONS = {"mp3", "mp4", "mov", "mkv", "wav", "aac", "flac"}

DEFAULT_MP3_BITRATES = ["128k", "192k", "320k"]
DEFAULT_MP4_RESOLUTIONS = ["1920:1080", "1280:720", "854:480"]

app = Flask(__name__)
app.config["SECRET_KEY"] = "local-dev-secret"


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required but was not found on PATH.")


def ensure_ytdlp() -> None:
    if shutil.which("yt-dlp") is None:
        raise RuntimeError("yt-dlp is required but was not found on PATH.")


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def build_mp3_commands(
    input_path: Path, output_dir: Path, bitrates: list[str]
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


def download_from_youtube(url: str, target_dir: Path) -> Path:
    ensure_ytdlp()
    target_dir.mkdir(parents=True, exist_ok=True)
    output_template = target_dir / "source.%(ext)s"
    subprocess.run(
        [
            "yt-dlp",
            "--no-playlist",
            "-f",
            "bv*+ba/b",
            "-o",
            str(output_template),
            url,
        ],
        check=True,
    )
    downloaded_files = sorted(target_dir.glob("source.*"))
    if not downloaded_files:
        raise RuntimeError("YouTube download failed to produce a file.")
    return downloaded_files[0]


@app.route("/", methods=["GET"])
def index() -> str:
    return render_template(
        "index.html",
        mp3_bitrates=DEFAULT_MP3_BITRATES,
        mp4_resolutions=DEFAULT_MP4_RESOLUTIONS,
    )


@app.route("/convert", methods=["POST"])
def convert() -> str:
    ensure_ffmpeg()
    uploaded = request.files.get("media")
    youtube_url = request.form.get("youtube_url", "").strip()
    if (not uploaded or uploaded.filename == "") and not youtube_url:
        flash("Please upload a media file or provide a YouTube URL.")
        return redirect(url_for("index"))

    if uploaded and uploaded.filename != "" and not allowed_file(uploaded.filename):
        flash("Unsupported file type.")
        return redirect(url_for("index"))

    mode = request.form.get("mode", "mp3")

    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    file_id = uuid.uuid4().hex
    if youtube_url:
        download_dir = DOWNLOAD_DIR / file_id
        try:
            input_path = download_from_youtube(youtube_url, download_dir)
        except (subprocess.CalledProcessError, RuntimeError) as exc:
            flash(str(exc))
            return redirect(url_for("index"))
    else:
        extension = uploaded.filename.rsplit(".", 1)[1].lower()
        input_path = UPLOAD_DIR / f"{file_id}.{extension}"
        uploaded.save(input_path)

    output_dir = OUTPUT_DIR / file_id
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        if mode == "mp3":
            bitrates = parse_csv(request.form.get("bitrates", ""))
            if not bitrates:
                bitrates = DEFAULT_MP3_BITRATES
            commands = build_mp3_commands(input_path, output_dir, bitrates)
        else:
            resolutions = parse_csv(request.form.get("resolutions", ""))
            if not resolutions:
                resolutions = DEFAULT_MP4_RESOLUTIONS
            video_bitrate = request.form.get("video_bitrate", "2000k")
            audio_bitrate = request.form.get("audio_bitrate", "128k")
            commands = build_mp4_commands(
                input_path, output_dir, resolutions, video_bitrate, audio_bitrate
            )

        run_commands(commands)
    except subprocess.CalledProcessError:
        flash("Conversion failed. Please check your inputs and try again.")
        return redirect(url_for("index"))

    outputs = sorted(path.name for path in output_dir.iterdir() if path.is_file())
    return render_template(
        "results.html",
        file_id=file_id,
        outputs=outputs,
    )


@app.route("/download/<file_id>/<filename>")
def download(file_id: str, filename: str):
    directory = OUTPUT_DIR / file_id
    return send_from_directory(directory, filename, as_attachment=True)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
