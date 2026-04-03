# OCR module for extracting text from welfare document images.
# Uses zai-org/GLM-OCR via HuggingFace Inference API.

from .engine import OCREngine, get_ocr_engine

__all__ = ["OCREngine", "get_ocr_engine"]
