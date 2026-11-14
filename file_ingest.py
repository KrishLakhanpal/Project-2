"""
Multi-input ingestion (screenshots, screen recordings, Word docs, code
files). Every ingestor returns plain text/code so it can feed straight into
the same agent pipeline used for live screen capture.
"""
import os
import cv2
import numpy as np
from PIL import Image
import docx

import preprocess
import ocr_engine


# ---------------------------------------------------------------- images ---

def ingest_image(path: str) -> str:
    """PNG/JPG/etc screenshot -> OCR text."""
    pil_img = Image.open(path).convert("RGB")
    bgr = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
    cleaned = preprocess.preprocess_for_ocr(bgr)
    return ocr_engine.extract_text(cleaned)


# ---------------------------------------------------------------- video ----

def ingest_video(path: str, sample_every_seconds: float = 2.0, max_frames: int = 20) -> str:
    """
    Screen-recording video -> sampled frames -> OCR each -> de-duplicated,
    concatenated text. This is how "video" input becomes analyzable without
    needing to process every single frame.
    """
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        return "[VIDEO ERROR] Could not open video file."

    fps = cap.get(cv2.CAP_PROP_FPS) or 24
    frame_interval = max(int(fps * sample_every_seconds), 1)

    texts = []
    seen = set()
    frame_idx = 0
    grabbed_count = 0

    while grabbed_count < max_frames:
        ok, frame = cap.read()
        if not ok:
            break
        if frame_idx % frame_interval == 0:
            cleaned = preprocess.preprocess_for_ocr(frame)
            text = ocr_engine.extract_text(cleaned)
            normalized = " ".join(text.split())
            # Skip near-duplicate frames (e.g. idle screen) to save OCR/API calls.
            if normalized and normalized not in seen:
                seen.add(normalized)
                texts.append(f"--- frame @ ~{frame_idx / fps:.1f}s ---\n{text}")
                grabbed_count += 1
        frame_idx += 1

    cap.release()
    if not texts:
        return "[VIDEO] No readable text found in sampled frames."
    return "\n\n".join(texts)


# ---------------------------------------------------------------- docx -----

def ingest_docx(path: str) -> str:
    """Word document -> extracted paragraph text (code pasted into Word,
    homework write-ups, etc.). Also pulls text out of tables if present."""
    document = docx.Document(path)
    chunks = [p.text for p in document.paragraphs if p.text.strip()]
    for table in document.tables:
        for row in table.rows:
            row_text = " | ".join(cell.text for cell in row.cells)
            if row_text.strip():
                chunks.append(row_text)
    return "\n".join(chunks) if chunks else "[DOCX] No text found in document."


# ------------------------------------------------------------ plain text ---

def ingest_text_file(path: str) -> str:
    """.py / .js / .txt / .log etc — just read it."""
    with open(path, "r", errors="replace") as f:
        return f.read()


# ------------------------------------------------------------- dispatcher --

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".webp", ".gif"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
TEXT_EXTS = {".py", ".js", ".ts", ".java", ".c", ".cpp", ".h", ".sql",
             ".html", ".css", ".txt", ".log", ".json", ".md"}


def ingest_any(path: str) -> tuple[str, str]:
    """Returns (source_type, extracted_text) based on file extension."""
    ext = os.path.splitext(path)[1].lower()
    if ext in IMAGE_EXTS:
        return "image", ingest_image(path)
    if ext in VIDEO_EXTS:
        return "video", ingest_video(path)
    if ext == ".docx":
        return "docx", ingest_docx(path)
    if ext in TEXT_EXTS:
        return "text", ingest_text_file(path)
    return "unknown", f"[INGEST ERROR] Unsupported file type: {ext}"
