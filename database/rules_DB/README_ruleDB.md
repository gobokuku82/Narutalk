# 제약 영업 규제 준수 검색 시스템 (Rule_DB)

## 📋 시스템 개요

제약 영업 담당자를 위한 한국 의약품 규제 검색 및 답변 시스템입니다. 청탁금지법, 약사법, 공정경쟁규약 등의 규제를 자연어로 검색하고 실무에 적용 가능한 답변을 제공합니다.

### 주요 기능
- 🔍 **하이브리드 검색**: 벡터 유사도 + 메타데이터 필터링
- 🤖 **GPT-4o 통합**: 자연어 답변 생성
- ⚖️ **충돌 해결**: 법령 간 우선순위 자동 적용
- 📊 **구조화된 데이터**: 금액, 빈도, 대상 등 메타데이터 추출

## 🗂️ 디렉토리 구조

```
database/
├── Rule_DB/
│   ├── chroma_db/           # ChromaDB 벡터 데이터베이스
│   │   └── [벡터 인덱스 파일들]
│   ├── search_engine.py     # 기본 검색 엔진
│   ├── gpt_enhanced_search.py  # GPT-4o 통합 검색
│   ├── conflict_resolver.py    # 법령 충돌 해결
│   └── README.md            # 본 문서
├── test_data/
│   └── test_chunks.json    # 테스트용 청킹 데이터 (11개)
└── models/
    └── kure_v1/            # KURE-v1 임베딩 모델 (로컬)
```

## 📊 데이터베이스 스키마

### ChromaDB Collection: `compliance_chunks`
- **차원**: 1024 (KURE-v1 임베딩)
- **총 문서 수**: 11개 청크
- **거리 측정**: cosine similarity

### 메타데이터 필드

| 필드명 | 타입 | 설명 | 예시 |
|--------|------|------|------|
| `law_name` | string | 법령명 | "공정경쟁규약", "청탁금지법", "약사법" |
| `article` | string | 조항 | "제10조", "제8조" |
| `prohibition_type` | string | 금지 유형 | "조건부허용", "절대금지" |
| `limit_value` | number | 금액 한도 (원) | 100000, 350000 |
| `frequency_count` | number | 빈도 횟수 | 4, 1 |
| `frequency_period` | string | 빈도 기간 | "month", "year" |
| `activity` | string | 활동 유형 | "제품설명회", "학술대회", "강연" |
| `target` | string | 대상 | "요양기관", "의료인", "공직자" |
| `target_type` | string | 대상 유형 | "복수기관", "개별기관" |
| `item_type` | string | 항목 유형 | "식음료", "숙박비", "선물" |
| `conditions` | string | 조건 (리스트→문자열) | "최소포장단위,견본품표시" |

## 🔍 검색 엔진 API

### 1. 기본 검색 엔진 (search_engine.py)

```python
from search_engine import ComplianceSearchEngine, SearchQuery

# 엔진 초기화
engine = ComplianceSearchEngine(chunks_file="test_chunks.json")

# 검색 실행
query = SearchQuery(text="대학병원 교수 식사", top_k=5)
results = engine.search(query)

# 결과 처리
for result in results:
    print(f"법령: {result.source_law}")
    print(f"내용: {result.text}")
    print(f"점수: {result.score:.2f}")
```

### 2. GPT 통합 검색 (gpt_enhanced_search.py)

```python
from gpt_enhanced_search import GPTEnhancedSearchEngine

# 엔진 초기화 (OpenAI API 키 필요)
engine = GPTEnhancedSearchEngine(chunks_file="test_chunks.json")

# 자연어 질문
result = engine.search_and_answer(
    query="대학병원 교수님께 10만원 식사 대접 가능한가요?",
    top_k=5
)

# GPT 답변 출력
print(result.gpt_answer)
print(f"신뢰도: {result.confidence:.1%}")
```

## 📝 샘플 데이터 (test_chunks.json)

현재 11개의 테스트 청크가 포함되어 있습니다:

1. **test_001**: 제품설명회 식음료 제공 (월 4회, 1회 10만원)
2. **test_002**: 해외 학술대회 숙박비 (1박 35만원)
3. **test_003**: 의약품 견본품 제공 규정
4. **test_004**: 강연료 한도 (1회 50만원, 연 300만원)
5. **test_005**: 공직자 선물 제공 금지
6. **test_006**: 복수 요양기관 제품설명회
7. **test_007**: 임상시험 비용 지급
8. **test_008**: 시판후조사 대가 지급
9. **test_009**: 학술대회 기념품 제공
10. **test_010**: 의료인 경제적 이익 제공 금지
11. **test_011**: 대학병원 교수 청탁금지법 적용

## ⚖️ 법령 우선순위

충돌 시 다음 순서로 우선 적용됩니다:
1. **청탁금지법** (가장 엄격)
2. **약사법**
3. **공정경쟁규약** (가장 유연)

## 🚀 사용 방법

### 1. 필수 패키지 설치

```bash
pip install -r requirements.txt
```

### 2. 환경 변수 설정 (.env)

```env
OPENAI_API_KEY=your_api_key_here
HUGGINGFACE_TOKEN=your_token_here
```

### 3. 대화형 모드 실행

```bash
python gpt_enhanced_search.py
```

### 4. 프로그래밍 방식 사용

```python
# 질문 예시
questions = [
    "대학병원 교수님께 식사 대접이 가능한가요?",
    "해외 학술대회 지원 한도는 얼마인가요?",
    "의료진에게 선물을 줄 수 있나요?"
]

# 일괄 처리
engine = GPTEnhancedSearchEngine()
for question in questions:
    result = engine.search_and_answer(question)
    print(f"Q: {question}")
    print(f"A: {result.gpt_answer}")
    print("-" * 50)
```

## 📈 성능 지표

- **검색 속도**: < 500ms (11개 청크 기준)
- **임베딩 차원**: 1024 (KURE-v1)
- **답변 생성**: 1-2초 (GPT-4o)
- **정확도**: 법령 우선순위 100% 준수

## 🔧 커스터마이징

### 새로운 문서 추가

1. 문서를 청킹하여 test_chunks.json 형식으로 저장
2. 메타데이터 필드 추출 및 구조화
3. ChromaDB에 임베딩 추가

```python
# 새 청크 추가 예시
new_chunk = {
    "chunk_id": "custom_001",
    "text": "새로운 규제 내용...",
    "metadata": {
        "law_name": "공정경쟁규약",
        "article": "제15조",
        "limit_value": 50000
    }
}
```

### 검색 파라미터 조정

```python
# search_engine.py에서 조정 가능
self.weight_vector = 0.7  # 벡터 검색 가중치
self.weight_metadata = 0.3  # 메타데이터 가중치
```

## 🚨 주의사항

1. **모델 경로**: KURE-v1 모델이 로컬에 있어야 함
   - 경로: `C:\kdy\Projects\Narutalk_V003\beta_v0031\database\models\kure_v1`

2. **API 키**: GPT-4o 사용 시 OpenAI API 키 필요

3. **인코딩**: 한국어 처리를 위해 UTF-8 인코딩 필수

4. **Windows 호환**: 이모지 대신 텍스트 마커 사용

## 📞 문의 및 개선사항

추가 규제 문서 통합이나 기능 개선이 필요한 경우 이슈를 등록해 주세요.

## 🔄 다음 단계

이 README를 참고하여 다음 작업을 진행할 수 있습니다:
- 실제 규제 문서 전체 처리 및 통합
- 웹 인터페이스 개발
- 모바일 앱 API 서버 구축
- 규제 업데이트 자동화 시스템