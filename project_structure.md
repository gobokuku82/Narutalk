# QA 챗봇 시스템 프로젝트 구조

## 전체 프로젝트 구조

```
qa_chatbot_system/
├── backend/                              # Django 백엔드
│   ├── manage.py
│   ├── requirements.txt
│   ├── config/                          # Django 설정
│   │   ├── __init__.py
│   │   ├── settings/
│   │   │   ├── __init__.py
│   │   │   ├── base.py                  # 기본 설정
│   │   │   ├── development.py           # 개발 환경
│   │   │   └── production.py            # 운영 환경
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── apps/                            # Django 앱들
│   │   ├── __init__.py
│   │   ├── authentication/              # 인증 시스템
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   └── urls.py
│   │   ├── chat/                        # 채팅 API
│   │   │   ├── __init__.py
│   │   │   ├── models.py
│   │   │   ├── views.py
│   │   │   ├── serializers.py
│   │   │   └── urls.py
│   │   └── gateway/                     # API 게이트웨이
│   │       ├── __init__.py
│   │       ├── views.py
│   │       ├── middleware.py
│   │       └── urls.py
│   ├── services/                        # 비즈니스 로직
│   │   ├── __init__.py
│   │   ├── langgraph_service.py         # LangGraph 서비스
│   │   ├── openai_service.py            # OpenAI 서비스
│   │   └── memory_service.py            # 메모리 서비스
│   └── utils/                           # 유틸리티
│       ├── __init__.py
│       ├── database.py                  # DB 연결
│       ├── redis_client.py              # Redis 클라이언트
│       └── api_clients.py               # 외부 API 클라이언트
│
├── microservices/                       # FastAPI 마이크로서비스
│   ├── requirements.txt
│   ├── shared/                          # 공통 모듈
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── redis_client.py
│   │   ├── openai_client.py
│   │   └── models.py
│   ├── service_8001_search/             # 통합 검색 서비스
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── services.py
│   ├── service_8002_analytics/          # 성과 분석 서비스
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── services.py
│   ├── service_8003_client_analysis/    # 고객 분석 서비스
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── services.py
│   ├── service_8004_document/           # 문서 자동화 서비스
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── services.py
│   ├── service_8005_conversation/       # 대화 분석 서비스
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── services.py
│   ├── service_8006_wiki/               # 데이터 위키 서비스
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── services.py
│   ├── service_8007_news/               # 뉴스 추천 서비스
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   └── services.py
│   ├── service_8008_ml/                 # ML 성능 예측 서비스
│   │   ├── main.py
│   │   ├── app.py
│   │   ├── routes.py
│   │   ├── models.py
│   │   ├── services.py
│   │   └── ml_models/
│   │       ├── __init__.py
│   │       ├── performance_model.py
│   │       └── forecast_model.py
│   └── service_8009_memory/             # 메모리 관리 서비스
│       ├── main.py
│       ├── app.py
│       ├── routes.py
│       ├── models.py
│       └── services.py
│
├── frontend/                            # React 프론트엔드
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── index.html
│   ├── public/
│   │   ├── favicon.ico
│   │   └── manifest.json
│   ├── src/
│   │   ├── main.tsx
│   │   ├── App.tsx
│   │   ├── components/
│   │   │   ├── Chat/
│   │   │   │   ├── ChatInterface.tsx
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── MessageInput.tsx
│   │   │   │   └── index.ts
│   │   │   ├── Dashboard/
│   │   │   │   ├── DashboardMain.tsx
│   │   │   │   ├── PerformanceChart.tsx
│   │   │   │   ├── ClientAnalytics.tsx
│   │   │   │   └── index.ts
│   │   │   ├── Layout/
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── Footer.tsx
│   │   │   │   └── index.ts
│   │   │   └── Common/
│   │   │       ├── LoadingSpinner.tsx
│   │   │       ├── ErrorBoundary.tsx
│   │   │       └── index.ts
│   │   ├── pages/
│   │   │   ├── HomePage.tsx
│   │   │   ├── ChatPage.tsx
│   │   │   ├── DashboardPage.tsx
│   │   │   ├── LoginPage.tsx
│   │   │   └── index.ts
│   │   ├── services/
│   │   │   ├── api.ts
│   │   │   ├── auth.ts
│   │   │   ├── chat.ts
│   │   │   └── websocket.ts
│   │   ├── hooks/
│   │   │   ├── useAuth.ts
│   │   │   ├── useChat.ts
│   │   │   └── useWebSocket.ts
│   │   ├── store/
│   │   │   ├── index.ts
│   │   │   ├── authSlice.ts
│   │   │   ├── chatSlice.ts
│   │   │   └── dashboardSlice.ts
│   │   ├── types/
│   │   │   ├── auth.ts
│   │   │   ├── chat.ts
│   │   │   └── api.ts
│   │   └── utils/
│   │       ├── constants.ts
│   │       ├── helpers.ts
│   │       └── validators.ts
│   └── dist/                            # 빌드 결과물
│
├── langgraph_orchestrator/              # LangGraph 오케스트레이터
│   ├── requirements.txt
│   ├── main.py
│   ├── workflow/
│   │   ├── __init__.py
│   │   ├── state_graph.py               # StateGraph 정의
│   │   ├── nodes.py                     # 워크플로우 노드들
│   │   ├── edges.py                     # 엣지 정의
│   │   └── conditions.py                # 조건부 로직
│   ├── ai_services/
│   │   ├── __init__.py
│   │   ├── openai_client.py             # OpenAI 클라이언트
│   │   ├── text2sql_client.py           # Text2SQL 클라이언트
│   │   └── embedding_client.py          # 임베딩 클라이언트
│   ├── memory/
│   │   ├── __init__.py
│   │   ├── shortterm_memory.py          # 숏텀 메모리
│   │   ├── longterm_memory.py           # 롱텀 메모리
│   │   └── memory_manager.py            # 메모리 관리자
│   └── utils/
│       ├── __init__.py
│       ├── service_client.py            # 마이크로서비스 클라이언트
│       └── data_processor.py            # 데이터 처리
│
├── data/                                # 데이터 저장소
│   ├── databases/                       # SQLite 데이터베이스
│   │   ├── main.db
│   │   ├── users.db
│   │   ├── sales.db
│   │   ├── clients.db
│   │   ├── news.db
│   │   ├── cache.db
│   │   ├── ml.db
│   │   └── memory.db
│   ├── documents/                       # 문서 저장소
│   │   ├── pdfs/
│   │   ├── docx/
│   │   └── txt/
│   ├── uploads/                         # 업로드된 파일
│   ├── conversations/                   # 대화 기록
│   ├── wiki/                           # 지식 베이스
│   ├── memory/                         # 메모리 백업
│   └── vectors/                        # 벡터 데이터
│       ├── faiss_index/
│       └── embeddings/
│
├── config/                              # 설정 파일
│   ├── .env.example                     # 환경 변수 예시
│   ├── .env.development                 # 개발 환경 설정
│   ├── .env.production                  # 운영 환경 설정
│   ├── docker-compose.yml               # Docker 설정
│   ├── docker-compose.dev.yml           # 개발 환경 Docker
│   ├── nginx.conf                       # Nginx 설정
│   └── redis.conf                       # Redis 설정
│
├── scripts/                             # 스크립트
│   ├── setup_project.sh                 # 프로젝트 초기 설정
│   ├── start_services.sh                # 서비스 시작
│   ├── stop_services.sh                 # 서비스 종료
│   ├── migrate_databases.py             # 데이터베이스 마이그레이션
│   └── seed_data.py                     # 초기 데이터 생성
│
├── monitoring/                          # 모니터링 설정
│   ├── prometheus.yml                   # Prometheus 설정
│   ├── grafana/
│   │   ├── dashboards/
│   │   └── provisioning/
│   └── elk/
│       ├── elasticsearch.yml
│       ├── logstash.conf
│       └── kibana.yml
│
├── tests/                               # 테스트
│   ├── backend/
│   │   ├── test_authentication.py
│   │   ├── test_chat.py
│   │   └── test_gateway.py
│   ├── microservices/
│   │   ├── test_search.py
│   │   ├── test_analytics.py
│   │   └── test_ml.py
│   ├── frontend/
│   │   ├── Chat.test.tsx
│   │   ├── Dashboard.test.tsx
│   │   └── Auth.test.tsx
│   └── integration/
│       ├── test_end_to_end.py
│       └── test_workflow.py
│
├── docs/                                # 문서
│   ├── project_management/              # 기존 문서들
│   ├── 08_system_architecture_diagrams.md
│   ├── API_REFERENCE.md                 # API 참조
│   ├── DEPLOYMENT_GUIDE.md              # 배포 가이드
│   └── DEVELOPMENT_SETUP.md             # 개발 환경 설정
│
├── .gitignore                           # Git 무시 파일
├── .dockerignore                        # Docker 무시 파일
├── README.md                            # 프로젝트 설명
├── LICENSE                              # 라이센스
└── package.json                         # 루트 패키지 설정
```

## API 키 및 환경 변수 설정

### 1. API 키 저장 위치 및 파일명

#### 개발 환경
```
config/.env.development
```

#### 운영 환경
```
config/.env.production
```

### 2. 환경 변수 구조

```bash
# OpenAI API 설정
OPENAI_API_KEY=your-openai-api-key
OPENAI_ORG_ID=your-organization-id (선택사항)
OPENAI_GPT4O_MODEL=gpt-4o
OPENAI_GPT4O_MINI_MODEL=gpt-4o-mini
OPENAI_MAX_TOKENS=4000
OPENAI_TEMPERATURE=0.7

# Naver API 설정
NAVER_CLIENT_ID=your-naver-client-id
NAVER_CLIENT_SECRET=your-naver-client-secret
NAVER_SEARCH_API_URL=https://openapi.naver.com/v1/search

# Anthropic API 설정 (Text2SQL용)
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-3-haiku-20240307

# 데이터베이스 설정
DATABASE_URL=sqlite:///./data/databases/main.db
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password (선택사항)

# Django 설정
SECRET_KEY=your-django-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0

# 마이크로서비스 포트 설정
SERVICE_SEARCH_PORT=8001
SERVICE_ANALYTICS_PORT=8002
SERVICE_CLIENT_PORT=8003
SERVICE_DOCUMENT_PORT=8004
SERVICE_CONVERSATION_PORT=8005
SERVICE_WIKI_PORT=8006
SERVICE_NEWS_PORT=8007
SERVICE_ML_PORT=8008
SERVICE_MEMORY_PORT=8009

# 모니터링 설정
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
ELASTICSEARCH_PORT=9200
KIBANA_PORT=5601

# 보안 설정
JWT_SECRET_KEY=your-jwt-secret-key
JWT_EXPIRATION_HOURS=24
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

### 3. 보안 고려사항

1. **API 키 보호**
   - `.env` 파일은 절대 Git에 커밋하지 않음
   - `.env.example` 파일만 커밋하여 구조 공유
   - 운영 환경에서는 환경 변수로 직접 설정

2. **Git 설정**
   ```bash
   # .gitignore에 추가
   config/.env.development
   config/.env.production
   *.env
   .env
   ```

3. **키 로테이션**
   - 정기적으로 API 키 교체
   - 개발/운영 환경 키 분리
   - 키 사용량 모니터링

### 4. 다음 단계 준비

프로젝트 구조가 완성되면 다음 단계들을 순차적으로 진행합니다:

1. **환경 설정 및 디렉토리 생성**
2. **Django 백엔드 기본 구조 구현**
3. **FastAPI 마이크로서비스 기본 틀 구현**
4. **React 프론트엔드 기본 구조 구현**
5. **LangGraph 오케스트레이터 구현**
6. **OpenAI 통합 및 멀티-GPT 시스템 구현**

각 단계는 독립적으로 테스트 가능하며, 점진적으로 통합됩니다. 