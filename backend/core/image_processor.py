# backend/core/image_processor.py
from PIL import Image
import base64
from io import BytesIO
from typing import Tuple

# 허용된 이미지 확장자
ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp'}

# 최대 이미지 크기 (10MB)
MAX_IMAGE_SIZE = 10 * 1024 * 1024

def validate_image_extension(filename: str) -> bool:
    """이미지 확장자 검증"""
    if not filename:
        return False
    extension = filename.rsplit('.', 1)[-1].lower()
    return extension in ALLOWED_EXTENSIONS

def compress_image(image_bytes: bytes, max_size: int = 2048) -> bytes:
    """
    이미지 압축 (Azure OpenAI API 전송 최적화)
    
    Args:
        image_bytes: 원본 이미지 바이트
        max_size: 최대 이미지 크기 (픽셀, 긴 쪽 기준)
    
    Returns:
        압축된 이미지 바이트 (JPEG)
    """
    image = Image.open(BytesIO(image_bytes))
    
    # RGBA를 RGB로 변환 (JPEG는 RGBA 미지원)
    if image.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', image.size, (255, 255, 255))
        if image.mode == 'P':
            image = image.convert('RGBA')
        background.paste(image, mask=image.split()[-1] if image.mode == 'RGBA' else None)
        image = background
    
    # 이미지 리사이징 (긴 쪽 기준)
    if max(image.size) > max_size:
        image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
    
    # JPEG로 압축
    output = BytesIO()
    image.save(output, format='JPEG', quality=85, optimize=True)
    return output.getvalue()

def image_to_base64(image_bytes: bytes) -> str:
    """
    이미지를 base64로 인코딩
    
    Args:
        image_bytes: 이미지 바이트
    
    Returns:
        base64 인코딩된 문자열
    """
    return base64.b64encode(image_bytes).decode('utf-8')