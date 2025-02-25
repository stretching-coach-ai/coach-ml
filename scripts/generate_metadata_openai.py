"""
스트레칭 데이터 메타데이터 생성 스크립트

이 스크립트는 OpenAI GPT-4o Mini 모델을 사용하여 기존 스트레칭 데이터에서
사용자 맞춤형 추천을 위한 추가 메타데이터를 생성합니다.

사용법:
    python scripts/generate_metadata_openai.py --input <input_file> --output <output_file> [--limit <max_items>]

예시:
    python scripts/generate_metadata_openai.py --input data/raw/muscle_data_20250225_104413.json --output data/enhanced/enhanced_data.json --limit 50
"""

import os
import json
import argparse
import logging
import time
from pathlib import Path
from typing import Dict, List, Any, Optional
from tqdm import tqdm
from dotenv import load_dotenv
import openai

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("metadata_generation.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 환경 변수 로드
load_dotenv()

class MetadataGenerator:
    """스트레칭 데이터 메타데이터 생성기"""
    
    def __init__(self, model: str = "gpt-4o-mini"):
        """초기화"""
        self.model = model
        self.client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.batch_size = 10  # 배치 크기 (API 제한에 맞게 조정)
        self.delay = 1  # 요청 간 딜레이 (초)
    
    def create_metadata_prompt(self, exercise: Dict[str, Any], muscle_name: str, muscle_info: Dict[str, Any]) -> str:
        """메타데이터 생성을 위한 프롬프트 생성"""
        
        # 운동 정보 추출
        title = exercise.get('title', '')
        abstract = exercise.get('abstract', '')
        protocol = exercise.get('protocol', {})
        protocol_str = json.dumps(protocol, ensure_ascii=False) if protocol else ""
        
        # 근육 정보 추출
        english_name = muscle_info.get('english', '')
        common_issues = ', '.join(muscle_info.get('common_issues', []))
        occupations = ', '.join(muscle_info.get('occupations', []))
        
        # 프롬프트 생성
        prompt = f"""
        다음 스트레칭/운동 데이터를 분석하여 사용자 맞춤형 추천을 위한 메타데이터를 JSON 형식으로 생성해주세요:
        
        근육명: {muscle_name}
        영문명: {english_name}
        일반적 문제: {common_issues}
        관련 직업군: {occupations}
        
        운동 제목: {title}
        초록: {abstract}
        프로토콜: {protocol_str}
        
        사용자는 이름, 나이, 직업, 근육 부위, 통증 설명, 통증 강도(0-10)를 입력합니다. 이 정보를 바탕으로 적절한 스트레칭을 추천해야 합니다.
        특히 사용자의 통증 설명과 매칭될 수 있는 다양한 표현과 키워드를 포함해주세요.
        
        다음 메타데이터를 포함하세요:
        
        1. 난이도 정보:
           - 난이도_수준: "초급", "중급", "고급" 중 하나
           - 연령대별_적합성: 각 연령대(10대, 20-30대, 40-50대, 60대_이상)별 0-10 점수
           - 체력_수준별_적합성: 각 체력 수준(낮음, 중간, 높음)별 0-10 점수
        
        2. 운동 특성:
           - 운동_유형: 정적 스트레칭, 동적 스트레칭, PNF, 근력 운동 등 구체적 유형
           - 수행_시간: 분 단위로 명시
           - 권장_빈도: 일/주 단위로 명시
           - 권장_세트_및_반복: 구체적인 세트 수와 반복 횟수 또는 유지 시간
        
        3. 효과 및 적용:
           - 주요_효과: 구체적인 효과 목록 (유연성 증가, 통증 감소, 근력 향상 등)
           - 효과_발현_시간: "즉시", "단기(1-2주)", "중기(3-4주)", "장기(1개월 이상)" 중 하나
           - 통증_완화_효과: 통증 유형별(급성_통증, 만성_통증, 근육_긴장, 관절_통증) 0-10 점수
           - 통증_강도별_적합성: 통증 강도(0-3 경미, 4-6 중간, 7-10 심각)별 0-10 적합도 점수
           - 통증_부위별_효과: 신체 부위별 0-10 효과 점수
        
        4. 직업 관련성:
           - 직업별_관련성_점수: 다양한 직업군별 0-10 관련성 점수 (사무직, 서비스직, 육체노동, 운전직, 학생, 프로그래머, 디자이너 등)
           - 직업별_맞춤_수행_시간: 직업별 최적 수행 시간대
           - 업무_환경_적용_방법: 구체적인 적용 방법 설명
           - 직업_관련_증상_개선도: 0-10 점수
        
        5. 생활 패턴 적합성:
           - 좌식_생활자_적합도: 0-10 점수
           - 활동적_생활자_적합도: 0-10 점수
           - 일상_활동_통합_방법: 구체적인 통합 방법
           - 시간대별_효과: 각 시간대별 0-10 효과 점수
        
        6. 안전 및 주의사항:
           - 금기사항: 구체적인 금기 상태나 질환 목록
           - 연령대별_주의사항: 각 연령대별 구체적인 주의사항
           - 수행_시_주의점: 구체적인 주의사항 목록
           - 중단해야_할_신호: 구체적인 경고 신호 목록
           - 통증_유형별_안전도: 각 통증 유형별 0-10 안전도 점수
        
        7. 검색 및 추천용 태그:
           - 증상_관련_태그: 관련 증상 키워드 목록 (최소 10개)
           - 직업_관련_태그: 관련 직업 키워드 목록 (최소 5개)
           - 연령_관련_태그: 관련 연령대 키워드 목록
           - 상황_관련_태그: 관련 상황 키워드 목록 (최소 5개)
           - 효과_관련_태그: 관련 효과 키워드 목록 (최소 8개)
        
        8. 통증 표현 매핑:
           - 통증_표현_사전: 다양한 통증 표현과 그에 해당하는 의학적/전문적 용어를 매핑한 사전
             (예: "찌릿찌릿함" -> "신경통", "뻐근함" -> "근육 긴장", "화끈거림" -> "염증성 통증" 등)
           - 통증_위치_표현: 사용자가 표현할 수 있는 다양한 통증 위치 표현과 해당 근육/부위 매핑
             (예: "목덜미가 아파요" -> "승모근 상부", "어깨가 결려요" -> "삼각근/회전근개" 등)
           - 통증_상황_표현: 통증이 발생하는 상황에 대한 다양한 표현과 관련 활동/자세 매핑
             (예: "컴퓨터 할 때 아파요" -> "장시간 앉은 자세", "물건 들 때 아파요" -> "들어올리기 동작" 등)
           - 통증_강도_표현: 통증 강도를 표현하는 다양한 언어적 표현과 0-10 척도 매핑
             (예: "약간 불편해요" -> 2-3, "참기 힘들어요" -> 7-8 등)
           - 통증_특성_키워드: 통증의 특성을 설명하는 다양한 키워드 목록
             (날카로운, 둔한, 찌릿한, 욱신거리는, 쑤시는, 뻐근한, 당기는, 화끈거리는, 아리는, 저린, 무감각한 등)
        
        9. 사용자_맞춤_정보:
           - 통증_설명별_적합도: 다양한 통증 설명별 0-10 적합도 점수 (최소 15개 이상의 다양한 통증 표현 포함)
           - 통증_지속기간별_효과: 통증 지속 기간(일시적, 단기, 중기, 장기)별 0-10 효과 점수
           - 통증_강도별_권장_변형: 통증 강도(0-3, 4-6, 7-10)별 권장되는 운동 변형 또는 조정 사항
        
        JSON 형식으로만 응답해주세요. 모든 수치는 0-10 사이의 정수로 제공하고, 모든 텍스트 필드는 구체적이고 상세하게 작성하세요.
        특히 통증 표현과 관련된 키워드는 사용자가 일상적으로 사용할 수 있는 다양한 표현을 포함해주세요.
        """
        
        return prompt
    
    def extract_json_from_response(self, response_text: str) -> Dict[str, Any]:
        """응답에서 JSON 추출"""
        try:
            # 응답에서 JSON 부분만 추출
            return json.loads(response_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {str(e)}")
            # 기본 메타데이터 반환
            return {
                "난이도_정보": {
                    "난이도_수준": "중급",
                    "연령대별_적합성": {"10대": 5, "20-30대": 7, "40-50대": 6, "60대_이상": 4},
                    "체력_수준별_적합성": {"낮음": 4, "중간": 7, "높음": 8}
                },
                "운동_특성": {
                    "운동_유형": "정적 스트레칭",
                    "수행_시간": "5-10분",
                    "권장_빈도": "주 3-4회",
                    "권장_세트_및_반복": "3세트 x 30초 유지"
                },
                "효과_및_적용": {
                    "주요_효과": ["유연성 증가", "통증 감소"],
                    "효과_발현_시간": "단기 (1-2주)",
                    "통증_완화_효과": {
                        "급성_통증": 5,
                        "만성_통증": 7,
                        "근육_긴장": 8,
                        "관절_통증": 4
                    },
                    "통증_강도별_적합성": {
                        "0-3_경미": 8,
                        "4-6_중간": 6,
                        "7-10_심각": 3
                    },
                    "통증_부위별_효과": {
                        "목": 6,
                        "어깨": 7,
                        "등": 5,
                        "허리": 4,
                        "무릎": 3,
                        "기타_부위": 4
                    }
                },
                "직업_관련성": {
                    "직업별_관련성_점수": {
                        "사무직": 8,
                        "서비스직": 6,
                        "육체노동": 5,
                        "운전직": 7,
                        "학생": 6,
                        "프로그래머": 8,
                        "디자이너": 7,
                        "기타_직업군": 5
                    },
                    "직업별_맞춤_수행_시간": {
                        "사무직": ["아침", "업무 중 휴식시간", "저녁"],
                        "서비스직": ["업무 전", "취침 전"]
                    },
                    "업무_환경_적용_방법": "사무실 의자에서 간단히 수행 가능",
                    "직업_관련_증상_개선도": 7
                },
                "생활_패턴_적합성": {
                    "좌식_생활자_적합도": 8,
                    "활동적_생활자_적합도": 6,
                    "일상_활동_통합_방법": "업무 중 짧은 휴식 시간에 수행 가능",
                    "시간대별_효과": {
                        "아침": 7,
                        "점심": 6,
                        "저녁": 8,
                        "취침_전": 9
                    }
                },
                "안전_및_주의사항": {
                    "금기사항": ["급성 부상", "심한 염증"],
                    "연령대별_주의사항": {
                        "10대": "성장기 관절에 무리가 가지 않도록 주의",
                        "60대_이상": "균형을 잡기 위한 지지대 사용 권장"
                    },
                    "수행_시_주의점": ["과도한 스트레칭 피하기", "통증이 있을 경우 즉시 중단"],
                    "중단해야_할_신호": ["심한 통증", "어지러움", "숨가쁨"],
                    "통증_유형별_안전도": {
                        "급성_통증": 3,
                        "만성_통증": 7,
                        "근육_긴장": 8,
                        "관절_통증": 5
                    }
                },
                "검색_및_추천용_태그": {
                    "증상_관련_태그": ["목 통증", "어깨 통증", "근육 긴장", "자세 불량", "뻐근함", "결림", "찌릿함", "무감각", "저림", "당김"],
                    "직업_관련_태그": ["사무직", "학생", "컴퓨터 작업자", "프로그래머", "디자이너"],
                    "연령_관련_태그": ["성인", "직장인", "중년", "청년", "노년"],
                    "상황_관련_태그": ["사무실", "재택근무", "장시간 앉기", "운전", "스마트폰 사용"],
                    "효과_관련_태그": ["유연성", "통증 완화", "자세 개선", "근육 이완", "혈액순환", "스트레스 감소", "관절 가동성", "근력 강화"]
                },
                "통증_표현_매핑": {
                    "통증_표현_사전": {
                        "찌릿찌릿함": "신경통",
                        "뻐근함": "근육 긴장",
                        "화끈거림": "염증성 통증",
                        "욱신거림": "박동성 통증",
                        "당김": "근육 경직",
                        "저림": "감각 이상",
                        "결림": "근막 통증",
                        "쑤심": "관절 통증",
                        "무감각함": "신경 압박"
                    },
                    "통증_위치_표현": {
                        "목덜미가 아파요": "승모근 상부",
                        "어깨가 결려요": "삼각근/회전근개",
                        "등 위쪽이 뻐근해요": "승모근/능형근",
                        "허리가 아파요": "척추기립근",
                        "허벅지 안쪽이 당겨요": "내전근"
                    },
                    "통증_상황_표현": {
                        "컴퓨터 할 때 아파요": "장시간 앉은 자세",
                        "물건 들 때 아파요": "들어올리기 동작",
                        "오래 서 있으면 아파요": "정적 자세 유지",
                        "고개 돌릴 때 아파요": "목 회전 동작",
                        "아침에 일어나면 뻣뻣해요": "수면 자세"
                    },
                    "통증_강도_표현": {
                        "약간 불편해요": "2-3",
                        "신경 쓰일 정도예요": "4-5",
                        "꽤 아파요": "6-7",
                        "참기 힘들어요": "7-8",
                        "움직일 수 없을 정도로 아파요": "9-10"
                    },
                    "통증_특성_키워드": [
                        "날카로운", "둔한", "찌릿한", "욱신거리는", "쑤시는", 
                        "뻐근한", "당기는", "화끈거리는", "아리는", "저린", 
                        "무감각한", "결리는", "묵직한", "따끔한", "터질 것 같은"
                    ]
                },
                "사용자_맞춤_정보": {
                    "통증_설명별_적합도": {
                        "찌릿한_통증": 5,
                        "둔한_통증": 7,
                        "뻐근함": 9,
                        "당김": 8,
                        "무감각": 6,
                        "결림": 8,
                        "화끈거림": 4,
                        "쑤심": 6,
                        "저림": 5,
                        "욱신거림": 4,
                        "묵직함": 7,
                        "따끔함": 3,
                        "아림": 5,
                        "터질듯함": 2,
                        "칼로_베는듯함": 3
                    },
                    "통증_지속기간별_효과": {
                        "일시적": 7,
                        "단기": 8,
                        "중기": 7,
                        "장기": 6
                    },
                    "통증_강도별_권장_변형": {
                        "0-3_경미": "기본 형태로 수행",
                        "4-6_중간": "강도를 70%로 줄이고 유지 시간 단축",
                        "7-10_심각": "의사 상담 후 매우 부드럽게 시작하거나 다른 운동 고려"
                    }
                },
                "error": "메타데이터 생성 중 오류 발생"
            }
    
    def generate_metadata_for_exercise(self, exercise: Dict[str, Any], muscle_name: str, muscle_info: Dict[str, Any]) -> Dict[str, Any]:
        """운동 데이터에 대한 메타데이터 생성"""
        try:
            prompt = self.create_metadata_prompt(exercise, muscle_name, muscle_info)
            
            # OpenAI API 호출
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,  # 일관된 결과를 위해 낮은 temperature 사용
                response_format={"type": "json_object"}
            )
            
            # 응답에서 JSON 추출
            metadata = self.extract_json_from_response(response.choices[0].message.content)
            return metadata
            
        except Exception as e:
            logger.error(f"메타데이터 생성 중 오류 발생: {str(e)}")
            return {
                "error": f"메타데이터 생성 중 오류 발생: {str(e)}"
            }
    
    def process_muscle_data(self, data: Dict[str, Any], limit: Optional[int] = None) -> Dict[str, Any]:
        """근육 데이터 처리 및 메타데이터 생성"""
        enhanced_data = data.copy()
        total_processed = 0
        
        # 모든 근육 데이터 처리
        for muscle_name, muscle_data in tqdm(enhanced_data["muscles"].items(), desc="근육 처리 중"):
            muscle_info = muscle_data["info"]
            exercises = muscle_data.get("exercises", [])
            
            # 운동 데이터 처리
            for i, exercise in enumerate(tqdm(exercises, desc=f"{muscle_name} 운동 처리 중", leave=False)):
                # 처리 항목 수 제한 확인
                if limit and total_processed >= limit:
                    break
                
                # 메타데이터 생성
                metadata = self.generate_metadata_for_exercise(exercise, muscle_name, muscle_info)
                exercise["enhanced_metadata"] = metadata
                
                total_processed += 1
                
                # 배치 처리를 위한 딜레이
                if (i + 1) % self.batch_size == 0:
                    logger.info(f"{muscle_name}: {i+1}/{len(exercises)} 운동 처리 완료")
                    time.sleep(self.delay)
            
            # 처리 항목 수 제한 확인
            if limit and total_processed >= limit:
                logger.info(f"제한된 항목 수 ({limit}개) 처리 완료")
                break
        
        # 메타데이터 업데이트
        enhanced_data["metadata"]["enhanced_date"] = time.strftime("%Y-%m-%dT%H:%M:%S")
        enhanced_data["metadata"]["enhanced_items"] = total_processed
        enhanced_data["metadata"]["enhancement_model"] = self.model
        
        return enhanced_data

def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="스트레칭 데이터 메타데이터 생성 스크립트")
    parser.add_argument("--input", required=True, help="입력 파일 경로")
    parser.add_argument("--output", required=True, help="출력 파일 경로")
    parser.add_argument("--limit", type=int, help="처리할 최대 항목 수")
    parser.add_argument("--model", default="gpt-4o-mini", help="사용할 OpenAI 모델")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    # 입력 파일 확인
    if not input_path.exists():
        logger.error(f"입력 파일이 존재하지 않습니다: {input_path}")
        return
    
    # 출력 디렉토리 생성
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 데이터 로드
    logger.info(f"데이터 로드 중: {input_path}")
    with open(input_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 메타데이터 생성기 초기화
    generator = MetadataGenerator(model=args.model)
    
    # 데이터 처리
    logger.info("메타데이터 생성 시작")
    enhanced_data = generator.process_muscle_data(data, args.limit)
    
    # 결과 저장
    logger.info(f"결과 저장 중: {output_path}")
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(enhanced_data, f, ensure_ascii=False, indent=2)
    
    logger.info("메타데이터 생성 완료")

if __name__ == "__main__":
    main() 