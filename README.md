# n8n Text-To-Video Generator

![Python](https://img.shields.io/badge/Python-3.x-blue?style=flat-square&logo=python) ![Flask](https://img.shields.io/badge/Flask-Backend-black?style=flat-square&logo=flask) ![n8n](https://img.shields.io/badge/n8n-Workflow-orange?style=flat-square) ![Free Tools Only](https://img.shields.io/badge/Tools-Free%20Only-brightgreen?style=flat-square)

An automated pipeline that converts a structured `.txt` script into a narrated `.mp4` explainer video — no manual editing, no paid APIs, no cloud dependencies. Built for universities, educators, and teams who need to generate short announcement or explainer videos repeatably from plain text input. The workflow is orchestrated through n8n and all video processing runs through a local Python/Flask backend.

---

## Workflow Diagram

![Workflow Diagram](https://github.com/skwasimrazzak/n8n-Text-To-Video-Generator/blob/main/assets/workflow_diagram.png)

---

## Features

- Accepts a plain `.txt` file as input via n8n Webhook — no UI required
- Automatically splits the script into scenes using blank line separators
- Generates a spoken narration track from the full input text using Google TTS
- Renders each scene as a styled slide image with centered, word-wrapped text
- Combines all slides and narration into a single `.mp4` using MoviePy and FFmpeg
- Configurable slide duration, resolution, and font size — no code changes needed for common adjustments
- Built-in error handling for empty input, TTS failures, and video render errors
- Each run produces a uniquely named output file — no overwrites, fully repeatable
- 100% free tooling — no paid APIs, no subscriptions

---

## Tech Stack

| Tool | Role |
|---|---|
| **n8n** | Workflow orchestration — handles the Webhook trigger, file extraction, HTTP routing, and error branching |
| **Flask** | Local Python server that exposes the `/generate` endpoint and coordinates all processing steps |
| **gTTS** | Converts the full input text to a spoken MP3 narration using Google Text-to-Speech |
| **Pillow** | Generates individual slide images — draws background, word-wraps text, and centers it on canvas |
| **MoviePy** | Combines slide images and audio into the final `.mp4` video file |
| **FFmpeg** | System-level video/audio codec engine that MoviePy depends on for rendering |

---

## Setup Instructions

### Prerequisites

- Python 3.x installed on your machine
- n8n running (self-hosted via Docker, npm, or any other method)
- FFmpeg installed and added to your system PATH

**Install FFmpeg (Windows):**
1. Download `ffmpeg-release-essentials.zip` from [https://www.gyan.dev/ffmpeg/builds/](https://www.gyan.dev/ffmpeg/builds/)
2. Extract and rename the folder to `ffmpeg`, place it at `C:\ffmpeg` (or any drive)
3. Add `C:\ffmpeg\bin` to your system Environment Variables under `Path`
4. Verify with:
   ```bash
   ffmpeg -version
   ```

**Install FFmpeg (Mac):**
```bash
brew install ffmpeg
```

**Install FFmpeg (Linux):**
```bash
sudo apt install ffmpeg
```

---

### Clone the Repo

```bash
git clone https://github.com/skwasimrazzak/n8n-Text-To-Video-Generator.git
cd n8n-Text-To-Video-Generator
```

---

### Install Python Dependencies

```bash
pip install -r requirements.txt
```

The `requirements.txt` includes: `flask`, `gtts`, `pillow`, `moviepy==1.0.3`

---

### Create the Output Folder

Inside the project directory, create an `output` folder:

```bash
mkdir output
```

This is where all generated `.mp4` files and temporary assets will be saved.

---

### Configure the Output Path

Open `app.py` and update the `OUTPUT_DIR` constant to match your local path:

```python
OUTPUT_DIR = r"C:\your\path\to\n8n-Text-To-Video-Generator\output"
```

---

### Start the Flask Server

```bash
python app.py
```

Flask will start on port `5000`. Leave this terminal open while running the workflow.

---

### Import the n8n Workflow

1. Open n8n in your browser
2. Create a new workflow
3. Click the menu (top right) and select **Import from File**
4. Import the `workflow.json` file from this repo

---

### Update the HTTP Request Node URL

Inside n8n, open the **HTTP Request** node and update the URL to point to your Flask server:

- If n8n is running via Docker on Windows/Mac:
  ```
  http://host.docker.internal:5000/generate
  ```
- If n8n is running directly on your machine (npm/binary):
  ```
  http://127.0.0.1:5000/generate
  ```

---

### Trigger the Workflow

In n8n, click **Execute Workflow** to activate the Webhook listener, then send your input file using curl:

```bash
curl -X POST "http://localhost:5678/webhook-test/explainer" -F "data=@/path/to/input.txt"
```

Replace `/path/to/input.txt` with your actual file path. On Windows, use the full path with backslashes inside quotes.

---

## How It Works

1. A `.txt` file is sent via HTTP POST to the n8n Webhook endpoint, simulating a frontend file upload
2. The **Extract from File** node reads the binary content and converts it to plain text
3. The **Edit Fields** node attaches the `slide_duration` parameter alongside the extracted text
4. The **HTTP Request** node sends both values as JSON to the Flask `/generate` endpoint
5. Flask validates the input — empty or missing text returns a `400` error immediately
6. The script text is split into scenes on double newlines — each paragraph block becomes one slide
7. gTTS converts the full text to an MP3 narration file
8. Pillow generates one PNG slide image per scene with centered, word-wrapped text on a styled background
9. MoviePy combines all slide images (each held for `slide_duration` seconds) with the narration audio
10. FFmpeg renders the final `.mp4` and saves it to the `output` directory with a unique filename
11. Flask returns a JSON response with `status`, `output_file` path, and `scenes_count`
12. The **IF** node in n8n checks the `status` field — success ends the workflow cleanly, error routes to the **Stop and Error** node

---

## app.py Code Summary

### Configuration Constants
Defined at the top of the file — `OUTPUT_DIR`, `RESOLUTION`, `FONT_SIZE`, `BACKGROUND_COLOR`, `TEXT_COLOR`, and `DEFAULT_SLIDE_DURATION`. All common adjustments can be made here without touching any logic.

### Input Validation (`validate_input`)
Checks whether the received text is empty or whitespace-only. Raises a `ValueError` immediately if so, which the route handler catches and returns as a `400` response.

### Scene Splitting (`split_into_scenes`)
Normalizes line endings (handles both `\r\n` and `\n`) then splits on double newlines. Each resulting block becomes one slide. Raises a `ValueError` if no valid scenes are found after splitting.

### Text-to-Speech (`text_to_speech`)
Passes the full input text to gTTS and saves the output as `narration.mp3` inside a unique temp directory. Wraps the gTTS call in a try/except — any failure raises a `RuntimeError` with a descriptive message.

### Slide Image Generation (`create_slide_image`)
Creates a blank RGB canvas at the configured resolution, loads Arial font (falls back to default if unavailable), word-wraps the scene text to fit within the canvas width, and centers the result both horizontally and vertically. Saves each slide as a numbered PNG.

### Video Rendering (`generate_video`)
Loops through all scenes, generates a slide image for each, wraps each image in an `ImageClip` with the configured duration, concatenates all clips, attaches the narration audio (trimmed if longer than the video), and writes the final `.mp4` at 24fps using H.264 video and AAC audio codecs. Raises a `RuntimeError` on any failure.

### Flask Route (`/generate`)
Accepts a JSON POST body with `text` and `slide_duration`. Orchestrates all functions above in sequence. Three separate except blocks handle `ValueError` (400), `RuntimeError` (500), and unexpected exceptions (500 with full traceback).

---

## Configurable Parameters

| Parameter | Default | Location | How to Change |
|---|---|---|---|
| `slide_duration` | `4` seconds | n8n Edit Fields node | Change the value directly in the Edit Fields node — no code needed |
| `RESOLUTION` | `1280 x 720` | `app.py` constants | Update the tuple `(width, height)` at the top of `app.py` |
| `FONT_SIZE` | `36` | `app.py` constants | Update the integer value at the top of `app.py` |
| `BACKGROUND_COLOR` | `(30, 30, 60)` dark blue | `app.py` constants | Update the RGB tuple at the top of `app.py` |
| `TEXT_COLOR` | `(255, 255, 255)` white | `app.py` constants | Update the RGB tuple at the top of `app.py` |
| `DEFAULT_SLIDE_DURATION` | `4` seconds | `app.py` constants | Fallback value used if n8n doesn't send `slide_duration` |

---

## Contributing

Contributions are welcome. If you have an improvement in mind — better slide layouts, additional TTS options, subtitle overlays, transition effects — open a PR.

**Steps:**

1. Fork the repository
2. Create a new branch for your feature:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. Make your changes and test locally end-to-end
4. Commit with a clear message:
   ```bash
   git commit -m "Add: brief description of what you added"
   ```
5. Push to your fork and open a Pull Request against `main`

**Contributions that are especially welcome:**
- Title slide / bullet point formatting for slides
- Support for additional input formats (`.pdf`, `.docx`)
- Font customization via n8n parameters
- Background image or gradient support in slides
- n8n workflow improvements (e.g. folder watch trigger, email notification on completion)
- Cross-platform setup improvements

Please keep PRs focused — one feature or fix per PR makes review faster.
