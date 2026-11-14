"""OpenCV-based image preprocessing to improve OCR quality (FR-02 / Screen Agent)."""
import cv2
import numpy as np


def preprocess_for_ocr(image: np.ndarray, upscale_if_small=True) -> np.ndarray:
    """
    Takes a BGR image (screenshot / frame) and returns a cleaned-up grayscale
    image optimized for text extraction.
    """
    img = image.copy()

    h, w = img.shape[:2]
    if upscale_if_small and max(h, w) < 900:
        scale = 900 / max(h, w)
        img = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Most code editors/terminals use dark themes (light text on dark
    # background). Tesseract is trained on dark text on light background,
    # so auto-invert when the image is predominantly dark.
    if gray.mean() < 127:
        gray = cv2.bitwise_not(gray)

    # Light denoise — enough to smooth compression artifacts without
    # blurring away character edges (heavy denoising hurts OCR accuracy).
    denoised = cv2.fastNlMeansDenoising(gray, h=7)

    # Otsu's threshold auto-picks a good global cutoff for clean screenshots
    # (adaptive thresholding tends to fragment anti-aliased font glyphs).
    _, thresh = cv2.threshold(denoised, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return thresh


def crop_region(image: np.ndarray, box) -> np.ndarray:
    """box = (x1, y1, x2, y2) in pixel coordinates."""
    x1, y1, x2, y2 = [int(v) for v in box]
    x1, x2 = sorted((max(x1, 0), max(x2, 0)))
    y1, y2 = sorted((max(y1, 0), max(y2, 0)))
    return image[y1:y2, x1:x2]
