"""Text extraction from images via Tesseract OCR (part of the Screen Agent)."""
import pytesseract
import numpy as np

import config

if config.TESSERACT_CMD:
    pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

# Keep code punctuation (braces, colons, underscores etc.) which default OCR
# configs sometimes drop.
_TESS_CONFIG = "--oem 3 --psm 6"


def extract_text(image: np.ndarray) -> str:
    try:
        text = pytesseract.image_to_string(image, config=_TESS_CONFIG)
        return text.strip()
    except pytesseract.TesseractNotFoundError:
        return (
            "[OCR ERROR] Tesseract binary not found. Install it:\n"
            "  Ubuntu/Debian: sudo apt-get install tesseract-ocr\n"
            "  macOS:         brew install tesseract\n"
            "  Windows:       https://github.com/UB-Mannheim/tesseract/wiki\n"
            "Then set TESSERACT_CMD in .env if it's not on your PATH."
        )
    except Exception as e:
        return f"[OCR ERROR] {e}"
