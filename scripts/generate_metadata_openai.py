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
        self.batch_size = 10 
        self.delay = 1 
    
    def determine_prompt_type(self, exercise: Dict[str, Any]) -> str:
        """논문 내용에 따라 적절한 프롬프트 유형 결정
        
        Args:
            exercise: 운동/스트레칭 데이터
            
        Returns:
            str: "protocol_based" 또는 "content_based"
        """
        # 프로토콜 정보 확인
        protocol = exercise.get('protocol', {})
        steps = protocol.get('steps', [])
        
        # 초록 내용 분석
        abstract = exercise.get('abstract', '').lower()
        title = exercise.get('title', '').lower()
        
        # 스트레칭 관련 키워드
        stretching_keywords = [
            "stretching exercise", "스트레칭 운동", "stretch protocol", 
            "stretching method", "stretching technique", "perform stretch",
            "held for", "seconds", "repetitions", "유지", "반복", "스트레칭",
            "신장", "운동", "exercise", "protocol", "stretch", "hold"
        ]
        
        # 스트레칭 프로토콜 포함 여부 판단
        has_protocol = False
        
        # 1. 구체적인 단계가 있는지 확인
        if len(steps) >= 2:
            for step in steps:
                if isinstance(step, str) and any(keyword in step.lower() for keyword in stretching_keywords):
                    has_protocol = True
                    logger.info(f"프로토콜 단계에서 스트레칭 키워드 발견: {step[:50]}...")
                    break
        
        # 2. 제목에 스트레칭 관련 키워드가 있는지 확인
        if not has_protocol:
            if any(keyword in title for keyword in stretching_keywords):
                has_protocol = True
                logger.info(f"제목에서 스트레칭 키워드 발견: {title}")
        
        # 3. 초록에 스트레칭 방법 관련 내용이 있는지 확인
        if not has_protocol:
            protocol_indicators = [
                "performed for", "maintained for", "held for", 
                "stretch position", "seconds", "minutes", "sets", "repetitions",
                "protocol consisted of", "exercise protocol", "stretching protocol",
                "초 동안", "분 동안", "세트", "반복", "유지", "스트레칭 방법", "운동 방법"
            ]
            if any(indicator in abstract for indicator in protocol_indicators):
                has_protocol = True
                logger.info(f"초록에서 프로토콜 지표 발견")
        
        prompt_type = "protocol_based" if has_protocol else "content_based"
        logger.info(f"결정된 프롬프트 유형: {prompt_type}")
        return prompt_type
    
    def create_protocol_based_prompt(self, exercise: Dict[str, Any], muscle_name: str, muscle_info: Dict[str, Any]) -> str:
        """프로토콜 기반 메타데이터 생성을 위한 프롬프트 생성
        
        Args:
            exercise: 운동/스트레칭 데이터
            muscle_name: 근육 이름
            muscle_info: 근육 정보
            
        Returns:
            str: 프롬프트 문자열
        """
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
        당신은 과학적 근거에 기반한 스트레칭 전문가입니다. 다음 학술 논문에 포함된 스트레칭 프로토콜을 분석하고 
        확장하여 사용자 맞춤형 정보를 제공해주세요.
        
        [논문 정보]
        제목: {title}
        초록: {abstract}
        기존 프로토콜: {protocol_str}
        
        [대상 근육 정보]
        근육명: {muscle_name} ({english_name})
        일반적 문제: {common_issues}
        관련 직업군: {occupations}
        
        이 논문에 포함된 스트레칭 프로토콜을 기반으로, 다음 정보를 JSON 형식으로 제공해주세요:
        
        1. 프로토콜_분석:
           - 논문_제공_프로토콜: 논문에서 직접 설명한 스트레칭 방법 요약
           - 과학적_근거: 이 프로토콜의 효과성에 대한 논문의 근거 요약
           - 대상_조건: 논문에서 이 프로토콜을 적용한 대상/조건
        
        2. 스트레칭_상세화:
           - 시작_자세: 명확한 시작 자세 설명
           - 동작_단계: 단계별 상세 지침 (최소 5단계)
           - 호흡_패턴: 각 단계별 호흡법
           - 느껴야_할_감각: 올바른 수행 시 느껴야 할 감각
           - 시각적_큐: 정확한 자세를 위한 시각적 참고점
        
        3. 난이도_정보:
           - 난이도_수준: "초급", "중급", "고급" 중 하나
           - 연령대별_적합성: 각 연령대(10대, 20-30대, 40-50대, 60대_이상)별 0-10 점수
           - 체력_수준별_적합성: 각 체력 수준(낮음, 중간, 높음)별 0-10 점수
        
        4. 실행_가이드라인:
           - 권장_시간: 유지 시간
           - 권장_횟수: 반복 횟수
           - 권장_빈도: 일/주 단위 실행 빈도
           - 강도_조절_방법: 강도 조절법
           - 진행_방식: 초보자→고급자 진행 경로
        
        5. 효과_및_적용:
           - 주요_효과: 구체적인 효과 목록 (유연성 증가, 통증 감소, 근력 향상 등)
           - 효과_발현_시간: "즉시", "단기(1-2주)", "중기(3-4주)", "장기(1개월 이상)" 중 하나
           - 통증_완화_효과: 통증 유형별(급성_통증, 만성_통증, 근육_긴장, 관절_통증) 0-10 점수
           - 통증_강도별_적합성: 통증 강도(0-3 경미, 4-6 중간, 7-10 심각)별 0-10 적합도 점수
        
        6. 직업_관련성:
           - 직업별_관련성_점수: 다양한 직업군별 0-10 관련성 점수 (사무직, 서비스직, 육체노동, 운전직, 학생, 프로그래머, 디자이너 등)
           - 업무_환경_적용_방법: 구체적인 적용 방법 설명
           - 직업_관련_증상_개선도: 0-10 점수
        
        7. 생활_패턴_적합성:
           - 좌식_생활자_적합도: 0-10 점수
           - 활동적_생활자_적합도: 0-10 점수
           - 일상_활동_통합_방법: 구체적인 통합 방법
        
        8. 안전_및_주의사항:
           - 금기사항: 구체적인 금기 상태나 질환 목록
           - 수행_시_주의점: 구체적인 주의사항 목록
           - 중단해야_할_신호: 구체적인 경고 신호 목록
        
        9. 검색_및_추천용_태그:
           - 증상_관련_태그: 관련 증상 키워드 목록 (최소 5개)
           - 직업_관련_태그: 관련 직업 키워드 목록 (최소 5개)
           - 상황_관련_태그: 관련 상황 키워드 목록 (최소 5개)
           - 효과_관련_태그: 관련 효과 키워드 목록 (최소 8개)
        
        10. 통증_표현_매핑:
            - 통증_표현_사전: 다양한 통증 표현과 그에 해당하는 의학적/전문적 용어를 매핑한 사전
              (예: "찌릿찌릿함" -> "신경통", "뻐근함" -> "근육 긴장", "화끈거림" -> "염증성 통증" 등)
            - 통증_특성_키워드: 통증의 특성을 설명하는 다양한 키워드 목록
        
        11. 사용자_맞춤_정보:
            - 통증_설명별_적합도: 다양한 통증 설명별 0-10 적합도 점수 (최소 15개 이상의 다양한 통증 표현 포함)
            - 통증_지속기간별_효과: 통증 지속 기간(일시적, 단기, 중기, 장기)별 0-10 효과 점수
            - 통증_강도별_권장_변형: 통증 강도(0-3, 4-6, 7-10)별 권장되는 운동 변형 또는 조정 사항
        
        JSON 형식으로만 응답해주세요. 모든 수치는 0-10 사이의 정수로 제공하고, 모든 텍스트 필드는 구체적이고 상세하게 작성하세요.
        특히 통증 표현과 관련된 키워드는 사용자가 일상적으로 사용할 수 있는 다양한 표현을 포함해주세요.
        """
        
        return prompt
    
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
           - 업무_환경_적용_방법: 구체적인 적용 방법 설명
           - 직업_관련_증상_개선도: 0-10 점수
        
        5. 생활 패턴 적합성:
           - 좌식_생활자_적합도: 0-10 점수
           - 활동적_생활자_적합도: 0-10 점수
           - 일상_활동_통합_방법: 구체적인 통합 방법
        
        6. 안전 및 주의사항:
           - 금기사항: 구체적인 금기 상태나 질환 목록
           - 수행_시_주의점: 구체적인 주의사항 목록
           - 중단해야_할_신호: 구체적인 경고 신호 목록
        
        7. 검색 및 추천용 태그:
           - 증상_관련_태그: 관련 증상 키워드 목록 (최소 5개)
           - 직업_관련_태그: 관련 직업 키워드 목록 (최소 5개)
           - 상황_관련_태그: 관련 상황 키워드 목록 (최소 5개)
           - 효과_관련_태그: 관련 효과 키워드 목록 (최소 8개)
        
        8. 통증 표현 매핑:
           - 통증_표현_사전: 다양한 통증 표현과 그에 해당하는 의학적/전문적 용어를 매핑한 사전
             (예: "찌릿찌릿함" -> "신경통", "뻐근함" -> "근육 긴장", "화끈거림" -> "염증성 통증" 등)
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
                    "업무_환경_적용_방법": "사무실 의자에서 간단히 수행 가능",
                    "직업_관련_증상_개선도": 7
                },
                "생활_패턴_적합성": {
                    "좌식_생활자_적합도": 8,
                    "활동적_생활자_적합도": 6,
                    "일상_활동_통합_방법": "업무 중 짧은 휴식 시간에 수행 가능"
                },
                "안전_및_주의사항": {
                    "금기사항": ["급성 부상", "심한 염증"],
                    "수행_시_주의점": ["과도한 스트레칭 피하기", "통증이 있을 경우 즉시 중단"],
                    "중단해야_할_신호": ["심한 통증", "어지러움", "숨가쁨"]
                },
                "검색_및_추천용_태그": {
                    "증상_관련_태그": ["목 통증", "어깨 통증", "근육 긴장", "자세 불량", "뻐근함", "결림", "찌릿함", "무감각", "저림", "당김"],
                    "직업_관련_태그": ["사무직", "학생", "컴퓨터 작업자", "프로그래머", "디자이너"],
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
            # 프롬프트 유형 결정
            prompt_type = self.determine_prompt_type(exercise)
            
            # 기본 프롬프트 생성
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
            
            # 메타데이터에 생성 방식 추가
            metadata["생성_방식"] = prompt_type
            
            return metadata
            
        except Exception as e:
            logger.error(f"메타데이터 생성 중 오류 발생: {str(e)}")
            return {
                "error": f"메타데이터 생성 중 오류 발생: {str(e)}",
                "생성_방식": "error"
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