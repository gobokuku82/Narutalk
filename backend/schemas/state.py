"""
State schema for LangGraph 0.6.7
Defines mutable state that changes during graph execution
"""

from typing import TypedDict, List, Dict, Any, Optional, Annotated, Literal
from langchain_core.messages import AnyMessage
from langgraph.graph import add_messages
from datetime import datetime
from pydantic import BaseModel, Field


class AgentState(TypedDict):
    """
    그래프 실행 중 변경되는 상태 정보
    
    Attributes:
        messages: 대화 메시지 히스토리
        current_agent: 현재 실행 중인 에이전트
        agent_sequence: 실행된 에이전트 순서
        user_query: 원본 사용자 질의
        query_analysis: 질의 분석 결과
        execution_plan: 실행 계획
        analysis_results: 분석 에이전트 결과
        search_results: 검색 에이전트 결과  
        documents: 생성된 문서 목록
        customer_insights: 고객 분석 결과
        errors: 발생한 에러 목록
        metadata: 추가 메타데이터
        workflow_status: 워크플로우 상태
        interrupt_data: 인터럽트 데이터
        final_response: 최종 응답
    """
    
    # 메시지 관리
    messages: Annotated[List[AnyMessage], add_messages]
    
    # 워크플로우 상태
    current_agent: str
    agent_sequence: List[str]
    workflow_status: Literal["initializing", "analyzing", "executing", "interrupted", "completed", "failed"]
    
    # 사용자 질의 및 분석
    user_query: str
    query_analysis: Dict[str, Any]  # 의도, 엔티티, 필요 에이전트 등
    execution_plan: List[Dict[str, Any]]  # 실행 계획
    
    # 에이전트 실행 결과
    analysis_results: Optional[Dict[str, Any]]
    search_results: Optional[Dict[str, Any]]
    documents: List[Dict[str, Any]]
    customer_insights: Optional[Dict[str, Any]]
    
    # 에러 및 인터럽트
    errors: List[Dict[str, Any]]
    interrupt_data: Optional[Dict[str, Any]]
    
    # 메타데이터 및 최종 결과
    metadata: Dict[str, Any]
    final_response: Optional[str]


class QueryAnalysis(BaseModel):
    """질의 분석 결과"""
    intent: str = Field(description="사용자 의도")
    entities: List[Dict[str, str]] = Field(default_factory=list, description="추출된 엔티티")
    required_agents: List[str] = Field(default_factory=list, description="필요한 에이전트 목록")
    complexity: float = Field(default=0.5, description="질의 복잡도 (0-1)")
    keywords: List[str] = Field(default_factory=list, description="주요 키워드")
    
    
class ExecutionPlan(BaseModel):
    """실행 계획"""
    step_id: str = Field(description="단계 ID")
    agent_name: str = Field(description="실행할 에이전트")
    action: str = Field(description="수행할 작업")
    dependencies: List[str] = Field(default_factory=list, description="의존성 단계 ID")
    parallel: bool = Field(default=False, description="병렬 실행 가능 여부")
    estimated_time: int = Field(default=5, description="예상 소요 시간(초)")
    

class AnalysisResult(BaseModel):
    """분석 에이전트 결과"""
    query_type: str = Field(description="쿼리 타입")
    sql_query: Optional[str] = Field(default=None, description="생성된 SQL")
    data: List[Dict[str, Any]] = Field(default_factory=list, description="조회된 데이터")
    statistics: Dict[str, Any] = Field(default_factory=dict, description="통계 정보")
    visualization_config: Optional[Dict[str, Any]] = Field(default=None, description="시각화 설정")
    summary: str = Field(description="분석 요약")
    

class SearchResult(BaseModel):
    """검색 에이전트 결과"""
    internal_results: List[Dict[str, Any]] = Field(default_factory=list, description="내부 검색 결과")
    external_results: List[Dict[str, Any]] = Field(default_factory=list, description="외부 검색 결과")
    news_results: List[Dict[str, Any]] = Field(default_factory=list, description="뉴스 검색 결과")
    ranked_results: List[Dict[str, Any]] = Field(default_factory=list, description="랭킹된 전체 결과")
    requires_document: bool = Field(default=False, description="문서 생성 필요 여부")
    

class DocumentData(BaseModel):
    """생성된 문서 데이터"""
    document_id: str = Field(description="문서 ID")
    document_type: Literal["visit_report", "unofficial_report", "product_presentation", "presentation_result"] = Field(description="문서 타입")
    title: str = Field(description="문서 제목")
    content: str = Field(description="문서 내용")
    format: Literal["markdown", "html", "pdf", "docx"] = Field(default="markdown", description="문서 포맷")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="문서 메타데이터")
    created_at: datetime = Field(default_factory=datetime.now, description="생성 시간")
    

class CustomerInsight(BaseModel):
    """고객 분석 결과"""
    customer_id: str = Field(description="고객 ID")
    profile: Dict[str, Any] = Field(description="고객 프로필")
    preferences: List[str] = Field(default_factory=list, description="선호도")
    recommended_materials: List[Dict[str, Any]] = Field(default_factory=list, description="추천 자료")
    visit_history: List[Dict[str, Any]] = Field(default_factory=list, description="방문 이력")
    engagement_score: float = Field(default=0.0, description="참여도 점수")
    

class ErrorInfo(BaseModel):
    """에러 정보"""
    error_id: str = Field(description="에러 ID")
    agent_name: str = Field(description="에러 발생 에이전트")
    error_type: str = Field(description="에러 타입")
    message: str = Field(description="에러 메시지")
    timestamp: datetime = Field(default_factory=datetime.now, description="발생 시간")
    recoverable: bool = Field(default=True, description="복구 가능 여부")
    

class InterruptData(BaseModel):
    """인터럽트 데이터"""
    interrupt_id: str = Field(description="인터럽트 ID")
    reason: str = Field(description="인터럽트 이유")
    agent_name: str = Field(description="인터럽트 발생 에이전트")
    action: str = Field(description="승인 필요 작업")
    data: Dict[str, Any] = Field(description="관련 데이터")
    user_input_required: bool = Field(default=True, description="사용자 입력 필요 여부")
    options: List[str] = Field(default_factory=list, description="선택 옵션")
    

def create_initial_state(user_query: str) -> AgentState:
    """초기 상태 생성"""
    return {
        "messages": [],
        "current_agent": "supervisor",
        "agent_sequence": [],
        "workflow_status": "initializing",
        "user_query": user_query,
        "query_analysis": {},
        "execution_plan": [],
        "analysis_results": None,
        "search_results": None,
        "documents": [],
        "customer_insights": None,
        "errors": [],
        "interrupt_data": None,
        "metadata": {
            "start_time": datetime.now().isoformat(),
            "version": "0.0.1"
        },
        "final_response": None
    }