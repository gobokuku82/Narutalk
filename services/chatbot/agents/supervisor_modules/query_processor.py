"""
Query analysis and execution planning module
"""

from typing import Dict, Any, List
import json
import logging
from langgraph.runtime import Runtime
from langgraph.types import interrupt
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from ...schemas.context import AgentContext
from ...schemas.state import AgentState
from .utils import SupervisorUtils

logger = logging.getLogger(__name__)


class QueryProcessor:
    """질의 분석 및 실행 계획 수립"""
    
    def __init__(self):
        self.utils = SupervisorUtils()
    
    def analyze_query(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """사용자 질의 분석"""
        logger.info(f"Analyzing query for user: {runtime.context.user_id}")
        
        llm = self.utils.get_llm(runtime.context)
        
        system_prompt = """당신은 제약회사 직원을 위한 챗봇의 질의 분석기입니다.
        사용자의 질문을 분석하여 다음을 파악하세요:
        1. 사용자 의도 (분석, 검색, 문서생성, 고객분석 등)
        2. 필요한 에이전트 목록
        3. 주요 엔티티 (거래처명, 제품명, 기간 등)
        4. 질의 복잡도 (0-1)
        
        결과를 JSON 형식으로 반환하세요."""
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=state["user_query"])
        ]
        
        response = llm.invoke(messages)
        
        try:
            analysis = json.loads(response.content)
        except json.JSONDecodeError:
            analysis = self._get_default_analysis()
        
        return {
            "query_analysis": analysis,
            "workflow_status": "analyzing",
            "messages": [
                AIMessage(content=f"질의 분석 완료: {analysis.get('intent', 'unknown')}")
            ]
        }
    
    def create_plan(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """실행 계획 수립"""
        logger.info("Creating execution plan")
        
        analysis = state.get("query_analysis", {})
        required_agents = analysis.get("required_agents", ["search"])
        
        # 실행 계획 생성
        plan = self._build_execution_plan(required_agents)
        
        # 인터럽트 처리
        if runtime.context.interrupt_mode != "none":
            plan = self._handle_interrupts(plan, runtime.context)
            if plan is None:
                return {
                    "workflow_status": "interrupted",
                    "interrupt_data": {
                        "reason": "User declined action"
                    }
                }
        
        return {
            "execution_plan": plan,
            "workflow_status": "executing",
            "messages": [
                AIMessage(content=f"실행 계획 수립 완료: {len(plan)}개 단계")
            ]
        }
    
    def _build_execution_plan(self, required_agents: List[str]) -> List[Dict]:
        """실행 계획 구성"""
        plan = []
        for idx, agent in enumerate(required_agents):
            plan.append({
                "step_id": f"step_{idx+1}",
                "agent_name": agent,
                "action": self.utils.get_agent_action(agent),
                "dependencies": [] if idx == 0 else [f"step_{idx}"],
                "parallel": self.utils.can_run_parallel(agent, required_agents),
                "estimated_time": self.utils.estimate_time(agent)
            })
        return plan
    
    def _handle_interrupts(
        self, 
        plan: List[Dict], 
        context: AgentContext
    ) -> List[Dict]:
        """인터럽트 처리"""
        for step in plan:
            if self.utils.requires_approval(step["action"], context):
                approval = interrupt(
                    f"다음 작업을 수행하시겠습니까?\n"
                    f"에이전트: {step['agent_name']}\n"
                    f"작업: {step['action']}"
                )
                if not approval:
                    return None
        return plan
    
    def _get_default_analysis(self) -> Dict:
        """기본 분석 결과"""
        return {
            "intent": "search",
            "required_agents": ["search"],
            "entities": [],
            "complexity": 0.5,
            "keywords": []
        }