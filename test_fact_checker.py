import json
import os
from fact_checker import FactChecker
import logging

def test_fact_checker_with_samples():
    """
    샘플 텍스트로 FactChecker의 기능을 테스트합니다.
    """
    # 테스트 샘플 데이터
    samples = [
        # 명확하게 스트레칭 관련 텍스트
        "정적 스트레칭은 근육을 천천히 늘려 15-30초 동안 유지하는 방법으로, 유연성을 향상시키는데 효과적입니다.",
        "대흉근 스트레칭은 어깨 통증과 자세 개선에 도움이 됩니다.",
        "PNF 스트레칭은 근육의 수축과 이완을 번갈아 사용하여 관절 가동 범위를 증가시킵니다.",
        
        # 스트레칭과 관련 없는 텍스트
        "고강도 인터벌 트레이닝은 짧은 시간 내에 효과적인 유산소 운동입니다.",
        "단백질 보충제는 근육 회복과 성장에 도움이 됩니다.",
        "MRI 검사는 연부 조직 손상을 진단하는데 유용합니다."
    ]
    
    # FactChecker 인스턴스 생성
    fact_checker = FactChecker(max_retries=2, batch_size=3, confidence_threshold=0.7)
    
    print("=== 개별 텍스트 테스트 ===")
    for i, sample in enumerate(samples):
        is_relevant, confidence, error = fact_checker.check_stretching_relevance_with_retry(sample)
        print(f"샘플 {i+1}: {'관련됨' if is_relevant else '관련 없음'} - {sample[:50]}...")
        print(f"  신뢰도: {confidence:.4f}")
        if error:
            print(f"  오류: {error}")
    
    print("\n=== 배치 처리 테스트 ===")
    results = fact_checker.process_batch(samples)
    for i, (sample, is_relevant) in enumerate(zip(samples, results)):
        print(f"샘플 {i+1}: {'관련됨' if is_relevant else '관련 없음'} - {sample[:50]}...")

def test_with_small_dataset():
    """
    작은 데이터셋으로 전체 처리 과정을 테스트합니다.
    """
    # 테스트용 작은 데이터셋 생성
    test_data = {
        "metadata": {
            "total_items": 6,
            "front_muscles": ["대흉근", "복직근"],
            "back_muscles": ["광배근", "승모근"],
            "collection_date": "2025-02-25T10:44:13.904120",
            "data_sources": ["Test"]
        },
        "muscles": {
            "대흉근": {
                "info": {
                    "english": "pectoralis major",
                    "keywords_ko": ["대흉근 스트레칭", "가슴 스트레칭"],
                    "common_issues": ["라운드숄더", "거북목"]
                },
                "exercises": [
                    {
                        "source": "test",
                        "muscle": "대흉근",
                        "title": "대흉근 스트레칭 방법",
                        "abstract": "대흉근 스트레칭은 어깨와 가슴 통증 완화에 효과적입니다. 벽에 팔을 대고 몸을 돌려 스트레칭합니다.",
                        "protocol": {"steps": ["벽에 팔을 대고 몸을 돌립니다", "15-30초 유지합니다"]}
                    },
                    {
                        "source": "test",
                        "muscle": "대흉근",
                        "title": "대흉근 근력 운동",
                        "abstract": "벤치프레스는 대흉근을 강화하는 대표적인 운동입니다. 바벨이나 덤벨을 사용하여 수행합니다.",
                        "protocol": {"steps": ["벤치에 누워 바벨을 들어올립니다", "천천히 내렸다가 올립니다"]}
                    }
                ]
            },
            "광배근": {
                "info": {
                    "english": "latissimus dorsi",
                    "keywords_ko": ["광배근 스트레칭", "등 스트레칭"],
                    "common_issues": ["등 통증", "자세 불균형"]
                },
                "exercises": [
                    {
                        "source": "test",
                        "muscle": "광배근",
                        "title": "광배근 스트레칭 방법",
                        "abstract": "광배근 스트레칭은 등 통증 완화에 도움이 됩니다. 팔을 위로 뻗고 옆으로 기울여 스트레칭합니다.",
                        "protocol": {"steps": ["팔을 위로 뻗습니다", "옆으로 기울입니다", "15-30초 유지합니다"]}
                    },
                    {
                        "source": "test",
                        "muscle": "광배근",
                        "title": "광배근 MRI 분석",
                        "abstract": "광배근 손상은 MRI를 통해 정확히 진단할 수 있습니다. T2 강조 영상에서 고신호 강도로 나타납니다.",
                        "protocol": {"steps": ["MRI 촬영", "T2 강조 영상 분석", "손상 부위 확인"]}
                    }
                ]
            }
        }
    }
    
    # 테스트 데이터 저장
    os.makedirs("data/test", exist_ok=True)
    test_input_file = "data/test/test_muscle_data.json"
    test_output_file = "data/test/test_filtered_data.json"
    
    with open(test_input_file, 'w', encoding='utf-8') as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)
    
    # fact_checker 모듈에서 process_muscle_data 함수 임포트
    from fact_checker import process_muscle_data
    
    # 테스트 실행
    print("\n=== 작은 데이터셋 처리 테스트 ===")
    process_muscle_data(test_input_file, test_output_file)
    
    # 결과 확인
    with open(test_output_file, 'r', encoding='utf-8') as f:
        filtered_data = json.load(f)
    
    print("\n=== 필터링 결과 ===")
    for muscle_name, muscle_info in filtered_data["muscles"].items():
        print(f"{muscle_name}: {len(muscle_info['exercises'])}개 운동 남음")
        for exercise in muscle_info["exercises"]:
            print(f"  - {exercise['title']}")

if __name__ == "__main__":
    # 로깅 레벨 설정 (테스트 중에는 WARNING 이상만 표시)
    logging.basicConfig(level=logging.WARNING)
    
    # 개별 테스트 실행
    test_fact_checker_with_samples()
    test_with_small_dataset() 