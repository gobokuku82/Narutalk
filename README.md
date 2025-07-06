# 🏥 Narutalk - 의료업계 QA 챗봇 시스템

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Django](https://img.shields.io/badge/Django-4.2+-green.svg)](https://www.djangoproject.com/)
[![React](https://img.shields.io/badge/React-18.2+-blue.svg)](https://reactjs.org/)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-teal.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Narutalk**은 의료업계 전용 AI 기반 QA 챗봇 시스템입니다. GPT-4o와 LangGraph를 활용하여 의료진이 빠르고 정확한 정보를 얻을 수 있도록 설계되었습니다.

![Narutalk 시스템 아키텍처](https://via.placeholder.com/800x400?text=Narutalk+System+Architecture)

## 🚀 **주요 기능**

### 💬 **AI 챗봇**
- GPT-4o 기반 의료 전문 답변
- 실시간 채팅 (WebSocket)
- 다중 세션 관리
- 의료 카테고리별 분류

### 🔐 **사용자 관리**
- 역할 기반 접근 제어 (의사, 간호사, 관리자)
- JWT 기반 인증
- 의료진 전용 기능

### 🎨 **현대적 UI**
- Material-UI 기반 반응형 디자인
- 다크/라이트 테마 지원
- 모바일 친화적 인터페이스

### 📊 **데이터 분석**
- 의료 문서 검색 및 분석
- 실시간 차트 및 통계
- 성능 모니터링

## 🏗️ **시스템 아키텍처**

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   React UI      │    │   Django API    │    │   FastAPI       │
│   (Port 3000)   │◄──►│   (Port 8000)   │◄──►│   (Port 8001)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   WebSocket     │    │   Database      │    │   LangGraph     │
│   (Real-time)   │    │   (SQLite)      │    │   (AI Flow)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 **시스템 요구사항**

### 필수 소프트웨어
- **Python**: 3.10 이상
- **Node.js**: 18.x 이상 (LTS 권장)
- **npm**: 9.x 이상

### 권장 사양
- **RAM**: 8GB 이상
- **Storage**: 2GB 이상 여유 공간
- **OS**: Windows 10/11, macOS 10.15+, Ubuntu 20.04+

## 🛠️ **설치 방법**

### 📥 **자동 설치 (Windows)**
```bash
# 1. 저장소 클론
git clone https://github.com/your-username/narutalk.git
cd narutalk

# 2. 자동 설치 실행
install.bat
```

### 🔧 **수동 설치**
```bash
# 1. 가상환경 생성
python -m venv .venv

# 2. 가상환경 활성화
# Windows:
.\.venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate

# 3. Python 패키지 설치
pip install -r requirements/development.txt

# 4. Node.js 패키지 설치
npm install

# 5. 데이터베이스 마이그레이션
python manage.py makemigrations
python manage.py migrate

# 6. 환경 변수 설정
cp config/env.example .env
# .env 파일을 편집하여 API 키 등을 설정
```

### 🔑 **환경 변수 설정**
```env
# OpenAI API 키 (필수)
OPENAI_API_KEY=sk-your-openai-api-key-here

# Anthropic API 키 (선택)
ANTHROPIC_API_KEY=sk-ant-your-anthropic-api-key-here

# Django 비밀키
DJANGO_SECRET_KEY=your-secret-key-here
```

## 🚀 **실행 방법**

### 🎯 **간단한 실행 (권장)**
```bash
# Windows PowerShell
powershell -ExecutionPolicy Bypass -File start_narutalk.ps1

# 또는 배치 파일
start_narutalk.bat

# 또는 Python 스크립트
python run_narutalk.py
```

### 🔄 **수동 실행**
```bash
# 터미널 1: Django 백엔드
.\.venv\Scripts\activate
python manage.py runserver

# 터미널 2: React 프론트엔드
npm run dev

# 터미널 3: FastAPI 서비스 (선택사항)
.\.venv\Scripts\activate
cd service_8001_search
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

### 🌐 **접속 URL**
- **메인 웹사이트**: http://localhost:3000
- **Django 관리자**: http://localhost:8000/admin
- **FastAPI 문서**: http://localhost:8001/docs

## 📚 **API 문서**

### Django REST API
- **인증**: `/api/auth/`
- **채팅**: `/api/chat/`
- **사용자**: `/api/users/`
- **관리자**: `/api/admin/`

### FastAPI 마이크로서비스
- **검색**: `/search/`
- **분석**: `/analyze/`
- **예측**: `/predict/`

### WebSocket
- **실시간 채팅**: `ws://localhost:8000/ws/chat/`

## 🧪 **테스트**

### 단위 테스트
```bash
# Django 테스트
python manage.py test

# Pytest 실행
pytest

# 커버리지 포함
pytest --cov=apps --cov-report=html
```

### 통합 테스트
```bash
# 전체 시스템 테스트
python test_workflow.py

# LangGraph 테스트
python langgraph_orchestrator/test_workflow.py
```

## 📦 **배포**

### 🐳 **Docker 배포**
```bash
# Docker 이미지 빌드
docker build -t narutalk:latest .

# 컨테이너 실행
docker run -p 3000:3000 -p 8000:8000 narutalk:latest
```

### 🌐 **프로덕션 배포**
```bash
# 프로덕션 패키지 설치
pip install -r requirements/production.txt

# 정적 파일 수집
python manage.py collectstatic

# Gunicorn으로 실행
gunicorn config.wsgi:application --bind 0.0.0.0:8000
```

## 🔧 **개발**

### 🎨 **코드 스타일**
```bash
# 코드 포매팅
black .
isort .

# 린팅
flake8 .
eslint src/
```

### 📝 **커밋 규칙**
```bash
feat: 새로운 기능 추가
fix: 버그 수정
docs: 문서 업데이트
style: 코드 스타일 변경
refactor: 코드 리팩토링
test: 테스트 추가/수정
chore: 빌드 프로세스 또는 보조 도구 변경
```

## 🤝 **기여하기**

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📄 **라이선스**

이 프로젝트는 MIT 라이선스 하에 배포됩니다. 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 🆘 **문제 해결**

### 자주 묻는 질문 (FAQ)

**Q: 'vite' 명령어를 찾을 수 없다는 오류가 발생합니다.**
```bash
# 전역 설치
npm install -g vite

# 또는 npx 사용
npx vite
```

**Q: Django 마이그레이션 오류가 발생합니다.**
```bash
# 마이그레이션 파일 삭제 후 재생성
python manage.py makemigrations --empty your_app_name
python manage.py migrate
```

**Q: React 프론트엔드가 로드되지 않습니다.**
```bash
# 캐시 삭제 후 재설치
npm cache clean --force
rm -rf node_modules package-lock.json
npm install
```

### 🐛 **버그 리포트**
버그를 발견하셨나요? [Issues](https://github.com/your-username/narutalk/issues)에 리포트해주세요.

### 💬 **지원**
- 📧 Email: support@narutalk.com
- 💬 Discord: [Narutalk Community](https://discord.gg/narutalk)
- 📖 Wiki: [Documentation](https://github.com/your-username/narutalk/wiki)

---

<p align="center">
  <b>🏥 의료업계를 위한 AI 솔루션 - Narutalk</b><br>
  Made with ❤️ by the Narutalk Team
</p> 