# AI Coding Assistant — Screen Understanding

A desktop app that watches your screen (or accepts screenshots/videos/Word
docs/code files), extracts code and errors, and explains what's wrong —
like a teacher — using a multi-agent pipeline powered by Gemini.

## Architecture

```
   Screen / File Input
   (live region capture, screenshot, video, .docx, code file)
            |
            v
      Screen Agent            <- capture/screen_capture.py, preprocess.py,
                                  ocr_engine.py (OpenCV + Tesseract OCR)
            |
            v
  Code Extraction Agent       <- agents/code_agent.py
            |
            v
   Error Analysis Agent       <- agents/error_agent.py
            |
            v
     Research Agent           <- agents/research_agent.py
     (only when an unfamiliar library/import error is detected)
            |
            v
     Solution Agent           <- agents/solution_agent.py
     (generates the fix AND explains *why* it's needed)
            |
            v
     Testing Agent            <- agents/testing_agent.py + sandbox_runner.py
     (runs the fix in a restricted subprocess — ONLY after you confirm)
            |
            v
     Response Agent           <- agents/response_agent.py
     (final teacher-style write-up shown in the app)
```

`agents/manager.py` is the ADK-style orchestrator that runs this pipeline
end-to-end for every capture, whether it came from live monitoring or an
uploaded file.

## Features

- **Live screen monitoring**: select a screen region once; the app watches
  it in the background while you code and automatically analyzes new
  errors/code as they appear (no manual copy-paste).
- **Manual capture**: grab the selected region on demand.
- **Multi-format upload**: analyze a screenshot, a screen-recording video
  (frames are sampled and de-duplicated automatically), a Word document, or
  a raw code/log file.
- **Chat tab**: ask follow-up questions about any analysis, or general
  programming questions.
- **History tab**: browse and delete past analyses (SQLite-backed).
- **Sandboxed "Test Fix"**: runs the AI-suggested fix in a restricted
  subprocess, but only after you explicitly confirm — see the security note
  below.

## Setup

1. **Install Python 3.10+** if you don't have it.
2. **Install Tesseract OCR** (the OCR engine, separate from the Python package):
   - Ubuntu/Debian: `sudo apt-get install tesseract-ocr`
   - macOS: `brew install tesseract`
   - Windows: https://github.com/UB-Mannheim/tesseract/wiki (note the
     install path — you'll need it below if it's not on your PATH)
3. **Install Python dependencies**:
   ```
   pip install -r requirements.txt
   ```
4. **Get a Gemini API key** (free tier available): https://aistudio.google.com/apikey
5. **Configure**:
   ```
   cp .env.example .env
   ```
   Then edit `.env` and paste in your `GEMINI_API_KEY`. On Windows, also
   set `TESSERACT_CMD` to the full path of `tesseract.exe` if it's not on
   your PATH.
6. **Run it**:
   ```
   python main.py
   ```

## Using it

1. Go to the **Live Analysis** tab, click **Select Region**, and drag a box
   around your editor/terminal (or just your whole screen).
2. Click **Start Live Monitor** — it'll watch that region every ~2.5s
   (configurable in `.env`) and automatically run the full agent pipeline
   whenever new code/error text appears.
3. Or click **Capture Now** for a one-off snapshot, then **Analyze Selected Text**.
4. Or click **Upload File** to analyze a screenshot, `.mp4`/`.mov` screen
   recording, `.docx`, or code/log file instead.
5. If the Solution Agent produces a fix, **Test Suggested Fix (sandbox)**
   becomes enabled — it asks for confirmation, then runs the fix in a
   restricted subprocess and shows PASSED/FAILED plus stdout/stderr.
6. Use the **Chat** tab to ask follow-up questions — it has context on your
   most recent analysis.
7. Use the **History** tab to review or delete past analyses.

## Honest limitations (read before treating this as production-grade)

- **Live screen capture only works locally.** This is a desktop app for
  a reason — a hosted web app cannot see your OS-level screen without a
  browser screen-share prompt each time. Run it on your own machine.
- **The sandbox is best-effort, not a real security boundary.** It does a
  static AST scan to block obviously dangerous imports/calls (`os`,
  `subprocess`, `socket`, `eval`, etc.), runs in a subprocess with a
  timeout and (on Linux/Mac) CPU/memory/process-count limits, and uses a
  stripped environment. It does **not** provide OS-level isolation. If you
  want to run untrusted or AI-generated code with real guarantees, wrap the
  sandbox subprocess in Docker with `--network=none --read-only
  --pids-limit=64` or similar, or use gVisor/firecracker. Never disable the
  "confirm before running" step in the GUI.
- **OCR accuracy** depends on screen resolution, font, and theme. The
  preprocessing step (`preprocess.py`) auto-inverts dark IDE/terminal
  themes and applies denoising + Otsu thresholding, which handles most
  real screenshots well, but heavily stylized fonts or very small text may
  still OCR imperfectly.
- **Sandbox test execution currently supports Python only.** Testing
  Java/C++/JS fixes would need a compiler/runtime step per language —
  straightforward to add (see `agents/testing_agent.py`), just not wired up.
- **The Research Agent** uses a no-key DuckDuckGo endpoint by default,
  which returns limited results for very specific queries. Swap in Google
  Custom Search, Bing, or Serper for better documentation lookups if you
  want the Research Agent to be more reliable.
- **Gemini model name**: `GEMINI_MODEL` in `.env` defaults to
  `gemini-2.5-flash`. Check https://ai.google.dev/gemini-api/docs/models
  for the current recommended model and update it if needed.

## Project structure

```
ai_coding_assistant/
├── main.py                  entry point
├── config.py                loads .env
├── db.py                    SQLite persistence
├── preprocess.py            OpenCV image cleanup (Screen Agent)
├── ocr_engine.py            Tesseract OCR wrapper (Screen Agent)
├── detectors.py             fast offline language/error heuristics
├── gemini_client.py         google-genai SDK wrapper
├── sandbox_runner.py        restricted subprocess execution
├── file_ingest.py           image / video / docx / text ingestion
├── agents/
│   ├── manager.py           orchestrates the full pipeline
│   ├── code_agent.py        Code Extraction Agent
│   ├── error_agent.py       Error Analysis Agent
│   ├── research_agent.py    Research Agent
│   ├── solution_agent.py    Solution Agent (fix + "why it's needed")
│   ├── testing_agent.py     Testing Agent (sandbox wrapper)
│   └── response_agent.py    Response Agent (final teacher-style write-up)
├── capture/
│   ├── screen_capture.py    mss-based screenshot/region grab
│   ├── region_selector.py   drag-to-select overlay
│   └── live_monitor.py      background thread for live watching
└── gui/
    ├── app_gui.py            main window
    ├── chat_panel.py         chat tab
    └── history_panel.py      history tab
```

## Possible next steps (not built, but straightforward extensions)

- Wire up compiler/runtime sandboxes for Java/C++/JS in `testing_agent.py`.
- Swap the DuckDuckGo research call for a real search API + Stack Overflow API.
- Add a system-tray icon so live monitoring can run minimized.
- VS Code / PyCharm extension instead of a standalone window.
- Docker-wrap the sandbox for real isolation.
