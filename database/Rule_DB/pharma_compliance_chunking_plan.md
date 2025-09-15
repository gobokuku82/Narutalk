# 제약 영업 규제 준수 시스템 - 지능형 청킹 전략 및 구현 계획

## 1. 프로젝트 개요

### 목표
- 제약 영업사원이 실시간으로 규정 준수 여부를 확인할 수 있는 시스템 구축
- 복잡한 법령/규정을 실무 중심으로 재구조화하여 정확한 답변 제공
- 벡터 DB의 한계를 극복한 하이브리드 검색 시스템 구현

### 핵심 전략
1. **구조적 청킹**: 법령 구조가 아닌 실무 시나리오 기반 청킹
2. **계층적 인덱싱**: 상위 개념 → 세부 규정으로 이어지는 계층 구조
3. **풍부한 메타데이터**: 단순 출처를 넘어선 다차원 분류 체계
4. **충돌 해결 메커니즘**: 여러 법령 간 우선순위 자동 판단

## 2. 청킹 전략 상세

### 2.1 청킹 단위 설계

```python
CHUNKING_RULES = {
    "primary_unit": "의미 완결 단위",  # 하나의 규정이 독립적으로 이해 가능
    "size_constraints": {
        "min_chars": 50,
        "max_chars": 300,
        "optimal_chars": 150
    },
    "overlap": 30,  # 문맥 유지를 위한 중첩
    "preserve_context": True
}
```

### 2.2 문서별 청킹 전략

#### A. 청탁금지법 청킹
```python
청탁금지법_청킹 = {
    "제8조_1항": [
        {
            "chunk_id": "anti_graft_8_1_a",
            "text": "공직자는 동일인으로부터 1회 100만원 초과 금품 수수 금지",
            "metadata": {
                "law": "청탁금지법",
                "article": "제8조",
                "paragraph": "1항",
                "prohibition_type": "절대금지",
                "limit_value": 1000000,
                "frequency": "1회",
                "target": "공직자등"
            }
        },
        {
            "chunk_id": "anti_graft_8_1_b",
            "text": "공직자는 매 회계연도 300만원 초과 금품 수수 금지",
            "metadata": {
                "law": "청탁금지법",
                "article": "제8조",
                "paragraph": "1항",
                "prohibition_type": "절대금지",
                "limit_value": 3000000,
                "frequency": "연간",
                "target": "공직자등"
            }
        }
    ],
    "제8조_3항": [
        {
            "chunk_id": "anti_graft_8_3_meal",
            "text": "원활한 직무수행 목적 식음료는 대통령령이 정하는 가액 범위 내 허용",
            "metadata": {
                "law": "청탁금지법",
                "article": "제8조",
                "paragraph": "3항2호",
                "prohibition_type": "조건부허용",
                "item_type": "식음료",
                "purpose": "직무수행",
                "requires_limit_check": true
            }
        }
    ]
}
```

#### B. 공정경쟁규약 청킹
```python
공정경쟁규약_청킹 = {
    "제10조_복수기관": {
        "chunk_id": "fair_comp_10_multi",
        "text": "복수 요양기관 대상 제품설명회 시 1인당 10만원 이내 식음료 제공 가능",
        "metadata": {
            "source": "공정경쟁규약",
            "article": "제10조",
            "activity": "제품설명회",
            "target_type": "복수기관",
            "item": "식음료",
            "limit_value": 100000,
            "limit_unit": "1인당"
        }
    },
    "제10조_개별기관": {
        "chunk_id": "fair_comp_10_individual",
        "text": "개별 요양기관 방문 제품설명회는 월 4회까지, 1회 10만원 이내 식음료 가능",
        "metadata": {
            "source": "공정경쟁규약",
            "article": "제10조",
            "activity": "제품설명회",
            "target_type": "개별기관",
            "frequency_limit": 4,
            "frequency_period": "월",
            "amount_limit": 100000
        }
    }
}
```

### 2.3 실무 시나리오 기반 재구성

```python
SCENARIO_BASED_CHUNKS = {
    "병원_방문_식사": [
        {
            "scenario": "개별 병원 방문 시 식사 제공",
            "allowed": True,
            "conditions": [
                "제품설명회 목적",
                "월 4회 이내",
                "1회 10만원 이내"
            ],
            "source_chunks": ["fair_comp_10_individual"],
            "search_keywords": ["병원방문", "식사", "점심", "저녁", "개별방문"]
        }
    ],
    "학술대회_지원": [
        {
            "scenario": "학술대회 참가 지원",
            "allowed": True,
            "conditions": [
                "발표자/좌장/토론자에 한함",
                "협회 기탁 방식",
                "숙박비 국내 20만원/박, 해외 35만원/박"
            ],
            "source_chunks": ["fair_comp_9"],
            "search_keywords": ["학술대회", "세미나", "심포지엄", "참가비", "등록비"]
        }
    ]
}
```

## 3. 메타데이터 스키마

### 3.1 핵심 메타데이터 구조
```python
METADATA_SCHEMA = {
    # Level 1: 법령 정보
    "legal_source": {
        "law_name": str,        # "청탁금지법"
        "article": str,         # "제8조"
        "paragraph": str,       # "1항"
        "subparagraph": str,    # "2호"
        "effective_date": date
    },
    
    # Level 2: 행위 분류
    "activity_classification": {
        "category": str,        # "금품제공", "학술지원", "제품설명회"
        "subcategory": str,     # "식음료", "숙박", "교통비"
        "action": str,          # "제공", "수수", "요구"
        "target": str,          # "의료인", "공직자", "요양기관"
        "purpose": str          # "직무수행", "학술목적", "판촉"
    },
    
    # Level 3: 규제 속성
    "regulation_attributes": {
        "prohibition_level": str,  # "절대금지", "조건부허용", "허용"
        "severity": int,           # 1-5 (엄격도)
        "priority": int,           # 법령 간 우선순위
        "exception_exists": bool
    },
    
    # Level 4: 제한사항
    "limitations": {
        "monetary": {
            "value": int,
            "currency": str,
            "per": str,            # "person", "event", "year"
            "includes_vat": bool
        },
        "frequency": {
            "count": int,
            "period": str,         # "day", "month", "year"
            "reset_cycle": str
        },
        "temporal": {
            "allowed_hours": list,
            "blackout_dates": list
        }
    },
    
    # Level 5: 실무 정보
    "operational_info": {
        "required_documents": list,     # ["영수증", "참석자명단"]
        "approval_required": bool,
        "approval_authority": str,
        "reporting_deadline": str,
        "common_violations": list,
        "best_practices": list
    },
    
    # Level 6: 검색 최적화
    "search_optimization": {
        "keywords": list,               # 자연어 검색어
        "synonyms": list,              # 동의어
        "related_scenarios": list,     # 관련 시나리오 ID
        "frequently_asked_with": list  # 함께 질문되는 항목
    }
}
```

## 4. 충돌 해결 메커니즘

### 4.1 법령 우선순위
```python
LAW_PRIORITY = {
    1: "청탁금지법",          # 최우선
    2: "약사법",
    3: "공정거래법",
    4: "공정경쟁규약",        # 자율규약
    5: "가이드라인"
}

def resolve_conflict(chunks):
    """여러 법령이 충돌할 때 가장 엄격한 기준 적용"""
    if not chunks:
        return None
    
    # 우선순위별 정렬
    sorted_chunks = sorted(chunks, 
                          key=lambda x: LAW_PRIORITY.get(x['metadata']['law_name'], 999))
    
    # 가장 엄격한 제한 찾기
    strictest = sorted_chunks[0]
    for chunk in sorted_chunks[1:]:
        if chunk['metadata'].get('limit_value', float('inf')) < \
           strictest['metadata'].get('limit_value', float('inf')):
            strictest = chunk
    
    return strictest
```

## 5. 구현 계획

### 5.1 Phase 1: 데이터 준비 (Week 1)
```python
tasks_phase1 = [
    "원본 문서를 섹션별로 분리",
    "각 섹션을 의미 단위로 청킹",
    "메타데이터 자동 추출 스크립트 작성",
    "청킹 품질 검증 도구 개발"
]
```

### 5.2 Phase 2: 인덱싱 구축 (Week 2)
```python
tasks_phase2 = [
    "Pinecone/Weaviate 설정",
    "임베딩 모델 선택 (ko-sroberta-multitask 추천)",
    "청크별 임베딩 생성 및 저장",
    "메타데이터 필터링 로직 구현"
]
```

### 5.3 Phase 3: 검색 시스템 (Week 3)
```python
tasks_phase3 = [
    "하이브리드 검색 엔진 구현",
    "시나리오 기반 쿼리 처리기",
    "충돌 해결 로직 구현",
    "답변 생성 템플릿 작성"
]
```

### 5.4 Phase 4: 테스트 및 최적화 (Week 4)
```python
tasks_phase4 = [
    "실제 영업 시나리오 테스트 케이스 작성",
    "정확도 및 속도 벤치마킹",
    "사용자 피드백 반영",
    "성능 최적화"
]
```

## 6. 코드 구현 예시

### 6.1 청킹 함수
```python
import re
from typing import List, Dict, Any

class PharmaComplianceChunker:
    def __init__(self):
        self.chunk_id_counter = 0
        
    def chunk_document(self, text: str, doc_type: str) -> List[Dict[str, Any]]:
        """문서를 도메인 특화 방식으로 청킹"""
        chunks = []
        
        if doc_type == "청탁금지법":
            chunks.extend(self._chunk_anti_graft_law(text))
        elif doc_type == "공정경쟁규약":
            chunks.extend(self._chunk_fair_competition(text))
        elif doc_type == "약사법":
            chunks.extend(self._chunk_pharmaceutical_law(text))
            
        return chunks
    
    def _chunk_anti_graft_law(self, text: str) -> List[Dict[str, Any]]:
        """청탁금지법 특화 청킹"""
        chunks = []
        
        # 금액 제한 추출
        amount_patterns = [
            (r'(\d+)만원.*초과.*금지', 'prohibition'),
            (r'(\d+)만원.*이하.*허용', 'conditional_allow'),
            (r'(\d+)만원.*범위', 'allowed_range')
        ]
        
        for pattern, prohibition_type in amount_patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                context = self._extract_context(text, match.span())
                chunks.append({
                    'chunk_id': f'chunk_{self.chunk_id_counter}',
                    'text': context,
                    'metadata': {
                        'prohibition_type': prohibition_type,
                        'amount_limit': int(match.group(1)) * 10000,
                        'source': '청탁금지법'
                    }
                })
                self.chunk_id_counter += 1
                
        return chunks
    
    def _extract_context(self, text: str, span: tuple, window: int = 100) -> str:
        """매치된 부분 주변 컨텍스트 추출"""
        start = max(0, span[0] - window)
        end = min(len(text), span[1] + window)
        
        # 문장 경계 찾기
        context = text[start:end]
        first_period = context.find('.')
        last_period = context.rfind('.')
        
        if first_period != -1 and last_period != -1:
            context = context[first_period+1:last_period+1]
            
        return context.strip()
```

### 6.2 검색 시스템
```python
class ComplianceSearchEngine:
    def __init__(self, vector_store, metadata_db):
        self.vector_store = vector_store
        self.metadata_db = metadata_db
        
    def search(self, query: str, context: Dict = None) -> List[Dict]:
        """하이브리드 검색 수행"""
        
        # 1. 쿼리 분석
        query_metadata = self._analyze_query(query)
        
        # 2. 메타데이터 필터 생성
        filters = self._create_filters(query_metadata, context)
        
        # 3. 벡터 검색
        vector_results = self.vector_store.search(
            query_text=query,
            filters=filters,
            top_k=10
        )
        
        # 4. 구조적 검색으로 보완
        if len(vector_results) < 5:
            structured_results = self.metadata_db.search(
                category=query_metadata.get('category'),
                limit_type=query_metadata.get('limit_type')
            )
            vector_results.extend(structured_results)
        
        # 5. 충돌 해결 및 순위 조정
        final_results = self._resolve_conflicts(vector_results)
        
        return final_results
    
    def _analyze_query(self, query: str) -> Dict:
        """쿼리에서 메타데이터 추출"""
        metadata = {}
        
        # 금액 관련
        if any(word in query for word in ['얼마', '한도', '금액']):
            metadata['needs_limit'] = True
            
        # 활동 유형
        if '식사' in query or '음료' in query:
            metadata['category'] = '식음료'
        elif '학술대회' in query:
            metadata['category'] = '학술대회'
        elif '견본품' in query or '샘플' in query:
            metadata['category'] = '견본품'
            
        # 빈도 관련
        if any(word in query for word in ['몇 번', '횟수', '빈도']):
            metadata['needs_frequency'] = True
            
        return metadata
```

## 7. 테스트 시나리오

```python
TEST_SCENARIOS = [
    {
        "query": "대학병원 교수님께 점심 대접 가능한가요?",
        "expected_answer": "제품설명회 목적으로 월 4회, 1회 10만원 이내 가능",
        "relevant_chunks": ["fair_comp_10_individual"]
    },
    {
        "query": "해외 학술대회 참가비 지원 방법은?",
        "expected_answer": "발표자/좌장/토론자에 한해 협회 기탁 방식으로 지원, 숙박비 1박 35만원 한도",
        "relevant_chunks": ["fair_comp_9_international"]
    },
    {
        "query": "명절 선물 가능한가요?",
        "expected_answer": "보건의료전문가 개인에게 선물 제공은 금지",
        "relevant_chunks": ["fair_comp_5_gift_prohibition"]
    }
]
```

## 8. 성능 지표

```python
PERFORMANCE_METRICS = {
    "accuracy": {
        "target": 0.95,
        "measurement": "정답 청크 반환율"
    },
    "response_time": {
        "target": "< 500ms",
        "measurement": "쿼리 처리 시간"
    },
    "coverage": {
        "target": 0.98,
        "measurement": "실무 시나리오 커버리지"
    }
}
```

## 9. 주의사항 및 베스트 프랙티스

1. **청킹 시 주의점**
   - 숫자(금액, 횟수)는 반드시 포함
   - "다만", "단," 등 예외 조항 별도 청킹
   - 법령 간 참조 관계 메타데이터로 보존

2. **메타데이터 관리**
   - 모든 청크에 최소 5개 이상 메타데이터 필드
   - 검색 최적화를 위한 동의어 목록 관리
   - 정기적인 메타데이터 품질 검증

3. **성능 최적화**
   - 자주 검색되는 시나리오 캐싱
   - 메타데이터 인덱싱으로 필터링 속도 향상
   - 임베딩 차원 축소 고려 (768 → 384)

## 10. 향후 발전 방향

1. **AI 기반 개선**
   - 사용자 질문 패턴 학습
   - 자동 청킹 규칙 최적화
   - 답변 품질 자동 평가

2. **실시간 업데이트**
   - 법령 개정 시 자동 재청킹
   - 신규 판례/유권해석 반영
   - 업계 관행 변화 추적

3. **사용자 경험**
   - 대화형 인터페이스
   - 시나리오 기반 가이드
   - 위반 리스크 사전 경고
