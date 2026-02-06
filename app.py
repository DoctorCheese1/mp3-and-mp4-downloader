#!/usr/bin/env python3
"""Web app for converting media files into MP3/MP4 variants."""

from __future__ import annotations

import os
import shutil
import subprocess
import uuid
from pathlib import Path

from flask import Flask, flash, redirect, render_template, request, send_from_directory, url_for
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
ALLOWED_EXTENSIONS = {"mp3", "mp4", "mov", "mkv", "wav", "aac", "flac"}


app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 1024 * 1024 * 1024  # 1GB
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret")


def ensure_ffmpeg() -> None:
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required but was not found on PATH.")


def parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


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


@app.route("/", methods=["GET", "POST"])
def index():
    outputs = None
    job_id = None

    if request.method == "POST":
        uploaded_file = request.files.get("file")
        mode = request.form.get("mode", "mp3")

        if uploaded_file is None or uploaded_file.filename == "":
            flash("Please upload a media file.")
            return redirect(url_for("index"))

        if not allowed_file(uploaded_file.filename):
            flash("Unsupported file type. Please upload a valid media file.")
            return redirect(url_for("index"))

        try:
            ensure_ffmpeg()
        except RuntimeError as exc:
            flash(str(exc))
            return redirect(url_for("index"))

        job_id = uuid.uuid4().hex
        upload_path = UPLOAD_DIR / job_id
        output_path = OUTPUT_DIR / job_id
        upload_path.mkdir(parents=True, exist_ok=True)
        output_path.mkdir(parents=True, exist_ok=True)

        safe_name = secure_filename(uploaded_file.filename)
        input_path = upload_path / safe_name
        uploaded_file.save(input_path)

        if mode == "mp3":
            bitrates = parse_csv(request.form.get("bitrates", "128k,192k,320k"))
            commands = build_mp3_commands(input_path, output_path, bitrates)
        else:
            resolutions = parse_csv(
                request.form.get("resolutions", "1920:1080,1280:720,854:480")
            )
            video_bitrate = request.form.get("video_bitrate", "2000k")
            audio_bitrate = request.form.get("audio_bitrate", "128k")
            commands = build_mp4_commands(
                input_path, output_path, resolutions, video_bitrate, audio_bitrate
            )

        try:
            run_commands(commands)
        except subprocess.CalledProcessError:
            flash("Conversion failed. Please check your input and try again.")
            return redirect(url_for("index"))

        outputs = sorted(p.name for p in output_path.iterdir() if p.is_file())

    return render_template("index.html", outputs=outputs, job_id=job_id)


@app.route("/download/<job_id>/<filename>")
def download(job_id: str, filename: str):
    safe_filename = secure_filename(filename)
    directory = OUTPUT_DIR / job_id
    return send_from_directory(directory, safe_filename, as_attachment=True)


if __name__ == "__main__":
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=False)
