"""
Result aggregation and response generation module
"""

from typing import Dict, Any
import logging
from datetime import datetime
from langgraph.runtime import Runtime
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ...schemas.context import AgentContext
from ...schemas.state import AgentState
from .utils import SupervisorUtils

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """결과 취합 및 응답 생성"""
    
    def __init__(self):
        self.utils = SupervisorUtils()
    
    def aggregate_results(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """결과 취합"""
        logger.info("Aggregating results")
        
        # 각 에이전트 결과 수집
        results = self._collect_results(state)
        
        # None 값 제거
        results = {k: v for k, v in results.items() if v is not None}
        
        return {
            "metadata": {
                **state.get("metadata", {}),
                "aggregated_at": datetime.now().isoformat(),
                "total_agents": len(state.get("agent_sequence", [])),
                "results_count": len(results)
            }
        }
    
    def generate_response(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """최종 응답 생성"""
        logger.info("Generating final response")
        
        llm = self.utils.get_llm(runtime.context)
        
        # 결과 요약
        results_summary = self._summarize_results(state)
        
        # 응답 생성
        response = self._create_response(
            llm, 
            state["user_query"],
            results_summary,
            runtime.context.language
        )
        
        return {
            "final_response": response.content,
            "workflow_status": "completed",
            "messages": [AIMessage(content=response.content)],
            "metadata": {
                **state.get("metadata", {}),
                "completed_at": datetime.now().isoformat()
            }
        }
    
    def _collect_results(self, state: AgentState) -> Dict:
        """에이전트 결과 수집"""
        return {
            "analysis": state.get("analysis_results"),
            "search": state.get("search_results"),
            "documents": state.get("documents"),
            "customer": state.get("customer_insights")
        }
    
    def _summarize_results(self, state: AgentState) -> str:
        """결과 요약"""
        summary = []
        
        if state.get("analysis_results"):
            summary.append(f"분석 결과: {state['analysis_results'].get('summary', 'N/A')}")
        
        if state.get("search_results"):
            count = len(state['search_results'].get('ranked_results', []))
            summary.append(f"검색 결과: {count}건")
        
        if state.get("documents"):
            summary.append(f"생성된 문서: {len(state['documents'])}개")
        
        if state.get("customer_insights"):
            summary.append(f"고객 인사이트: 포함")
        
        return "\n".join(summary) if summary else "결과 없음"
    
    def _create_response(
        self,
        llm,
        user_query: str,
        results_summary: str,
        language: str
    ):
        """LLM 응답 생성"""
        system_prompt = f"""당신은 제약회사 직원을 위한 전문 AI 어시스턴트입니다.
        다음 분석 결과를 바탕으로 {'한국어로' if language == 'ko' else '영어로'} 
        명확하고 전문적인 응답을 생성하세요.
        
        사용자 질문: {user_query}
        
        분석 결과:
        {results_summary}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="위 결과를 바탕으로 종합적인 답변을 작성해주세요.")
        ]
        
        return llm.invoke(messages)