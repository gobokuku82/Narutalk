# Kure-v1 + ChromaDB 청킹 전략 지시사항

## 프로젝트 개요
- **문서**: 좋은제약 내부 규정 (취업규칙, 인사관리규정, 복무규정, 윤리강령 및 CP 규정)
- **임베딩 모델**: Kure-v1 (한국어 특화)
- **벡터 DB**: ChromaDB
- **목적**: 효율적인 한국어 규정 문서 검색 시스템 구축

## 문서 구조 분석
### 계층 구조
- 4개 주요 부: 취업규칙, 인사관리규정, 복무규정, 윤리강령 및 CP 규정
- 장(Chapter) → 조(Article) → 항(Clause) 구조
- 마지막 조항: 제21조 (제보자 보호)

### 데이터 유형
- 규정 텍스트: 법령 형식의 조항
- 테이블 데이터: 직급체계 표
- 설명적 텍스트: 각 규정의 배경과 목적 설명

## 청킹 전략

### 1. 기본 청킹 원칙
```python
chunking_principles = {
    "primary_strategy": "조항_중심_청킹",
    "chunk_boundaries": [
        "각 조(Article) 단위를 기본으로",
        "연관성 높은 조항은 묶어서 처리",
        "테이블은 독립 청크로 분리"
    ],
    "metadata_enrichment": "각 청크에 풍부한 메타데이터 추가"
}
```

### 2. 부별 청킹 구조
```python
chunk_structure = {
    "제1부_취업규칙": {
        "청크_단위": "1-2개 조항",
        "예시": {
            "chunk_1": ["제1조(목적)", "제2조(적용범위)"],
            "chunk_2": ["제3조(정의)"],
            "chunk_3": ["제4조(채용)", "제5조(근로계약)"],
            "chunk_4": ["제6조(수습기간)"]
        }
    },
    
    "제2부_인사관리규정": {
        "청크_단위": "조항 + 설명문",
        "특별처리": {
            "직급체계_테이블": "별도 청크 + 전후 설명 포함",
            "평정요소": "윤리/CP 관련 내용 강조"
        }
    },
    
    "제3부_복무규정": {
        "청크_단위": "의무사항별 그룹화",
        "그룹": {
            "기본의무": ["제1조(성실의무)", "제2조(품위유지의무)"],
            "근무관리": ["제3조(출근및결근)", "제4조(회사명의사용)"],
            "보안관리": ["제5조(자산보호)", "제6조(정보보안)"],
            "지식재산": ["제7조(비밀유지의무)", "제8조(직무발명)"],
            "금지사항": ["제9조(이해상충금지)", "제10조(겸직금지)"]
        }
    },
    
    "제4부_윤리강령_CP": {
        "청크_단위": "핵심 주제별",
        "중요도": "HIGH",
        "특별_인덱싱": True
    }
}
```

### 3. 최적 청크 크기
```python
optimal_chunk_sizes = {
    "일반_규정": {
        "target_tokens": 250-350,  # Kure-v1 optimal range
        "max_tokens": 500,
        "strategy": "조항 내용이 짧으면 2-3개 묶기"
    },
    
    "복잡한_규정": {
        "target_tokens": 400-500,
        "include": "조항 + 상세 설명 + 예외사항",
        "example": "제7조(평정요소) + CP 준수 설명"
    },
    
    "테이블_데이터": {
        "strategy": "테이블 + 전후 설명문",
        "format": "structured_text",
        "max_tokens": 300
    },
    
    "정의_조항": {
        "strategy": "모든 정의를 하나의 청크로",
        "reason": "용어 참조 시 일관성"
    }
}
```

## 메타데이터 구조

### 필수 메타데이터
```python
metadata_template = {
    "standard_metadata": {
        "doc_id": "좋은제약_내부규정",
        "part": "제N부",
        "part_title": "부 제목",
        "chapter": "제N장",
        "chapter_title": "장 제목",
        "article_nums": ["제N조"],
        "article_titles": ["조 제목"],
        "chunk_id": "unique_identifier",
        "chunk_sequence": 1  # 문서 내 순서
    },
    
    "semantic_metadata": {
        "keywords": ["자동 추출 키워드"],
        "topics": ["인사", "윤리", "복무", "보안"],
        "compliance_related": True/False,  # CP/윤리 관련 여부
        "legal_reference": ["근로기준법", "ISO37001"],
        "importance_score": 1-5
    },
    
    "structural_metadata": {
        "chunk_type": "regulation|table|definition|procedure",
        "has_subclauses": True/False,
        "related_articles": ["제N조", "제M조"],
        "cross_references": ["다른 부의 관련 조항"]
    }
}
```

## ChromaDB 구현

### 컬렉션 설정
```python
import chromadb
from typing import List, Dict

class WhaninRegulationDB:
    def __init__(self):
        self.client = chromadb.PersistentClient(path="./whanin_chroma_db")
        self.collection = self.client.get_or_create_collection(
            name="internal_regulations",
            metadata={"description": "좋은제약 내부 규정"}
        )
    
    def add_chunks(self, chunks: List[Dict]):
        for i, chunk in enumerate(chunks):
            self.collection.add(
                documents=[chunk['text']],
                metadatas=[{
                    'part': chunk['part'],
                    'chapter': chunk['chapter'],
                    'articles': ','.join(chunk['articles']),
                    'keywords': ','.join(chunk['keywords']),
                    'importance': chunk.get('importance', 'medium'),
                    'compliance_related': chunk.get('compliance_related', False),
                    'chunk_type': chunk['chunk_type'],
                    'sequence': i
                }],
                ids=[f"chunk_{i:04d}"]
            )
```

## 특수 콘텐츠 처리

### 1. 직급체계 테이블
- 테이블 데이터와 설명문을 하나의 청크로 통합
- 구조화된 텍스트 형식으로 변환
- 메타데이터에 'table' 타입 명시

### 2. 윤리/CP 관련 조항
- 높은 중요도(HIGH) 설정
- compliance_related 플래그 True
- 인사평가 조항과 상호 참조 연결

### 3. 제보 및 보호 조항
- 제20조와 제21조를 하나의 청크로 결합
- 프로시저 타입으로 분류
- 윤리 관련 키워드 강화

## 검색 최적화

### 동의어 처리
```python
synonym_mapping = {
    "직원": ["근로자", "임직원", "사원"],
    "CP": ["공정거래", "자율준수프로그램", "Compliance Program"],
    "윤리": ["윤리강령", "윤리규정", "행동강령"],
    "징계": ["제재", "처벌", "불이익"],
    "휴가": ["휴일", "연차", "휴직"]
}
```

### 검색 전략
1. **기본 검색**: Kure-v1 임베딩 기반 의미적 유사도
2. **확장 검색**: 전후 청크 포함 (context window = 1)
3. **필터 검색**: 메타데이터 기반 필터링
4. **리랭킹**: 중요도, 준법 관련성, 키워드 매칭 고려

## 구현 체크리스트

- [ ] 문서를 조항 단위로 파싱
- [ ] 각 청크에 메타데이터 추가
- [ ] 테이블 데이터를 구조화된 텍스트로 변환
- [ ] 윤리/CP 관련 조항 특별 처리
- [ ] ChromaDB 컬렉션 생성 및 인덱싱
- [ ] 동의어 사전 구축
- [ ] 검색 쿼리 최적화
- [ ] 리랭킹 로직 구현
- [ ] 테스트 쿼리 실행 및 검증

## 주의사항

1. **청크 크기**: Kure-v1의 최적 성능을 위해 250-350 토큰 유지
2. **중복 방지**: 조항 간 중복 내용 최소화
3. **컨텍스트 유지**: 관련 조항들의 연결성 보존
4. **메타데이터 일관성**: 모든 청크에 동일한 메타데이터 구조 적용
5. **윤리 규정 강조**: CP 및 윤리 관련 내용은 항상 높은 중요도로 설정

## 성능 지표

- 검색 정확도 목표: 90% 이상
- 응답 시간 목표: 100ms 이내
- 청크 크기 분포: 250-350 토큰 (80% 이상)
- 메타데이터 완전성: 100%
