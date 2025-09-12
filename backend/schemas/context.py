"""
Context schema for LangGraph 0.6.7 Runtime API
Defines immutable runtime configuration for the agent system
"""

from dataclasses import dataclass, field
from typing import Optional, Literal, Dict, List
from datetime import datetime
import os


@dataclass
class AgentContext:
    """
    런타임 컨텍스트 - 실행 중 변하지 않는 설정 정보
    
    Attributes:
        user_id: 사용자 고유 식별자
        company_id: 제약회사 고유 식별자
        session_id: 현재 세션 ID
        model_provider: LLM 제공자 (openai, anthropic)
        model_name: 사용할 모델명
        api_key: API 키 (환경변수에서 자동 로드)
        interrupt_mode: 인터럽트 모드 설정
        approval_required: 각 작업별 승인 필요 여부
        max_retries: 최대 재시도 횟수
        timeout: 작업 타임아웃 (초)
        language: 응답 언어 설정
        enable_cache: 캐싱 활성화 여부
        parallel_execution: 병렬 실행 허용 여부
        created_at: 컨텍스트 생성 시간
    """
    
    # 필수 필드
    user_id: str
    company_id: str
    session_id: str
    
    # LLM 설정
    model_provider: Literal["openai", "anthropic"] = "openai"
    model_name: str = "gpt-4o"
    _api_key: Optional[str] = field(default=None, repr=False)
    
    # Interrupt 설정
    interrupt_mode: Literal["all", "critical", "none"] = "critical"
    approval_required: Dict[str, bool] = field(default_factory=lambda: {
        "sql_execution": True,
        "document_generation": False,
        "external_api_call": True,
        "data_modification": True
    })
    
    # 실행 설정
    max_retries: int = 3
    timeout: int = 300  # 5 minutes
    language: Literal["ko", "en"] = "ko"
    
    # 성능 설정
    enable_cache: bool = True
    parallel_execution: bool = True
    
    # 메타데이터
    created_at: datetime = field(default_factory=datetime.now)
    
    @property
    def api_key(self) -> str:
        """API 키를 환경변수에서 가져오거나 설정된 값 반환"""
        if self._api_key:
            return self._api_key
        
        if self.model_provider == "openai":
            return os.getenv("OPENAI_API_KEY", "")
        elif self.model_provider == "anthropic":
            return os.getenv("ANTHROPIC_API_KEY", "")
        return ""
    
    @api_key.setter
    def api_key(self, value: str):
        """API 키 설정"""
        self._api_key = value
    
    def should_interrupt(self, action: str) -> bool:
        """특정 작업에 대해 인터럽트가 필요한지 판단"""
        if self.interrupt_mode == "none":
            return False
        if self.interrupt_mode == "all":
            return True
        # critical mode
        return self.approval_required.get(action, False)
    
    def to_dict(self) -> Dict:
        """Context를 딕셔너리로 변환 (API 키 제외)"""
        data = {
            "user_id": self.user_id,
            "company_id": self.company_id,
            "session_id": self.session_id,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "interrupt_mode": self.interrupt_mode,
            "approval_required": self.approval_required,
            "max_retries": self.max_retries,
            "timeout": self.timeout,
            "language": self.language,
            "enable_cache": self.enable_cache,
            "parallel_execution": self.parallel_execution,
            "created_at": self.created_at.isoformat()
        }
        return data


@dataclass
class AgentMetadata:
    """에이전트별 추가 메타데이터"""
    agent_name: str
    agent_type: Literal["analysis", "search", "document", "customer"]
    capabilities: List[str] = field(default_factory=list)
    required_tools: List[str] = field(default_factory=list)
    priority: int = 1  # 1-5, 낮을수록 높은 우선순위