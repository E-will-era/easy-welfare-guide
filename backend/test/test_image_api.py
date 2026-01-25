"""
이미지 텍스트 추출 API 테스트 스크립트
"""
import httpx
import asyncio
import json
from pathlib import Path

# API 엔드포인트
BASE_URL = "http://localhost:8000"

async def test_extract_text(
    image_path: str,
    verify: bool = True,
    enable_compression: bool = True,
    compression_quality: int = 85,
    max_image_size: int = 2048
):
    """
    이미지 텍스트 추출 테스트
    
    Args:
        image_path: 테스트할 이미지 파일 경로
        verify: 텍스트 검증 여부
        enable_compression: 압축 활성화 여부
        compression_quality: 압축 품질 (1-100)
        max_image_size: 최대 이미지 크기 (px)
    """
    # 파일 존재 확인
    if not Path(image_path).exists():
        print(f"❌ 오류: 파일을 찾을 수 없습니다 - {image_path}")
        return
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        # 이미지 파일 읽기
        with open(image_path, "rb") as f:
            files = {"image": (Path(image_path).name, f, "image/png")}
            data = {
                "verify": str(verify).lower(),
                "enable_compression": str(enable_compression).lower(),
                "compression_quality": compression_quality,
                "max_image_size": max_image_size
            }
            
            print(f"\n{'='*60}")
            print(f"테스트 시작: {Path(image_path).name}")
            print(f"{'='*60}")
            print(f"설정:")
            print(f"  - 검증: {verify}")
            print(f"  - 압축: {enable_compression}")
            print(f"  - 압축 품질: {compression_quality}")
            print(f"  - 최대 크기: {max_image_size}px")
            print(f"{'='*60}\n")
            
            try:
                response = await client.post(
                    f"{BASE_URL}/api/v1/extract-text",
                    files=files,
                    data=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    print("✅ 성공!")
                    print(f"\n추출된 텍스트:")
                    print(f"{'-'*60}")
                    print(result.get("extracted_text", ""))
                    print(f"{'-'*60}")
                    
                    # 압축 정보
                    compression_info = result.get("compression_info", {})
                    if compression_info.get("compressed"):
                        print(f"\n압축 정보:")
                        print(f"  원본 크기: {compression_info['original_size']:,} bytes")
                        print(f"  최종 크기: {compression_info['final_size']:,} bytes")
                        print(f"  감소율: {compression_info['size_reduction_percent']}%")
                        print(f"  원본 해상도: {compression_info['original_dimensions']}")
                        print(f"  최종 해상도: {compression_info['final_dimensions']}")
                    
                    # 검증 정보
                    if result.get("verification"):
                        verification = result["verification"]
                        print(f"\n검증 결과:")
                        print(f"  유효성: {verification.get('is_valid')}")
                        print(f"  신뢰도: {verification.get('confidence_score')}%")
                        if verification.get("issues"):
                            print(f"  문제점: {', '.join(verification['issues'])}")
                    
                    # 최종 텍스트
                    if result.get("text_corrected"):
                        print(f"\n최종 텍스트 (수정됨):")
                        print(f"{'-'*60}")
                        print(result.get("final_text", ""))
                        print(f"{'-'*60}")
                    
                else:
                    print(f"❌ 실패: {response.status_code}")
                    try:
                        error_detail = response.json()
                        print(f"에러 내용: {json.dumps(error_detail, indent=2, ensure_ascii=False)}")
                    except:
                        print(f"에러 내용: {response.text}")
                    
            except httpx.ConnectError:
                print(f"❌ 연결 오류: 서버가 실행 중인지 확인하세요 ({BASE_URL})")
            except httpx.TimeoutException:
                print(f"❌ 타임아웃: 서버 응답이 60초를 초과했습니다")
            except Exception as e:
                print(f"❌ 오류: {str(e)}")

async def test_multiple_scenarios():
    """다양한 시나리오 테스트"""
    # 실제 테스트 이미지 경로
    test_image = r"C:\Users\admin\Desktop\e-will-era-backend\easy-welfare-guide\backend\test_image.png"
    
    # 파일 존재 확인
    if not Path(test_image).exists():
        print(f"❌ 테스트 이미지를 찾을 수 없습니다: {test_image}")
        print("경로를 확인해주세요.")
        return
    
    # 시나리오 1: 기본 설정 (압축 + 검증)
    print("\n" + "="*70)
    print("[시나리오 1] 기본 설정 (압축 + 검증)")
    print("="*70)
    await test_extract_text(
        test_image,
        verify=True,
        enable_compression=True,
        compression_quality=85,
        max_image_size=2048
    )
    
    await asyncio.sleep(1)  # 서버 부하 방지
    
    # 시나리오 2: 압축 없이 원본 사용
    print("\n" + "="*70)
    print("[시나리오 2] 압축 비활성화")
    print("="*70)
    await test_extract_text(
        test_image,
        verify=True,
        enable_compression=False
    )
    
    await asyncio.sleep(1)
    
    # 시나리오 3: 고품질 압축
    print("\n" + "="*70)
    print("[시나리오 3] 고품질 압축 (품질 95)")
    print("="*70)
    await test_extract_text(
        test_image,
        verify=True,
        enable_compression=True,
        compression_quality=95,
        max_image_size=4096
    )
    
    await asyncio.sleep(1)
    
    # 시나리오 4: 강한 압축
    print("\n" + "="*70)
    print("[시나리오 4] 강한 압축 (품질 60)")
    print("="*70)
    await test_extract_text(
        test_image,
        verify=True,
        enable_compression=True,
        compression_quality=60,
        max_image_size=1024
    )
    
    await asyncio.sleep(1)
    
    # 시나리오 5: 검증 없이 빠른 추출
    print("\n" + "="*70)
    print("[시나리오 5] 검증 없이 빠른 추출")
    print("="*70)
    await test_extract_text(
        test_image,
        verify=False,
        enable_compression=True,
        compression_quality=85,
        max_image_size=2048
    )

if __name__ == "__main__":
    print("="*70)
    print("이미지 텍스트 추출 API 테스트")
    print("="*70)
    print(f"테스트 대상 서버: {BASE_URL}")
    print("="*70)
    
    # 단일 테스트 (기본)
    test_image_path = r"C:\Users\admin\Desktop\e-will-era-backend\easy-welfare-guide\backend\test_image.png"
    asyncio.run(test_extract_text(test_image_path))
    
    # 다중 시나리오 테스트를 원하면 아래 주석 해제
    # asyncio.run(test_multiple_scenarios())