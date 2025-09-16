# 좋은제약 내부 규정 검색 시스템

## 필요 파일
ChromaDB를 사용하려면 다음 파일들이 필요합니다:

### 필수 파일
1. **chromadb/** 폴더 - 벡터 데이터베이스 (이미 구축됨)
2. **hr_rules_search.py** - 대화형 검색 프로그램
3. **hr_rules_api.py** - 프로그래밍 API

### 선택 파일 (필요시)
- embedding_processor.py - 새로운 문서 추가시 필요
- 원본 DOCX 파일 - 재구축시 필요

## 설치
```bash
pip install chromadb
```

## 사용 방법

### 1. 대화형 검색 (hr_rules_search.py)
```bash
python hr_rules_search.py
```

명령어:
- 일반 검색: `연차 휴가`
- 부별 검색: `part:1 채용` (1부에서 채용 검색)
- 키워드 검색: `key:윤리`
- 통계 보기: `stats`
- 종료: `quit`

### 2. 프로그래밍 API (hr_rules_api.py)

#### 기본 사용
```python
from hr_rules_api import HRRulesAPI

# API 초기화
api = HRRulesAPI("./chromadb")

# 일반 검색
results = api.search("휴가 규정", top_k=5)
for result in results:
    print(result['text'])
    print(f"부: {result['metadata']['part']}")
```

#### 조항 검색
```python
# 제7조 검색
results = api.get_by_article("7")
```

#### 주제별 검색
```python
# 휴가 관련 규정 검색
results = api.get_by_topic("휴가")
```

#### 가장 간단한 사용법
```python
from hr_rules_api import quick_search

results = quick_search("징계 절차")
for text in results:
    print(text)
```

### 3. 다른 프로그램에서 통합
```python
import sys
sys.path.append("C:/kdy/Projects/Narutalk_V003/beta_v0031/database/hr_rules_db")

from hr_rules_api import HRRulesAPI

api = HRRulesAPI("C:/kdy/Projects/Narutalk_V003/beta_v0031/database/hr_rules_db/chromadb")
results = api.search("원하는 검색어")
```

## 데이터베이스 구조

### 문서 구성
- **제1부**: 취업규칙
- **제2부**: 인사관리규정
- **제3부**: 복무규정
- **제4부**: 윤리강령 및 CP 규정

### 메타데이터
- part: 부 정보
- article_nums: 조항 번호
- keywords: 키워드
- importance_score: 중요도 (1-5)
- chunk_type: 청크 타입 (regulation, table, definition, procedure)

## 주의사항
- ChromaDB는 자체 임베딩 모델을 사용합니다
- 한국어 검색에 최적화되어 있습니다
- 총 29개 청크로 구성되어 있습니다

## 문제 해결
- "컬렉션을 찾을 수 없습니다" 오류: chromadb 폴더 경로 확인
- 검색 결과 없음: 검색어를 더 일반적으로 변경
- 한글 깨짐: Windows에서 UTF-8 설정 확인