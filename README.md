# MP3 and MP4 Converter

A simple Python project for converting media files into multiple MP3 bitrates or MP4 resolutions using `ffmpeg`. It includes both a CLI and a web interface.

## Requirements

- Python 3.10+
- `ffmpeg` installed and available on your `PATH`

## Web app

```bash
pip install -r requirements.txt
python app.py
```

Open `http://localhost:5000` in your browser, upload a media file, and choose MP3 or MP4 conversion settings.

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
