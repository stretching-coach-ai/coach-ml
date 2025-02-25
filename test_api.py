import requests
import os
from dotenv import load_dotenv
import json
import time

# 환경 변수 로드
load_dotenv()

def test_stretching_examples():
    """
    다양한 스트레칭 관련 예제를 테스트하여 API의 판단 기준을 확인합니다.
    """
    api_key = os.getenv("ELICE_API_KEY")
    url = "https://api-cloud-function.elice.io/8d0fbc41-2edd-4525-8af7-25a6f429ad11/check"
    
    # 스트레칭 컨텍스트 (fact_checker.py에서 가져옴)
    stretching_context = """
    스트레칭은 신체의 유연성과 가동성을 향상시키는 운동 방법입니다.

    1. 스트레칭의 종류:
    - 정적 스트레칭: 특정 자세를 15-30초 유지
    - 동적 스트레칭: 관절을 천천히 움직이며 근육을 늘림
    - PNF 스트레칭: 수축과 이완을 번갈아 하는 전문적 기법
    - 밸리스틱 스트레칭: 반동을 이용한 동작

    2. 주요 목적:
    - 근육 긴장 완화
    - 관절 가동 범위 증가
    - 혈액 순환 개선
    - 부상 예방
    - 자세 교정
    - 운동 수행력 향상

    3. 적용 분야:
    - 운동 전후 준비/정리
    - 재활 치료
    - 자세 교정
    - 일상생활 건강관리
    - 스포츠 퍼포먼스 향상

    4. 주요 용어:
    - ROM(Range of Motion, 관절가동범위)
    - 근막이완
    - 스트레칭 포인트
    - 근육 신장
    - 관절 가동성
    """
    
    # 확장된 스트레칭 컨텍스트 (범위를 넓힘)
    extended_stretching_context = """
    스트레칭은 신체의 유연성과 가동성을 향상시키는 운동 방법입니다.

    1. 스트레칭의 종류:
    - 정적 스트레칭: 특정 자세를 15-30초 유지
    - 동적 스트레칭: 관절을 천천히 움직이며 근육을 늘림
    - PNF 스트레칭: 수축과 이완을 번갈아 하는 전문적 기법
    - 밸리스틱 스트레칭: 반동을 이용한 동작
    - 액티브 스트레칭: 근육의 능동적 수축을 통한 스트레칭
    - 패시브 스트레칭: 외부 힘을 이용한 스트레칭
    - 마이오파셜 릴리즈: 폼롤러 등을 이용한 근막 이완

    2. 주요 목적:
    - 근육 긴장 완화
    - 관절 가동 범위 증가
    - 혈액 순환 개선
    - 부상 예방 및 재활
    - 자세 교정 및 통증 완화
    - 운동 수행력 향상
    - 스트레스 감소 및 정신적 이완

    3. 적용 분야:
    - 운동 전후 준비/정리
    - 재활 치료 및 물리치료
    - 자세 교정 및 체형 관리
    - 일상생활 건강관리
    - 스포츠 퍼포먼스 향상
    - 요가, 필라테스 등 유연성 중심 운동
    - 직장인 건강관리 및 사무실 스트레칭

    4. 주요 용어 및 관련 개념:
    - ROM(Range of Motion, 관절가동범위)
    - 근막이완 및 근막 릴리즈
    - 스트레칭 포인트 및 트리거 포인트
    - 근육 신장 및 이완
    - 관절 가동성 및 안정성
    - 유연성 훈련 및 모빌리티 운동
    - 자세 교정 및 체형 관리
    """
    
    # 테스트할 다양한 예제들
    test_examples = [
        # 명확한 스트레칭 예제
        "정적 스트레칭은 근육을 천천히 늘려 15-30초 동안 유지하는 방법으로, 유연성을 향상시키는데 효과적입니다.",
        "대흉근 스트레칭은 어깨 통증과 자세 개선에 도움이 됩니다.",
        "PNF 스트레칭은 근육의 수축과 이완을 번갈아 사용하여 관절 가동 범위를 증가시킵니다.",
        
        # 덜 명확한 스트레칭 관련 예제
        "폼롤러를 이용한 등 근육 이완은 근막을 풀어주는데 효과적입니다.",
        "요가 자세 중 다운독 포지션은 전신 스트레칭에 좋습니다.",
        "햄스트링 근육을 늘려주는 운동은 허리 통증 예방에 도움이 됩니다.",
        
        # 스트레칭과 관련 없는 예제
        "고강도 인터벌 트레이닝은 짧은 시간 내에 효과적인 유산소 운동입니다.",
        "단백질 보충제는 근육 회복과 성장에 도움이 됩니다.",
        "MRI 검사는 연부 조직 손상을 진단하는데 유용합니다."
    ]
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    print("=== 기존 컨텍스트로 테스트 ===")
    for i, example in enumerate(test_examples):
        try:
            # API 호출 전 대기 (속도 제한 방지)
            time.sleep(3)
            
            request_data = {
                "document": stretching_context,
                "claim": example
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=request_data,
                timeout=15
            )
            
            response.raise_for_status()
            result = response.json()
            
            print(f"예제 {i+1}: {example[:50]}...")
            print(f"  결과: {'스트레칭 관련' if result.get('supported', False) else '관련 없음'}")
            print(f"  신뢰도: {result.get('confidence', 0):.4f}")
            print(f"  전체 응답: {result}")
            print()
            
        except Exception as e:
            print(f"예제 {i+1} 처리 중 오류 발생: {str(e)}")
    
    print("\n=== 확장된 컨텍스트로 테스트 ===")
    for i, example in enumerate(test_examples):
        try:
            # API 호출 전 대기 (속도 제한 방지)
            time.sleep(3)
            
            request_data = {
                "document": extended_stretching_context,
                "claim": example
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=request_data,
                timeout=15
            )
            
            response.raise_for_status()
            result = response.json()
            
            print(f"예제 {i+1}: {example[:50]}...")
            print(f"  결과: {'스트레칭 관련' if result.get('supported', False) else '관련 없음'}")
            print(f"  신뢰도: {result.get('confidence', 0):.4f}")
            print(f"  전체 응답: {result}")
            print()
            
        except Exception as e:
            print(f"예제 {i+1} 처리 중 오류 발생: {str(e)}")

def test_api_with_auth():
    """
    API 키를 사용하여 API 호출을 테스트합니다.
    """
    api_key = os.getenv("ELICE_API_KEY")
    url = "https://api-cloud-function.elice.io/8d0fbc41-2edd-4525-8af7-25a6f429ad11/check"
    
    # 테스트 데이터
    test_data = {
        "document": "스트레칭은 근육을 늘리는 운동입니다.",
        "claim": "스트레칭은 유연성을 향상시킵니다."
    }
    
    # 다양한 인증 방식 시도
    auth_methods = [
        # 1. 헤더에 API 키 추가 (Bearer 토큰)
        {
            "headers": {
                "accept": "application/json",
                "content-type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            "description": "Bearer 토큰 인증"
        },
        # 2. 헤더에 API 키 추가 (API 키)
        {
            "headers": {
                "accept": "application/json",
                "content-type": "application/json",
                "X-API-Key": api_key
            },
            "description": "X-API-Key 헤더 인증"
        },
        # 3. 쿼리 파라미터로 API 키 추가
        {
            "url": f"{url}?api_key={api_key}",
            "headers": {
                "accept": "application/json",
                "content-type": "application/json"
            },
            "description": "쿼리 파라미터 인증"
        },
        # 4. 기본 인증
        {
            "headers": {
                "accept": "application/json",
                "content-type": "application/json"
            },
            "auth": ("api", api_key),
            "description": "기본 인증"
        },
        # 5. 인증 없음 (테스트용)
        {
            "headers": {
                "accept": "application/json",
                "content-type": "application/json"
            },
            "description": "인증 없음"
        }
    ]
    
    print("=== API 인증 테스트 ===")
    
    for method in auth_methods:
        print(f"\n테스트: {method['description']}")
        try:
            # URL 설정
            request_url = method.get("url", url)
            
            # 인증 설정
            auth = method.get("auth", None)
            
            # API 호출
            response = requests.post(
                request_url,
                headers=method["headers"],
                json=test_data,
                auth=auth,
                timeout=10
            )
            
            # 결과 출력
            print(f"상태 코드: {response.status_code}")
            print(f"응답: {response.text[:200]}...")
            
            if response.status_code == 200:
                print("성공! 이 인증 방식이 작동합니다.")
                
        except Exception as e:
            print(f"오류 발생: {str(e)}")

def test_api_responses():
    """
    실제 논문/문서가 우리 서비스에 필요한 자료인지 테스트합니다.
    """
    api_key = os.getenv("ELICE_API_KEY")
    url = "https://api-cloud-function.elice.io/8d0fbc41-2edd-4525-8af7-25a6f429ad11/check"
    
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }

    service_context = """
    코치ML 서비스는 다음과 같은 자료가 필요합니다:

    1. 스트레칭 운동 관련 자료
    - 신체 부위별 스트레칭 방법
    - 증상/통증별 맞춤 스트레칭
    - 스트레칭의 효과와 영향
    - 올바른 스트레칭 자세와 기법

    2. 통증 관리 관련 자료
    - 근골격계 통증의 원인과 증상
    - 통증 완화를 위한 운동 방법
    - 자세 교정과 통증 관리
    - 일상생활에서의 통증 예방

    3. 운동 효과 검증 자료
    - 스트레칭의 효과성 연구
    - 통증 개선 효과 연구
    - 운동 방법의 안전성 검증
    - 운동 효과의 과학적 근거

    4. 제외 대상
    - 전문 운동선수 대상 연구
    - 특수 의료장비 필요 연구
    - 임상실험/수술 관련 연구
    - 약물 치료 관련 연구
    """

    # 테스트할 논문/문서 예제들
    test_cases = [
        {
            "document": "Effects of Static Stretching on Range of Motion and Muscle Length: A systematic review of stretching protocols for office workers with neck pain",
            "claim": "이 자료는 코치ML 서비스에 필요한 스트레칭/통증 관리 관련 자료입니다."
        },
        {
            "document": "Trunk muscle activation in prone plank exercises with different body tilts: EMG analysis of core muscle activation patterns in athletes",
            "claim": "이 자료는 코치ML 서비스에 필요한 스트레칭/통증 관리 관련 자료입니다."
        },
        {
            "document": "The effectiveness of stretching exercises for reducing chronic neck pain and improving range of motion in office workers: A randomized controlled trial",
            "claim": "이 자료는 코치ML 서비스에 필요한 스트레칭/통증 관리 관련 자료입니다."
        },
        {
            "document": "Effect of whole body vibration on the electromyographic activity of core stabilizer muscles in professional athletes",
            "claim": "이 자료는 코치ML 서비스에 필요한 스트레칭/통증 관리 관련 자료입니다."
        },
        {
            "document": "Simple stretching exercises for neck pain relief: A guide for daily practice in office environments",
            "claim": "이 자료는 코치ML 서비스에 필요한 스트레칭/통증 관리 관련 자료입니다."
        }
    ]

    print("\n=== 논문/문서 관련성 테스트 시작 ===")
    
    for i, test_case in enumerate(test_cases, 1):
        try:
            # API 호출 전 대기 (속도 제한 방지)
            time.sleep(2)
            
            # 컨텍스트와 테스트 케이스 결합
            request_data = {
                "document": f"{service_context}\n\n분석할 자료:\n{test_case['document']}",
                "claim": test_case['claim']
            }
            
            response = requests.post(
                url,
                headers=headers,
                json=request_data,
                timeout=10
            )
            
            response.raise_for_status()
            result = response.json()
            
            print(f"\n테스트 케이스 {i}:")
            print(f"자료: {test_case['document']}")
            print(f"서비스 관련성: {result.get('supported', False)}")
            print(f"신뢰도: {result.get('confidence', 0):.4f}")
            print("-" * 50)
            
        except Exception as e:
            print(f"테스트 케이스 {i} 처리 중 오류 발생: {str(e)}")
    
    print("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    # test_stretching_examples()  # 기존 테스트는 주석 처리
    # test_api_with_auth()       # 기존 테스트는 주석 처리
    test_api_responses()         # 논문/문서 관련성 테스트 실행 