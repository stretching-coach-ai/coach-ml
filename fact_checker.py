import json
import os
import requests
from dotenv import load_dotenv
from typing import Dict, List, Tuple
import time
from datetime import datetime
import logging
from tqdm import tqdm
import random
import re

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'fact_checker_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

class FactChecker:
    def __init__(self, max_retries: int = 5, batch_size: int = 3, rate_limit_delay: float = 2.0):
        self.base_url = "https://api-cloud-function.elice.io/8d0fbc41-2edd-4525-8af7-25a6f429ad11/check"
        self.api_key = os.getenv("ELICE_API_KEY")
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay
        
        # 통계 추적
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.rate_limited_requests = 0
    
    def get_stretching_context(self) -> str:
        """스트레칭 관련성 판단을 위한 컨텍스트를 반환합니다."""
        return """
        coach - ai 서비스는 다음과 같은 자료가 필요합니다:

        1. 스트레칭 운동 관련 자료
        - 신체 부위별 스트레칭 방법
        - 증상/통증별 맞춤 스트레칭
        - 스트레칭의 효과와 영향
        - 올바른 스트레칭 자세와 기법
        - 일상생활에서 활용 가능한 스트레칭

        2. 통증 관리 관련 자료
        - 근골격계 통증의 원인과 증상
        - 통증 완화를 위한 운동 방법
        - 자세 교정과 통증 관리
        - 일상생활에서의 통증 예방
        - 사무직 근로자를 위한 운동

        3. 운동 효과 검증 자료
        - 스트레칭의 효과성 연구
        - 통증 개선 효과 연구
        - 운동 방법의 안전성 검증
        - 운동 효과의 과학적 근거
        - 일반인 대상 연구 결과

        4. 제외 대상
        - 특수 의료장비 필요 연구
        - 임상실험/수술 관련 연구
        - 약물 치료 관련 연구
        """
    
    def check_stretching_relevance_with_retry(self, text: str) -> Tuple[bool, float, str]:
        """텍스트의 스트레칭 관련성을 판단합니다."""
        self.total_requests += 1
        
        for attempt in range(self.max_retries):
            try:
                # API 호출 전 대기 (속도 제한 방지)
                wait_time = self.rate_limit_delay + random.uniform(0.5, 1.5)
                time.sleep(wait_time)
                
                logging.debug(f"API 호출 시도 {attempt + 1}/{self.max_retries}")
                
                # API 요청 데이터 준비
                request_data = {
                    "document": f"""
                    {self.get_stretching_context()}
                    
                    분석할 자료:
                    {text}
                    """,
                    "claim": "이 자료는 코치ML 서비스에 필요한 스트레칭/통증 관리 관련 자료입니다."
                }
                
                response = requests.post(
                    self.base_url,
                    headers=self.headers,
                    json=request_data,
                    timeout=15
                )
                
                # 응답 상태 코드 로깅
                logging.debug(f"응답 상태 코드: {response.status_code}")
                
                # 속도 제한 처리
                if response.status_code == 429:
                    self.rate_limited_requests += 1
                    wait_time = (attempt + 1) * 5  # 점진적 대기 시간 증가
                    logging.warning(f"속도 제한 감지, {wait_time}초 대기")
                    time.sleep(wait_time)
                    continue
                
                response.raise_for_status()
                result = response.json()
                
                self.successful_requests += 1
                
                is_supported = result.get("supported", False)
                confidence = result.get("confidence", 0.0)
                
                logging.info(f"API 응답 - supported: {is_supported}, confidence: {confidence:.2f}")
                
                return is_supported, confidence, ""
                
            except requests.exceptions.RequestException as e:
                logging.error(f"API 요청 오류: {str(e)}")
                if attempt == self.max_retries - 1:
                    self.failed_requests += 1
                    return False, 0.0, str(e)
                continue
    
    def process_batch(self, texts: List[str]) -> List[bool]:
        """여러 텍스트의 스트레칭 관련성을 배치로 처리합니다."""
        results = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_results = []
            for text in batch:
                is_relevant, confidence, error = self.check_stretching_relevance_with_retry(text)
                batch_results.append(is_relevant)
            results.extend(batch_results)
        return results
    
    def print_stats(self):
        """API 호출 통계를 출력합니다."""
        print("\n=== API 호출 통계 ===")
        print(f"총 요청 수: {self.total_requests}")
        print(f"성공한 요청: {self.successful_requests}")
        print(f"실패한 요청: {self.failed_requests}")
        print(f"속도 제한 횟수: {self.rate_limited_requests}")
        if self.total_requests > 0:
            success_rate = (self.successful_requests / self.total_requests) * 100
            print(f"성공률: {success_rate:.1f}%")

def process_muscle_data(input_file: str, output_file: str, limit_muscles: int = None, exercises_per_muscle: int = None):
    """근육 데이터를 처리하고 스트레칭 관련 운동만 필터링합니다."""
    try:
        # 입력 파일 읽기
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # FactChecker 인스턴스 생성
        fact_checker = FactChecker(max_retries=3, batch_size=3, rate_limit_delay=2.0)
        
        # 결과 저장을 위한 임시 파일 경로
        temp_dir = os.path.dirname(output_file)
        os.makedirs(temp_dir, exist_ok=True)
        temp_output_file = os.path.join(temp_dir, "stretching_filtered_data_temp.json")
        
        # 결과 데이터 구조 초기화
        filtered_data = {
            "metadata": data["metadata"].copy(),
            "muscles": {}
        }
        
        # 처리할 근육 수 제한
        muscles = list(data["muscles"].items())
        if limit_muscles:
            muscles = muscles[:limit_muscles]
        
        # 진행 상황 표시
        with tqdm(total=len(muscles), desc="근육 데이터 처리 중") as pbar:
            for muscle_name, muscle_info in muscles:
                exercises = muscle_info["exercises"]
                
                # 운동 수 제한
                if exercises_per_muscle:
                    exercises = exercises[:exercises_per_muscle]
                
                filtered_exercises = []
                
                for exercise in exercises:
                    # 운동 정보를 하나의 텍스트로 결합
                    exercise_text = f"{exercise.get('title', '')}. {exercise.get('abstract', '')}"
                    if 'protocol' in exercise and 'steps' in exercise['protocol']:
                        steps_text = ' '.join(exercise['protocol']['steps'])
                        exercise_text += f" {steps_text}"
                    
                    # 스트레칭 관련성 확인
                    is_relevant, confidence, error = fact_checker.check_stretching_relevance_with_retry(exercise_text)
                    
                    if is_relevant:
                        logging.info(f"스트레칭 관련 자료로 포함: {exercise.get('title', '')} (신뢰도: {confidence:.2f})")
                        filtered_exercises.append(exercise)
                    else:
                        logging.info(f"스트레칭 무관으로 제외: {exercise.get('title', '')} (신뢰도: {confidence:.2f})")
                
                # 필터링된 운동이 있는 경우만 결과에 포함
                if filtered_exercises:
                    filtered_data["muscles"][muscle_name] = {
                        "info": muscle_info["info"],
                        "exercises": filtered_exercises
                    }
                
                # 중간 결과 저장
                with open(temp_output_file, 'w', encoding='utf-8') as f:
                    json.dump(filtered_data, f, ensure_ascii=False, indent=2)
                
                pbar.update(1)
        
        # 최종 결과 저장
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(filtered_data, f, ensure_ascii=False, indent=2)
        
        # 통계 출력
        fact_checker.print_stats()
        
        # 결과 요약
        total_exercises = sum(len(m["exercises"]) for m in filtered_data["muscles"].values())
        print(f"\n=== 처리 결과 ===")
        print(f"처리된 근육 수: {len(filtered_data['muscles'])}")
        print(f"필터링된 운동 수: {total_exercises}")
        
    except Exception as e:
        logging.error(f"데이터 처리 중 치명적 오류 발생: {str(e)}")
        raise

if __name__ == "__main__":
    input_file = "data/raw/muscle_data_20250225_104413.json"
    output_file = "data/processed/stretching_filtered_data.json"
    
    # processed 디렉토리가 없으면 생성
    os.makedirs("data/processed", exist_ok=True)
    
    # 테스트 모드 해제: 모든 근육 처리
    limit_muscles = None
    
    # 테스트 모드 해제: 각 근육의 모든 운동 처리
    exercises_per_muscle = None
    
    process_muscle_data(input_file, output_file, limit_muscles, exercises_per_muscle) 