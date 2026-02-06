# MP3 and MP4 Converter

A simple Python project for converting media files into multiple MP3 bitrates or MP4 resolutions using `ffmpeg`. It includes both a CLI tool and a web interface.

## Requirements

- Python 3.10+
- `ffmpeg` installed and available on your `PATH`

## Web app

### Run without installing Python (Docker)

```bash
docker compose up --build
```

Open `http://localhost:5000` in your browser.

### Run with Python

Install dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Ensure these executables are available on your `PATH`:

- `ffmpeg` for media conversion
- `yt-dlp` for YouTube downloads

If you see an error about FFmpeg missing, install it with your package manager (for example: `brew install ffmpeg` on macOS, `sudo apt-get install ffmpeg` on Debian/Ubuntu, or `choco install ffmpeg` on Windows with Chocolatey).

Run the server:

```bash
python app.py
```

Open `http://localhost:5000` and upload a media file. Choose MP3 or MP4 options and download the generated variants.

## CLI usage

### MP3 variants

```bash
python converter.py path/to/input.mp4 mp3 --bitrates 128k,192k,320k
```

### MP4 variants

```bash
python converter.py path/to/input.mp4 mp4 --resolutions 1920:1080,1280:720,854:480 --video-bitrate 2000k --audio-bitrate 128k
```

### Output directory

By default, output files are placed in an `output/` folder. Override with `--output-dir`:

```bash
python converter.py path/to/input.mp4 mp3 --output-dir exports
```

## Notes

- MP3 output names: `<input>_<bitrate>.mp3`
- MP4 output names: `<input>_<resolution>.mp4`
- Resolutions use `WIDTH:HEIGHT` format for ffmpeg scaling.
