import os
from dotenv import load_dotenv
import logging
from datetime import datetime
import requests
import re

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'stretching_test_{datetime.now().strftime("%Y%m%d")}.log'),
        logging.StreamHandler()
    ]
)

# 환경 변수 로드
load_dotenv()

class StretchingClassifier:
    def __init__(self):
        self.api_key = os.getenv("ELICE_API_KEY")
        self.base_url = "https://api-cloud-function.elice.io/8d0fbc41-2edd-4525-8af7-25a6f429ad11/check"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
    def classify_text(self, text: str) -> dict:
        """텍스트의 스트레칭 관련성을 판단"""
        try:
            # 키워드 기반 1차 필터링
            stretching_keywords = [
                "스트레칭", "stretching", "신장", "유연성", "가동성", "flexibility",
                "mobility", "근육", "관절", "자세", "신전", "이완", "신장성",
                "ROM", "가동범위", "관절가동범위", "근막", "fascia",
                "근육신장", "muscle stretching", "관절가동", "joint mobility",
                "유연성운동", "flexibility exercise", "동적스트레칭", "정적스트레칭",
                "PNF", "proprioceptive", "신경근", "neuromuscular"
            ]
            
            # 키워드가 포함된 경우 문맥 분석
            has_keyword = any(keyword in text.lower() for keyword in stretching_keywords)
            if has_keyword:
                found_keywords = [kw for kw in stretching_keywords if kw in text.lower()]
                logging.info(f"발견된 키워드: {', '.join(found_keywords)}")
            
            response = requests.post(
                self.base_url,
                headers=self.headers,
                json={
                    "document": self._get_context(),
                    "claim": text
                },
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            
            is_supported = result.get("supported", False)
            confidence = result.get("confidence", 0.0)
            
            # API 응답 상세 로깅
            logging.info(f"API 응답 - supported: {is_supported}, confidence: {confidence:.2f}")
            
            # 새로운 판단 로직
            if has_keyword:
                if confidence < 0.95:  # 매우 높은 신뢰도가 아니면
                    is_stretching_related = True
                    classification = "keyword_based"
                    logging.info(f"키워드 존재, 낮은 API 신뢰도로 스트레칭 관련 판단 (신뢰도: {confidence:.2f})")
                else:
                    # 매우 높은 신뢰도에서도 문맥 확인
                    context_related = self._check_keyword_context(text)
                    is_stretching_related = context_related
                    classification = "high_confidence_with_context"
                    logging.info(f"키워드 존재, 높은 신뢰도, 문맥 분석 결과: {context_related} (신뢰도: {confidence:.2f})")
            elif confidence >= 0.95:
                is_stretching_related = is_supported
                classification = "api_based"
                logging.info(f"키워드 없음, 매우 높은 신뢰도로 API 판단 채택 (신뢰도: {confidence:.2f})")
            else:
                # 키워드도 없고 신뢰도도 낮으면 문맥 분석
                is_stretching_related = self._analyze_context(text)
                classification = "context_based"
                logging.info(f"키워드 없음, 낮은 신뢰도, 문맥 분석 결과: {is_stretching_related} (신뢰도: {confidence:.2f})")
            
            return {
                "text": text,
                "is_stretching_related": is_stretching_related,
                "confidence": confidence,
                "classification": classification,
                "api_supported": is_supported,
                "has_keyword": has_keyword,
                "found_keywords": found_keywords if has_keyword else []
            }
            
        except Exception as e:
            logging.error(f"API 호출 오류: {str(e)}")
            return {
                "text": text,
                "is_stretching_related": False,
                "confidence": 0.0,
                "classification": "error",
                "error": str(e)
            }
    
    def _check_keyword_context(self, text: str) -> bool:
        """키워드가 있을 때 문맥 확인"""
        positive_patterns = [
            r"(스트레칭|stretching).*(효과|영향|방법|프로그램)",
            r"(근육|muscle).*(신장|늘리기|flexibility)",
            r"(운동|exercise).*(스트레칭|stretching)",
            r"(유연성|flexibility).*(향상|개선|증가)",
            r"(mobility|가동성).*(exercise|운동)",
            r"(rehabilitation|재활).*(program|프로그램)"
        ]
        return any(re.search(pattern, text, re.I) for pattern in positive_patterns)
    
    def _analyze_context(self, text: str) -> bool:
        """전반적인 문맥 분석"""
        related_terms = [
            r"(flexibility|유연성).*(improvement|향상|증가)",
            r"(mobility|가동성).*(exercise|운동)",
            r"(rehabilitation|재활).*(program|프로그램)",
            r"(muscle|근육).*(elongation|신장|늘리기)",
            r"(joint|관절).*(range|가동|움직임)",
            r"(posture|자세).*(correction|교정|개선)"
        ]
        return any(re.search(pattern, text, re.I) for pattern in related_terms)
            
    def _get_context(self) -> str:
        """스트레칭 관련 컨텍스트"""
        return """
        스트레칭은 다음과 같은 상황에서 사용됩니다:
        
        1. 직접적인 스트레칭 운동
        - 근육 신장 운동
        - 유연성 향상 운동
        - 관절 가동성 운동
        
        2. 운동의 일부로서의 스트레칭
        - 운동 전후 준비/정리
        - 재활 운동의 일부
        - 자세 교정 운동의 구성요소
        - 필라테스나 요가의 동작 요소
        
        3. 연구/실험에서의 스트레칭
        - 스트레칭 효과 연구
        - 근육/관절 관련 실험의 요소
        - 운동 프로그램의 구성 요소
        - 재활 프로토콜의 일부
        
        4. 치료적 스트레칭
        - 물리치료의 일환
        - 재활 치료 과정
        - 통증 관리 방법
        - 자세 교정 요법
        """

def test_classifier():
    """다양한 케이스로 분류기를 테스트"""
    classifier = StretchingClassifier()
    
    test_cases = [
        # 명확한 스트레칭 관련 텍스트
        "정적 스트레칭은 근육을 천천히 늘려 15-30초 동안 유지하는 방법입니다.",
        "대흉근 스트레칭은 어깨 통증과 자세 개선에 도움이 됩니다.",
        
        # 애매한 케이스
        "근육의 긴장을 풀어주는 운동이 필요합니다.",
        "자세 교정을 위한 운동 방법을 찾고 있습니다.",
        
        # 스트레칭과 무관한 텍스트
        "단백질 보충제는 근육 회복에 도움이 됩니다.",
        "고강도 인터벌 트레이닝은 효과적인 유산소 운동입니다."
    ]
    
    logging.info("=== 스트레칭 분류 테스트 시작 ===")
    
    for text in test_cases:
        result = classifier.classify_text(text)
        logging.info(f"\n텍스트: {text}")
        logging.info(f"스트레칭 관련: {result['is_stretching_related']}")
        logging.info(f"신뢰도: {result['confidence']:.2f}")
        logging.info(f"API 판단: {result['api_supported']}")
        logging.info(f"최종 분류: {result['classification']}")
        logging.info("-" * 50)
    
    logging.info("\n=== 테스트 완료 ===")

if __name__ == "__main__":
    test_classifier() 