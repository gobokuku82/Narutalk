"""
Supervisor Agent for orchestrating multi-agent workflow
LangGraph 0.6.7 with Runtime[Context] API
"""

from typing import Dict, Any, List, Literal, Optional
from langgraph.graph import StateGraph, START, END
from langgraph.runtime import Runtime
from langgraph.types import Send, interrupt, Command
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_openai import ChatOpenAI
import json
import logging
from datetime import datetime

from ..schemas.context import AgentContext
from ..schemas.state import AgentState, QueryAnalysis, ExecutionPlan

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    Supervisor Agent - 전체 워크플로우를 관리하는 메인 에이전트
    
    주요 기능:
    1. 사용자 질의 분석
    2. 실행 계획 수립
    3. 하위 에이전트 라우팅
    4. 병렬/순차 실행 관리
    5. 결과 취합 및 응답 생성
    """
    
    def __init__(self):
        self.builder = None
        self.graph = None
        
    def create_graph(self) -> StateGraph:
        """StateGraph 생성 및 구성"""
        builder = StateGraph(
            state_schema=AgentState,
            context_schema=AgentContext
        )
        
        # 노드 추가
        builder.add_node("analyze_query", self.analyze_query_node)
        builder.add_node("create_plan", self.create_plan_node)
        builder.add_node("route_agents", self.route_agents_node)
        builder.add_node("aggregate_results", self.aggregate_results_node)
        builder.add_node("generate_response", self.generate_response_node)
        
        # 엣지 연결
        builder.add_edge(START, "analyze_query")
        builder.add_edge("analyze_query", "create_plan")
        builder.add_edge("create_plan", "route_agents")
        builder.add_conditional_edges(
            "route_agents",
            self.check_completion,
            {
                "continue": "route_agents",
                "aggregate": "aggregate_results",
                "error": "generate_response"
            }
        )
        builder.add_edge("aggregate_results", "generate_response")
        builder.add_edge("generate_response", END)
        
        self.builder = builder
        return builder
    
    def analyze_query_node(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """사용자 질의 분석"""
        logger.info(f"Analyzing query for user: {runtime.context.user_id}")
        
        # LLM 초기화
        llm = self._get_llm(runtime.context)
        
        # 질의 분석 프롬프트
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
            # 파싱 실패 시 기본값
            analysis = {
                "intent": "search",
                "required_agents": ["search"],
                "entities": [],
                "complexity": 0.5,
                "keywords": []
            }
        
        return {
            "query_analysis": analysis,
            "workflow_status": "analyzing",
            "messages": [
                AIMessage(content=f"질의 분석 완료: {analysis.get('intent', 'unknown')}")
            ]
        }
    
    def create_plan_node(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """실행 계획 수립"""
        logger.info("Creating execution plan")
        
        analysis = state.get("query_analysis", {})
        required_agents = analysis.get("required_agents", ["search"])
        
        # 실행 계획 생성
        plan = []
        for idx, agent in enumerate(required_agents):
            plan.append({
                "step_id": f"step_{idx+1}",
                "agent_name": agent,
                "action": self._get_agent_action(agent),
                "dependencies": [] if idx == 0 else [f"step_{idx}"],
                "parallel": self._can_run_parallel(agent, required_agents),
                "estimated_time": self._estimate_time(agent)
            })
        
        # 인터럽트 필요 여부 확인
        if runtime.context.interrupt_mode != "none":
            for step in plan:
                if self._requires_approval(step["action"], runtime.context):
                    # 사용자 승인 요청
                    approval = interrupt(
                        f"다음 작업을 수행하시겠습니까?\n"
                        f"에이전트: {step['agent_name']}\n"
                        f"작업: {step['action']}"
                    )
                    if not approval:
                        return {
                            "workflow_status": "interrupted",
                            "interrupt_data": {
                                "reason": "User declined action",
                                "step": step
                            }
                        }
        
        return {
            "execution_plan": plan,
            "workflow_status": "executing",
            "messages": [
                AIMessage(content=f"실행 계획 수립 완료: {len(plan)}개 단계")
            ]
        }
    
    def route_agents_node(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """에이전트 라우팅 및 실행"""
        logger.info("Routing to agents")
        
        plan = state.get("execution_plan", [])
        current_step = self._get_next_step(plan, state)
        
        if not current_step:
            return {"workflow_status": "completed"}
        
        agent_name = current_step["agent_name"]
        
        # 병렬 실행 가능한 에이전트 확인
        parallel_agents = []
        if runtime.context.parallel_execution and current_step.get("parallel"):
            parallel_agents = self._get_parallel_agents(plan, current_step)
        
        # Send를 사용한 에이전트 호출
        sends = []
        if parallel_agents:
            # 병렬 실행
            for agent in parallel_agents:
                sends.append(Send(f"{agent}_agent", {
                    "state": state,
                    "context": runtime.context
                }))
        else:
            # 단일 실행
            sends.append(Send(f"{agent_name}_agent", {
                "state": state,
                "context": runtime.context
            }))
        
        # 에이전트 시퀀스 업데이트
        executed_agents = [agent_name] + [a["agent_name"] for a in parallel_agents]
        
        return {
            "current_agent": agent_name,
            "agent_sequence": state.get("agent_sequence", []) + executed_agents,
            "messages": [
                AIMessage(content=f"실행 중: {', '.join(executed_agents)}")
            ]
        }
    
    def aggregate_results_node(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """결과 취합"""
        logger.info("Aggregating results")
        
        # 각 에이전트 결과 취합
        results = {
            "analysis": state.get("analysis_results"),
            "search": state.get("search_results"),
            "documents": state.get("documents"),
            "customer": state.get("customer_insights")
        }
        
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
    
    def generate_response_node(
        self,
        state: AgentState,
        runtime: Runtime[AgentContext]
    ) -> Dict[str, Any]:
        """최종 응답 생성"""
        logger.info("Generating final response")
        
        llm = self._get_llm(runtime.context)
        
        # 결과 요약
        results_summary = self._summarize_results(state)
        
        # 응답 생성 프롬프트
        system_prompt = f"""당신은 제약회사 직원을 위한 전문 AI 어시스턴트입니다.
        다음 분석 결과를 바탕으로 {'한국어로' if runtime.context.language == 'ko' else '영어로'} 
        명확하고 전문적인 응답을 생성하세요.
        
        사용자 질문: {state['user_query']}
        
        분석 결과:
        {results_summary}
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="위 결과를 바탕으로 종합적인 답변을 작성해주세요.")
        ]
        
        response = llm.invoke(messages)
        
        return {
            "final_response": response.content,
            "workflow_status": "completed",
            "messages": [
                AIMessage(content=response.content)
            ],
            "metadata": {
                **state.get("metadata", {}),
                "completed_at": datetime.now().isoformat()
            }
        }
    
    def check_completion(self, state: AgentState) -> Literal["continue", "aggregate", "error"]:
        """완료 상태 확인"""
        if state.get("errors"):
            return "error"
        
        plan = state.get("execution_plan", [])
        executed = state.get("agent_sequence", [])
        
        # 모든 계획된 에이전트가 실행되었는지 확인
        planned_agents = [step["agent_name"] for step in plan]
        if all(agent in executed for agent in planned_agents):
            return "aggregate"
        
        return "continue"
    
    # Helper methods
    def _get_llm(self, context: AgentContext):
        """LLM 인스턴스 생성"""
        if context.model_provider == "openai":
            return ChatOpenAI(
                model=context.model_name,
                api_key=context.api_key,
                temperature=0.7
            )
        # anthropic 등 다른 프로바이더 추가 가능
        raise ValueError(f"Unsupported model provider: {context.model_provider}")
    
    def _get_agent_action(self, agent_name: str) -> str:
        """에이전트별 기본 작업"""
        actions = {
            "analysis": "데이터 분석 및 통계 생성",
            "search": "정보 검색 및 수집",
            "document": "문서 자동 생성",
            "customer": "고객 데이터 분석"
        }
        return actions.get(agent_name, "작업 수행")
    
    def _can_run_parallel(self, agent: str, all_agents: List[str]) -> bool:
        """병렬 실행 가능 여부"""
        # 검색과 고객분석은 병렬 가능
        parallel_compatible = ["search", "customer"]
        return agent in parallel_compatible
    
    def _estimate_time(self, agent: str) -> int:
        """예상 실행 시간 (초)"""
        times = {
            "analysis": 10,
            "search": 5,
            "document": 15,
            "customer": 8
        }
        return times.get(agent, 5)
    
    def _requires_approval(self, action: str, context: AgentContext) -> bool:
        """승인 필요 여부"""
        approval_actions = ["sql_execution", "document_generation", "external_api_call"]
        return any(a in action.lower() for a in approval_actions)
    
    def _get_next_step(self, plan: List[Dict], state: AgentState) -> Optional[Dict]:
        """다음 실행할 단계 찾기"""
        executed = state.get("agent_sequence", [])
        for step in plan:
            if step["agent_name"] not in executed:
                # 의존성 확인
                deps = step.get("dependencies", [])
                if all(d in executed for d in deps):
                    return step
        return None
    
    def _get_parallel_agents(self, plan: List[Dict], current_step: Dict) -> List[Dict]:
        """병렬 실행 가능한 에이전트 찾기"""
        parallel = []
        for step in plan:
            if (step != current_step and 
                step.get("parallel") and 
                step["agent_name"] not in state.get("agent_sequence", [])):
                parallel.append(step)
        return parallel
    
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