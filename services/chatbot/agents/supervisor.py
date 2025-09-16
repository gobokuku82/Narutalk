"""
Main supervisor agent orchestrator
LangGraph 0.6.7 with modular architecture
"""

from langgraph.graph import StateGraph, START, END

from ..schemas.context import AgentContext
from ..schemas.state import AgentState
from .supervisor.query_processor import QueryProcessor
from .supervisor.agent_executor import AgentExecutor
from .supervisor.response_generator import ResponseGenerator


class SupervisorAgent:
    """
    메인 Supervisor Agent - 모듈화된 워크플로우 오케스트레이터
    
    모듈 구성:
    - QueryProcessor: 질의 분석 및 계획 수립
    - AgentExecutor: 에이전트 라우팅 및 실행
    - ResponseGenerator: 결과 취합 및 응답 생성
    """
    
    def __init__(self):
        # 모듈 초기화
        self.query_processor = QueryProcessor()
        self.agent_executor = AgentExecutor()
        self.response_generator = ResponseGenerator()
        
        self.builder = None
        self.graph = None
        
    def create_graph(self) -> StateGraph:
        """StateGraph 생성 및 구성"""
        builder = StateGraph(
            state_schema=AgentState,
            context_schema=AgentContext
        )
        
        # 노드 추가 (모듈 메서드 연결)
        builder.add_node("analyze_query", self.query_processor.analyze_query)
        builder.add_node("create_plan", self.query_processor.create_plan)
        builder.add_node("route_agents", self.agent_executor.route_agents)
        builder.add_node("aggregate_results", self.response_generator.aggregate_results)
        builder.add_node("generate_response", self.response_generator.generate_response)
        
        # 엣지 연결
        builder.add_edge(START, "analyze_query")
        builder.add_edge("analyze_query", "create_plan")
        builder.add_edge("create_plan", "route_agents")
        
        # 조건부 엣지
        builder.add_conditional_edges(
            "route_agents",
            self.agent_executor.check_completion,
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
    
    def get_modules(self) -> dict:
        """모듈 접근자 (테스트/디버깅용)"""
        return {
            "query_processor": self.query_processor,
            "agent_executor": self.agent_executor,
            "response_generator": self.response_generator
        }