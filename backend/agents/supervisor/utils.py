"""
Utility functions for supervisor agent
"""

from typing import List
from langchain_openai import ChatOpenAI

from ...schemas.context import AgentContext


class SupervisorUtils:
    """Supervisor 공통 유틸리티 함수"""
    
    @staticmethod
    def get_llm(context: AgentContext):
        """LLM 인스턴스 생성"""
        if context.model_provider == "openai":
            return ChatOpenAI(
                model=context.model_name,
                api_key=context.api_key,
                temperature=0.7
            )
        # anthropic 등 다른 프로바이더 추가 가능
        raise ValueError(f"Unsupported model provider: {context.model_provider}")
    
    @staticmethod
    def get_agent_action(agent_name: str) -> str:
        """에이전트별 기본 작업"""
        actions = {
            "analysis": "데이터 분석 및 통계 생성",
            "search": "정보 검색 및 수집",
            "document": "문서 자동 생성",
            "customer": "고객 데이터 분석"
        }
        return actions.get(agent_name, "작업 수행")
    
    @staticmethod
    def can_run_parallel(agent: str, all_agents: List[str]) -> bool:
        """병렬 실행 가능 여부"""
        # 검색과 고객분석은 병렬 가능
        parallel_compatible = ["search", "customer"]
        return agent in parallel_compatible
    
    @staticmethod
    def estimate_time(agent: str) -> int:
        """예상 실행 시간 (초)"""
        times = {
            "analysis": 10,
            "search": 5,
            "document": 15,
            "customer": 8
        }
        return times.get(agent, 5)
    
    @staticmethod
    def requires_approval(action: str, context: AgentContext) -> bool:
        """승인 필요 여부"""
        if context.interrupt_mode == "none":
            return False
        if context.interrupt_mode == "all":
            return True
            
        # critical mode - 특정 작업만 승인 필요
        approval_actions = ["sql_execution", "document_generation", "external_api_call"]
        return any(a in action.lower() for a in approval_actions)