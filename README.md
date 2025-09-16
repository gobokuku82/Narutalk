# Pharmaceutical Chatbot System

## 프로젝트 구조

```
.
├── services/               # 마이크로서비스
│   ├── chatbot/           # LangGraph 챗봇 서비스
│   │   ├── agents/        # 에이전트 로직
│   │   ├── supervisor/    # 수퍼바이저
│   │   ├── persistence/   # 체크포인터
│   │   ├── schemas/       # 챗봇 스키마
│   │   ├── main.py        # 챗봇 API (포트 8001)
│   │   └── Dockerfile
│   │
│   └── data_api/          # 데이터 접근 서비스
│       ├── routers/       # API 라우터
│       ├── services/      # 비즈니스 로직
│       ├── repositories/  # DB 접근 계층
│       ├── schemas/       # 데이터 스키마
│       ├── main.py        # 데이터 API (포트 8002)
│       └── Dockerfile
│
├── shared/                # 공유 코드
│   ├── models/           # SQLAlchemy 모델
│   ├── database/         # DB 연결 관리
│   └── config/           # 설정 파일
│
├── database/              # 데이터베이스 파일
│   ├── hr_information/    # HR SQLite
│   ├── sales_performance_db/ # 매출 SQLite
│   ├── rules_DB/          # 규정 ChromaDB
│   └── hr_rules_db/       # HR 규정 ChromaDB
│
├── models/                # ML 모델
│   ├── kure_v1/          # 한국어 임베딩 모델
│   └── bge-reranker-v2-m3-ko/ # 리랭킹 모델
│
├── frontend/              # 프론트엔드 (React)
├── docker-compose.yml     # 서비스 오케스트레이션
└── requirements.txt       # Python 의존성
```

## 서비스 설명

### 1. Chatbot Service (포트 8001)
- **기능**: LangGraph 기반 멀티에이전트 챗봇
- **엔드포인트**:
  - `GET /` - 헬스체크
  - `POST /chat` - 동기식 채팅
  - `WS /ws/{session_id}` - WebSocket 스트리밍
  - `POST /interrupt/resume` - 인터럽트 재개
  - `GET /sessions/{session_id}/checkpoints` - 체크포인트 조회

### 2. Data API Service (포트 8002)
- **기능**: SQL 및 벡터 데이터베이스 접근
- **엔드포인트**:
  - **SQL API**:
    - `POST /api/v1/data/sql/query` - Text2SQL 실행
    - `GET /api/v1/data/sql/schema/{database}` - 스키마 조회
  - **Vector API**:
    - `POST /api/v1/data/vector/search` - 벡터 검색
    - `GET /api/v1/data/vector/collection/{collection}` - 컬렉션 정보
  - **Hybrid API**:
    - `POST /api/v1/data/hybrid/search` - 하이브리드 검색
    - `POST /api/v1/data/hybrid/employee-compliance` - 직원-규정 검색
    - `POST /api/v1/data/hybrid/sales-context` - 매출 컨텍스트 검색
  - **Metadata**:
    - `GET /api/v1/data/metadata` - 전체 메타데이터

## 실행 방법

### 1. 개별 서비스 실행

#### Chatbot Service
```bash
cd services/chatbot
python main.py
```

#### Data API Service
```bash
cd services/data_api
python main.py
```

### 2. Docker Compose 실행
```bash
# 모든 서비스 실행
docker-compose up -d

# 특정 서비스만 실행
docker-compose up -d chatbot
docker-compose up -d data-api

# 로그 확인
docker-compose logs -f chatbot
docker-compose logs -f data-api

# 서비스 중지
docker-compose down
```

### 3. 개발 모드 실행
```bash
# 환경변수 설정
cp .env.example .env
# .env 파일 수정

# 의존성 설치
pip install -r requirements.txt

# 각 서비스 실행
python services/chatbot/main.py
python services/data_api/main.py
```

## API 사용 예시

### Text2SQL 쿼리
```bash
curl -X POST "http://localhost:8002/api/v1/data/sql/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "김철수 직원의 정보를 조회해주세요",
    "database": "hr_data"
  }'
```

### 벡터 검색
```bash
curl -X POST "http://localhost:8002/api/v1/data/vector/search" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "제품설명회 식사 한도",
    "collection": "compliance_rules",
    "use_reranker": true,
    "top_k": 5
  }'
```

### 챗봇 대화
```bash
curl -X POST "http://localhost:8001/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "안녕하세요",
    "user_id": "user123",
    "company_id": "company456"
  }'
```

## 환경 변수

`.env` 파일에 다음 설정 필요:

```env
# API Keys
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Service Ports
CHATBOT_PORT=8001
DATA_API_PORT=8002

# Database Paths
HR_DB_PATH=database/hr_information/hr_data.db
SALES_DB_PATH=database/sales_performance_db/sales_performance_db.db

# Model Paths
EMBEDDING_MODEL_PATH=models/kure_v1
RERANKER_MODEL_PATH=models/bge-reranker-v2-m3-ko
```

## 개발 가이드

### 새로운 API 엔드포인트 추가
1. `services/data_api/routers/` 에 라우터 추가
2. `services/data_api/services/` 에 비즈니스 로직 구현
3. `services/data_api/schemas/` 에 Pydantic 모델 정의

### 새로운 에이전트 추가
1. `services/chatbot/agents/` 에 에이전트 클래스 생성
2. `services/chatbot/supervisor/` 에서 에이전트 등록
3. `services/chatbot/config/agents_config.yaml` 수정

## 문제 해결

### Import 오류
- Python 경로가 올바른지 확인
- `PYTHONPATH` 환경변수 설정 확인

### 데이터베이스 연결 오류
- SQLite 파일 경로 확인
- ChromaDB 디렉토리 권한 확인

### 모델 로딩 오류
- 모델 파일이 `models/` 디렉토리에 있는지 확인
- 필요한 패키지 설치 확인 (sentence-transformers)

## 라이선스
Private - Pharmaceutical Company Internal Use Only