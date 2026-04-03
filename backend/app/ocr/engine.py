"""
Upstage Document Digitization API를 사용하는 OCR 엔진 모듈.

업로드된 이미지에서 텍스트를 추출한 후, PII 마스킹을 적용합니다.
"""

import asyncio
import io
import re
import logging
from typing import Optional

import httpx
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
UPSTAGE_OCR_URL = "https://api.upstage.ai/v1/document-digitization"

# ---------------------------------------------------------------------------
# Module-level singleton storage
# ---------------------------------------------------------------------------
_ocr_engine_instance: Optional["OCREngine"] = None


class OCREngine:
    """
    Upstage Document Digitization API를 사용하여 복지 문서 이미지에서 텍스트를 추출합니다.
    """

    def __init__(self) -> None:
        token = settings.UPSTAGE_API_KEY
        if not token:
            raise ValueError(
                "UPSTAGE_API_KEY environment variable is required for OCR API."
            )
        self._headers = {"Authorization": f"Bearer {token}"}
        self._client = httpx.AsyncClient(timeout=60.0)
        logger.info("OCREngine initialised (Upstage Document Digitization)")

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def extract_text(self, image_bytes: bytes) -> dict:
        """
        Upstage OCR API를 통해 이미지 바이트에서 텍스트를 비동기로 추출합니다.

        반환값: 'text', 'confidence', 'raw_results' 키를 포함하는 dict.
        """
        if not image_bytes:
            raise ValueError("image_bytes must not be empty.")

        jpeg_bytes = await asyncio.to_thread(self._prepare_image, image_bytes)

        try:
            response = await self._client.post(
                UPSTAGE_OCR_URL,
                headers=self._headers,
                files={"document": ("image.jpg", jpeg_bytes, "image/jpeg")},
                data={"model": "ocr"},
            )
            response.raise_for_status()
            result = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Upstage OCR API error %s: %s", exc.response.status_code, exc.response.text)
            raise RuntimeError(f"Upstage OCR API error: {exc.response.status_code}") from exc
        except Exception as exc:
            logger.error("Upstage OCR request failed: %s", exc)
            raise RuntimeError(f"Upstage OCR request failed: {exc}") from exc

        extracted_text = self._parse_response(result)
        confidence = result.get("confidence", 1.0 if extracted_text.strip() else 0.0)
        masked_text = self._mask_pii(extracted_text)

        return {
            "text": masked_text,
            "confidence": confidence,
            "raw_results": [{"text": extracted_text}],
        }

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _prepare_image(self, image_bytes: bytes) -> bytes:
        """Converts image bytes to JPEG bytes."""
        try:
            pil_image = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            max_dim = 2048
            if max(pil_image.size) > max_dim:
                pil_image.thumbnail((max_dim, max_dim), Image.LANCZOS)
            buf = io.BytesIO()
            pil_image.save(buf, format="JPEG", quality=85)
            return buf.getvalue()
        except Exception as exc:
            raise ValueError(
                f"Failed to decode image bytes as a valid image: {exc}"
            ) from exc

    def _parse_response(self, result: dict) -> str:
        """Upstage API 응답에서 텍스트를 추출합니다."""
        if isinstance(result, dict):
            # Upstage returns {"text": "...", "confidence": 0.87, "pages": [...]}
            return result.get("text", "")
        return str(result)

    def _mask_pii(self, text: str) -> str:
        """추출된 텍스트에서 개인 식별 정보를 마스킹합니다."""
        mobile_pattern = re.compile(
            r"01[016789][\s\-\.]?\d{3,4}[\s\-\.]?\d{4}"
        )
        landline_pattern = re.compile(
            r"0(?:2|\d{2})[\s\-\.]\d{3,4}[\s\-\.]\d{4}"
        )
        rrn_pattern = re.compile(r"\d{6}[\s\-]\d{7}")

        text = mobile_pattern.sub("***", text)
        text = landline_pattern.sub("***", text)
        text = rrn_pattern.sub("***", text)

        return text


# ---------------------------------------------------------------------------
# Singleton accessor
# ---------------------------------------------------------------------------

def get_ocr_engine() -> OCREngine:
    """모듈 레벨의 싱글톤 OCREngine 인스턴스를 리턴합니다."""
    global _ocr_engine_instance
    if _ocr_engine_instance is None:
        logger.info("Creating OCREngine singleton instance.")
        _ocr_engine_instance = OCREngine()
    return _ocr_engine_instance
