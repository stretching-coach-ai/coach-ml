"""
자세 교정 및 스트레칭 데이터 수집 크롤러

이 스크립트는 다음 소스에서 자세 교정 및 스트레칭 관련 데이터를 수집합니다:
- JOSPT (Journal of Orthopedic & Sports Physical Therapy)
- PEDro (Physiotherapy Evidence Database)
- PubMed (스트레칭/자세 교정 관련 논문)
- APTA (American Physical Therapy Association)

수집된 데이터는 JSON 형식으로 저장되며, 각 운동/스트레칭에 대한 상세 프로토콜과
과학적 근거를 포함합니다.

사용법:
    python muscle_data_crawler.py --output <output_dir> [--limit <max_items>]

예시:
    python muscle_data_crawler.py --output ./data/raw --limit 1000
"""

import os
import sys
import json
import asyncio
import aiohttp
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
import re
from urllib.parse import urljoin
from tqdm import tqdm
import argparse

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("stretching_crawler.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# 근육 카테고리 및 관련 정보
MUSCLE_CATEGORIES = {
    "목": {
        "muscles": ["흉쇄유돌근", "승모근"],
        "common_issues": ["거북목", "목 통증", "목 뻐근함"],
        "occupations": ["사무직", "학생", "운전기사"],
        "stretches": ["목 스트레칭", "자세 교정 운동", "근력 강화 운동"],
        "keywords": [
            "neck posture correction",
            "cervical stretching exercises",
            "forward head posture",
            "neck pain exercises",
            "office worker neck stretches"
        ]
    },
    "어깨": {
        "muscles": ["삼각근", "승모근", "광배근"],
        "common_issues": ["어깨 통증", "둥근 어깨", "오십견"],
        "occupations": ["사무직", "프로그래머", "디자이너"],
        "stretches": ["어깨 스트레칭", "자세 교정 운동", "가동성 운동"],
        "keywords": [
            "shoulder posture exercises",
            "rounded shoulder correction",
            "desk worker shoulder stretches",
            "shoulder mobility exercises",
            "programmer shoulder routine"
        ]
    },
    "허리": {
        "muscles": ["복직근", "외복사근", "척추기립근"],
        "common_issues": ["허리 통증", "디스크", "요통"],
        "occupations": ["사무직", "서비스직", "제조업"],
        "stretches": ["허리 스트레칭", "코어 강화 운동", "자세 교정"],
        "keywords": [
            "lower back stretching",
            "core strengthening exercises",
            "office worker back pain",
            "posture correction exercises",
            "ergonomic back stretches"
        ]
    },
    "무릎": {
        "muscles": ["대퇴직근", "내전근", "외전근"],
        "common_issues": ["무릎 통증", "관절염", "연골 손상"],
        "occupations": ["서비스직", "판매직", "운동선수"],
        "stretches": ["무릎 스트레칭", "하체 강화 운동", "관절 가동성"],
        "keywords": [
            "knee mobility exercises",
            "standing worker knee stretches",
            "leg strengthening routine",
            "knee pain relief exercises",
            "joint mobility protocol"
        ]
    }
}

# 전면 근육 정의
FRONT_MUSCLES = {
    "대흉근": {
        "english": "pectoralis major",
        "keywords_ko": ["대흉근 스트레칭", "가슴 스트레칭", "가슴 운동", "자세교정"],
        "keywords_en": ["pectoralis major stretching", "chest stretching", "posture correction"],
        "common_issues": ["라운드숄더", "거북목", "가슴 통증"],
        "occupations": ["사무직", "학생", "프로그래머"]
    },
    "흉쇄유돌근": {
        "english": "sternocleidomastoid",
        "keywords_ko": ["흉쇄유돌근 스트레칭", "목 스트레칭", "거북목 교정"],
        "keywords_en": ["sternocleidomastoid stretching", "neck stretching", "forward head posture"],
        "common_issues": ["거북목", "목 통증", "두통"],
        "occupations": ["사무직", "학생", "운전기사"]
    },
    "복직근": {
        "english": "rectus abdominis",
        "keywords_ko": ["복직근 스트레칭", "복부 스트레칭", "코어 운동"],
        "keywords_en": ["rectus abdominis stretching", "abdominal stretching", "core exercise"],
        "common_issues": ["허리 통증", "자세 불균형"],
        "occupations": ["사무직", "운동선수"]
    },
    "외복사근": {
        "english": "external oblique",
        "keywords_ko": ["외복사근 스트레칭", "옆구리 스트레칭", "허리 통증"],
        "keywords_en": ["external oblique stretching", "side stretching", "waist pain"],
        "common_issues": ["허리 통증", "측면 통증"],
        "occupations": ["사무직", "서비스직"]
    },
    "내전근": {
        "english": "adductor muscles",
        "keywords_ko": ["내전근 스트레칭", "허벅지 안쪽 스트레칭"],
        "keywords_en": ["adductor stretching", "inner thigh stretching"],
        "common_issues": ["사타구니 통증", "허벅지 통증"],
        "occupations": ["운동선수", "서비스직"]
    },
    "대퇴직근": {
        "english": "rectus femoris",
        "keywords_ko": ["대퇴직근 스트레칭", "허벅지 앞쪽 스트레칭"],
        "keywords_en": ["rectus femoris stretching", "quadriceps stretching"],
        "common_issues": ["무릎 통증", "허벅지 통증"],
        "occupations": ["운동선수", "서비스직"]
    },
    "외측광근": {
        "english": "vastus lateralis",
        "keywords_ko": ["외측광근 스트레칭", "허벅지 바깥쪽 스트레칭"],
        "keywords_en": ["vastus lateralis stretching", "outer thigh stretching"],
        "common_issues": ["무릎 통증", "IT밴드 증후군"],
        "occupations": ["운동선수", "서비스직"]
    },
    "내측광근": {
        "english": "vastus medialis",
        "keywords_ko": ["내측광근 스트레칭", "허벅지 안쪽 스트레칭"],
        "keywords_en": ["vastus medialis stretching", "inner thigh stretching"],
        "common_issues": ["무릎 통증", "슬개골 불안정"],
        "occupations": ["운동선수", "서비스직"]
    },
    "봉공근": {
        "english": "sartorius",
        "keywords_ko": ["봉공근 스트레칭", "허벅지 스트레칭"],
        "keywords_en": ["sartorius stretching", "thigh stretching"],
        "common_issues": ["고관절 통증", "무릎 통증"],
        "occupations": ["운동선수", "무용수"]
    },
    "전경골근": {
        "english": "tibialis anterior",
        "keywords_ko": ["전경골근 스트레칭", "정강이 스트레칭"],
        "keywords_en": ["tibialis anterior stretching", "shin stretching"],
        "common_issues": ["정강이 통증", "발목 통증"],
        "occupations": ["운동선수", "서비스직"]
    }
}

# 후면 근육 정의
BACK_MUSCLES = {
    "대둔근": {
        "english": "gluteus maximus",
        "keywords_ko": ["대둔근 스트레칭", "엉덩이 스트레칭"],
        "keywords_en": ["gluteus maximus stretching", "glute stretching"],
        "common_issues": ["좌골신경통", "허리 통증"],
        "occupations": ["사무직", "운전기사"]
    },
    "광배근": {
        "english": "latissimus dorsi",
        "keywords_ko": ["광배근 스트레칭", "등 스트레칭"],
        "keywords_en": ["latissimus dorsi stretching", "back stretching"],
        "common_issues": ["어깨 통증", "등 통증"],
        "occupations": ["사무직", "운동선수"]
    },
    "단두": {
        "english": "biceps brachii short head",
        "keywords_ko": ["이두근 스트레칭", "팔 스트레칭"],
        "keywords_en": ["biceps stretching", "arm stretching"],
        "common_issues": ["팔꿈치 통증", "어깨 통증"],
        "occupations": ["사무직", "육체노동자"]
    },
    "장두": {
        "english": "biceps brachii long head",
        "keywords_ko": ["이두근 스트레칭", "팔 스트레칭"],
        "keywords_en": ["biceps stretching", "arm stretching"],
        "common_issues": ["팔꿈치 통증", "어깨 통증"],
        "occupations": ["사무직", "육체노동자"]
    },
    "비복근": {
        "english": "gastrocnemius",
        "keywords_ko": ["비복근 스트레칭", "종아리 스트레칭"],
        "keywords_en": ["gastrocnemius stretching", "calf stretching"],
        "common_issues": ["종아리 통증", "아킬레스건 통증"],
        "occupations": ["서비스직", "운동선수"]
    },
    "반건양근": {
        "english": "semitendinosus",
        "keywords_ko": ["반건양근 스트레칭", "햄스트링 스트레칭"],
        "keywords_en": ["semitendinosus stretching", "hamstring stretching"],
        "common_issues": ["허벅지 뒤쪽 통증", "좌골신경통"],
        "occupations": ["사무직", "운동선수"]
    },
    "삼각근": {
        "english": "deltoid",
        "keywords_ko": ["삼각근 스트레칭", "어깨 스트레칭"],
        "keywords_en": ["deltoid stretching", "shoulder stretching"],
        "common_issues": ["어깨 통증", "어깨 충돌 증후군"],
        "occupations": ["사무직", "육체노동자"]
    },
    "삼두근": {
        "english": "triceps brachii",
        "keywords_ko": ["삼두근 스트레칭", "팔 뒤쪽 스트레칭"],
        "keywords_en": ["triceps stretching", "back arm stretching"],
        "common_issues": ["팔꿈치 통증", "어깨 통증"],
        "occupations": ["사무직", "육체노동자"]
    },
    "전완근": {
        "english": "forearm muscles",
        "keywords_ko": ["전완근 스트레칭", "손목 스트레칭"],
        "keywords_en": ["forearm stretching", "wrist stretching"],
        "common_issues": ["손목 통증", "테니스 엘보"],
        "occupations": ["사무직", "프로그래머"]
    },
    "승모근": {
        "english": "trapezius",
        "keywords_ko": ["승모근 스트레칭", "목 어깨 스트레칭"],
        "keywords_en": ["trapezius stretching", "neck shoulder stretching"],
        "common_issues": ["목 통증", "어깨 통증", "두통"],
        "occupations": ["사무직", "학생"]
    },
    "내전근": {
        "english": "adductor muscles",
        "keywords_ko": ["내전근 스트레칭", "허벅지 안쪽 스트레칭"],
        "keywords_en": ["adductor stretching", "inner thigh stretching"],
        "common_issues": ["사타구니 통증", "허벅지 통증"],
        "occupations": ["운동선수", "서비스직"]
    }
}

# 모든 근육 목록
ALL_MUSCLES = {**FRONT_MUSCLES, **BACK_MUSCLES}

class StretchingDataCrawler:
    """자세 교정 및 스트레칭 데이터 크롤러"""
    
    def __init__(self, output_dir: Path, max_items: int = None):
        """초기화"""
        self.output_dir = output_dir
        self.max_items = max_items
        self.session = None
        self.collected_data = {muscle: [] for muscle in ALL_MUSCLES.keys()}
        
        # 크롤링 설정
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
        self.delay = 1  # 요청 간 딜레이 (초)
        
        # API 엔드포인트
        self.endpoints = {
            "jospt": "https://www.jospt.org/action/doSearch",
            "pedro": "https://pedro.org.au/english/search-results",
            "pubmed": "https://eutils.ncbi.nlm.nih.gov/entrez/eutils",
            "apta": "https://www.apta.org/search",
            "kmbase": "https://kmbase.medric.or.kr/Search.aspx",
            "koreamed": "https://koreamed.org/search/search.php"
        }
    
    async def init_session(self):
        """HTTP 세션 초기화"""
        if not self.session:
            self.session = aiohttp.ClientSession(headers=self.headers)
    
    async def close_session(self):
        """HTTP 세션 종료"""
        if self.session:
            await self.session.close()
            self.session = None
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정제"""
        if not text:
            return ""
        text = re.sub(r'<[^>]+>', ' ', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    async def crawl_muscle(self, muscle_name: str) -> List[Dict[str, Any]]:
        """특정 근육에 대한 데이터 수집"""
        results = []
        muscle_info = ALL_MUSCLES[muscle_name]
        
        # 영문 키워드로 PubMed 검색
        for keyword in muscle_info["keywords_en"]:
            search_query = f"{muscle_info['english']} AND {keyword}"
            pubmed_results = await self.crawl_pubmed_for_muscle(muscle_name, search_query)
            results.extend(pubmed_results)
        
        # 한글 키워드로 KoreaMed 검색
        for keyword in muscle_info["keywords_ko"]:
            search_query = f"{muscle_name} {keyword}"
            koreamed_results = await self.crawl_koreamed_for_muscle(muscle_name, search_query)
            results.extend(koreamed_results)
        
        # JOSPT 검색
        for keyword in muscle_info["keywords_en"]:
            search_query = f"{muscle_info['english']} {keyword}"
            jospt_results = await self.crawl_jospt_for_muscle(muscle_name, search_query)
            results.extend(jospt_results)
        
        return results
    
    async def crawl_pubmed_for_muscle(self, muscle_name: str, search_query: str) -> List[Dict[str, Any]]:
        """PubMed에서 특정 근육 관련 데이터 검색"""
        results = []
        
        try:
            # 검색 요청
            search_url = f"{self.endpoints['pubmed']}/esearch.fcgi"
            search_params = {
                "db": "pubmed",
                "term": f"{search_query} AND (exercise OR stretching OR rehabilitation)",
                "retmax": "10",
                "format": "json"
            }
            
            async with self.session.get(search_url, params=search_params) as response:
                if response.status == 200:
                    data = await response.json()
                    ids = data.get("esearchresult", {}).get("idlist", [])
                    
                    # 검색된 논문 상세 정보 수집
                    for pmid in ids:
                        fetch_url = f"{self.endpoints['pubmed']}/efetch.fcgi"
                        fetch_params = {
                            "db": "pubmed",
                            "id": pmid,
                            "retmode": "xml"
                        }
                        
                        async with self.session.get(fetch_url, params=fetch_params) as fetch_response:
                            if fetch_response.status == 200:
                                content = await fetch_response.text()
                                soup = BeautifulSoup(content, 'xml')
                                
                                # 논문 정보 추출
                                title = self._clean_text(soup.find('ArticleTitle').text if soup.find('ArticleTitle') else "")
                                abstract = self._clean_text(soup.find('Abstract').text if soup.find('Abstract') else "")
                                
                                if title and abstract:
                                    # 프로토콜 정보 추출 시도
                                    protocol = self._extract_protocol_from_abstract(abstract)
                                    
                                    results.append({
                                        "source": "pubmed",
                                        "muscle": muscle_name,
                                        "title": title,
                                        "abstract": abstract,
                                        "protocol": protocol,
                                        "evidence": {
                                            "pmid": pmid,
                                            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/",
                                            "publication_date": self._extract_publication_date(soup)
                                        },
                                        "timestamp": datetime.now().isoformat()
                                    })
                        
                        await asyncio.sleep(self.delay)
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.error(f"PubMed 검색 중 오류 발생 ({muscle_name}): {str(e)}")
        
        return results
    
    async def crawl_koreamed_for_muscle(self, muscle_name: str, search_query: str) -> List[Dict[str, Any]]:
        """KoreaMed에서 특정 근육 관련 데이터 검색"""
        results = []
        
        try:
            # 검색 요청
            search_params = {
                "q": search_query,
                "sort": "relevance"
            }
            
            async with self.session.get(self.endpoints["koreamed"], params=search_params) as response:
                if response.status == 200:
                    content = await response.text()
                    soup = BeautifulSoup(content, 'html.parser')
                    
                    # 검색 결과 처리
                    for article in soup.select('.articleList'):
                        title_elem = article.select_one('.articleTitle')
                        if not title_elem:
                            continue
                            
                        title = self._clean_text(title_elem.text)
                        abstract_elem = article.select_one('.abstract')
                        abstract = self._clean_text(abstract_elem.text) if abstract_elem else ""
                        
                        if title:
                            # 프로토콜 정보 추출 시도
                            protocol = self._extract_protocol_from_abstract(abstract) if abstract else {}
                            
                            results.append({
                                "source": "koreamed",
                                "muscle": muscle_name,
                                "title": title,
                                "abstract": abstract,
                                "protocol": protocol,
                                "url": urljoin(self.endpoints["koreamed"], title_elem.get('href', '')),
                                "timestamp": datetime.now().isoformat()
                            })
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.error(f"KoreaMed 검색 중 오류 발생 ({muscle_name}): {str(e)}")
        
        return results
    
    async def crawl_jospt_for_muscle(self, muscle_name: str, search_query: str) -> List[Dict[str, Any]]:
        """JOSPT에서 특정 근육 관련 데이터 검색"""
        results = []
        
        try:
            search_params = {
                "query": search_query,
                "content-type": "article",
                "field": "exercise",
                "pageSize": "10"
            }
            
            async with self.session.get(self.endpoints["jospt"], params=search_params) as response:
                if response.status == 200:
                    data = await response.json()
                    
                    for item in data.get("items", []):
                        protocol = self._extract_exercise_protocol(item)
                        if protocol:
                            results.append({
                                "source": "jospt",
                                "muscle": muscle_name,
                                "title": item.get("title", ""),
                                "protocol": protocol,
                                "evidence": {
                                    "doi": item.get("doi", ""),
                                    "citation": item.get("citation", ""),
                                    "publication_date": item.get("publicationDate", "")
                                },
                                "url": item.get("url", ""),
                                "timestamp": datetime.now().isoformat()
                            })
            
            await asyncio.sleep(self.delay)
            
        except Exception as e:
            logger.error(f"JOSPT 검색 중 오류 발생 ({muscle_name}): {str(e)}")
        
        return results
    
    def _extract_exercise_protocol(self, item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """운동 프로토콜 추출"""
        try:
            content = item.get("content", "")
            if not content:
                return None
            
            # 프로토콜 정보 추출
            protocol = {
                "preparation": [],
                "steps": [],
                "variations": [],
                "precautions": [],
                "evidence_level": "",
                "recommended_sets": "",
                "recommended_frequency": ""
            }
            
            # 여기에 프로토콜 추출 로직 구현
            # BeautifulSoup 등을 사용하여 구조화된 데이터 추출
            
            return protocol
            
        except Exception as e:
            logger.error(f"프로토콜 추출 중 오류 발생: {str(e)}")
            return None
    
    def _extract_protocol_from_abstract(self, abstract: str) -> Dict[str, Any]:
        """초록에서 운동 프로토콜 정보 추출"""
        protocol = {
            "preparation": [],
            "steps": [],
            "variations": [],
            "precautions": [],
            "evidence_level": "",
            "recommended_sets": "",
            "recommended_frequency": ""
        }
        
        # 초록에서 운동 관련 정보 추출
        sentences = abstract.split('. ')
        for sentence in sentences:
            # 준비 운동 관련 문장 찾기
            if any(keyword in sentence.lower() for keyword in ["preparation", "warm-up", "before exercise"]):
                protocol["preparation"].append(sentence.strip())
            
            # 운동 단계 관련 문장 찾기
            if any(keyword in sentence.lower() for keyword in ["exercise", "stretch", "movement", "position"]):
                protocol["steps"].append(sentence.strip())
            
            # 주의사항 관련 문장 찾기
            if any(keyword in sentence.lower() for keyword in ["caution", "warning", "avoid", "stop if"]):
                protocol["precautions"].append(sentence.strip())
            
            # 운동 빈도 관련 정보 찾기
            if any(keyword in sentence.lower() for keyword in ["times per", "frequency", "weekly", "daily"]):
                protocol["recommended_frequency"] = sentence.strip()
        
        return protocol
    
    def _extract_publication_date(self, soup: BeautifulSoup) -> str:
        """논문 출판일 추출"""
        try:
            pub_date = soup.find('PubDate')
            if pub_date:
                year = pub_date.find('Year').text if pub_date.find('Year') else ""
                month = pub_date.find('Month').text if pub_date.find('Month') else ""
                day = pub_date.find('Day').text if pub_date.find('Day') else ""
                
                if year:
                    if month and day:
                        return f"{year}-{month:0>2}-{day:0>2}"
                    elif month:
                        return f"{year}-{month:0>2}"
                    else:
                        return year
            
            return ""
            
        except Exception as e:
            logger.error(f"출판일 추출 중 오류 발생: {str(e)}")
            return ""
    
    async def crawl_all_muscles(self):
        """모든 근육 데이터 수집"""
        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            await self.init_session()
            
            all_results = []
            
            # 전면 근육 수집
            logger.info("전면 근육 데이터 수집 시작")
            for muscle_name in tqdm(FRONT_MUSCLES.keys(), desc="전면 근육 처리 중"):
                results = await self.crawl_muscle(muscle_name)
                self.collected_data[muscle_name] = results
                all_results.extend(results)
                
                if self.max_items and len(all_results) >= self.max_items:
                    all_results = all_results[:self.max_items]
                    break
            
            # 후면 근육 수집 (최대 항목 수에 도달하지 않은 경우)
            if not self.max_items or len(all_results) < self.max_items:
                logger.info("후면 근육 데이터 수집 시작")
                for muscle_name in tqdm(BACK_MUSCLES.keys(), desc="후면 근육 처리 중"):
                    # 내전근은 전면에서 이미 수집했으므로 중복 방지
                    if muscle_name == "내전근" and "내전근" in self.collected_data and self.collected_data["내전근"]:
                        continue
                        
                    results = await self.crawl_muscle(muscle_name)
                    self.collected_data[muscle_name] = results
                    all_results.extend(results)
                    
                    if self.max_items and len(all_results) >= self.max_items:
                        all_results = all_results[:self.max_items]
                        break
            
            # 결과 저장
            output_file = self.output_dir / f"muscle_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            # 데이터 구조화
            structured_data = {
                "metadata": {
                    "total_items": len(all_results),
                    "front_muscles": list(FRONT_MUSCLES.keys()),
                    "back_muscles": list(BACK_MUSCLES.keys()),
                    "collection_date": datetime.now().isoformat(),
                    "data_sources": ["PubMed", "KoreaMed", "JOSPT"]
                },
                "muscles": {
                    muscle_name: {
                        "info": ALL_MUSCLES[muscle_name],
                        "exercises": self.collected_data[muscle_name]
                    }
                    for muscle_name in ALL_MUSCLES
                    if muscle_name in self.collected_data and self.collected_data[muscle_name]
                }
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(structured_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"데이터 수집 완료: {len(all_results)}개 항목")
            logger.info(f"결과 저장 완료: {output_file}")
            
        except Exception as e:
            logger.error(f"데이터 수집 중 오류 발생: {str(e)}")
            raise
        
        finally:
            await self.close_session()

async def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="자세 교정 및 스트레칭 데이터 수집 크롤러")
    parser.add_argument("--output", required=True, help="출력 디렉토리 경로")
    parser.add_argument("--limit", type=int, help="수집할 최대 항목 수")
    
    args = parser.parse_args()
    
    output_dir = Path(args.output)
    max_items = args.limit
    
    # 크롤러 실행
    crawler = StretchingDataCrawler(output_dir, max_items)
    await crawler.crawl_all_muscles()

if __name__ == "__main__":
    asyncio.run(main()) 