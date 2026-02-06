const express = require("express");
const path = require("path");
const fs = require("fs");
const { execFileSync } = require("child_process");
const multer = require("multer");

const app = express();
const PORT = process.env.PORT || 5000;

const BASE_DIR = __dirname;
const UPLOAD_DIR = path.join(BASE_DIR, "uploads");
const DOWNLOAD_DIR = path.join(BASE_DIR, "downloads");
const OUTPUT_DIR = path.join(BASE_DIR, "output");

const ALLOWED_EXTENSIONS = new Set([
  "mp3",
  "mp4",
  "mov",
  "mkv",
  "wav",
  "aac",
  "flac",
]);

const DEFAULT_MP3_BITRATES = ["128k", "192k", "320k"];
const DEFAULT_MP4_RESOLUTIONS = ["1920:1080", "1280:720", "854:480"];

const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    fs.mkdirSync(UPLOAD_DIR, { recursive: true });
    cb(null, UPLOAD_DIR);
  },
  filename: (req, file, cb) => {
    const extension = path.extname(file.originalname) || "";
    cb(null, `${Date.now()}-${Math.random().toString(16).slice(2)}${extension}`);
  },
});

const upload = multer({
  storage,
  limits: { fileSize: 1024 * 1024 * 1024 },
});

app.set("view engine", "ejs");
app.set("views", path.join(BASE_DIR, "views"));
app.use(express.static(path.join(BASE_DIR, "public")));
app.use(express.urlencoded({ extended: true }));

function ensureExecutable(name) {
  try {
    execFileSync("which", [name]);
    return true;
  } catch (error) {
    return false;
  }
}

function getRuntimeStatus() {
  return {
    ffmpeg: ensureExecutable("ffmpeg"),
    ytDlp: ensureExecutable("yt-dlp"),
  };
}

function parseCsv(value) {
  return value
    .split(",")
    .map((item) => item.trim())
    .filter(Boolean);
}

function runCommand(args) {
  execFileSync(args[0], args.slice(1), { stdio: "inherit" });
}

function buildMp3Commands(inputPath, outputDir, bitrates) {
  return bitrates.map((bitrate) => [
    "ffmpeg",
    "-y",
    "-i",
    inputPath,
    "-vn",
    "-b:a",
    bitrate,
    path.join(outputDir, `${path.parse(inputPath).name}_${bitrate}.mp3`),
  ]);
}

function buildMp4Commands(inputPath, outputDir, resolutions, videoBitrate, audioBitrate) {
  return resolutions.map((resolution) => [
    "ffmpeg",
    "-y",
    "-i",
    inputPath,
    "-vf",
    `scale=${resolution}`,
    "-b:v",
    videoBitrate,
    "-b:a",
    audioBitrate,
    path.join(outputDir, `${path.parse(inputPath).name}_${resolution}.mp4`),
  ]);
}

function downloadFromYoutube(url, targetDir) {
  if (!ensureExecutable("yt-dlp")) {
    throw new Error("yt-dlp is required but was not found on PATH.");
  }
  fs.mkdirSync(targetDir, { recursive: true });
  const outputTemplate = path.join(targetDir, "source.%(ext)s");
  runCommand([
    "yt-dlp",
    "--no-playlist",
    "-f",
    "bv*+ba/b",
    "-o",
    outputTemplate,
    url,
  ]);
  const files = fs
    .readdirSync(targetDir)
    .filter((name) => name.startsWith("source."))
    .map((name) => path.join(targetDir, name));
  if (files.length === 0) {
    throw new Error("YouTube download failed to produce a file.");
  }
  return files[0];
}

app.get("/", (req, res) => {
  res.render("index", {
    mp3Bitrates: DEFAULT_MP3_BITRATES,
    mp4Resolutions: DEFAULT_MP4_RESOLUTIONS,
    runtime: getRuntimeStatus(),
    message: null,
  });
});

app.post("/convert", upload.single("media"), (req, res) => {
  if (!ensureExecutable("ffmpeg")) {
    return res.render("index", {
      mp3Bitrates: DEFAULT_MP3_BITRATES,
      mp4Resolutions: DEFAULT_MP4_RESOLUTIONS,
      runtime: getRuntimeStatus(),
      message: "ffmpeg is required but was not found on PATH.",
    });
  }

  const youtubeUrl = (req.body.youtube_url || "").trim();
  const uploadedFile = req.file;

  if (!youtubeUrl && !uploadedFile) {
    return res.render("index", {
      mp3Bitrates: DEFAULT_MP3_BITRATES,
      mp4Resolutions: DEFAULT_MP4_RESOLUTIONS,
      runtime: getRuntimeStatus(),
      message: "Please upload a media file or provide a YouTube URL.",
    });
  }

  if (uploadedFile) {
    const extension = path.extname(uploadedFile.originalname).slice(1).toLowerCase();
    if (!ALLOWED_EXTENSIONS.has(extension)) {
      return res.render("index", {
        mp3Bitrates: DEFAULT_MP3_BITRATES,
        mp4Resolutions: DEFAULT_MP4_RESOLUTIONS,
        runtime: getRuntimeStatus(),
        message: "Unsupported file type.",
      });
    }
  }

  fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  fs.mkdirSync(DOWNLOAD_DIR, { recursive: true });

  const jobId = `${Date.now()}-${Math.random().toString(16).slice(2)}`;
  let inputPath = uploadedFile ? uploadedFile.path : null;

  try {
    if (youtubeUrl) {
      inputPath = downloadFromYoutube(youtubeUrl, path.join(DOWNLOAD_DIR, jobId));
    }

    const outputDir = path.join(OUTPUT_DIR, jobId);
    fs.mkdirSync(outputDir, { recursive: true });

    const mode = req.body.mode || "mp3";
    if (mode === "mp3") {
      const bitrates = parseCsv(req.body.bitrates || "");
      const commands = buildMp3Commands(
        inputPath,
        outputDir,
        bitrates.length ? bitrates : DEFAULT_MP3_BITRATES
      );
      commands.forEach(runCommand);
    } else {
      const resolutions = parseCsv(req.body.resolutions || "");
      const videoBitrate = req.body.video_bitrate || "2000k";
      const audioBitrate = req.body.audio_bitrate || "128k";
      const commands = buildMp4Commands(
        inputPath,
        outputDir,
        resolutions.length ? resolutions : DEFAULT_MP4_RESOLUTIONS,
        videoBitrate,
        audioBitrate
      );
      commands.forEach(runCommand);
    }

    const outputs = fs.readdirSync(outputDir).filter((name) => fs.lstatSync(path.join(outputDir, name)).isFile());
    return res.render("results", { outputs, jobId });
  } catch (error) {
    return res.render("index", {
      mp3Bitrates: DEFAULT_MP3_BITRATES,
      mp4Resolutions: DEFAULT_MP4_RESOLUTIONS,
      runtime: getRuntimeStatus(),
      message: error.message || "Conversion failed.",
    });
  }
});

app.get("/download/:jobId/:filename", (req, res) => {
  const filePath = path.join(OUTPUT_DIR, req.params.jobId, req.params.filename);
  res.download(filePath);
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
