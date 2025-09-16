# SupervisorAgent 시스템 상세 코드 분석 보고서

## 목차
1. [시스템 개요](#1-시스템-개요)
2. [LangGraph 핵심 개념](#2-langgraph-핵심-개념)
3. [State 관리 메커니즘](#3-state-관리-메커니즘)
4. [코드 실행 흐름 (Line by Line)](#4-코드-실행-흐름-line-by-line)
5. [LLM 호출 분석](#5-llm-호출-분석)
6. [함수별 입출력 명세](#6-함수별-입출력-명세)
7. [미사용 코드 분석](#7-미사용-코드-분석)

---

## 1. 시스템 개요

### 아키텍처 구조
```
FastAPI → LangGraph StateGraph → 5개 노드 순차 실행 → 응답
         ↓
    AsyncSqliteSaver (상태 저장)
```

### 핵심 컴포넌트
- **StateGraph**: LangGraph의 워크플로우 그래프
- **AgentState**: 가변 상태 (TypedDict)
- **AgentContext**: 불변 설정 (dataclass)
- **Runtime**: LangGraph 런타임 API

---

## 2. LangGraph 핵심 개념

### 2.1 StateGraph 클래스
```python
from langgraph.graph import StateGraph, START, END

builder = StateGraph(
    state_schema=AgentState,    # TypedDict 스키마
    context_schema=AgentContext  # Runtime Context 스키마
)
```

**파라미터 설명:**
- `state_schema`: 그래프 실행 중 변경되는 상태 정의
- `context_schema`: 실행 중 불변인 설정 정의

### 2.2 노드 추가 메서드
```python
builder.add_node("node_name", callable_function)
```
- **"node_name"**: 노드 식별자 (문자열)
- **callable_function**: `(state, runtime) -> dict` 시그니처 함수
- **반환값**: State 업데이트 딕셔너리

### 2.3 엣지 연결 메서드

#### 단순 엣지
```python
builder.add_edge(START, "analyze_query")  # 시작 → 첫 노드
builder.add_edge("analyze_query", "create_plan")  # 노드 간 연결
```

#### 조건부 엣지
```python
builder.add_conditional_edges(
    "route_agents",              # 소스 노드
    self.agent_executor.check_completion,  # 조건 함수
    {
        "continue": "route_agents",     # 조건값: 타겟노드
        "aggregate": "aggregate_results",
        "error": "generate_response"
    }
)
```
- **조건 함수**: `(state) -> Literal["continue", "aggregate", "error"]`
- **반환값에 따라 다른 노드로 분기**

### 2.4 그래프 컴파일
```python
graph = builder.compile(
    checkpointer=AsyncSqliteSaver,  # 상태 저장소
    durability="async"               # 저장 모드
)
```

---

## 3. State 관리 메커니즘

### 3.1 AgentState 구조 (schemas/state.py)

```python
class AgentState(TypedDict):
    # 메시지 관리 (특수 Annotated 타입)
    messages: Annotated[List[AnyMessage], add_messages]

    # 워크플로우 상태
    current_agent: str
    agent_sequence: List[str]
    workflow_status: Literal["initializing", "analyzing", "executing",
                           "interrupted", "completed", "failed"]

    # 질의 분석
    user_query: str
    query_analysis: Dict[str, Any]
    execution_plan: List[Dict[str, Any]]

    # 에이전트 결과 (모두 Optional)
    analysis_results: Optional[Dict[str, Any]]
    search_results: Optional[Dict[str, Any]]
    documents: List[Dict[str, Any]]
    customer_insights: Optional[Dict[str, Any]]

    # 기타
    errors: List[Dict[str, Any]]
    interrupt_data: Optional[Dict[str, Any]]
    metadata: Dict[str, Any]
    final_response: Optional[str]
```

### 3.2 State 업데이트 메커니즘

**노드 함수 반환값이 State를 업데이트:**
```python
def analyze_query(state: AgentState, runtime: Runtime) -> Dict:
    return {
        "query_analysis": {...},      # 덮어쓰기
        "workflow_status": "analyzing",  # 덮어쓰기
        "messages": [AIMessage(...)]     # add_messages로 추가
    }
```

**특수 Annotated 타입 동작:**
```python
messages: Annotated[List[AnyMessage], add_messages]
# add_messages 리듀서가 새 메시지를 기존 리스트에 추가
# 다른 필드는 단순 덮어쓰기
```

---

## 4. 코드 실행 흐름 (Line by Line)

### 4.1 요청 진입 (main.py)

```python
# LINE 147-186: POST /chat 엔드포인트
@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    # LINE 152: 세션 ID 생성 또는 재사용
    session_id = request.session_id or str(uuid.uuid4())

    # LINE 155-159: AgentContext 생성 (불변 설정)
    context = AgentContext(
        user_id=request.user_id,        # 필수
        company_id=request.company_id,  # 필수
        session_id=session_id           # 필수
    )
    # 기본값 자동 설정:
    # - model_provider: "openai"
    # - model_name: "gpt-4o"
    # - interrupt_mode: "critical"
    # - language: "ko"
    # - parallel_execution: True

    # LINE 162-165: 컨텍스트 오버라이드 (선택적)
    if request.context_override:
        for key, value in request.context_override.items():
            if hasattr(context, key):
                setattr(context, key, value)

    # LINE 168: 초기 State 생성
    initial_state = create_initial_state(request.query)
    # 반환값:
    # {
    #     "messages": [],
    #     "current_agent": "supervisor",
    #     "agent_sequence": [],
    #     "workflow_status": "initializing",
    #     "user_query": request.query,
    #     "query_analysis": {},
    #     "execution_plan": [],
    #     "analysis_results": None,
    #     "search_results": None,
    #     "documents": [],
    #     "customer_insights": None,
    #     "errors": [],
    #     "interrupt_data": None,
    #     "metadata": {
    #         "start_time": "2024-XX-XX...",
    #         "version": "0.0.1"
    #     },
    #     "final_response": None
    # }

    # LINE 171: 체크포인터 설정 생성
    config = checkpointer_manager.get_config(session_id)
    # 반환값:
    # {
    #     "configurable": {
    #         "thread_id": session_id,
    #         "checkpoint_ns": "",
    #         "checkpoint_id": None
    #     }
    # }

    # LINE 172-176: 그래프 실행 (비동기)
    result = await app.state.graph.ainvoke(
        initial_state,    # 초기 상태
        context=context,  # Runtime 컨텍스트
        config=config     # 체크포인터 설정
    )
```

### 4.2 그래프 생성 (supervisor.py)

```python
# LINE 34-68: 그래프 구성
def create_graph(self) -> StateGraph:
    # LINE 36-39: StateGraph 인스턴스 생성
    builder = StateGraph(
        state_schema=AgentState,      # TypedDict 스키마
        context_schema=AgentContext    # dataclass 스키마
    )

    # LINE 42-46: 노드 추가 (함수 레퍼런스 전달)
    builder.add_node("analyze_query", self.query_processor.analyze_query)
    builder.add_node("create_plan", self.query_processor.create_plan)
    builder.add_node("route_agents", self.agent_executor.route_agents)
    builder.add_node("aggregate_results", self.response_generator.aggregate_results)
    builder.add_node("generate_response", self.response_generator.generate_response)

    # LINE 49-51: 순차 엣지 연결
    builder.add_edge(START, "analyze_query")          # 시작 → 분석
    builder.add_edge("analyze_query", "create_plan")  # 분석 → 계획
    builder.add_edge("create_plan", "route_agents")   # 계획 → 라우팅

    # LINE 54-62: 조건부 엣지 (route_agents 이후)
    builder.add_conditional_edges(
        "route_agents",
        self.agent_executor.check_completion,  # 조건 평가 함수
        {
            "continue": "route_agents",      # 계속 실행
            "aggregate": "aggregate_results", # 결과 취합
            "error": "generate_response"      # 에러 처리
        }
    )

    # LINE 64-65: 마지막 엣지
    builder.add_edge("aggregate_results", "generate_response")
    builder.add_edge("generate_response", END)
```

### 4.3 Node 1: analyze_query (query_processor.py)

```python
# LINE 25-62: 질의 분석 노드
def analyze_query(
    self,
    state: AgentState,              # 현재 상태
    runtime: Runtime[AgentContext]  # 런타임 컨텍스트
) -> Dict[str, Any]:
    # LINE 31: 로깅
    logger.info(f"Analyzing query for user: {runtime.context.user_id}")

    # LINE 33: LLM 인스턴스 생성 🔴
    llm = self.utils.get_llm(runtime.context)
    # utils.py LINE 16-24:
    # if context.model_provider == "openai":
    #     return ChatOpenAI(
    #         model="gpt-4o",
    #         api_key=os.getenv("OPENAI_API_KEY"),
    #         temperature=0.7
    #     )

    # LINE 35-42: 시스템 프롬프트
    system_prompt = """당신은 제약회사 직원을 위한 챗봇의 질의 분석기입니다.
    사용자의 질문을 분석하여 다음을 파악하세요:
    1. 사용자 의도 (분석, 검색, 문서생성, 고객분석 등)
    2. 필요한 에이전트 목록
    3. 주요 엔티티 (거래처명, 제품명, 기간 등)
    4. 질의 복잡도 (0-1)

    결과를 JSON 형식으로 반환하세요."""

    # LINE 44-47: 메시지 구성
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=state["user_query"])  # "지난 분기 매출 분석"
    ]

    # LINE 49: LLM 호출 🔴
    response = llm.invoke(messages)
    # 예상 응답:
    # {
    #   "intent": "analysis",
    #   "required_agents": ["analysis"],
    #   "entities": [
    #     {"type": "period", "value": "지난 분기"}
    #   ],
    #   "complexity": 0.6,
    #   "keywords": ["매출", "분석", "분기"]
    # }

    # LINE 51-54: JSON 파싱 (실패시 기본값)
    try:
        analysis = json.loads(response.content)
    except json.JSONDecodeError:
        analysis = self._get_default_analysis()
        # LINE 128-136:
        # return {
        #     "intent": "search",
        #     "required_agents": ["search"],
        #     "entities": [],
        #     "complexity": 0.5,
        #     "keywords": []
        # }

    # LINE 56-62: State 업데이트 반환
    return {
        "query_analysis": analysis,           # 분석 결과 저장
        "workflow_status": "analyzing",       # 상태 변경
        "messages": [                         # 메시지 추가
            AIMessage(content=f"질의 분석 완료: {analysis.get('intent', 'unknown')}")
        ]
    }
```

### 4.4 Node 2: create_plan (query_processor.py)

```python
# LINE 64-95: 실행 계획 수립
def create_plan(
    self,
    state: AgentState,
    runtime: Runtime[AgentContext]
) -> Dict[str, Any]:
    # LINE 70: 로깅
    logger.info("Creating execution plan")

    # LINE 72-73: 이전 노드 결과 가져오기
    analysis = state.get("query_analysis", {})
    required_agents = analysis.get("required_agents", ["search"])
    # 예: ["analysis"] 또는 ["search", "document"]

    # LINE 76: 실행 계획 생성 (LLM 없이)
    plan = self._build_execution_plan(required_agents)

    # LINE 97-109: _build_execution_plan 상세
    def _build_execution_plan(self, required_agents: List[str]) -> List[Dict]:
        plan = []
        for idx, agent in enumerate(required_agents):
            plan.append({
                "step_id": f"step_{idx+1}",
                "agent_name": agent,  # "analysis"
                "action": self.utils.get_agent_action(agent),
                # utils.py LINE 27-35:
                # {
                #   "analysis": "데이터 분석 및 통계 생성",
                #   "search": "정보 검색 및 수집",
                #   "document": "문서 자동 생성",
                #   "customer": "고객 데이터 분석"
                # }
                "dependencies": [] if idx == 0 else [f"step_{idx}"],
                "parallel": self.utils.can_run_parallel(agent, required_agents),
                # utils.py LINE 38-42:
                # parallel_compatible = ["search", "customer"]
                # return agent in parallel_compatible
                "estimated_time": self.utils.estimate_time(agent)
                # utils.py LINE 45-53:
                # times = {
                #   "analysis": 10,
                #   "search": 5,
                #   "document": 15,
                #   "customer": 8
                # }
            })
        return plan

    # LINE 79-87: 인터럽트 처리 (Human-in-the-loop)
    if runtime.context.interrupt_mode != "none":
        plan = self._handle_interrupts(plan, runtime.context)

    # LINE 111-126: _handle_interrupts 상세
    def _handle_interrupts(self, plan: List[Dict], context: AgentContext):
        for step in plan:
            if self.utils.requires_approval(step["action"], context):
                # utils.py LINE 56-65:
                # if context.interrupt_mode == "all": return True
                # if context.interrupt_mode == "critical":
                #     approval_actions = ["sql_execution",
                #                        "document_generation",
                #                        "external_api_call"]
                #     return any(a in action.lower() for a in approval_actions)

                # LINE 119-123: interrupt 함수 (LangGraph API)
                approval = interrupt(
                    f"다음 작업을 수행하시겠습니까?\n"
                    f"에이전트: {step['agent_name']}\n"
                    f"작업: {step['action']}"
                )
                if not approval:
                    return None

    # LINE 89-95: State 업데이트 반환
    return {
        "execution_plan": plan,
        "workflow_status": "executing",
        "messages": [
            AIMessage(content=f"실행 계획 수립 완료: {len(plan)}개 단계")
        ]
    }
```

### 4.5 Node 3: route_agents (agent_executor.py)

```python
# LINE 20-53: 에이전트 라우팅
def route_agents(
    self,
    state: AgentState,
    runtime: Runtime[AgentContext]
) -> Dict[str, Any]:
    # LINE 26: 로깅
    logger.info("Routing to agents")

    # LINE 28-29: 계획에서 다음 단계 찾기
    plan = state.get("execution_plan", [])
    current_step = self._get_next_step(plan, state)

    # LINE 72-84: _get_next_step 상세
    def _get_next_step(self, plan: List[Dict], state: AgentState):
        executed = state.get("agent_sequence", [])  # 이미 실행된 에이전트
        for step in plan:
            if step["agent_name"] not in executed:
                deps = step.get("dependencies", [])
                # 의존성이 모두 실행되었는지 확인
                if all(d in executed for d in deps):
                    return step
        return None

    # LINE 31-33: 완료 체크
    if not current_step:
        return {"workflow_status": "completed"}

    # LINE 35: 현재 에이전트 이름
    agent_name = current_step["agent_name"]  # 예: "analysis"

    # LINE 38-40: 병렬 실행 처리
    parallel_agents = []
    if runtime.context.parallel_execution and current_step.get("parallel"):
        parallel_agents = self._get_parallel_agents(plan, current_step, state)

    # LINE 86-101: _get_parallel_agents 상세
    def _get_parallel_agents(self, plan, current_step, state):
        parallel = []
        executed = state.get("agent_sequence", [])
        for step in plan:
            if (step != current_step and
                step.get("parallel") and
                step["agent_name"] not in executed):
                parallel.append(step)
        return parallel

    # LINE 43: Send 메커니즘 생성 ⚠️ 문제: 타겟 노드 없음
    sends = self._create_sends(agent_name, parallel_agents, state, runtime.context)

    # LINE 103-126: _create_sends 상세
    def _create_sends(self, agent_name, parallel_agents, state, context):
        sends = []
        if parallel_agents:
            for agent in parallel_agents:
                sends.append(Send(f"{agent['agent_name']}_agent", {
                    "state": state,
                    "context": context
                }))
        else:
            sends.append(Send(f"{agent_name}_agent", {  # "analysis_agent"
                "state": state,
                "context": context
            }))
        return sends
    # ⚠️ Send는 존재하지 않는 노드를 가리킴!

    # LINE 46: 실행된 에이전트 목록 업데이트
    executed_agents = [agent_name] + [a["agent_name"] for a in parallel_agents]

    # LINE 47-53: State 업데이트
    return {
        "current_agent": agent_name,
        "agent_sequence": state.get("agent_sequence", []) + executed_agents,
        "messages": [
            AIMessage(content=f"실행 중: {', '.join(executed_agents)}")
        ]
    }
```

### 4.6 조건부 라우팅 평가 (agent_executor.py)

```python
# LINE 55-70: 완료 상태 확인 (조건부 엣지용)
def check_completion(
    self,
    state: AgentState
) -> Literal["continue", "aggregate", "error"]:
    # LINE 60-61: 에러 체크
    if state.get("errors"):
        return "error"  # → generate_response로 직행

    # LINE 63-64: 실행 계획 가져오기
    plan = state.get("execution_plan", [])
    executed = state.get("agent_sequence", [])

    # LINE 66-68: 모든 에이전트 실행 완료 확인
    planned_agents = [step["agent_name"] for step in plan]
    if all(agent in executed for agent in planned_agents):
        return "aggregate"  # → aggregate_results로

    # LINE 70: 계속 실행
    return "continue"  # → route_agents 반복
```

### 4.7 Node 4: aggregate_results (response_generator.py)

```python
# LINE 24-45: 결과 취합
def aggregate_results(
    self,
    state: AgentState,
    runtime: Runtime[AgentContext]
) -> Dict[str, Any]:
    # LINE 30: 로깅
    logger.info("Aggregating results")

    # LINE 33: 각 에이전트 결과 수집
    results = self._collect_results(state)

    # LINE 78-85: _collect_results 상세
    def _collect_results(self, state: AgentState) -> Dict:
        return {
            "analysis": state.get("analysis_results"),    # None (미구현)
            "search": state.get("search_results"),        # None (미구현)
            "documents": state.get("documents"),          # []
            "customer": state.get("customer_insights")    # None (미구현)
        }

    # LINE 36: None 값 제거
    results = {k: v for k, v in results.items() if v is not None}
    # 현재 모두 None이므로 results = {}

    # LINE 38-45: 메타데이터 업데이트
    return {
        "metadata": {
            **state.get("metadata", {}),  # 기존 메타데이터 유지
            "aggregated_at": datetime.now().isoformat(),
            "total_agents": len(state.get("agent_sequence", [])),
            "results_count": len(results)  # 0
        }
    }
```

### 4.8 Node 5: generate_response (response_generator.py)

```python
# LINE 47-76: 최종 응답 생성
def generate_response(
    self,
    state: AgentState,
    runtime: Runtime[AgentContext]
) -> Dict[str, Any]:
    # LINE 53: 로깅
    logger.info("Generating final response")

    # LINE 55: LLM 인스턴스 생성 🔴
    llm = self.utils.get_llm(runtime.context)

    # LINE 58: 결과 요약
    results_summary = self._summarize_results(state)

    # LINE 87-104: _summarize_results 상세
    def _summarize_results(self, state: AgentState) -> str:
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
    # 현재 반환값: "결과 없음"

    # LINE 61-65: LLM 응답 생성
    response = self._create_response(
        llm,
        state["user_query"],      # "지난 분기 매출 분석"
        results_summary,          # "결과 없음"
        runtime.context.language  # "ko"
    )

    # LINE 106-129: _create_response 상세
    def _create_response(self, llm, user_query, results_summary, language):
        # LINE 114-122: 시스템 프롬프트
        system_prompt = f"""당신은 제약회사 직원을 위한 전문 AI 어시스턴트입니다.
        다음 분석 결과를 바탕으로 {'한국어로' if language == 'ko' else '영어로'}
        명확하고 전문적인 응답을 생성하세요.

        사용자 질문: {user_query}

        분석 결과:
        {results_summary}
        """

        # LINE 124-127: 메시지 구성
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content="위 결과를 바탕으로 종합적인 답변을 작성해주세요.")
        ]

        # LINE 129: LLM 호출 🔴
        return llm.invoke(messages)

    # LINE 67-76: State 업데이트 (최종)
    return {
        "final_response": response.content,  # LLM 생성 응답
        "workflow_status": "completed",
        "messages": [AIMessage(content=response.content)],
        "metadata": {
            **state.get("metadata", {}),
            "completed_at": datetime.now().isoformat()
        }
    }
```

---

## 5. LLM 호출 분석

### 5.1 LLM 호출 지점 (총 2곳)

#### 호출 1: analyze_query (query_processor.py:49)
```python
# 목적: 사용자 질의 분석
response = llm.invoke(messages)

# 입력:
SystemMessage: "당신은 제약회사 직원을 위한 챗봇의 질의 분석기입니다..."
HumanMessage: "지난 분기 매출 분석"

# 출력 (JSON):
{
  "intent": "analysis",
  "required_agents": ["analysis"],
  "entities": [{"type": "period", "value": "지난 분기"}],
  "complexity": 0.6,
  "keywords": ["매출", "분석"]
}
```

#### 호출 2: generate_response (response_generator.py:129)
```python
# 목적: 최종 응답 생성
response = llm.invoke(messages)

# 입력:
SystemMessage: "당신은 제약회사 직원을 위한 전문 AI 어시스턴트입니다..."
HumanMessage: "위 결과를 바탕으로 종합적인 답변을 작성해주세요."

# 출력 (텍스트):
"지난 분기 매출 분석 결과를 제공해드리겠습니다.
현재 시스템에서 데이터를 조회할 수 없는 상황입니다..."
```

### 5.2 LLM 설정 (utils.py:16-24)
```python
def get_llm(context: AgentContext):
    if context.model_provider == "openai":
        return ChatOpenAI(
            model=context.model_name,     # "gpt-4o"
            api_key=context.api_key,       # 환경변수
            temperature=0.7                # 고정값
        )
```

---

## 6. 함수별 입출력 명세

### 6.1 analyze_query
```python
입력:
  state: {
    "user_query": "지난 분기 매출 분석",
    "workflow_status": "initializing",
    ...
  }
  runtime.context: AgentContext(user_id="user123", ...)

출력:
  {
    "query_analysis": {
      "intent": "analysis",
      "required_agents": ["analysis"],
      ...
    },
    "workflow_status": "analyzing",
    "messages": [AIMessage(...)]
  }
```

### 6.2 create_plan
```python
입력:
  state: {
    "query_analysis": {"required_agents": ["analysis"]},
    ...
  }

출력:
  {
    "execution_plan": [
      {
        "step_id": "step_1",
        "agent_name": "analysis",
        "action": "데이터 분석 및 통계 생성",
        "dependencies": [],
        "parallel": false,
        "estimated_time": 10
      }
    ],
    "workflow_status": "executing"
  }
```

### 6.3 route_agents
```python
입력:
  state: {
    "execution_plan": [...],
    "agent_sequence": [],
    ...
  }

출력:
  {
    "current_agent": "analysis",
    "agent_sequence": ["analysis"],
    "messages": [AIMessage("실행 중: analysis")]
  }
```

### 6.4 check_completion
```python
입력:
  state: {
    "execution_plan": [{"agent_name": "analysis"}],
    "agent_sequence": ["analysis"],
    ...
  }

출력: "aggregate"  # Literal 타입
```

### 6.5 aggregate_results
```python
입력:
  state: {
    "analysis_results": None,
    "search_results": None,
    ...
  }

출력:
  {
    "metadata": {
      "aggregated_at": "2024-...",
      "total_agents": 1,
      "results_count": 0
    }
  }
```

### 6.6 generate_response
```python
입력:
  state: {
    "user_query": "지난 분기 매출 분석",
    "analysis_results": None,
    ...
  }

출력:
  {
    "final_response": "매출 분석 결과...",
    "workflow_status": "completed",
    "messages": [AIMessage(...)],
    "metadata": {"completed_at": "2024-..."}
  }
```

---

## 7. 미사용 코드 분석

### 7.1 Send 메커니즘 (agent_executor.py)
```python
# LINE 43, 103-126
sends = self._create_sends(...)
Send(f"{agent_name}_agent", {...})
```
**문제**: "analysis_agent", "search_agent" 등 노드가 존재하지 않음

### 7.2 병렬 실행 로직 (agent_executor.py)
```python
# LINE 38-40, 86-101
parallel_agents = self._get_parallel_agents(...)
```
**문제**: Send가 작동하지 않아 병렬 실행 불가능

### 7.3 인터럽트 데이터 (state.py)
```python
# LINE 132-141
class InterruptData(BaseModel):
    interrupt_id: str
    reason: str
    ...
```
**문제**: 실제로 사용되지 않음

### 7.4 에러 처리 경로
```python
# check_completion에서 "error" 반환
if state.get("errors"):
    return "error"
```
**문제**: errors 필드를 설정하는 코드 없음

### 7.5 WebSocket 인터럽트 (main.py)
```python
# LINE 282-309
async def process_interrupt_response(session_id: str, data: dict):
    command = Command(resume=data.get("value"))
```
**문제**: 인터럽트 발생 코드 없음

---

## 8. 개선 필요 사항

### 8.1 즉시 개선 가능
1. Send 메커니즘 제거 또는 수정
2. 미사용 스키마 정리
3. 에러 처리 로직 구현

### 8.2 구조적 개선
1. 실제 에이전트 노드 구현
2. 도구(Tools) 시스템 구축
3. 데이터베이스 연동

### 8.3 최적화
1. LLM 호출 캐싱
2. 병렬 실행 실제 구현
3. 스트리밍 응답 개선

---

## 9. 데이터 흐름 예시

### 입력: "지난 분기 매출 분석"

```
1. initial_state 생성
   ↓
2. analyze_query: LLM이 intent="analysis" 판단
   ↓
3. create_plan: [{agent_name: "analysis", ...}] 생성
   ↓
4. route_agents: Send("analysis_agent") 시도 (실패)
   ↓
5. check_completion: "aggregate" 반환
   ↓
6. aggregate_results: 빈 결과 취합
   ↓
7. generate_response: LLM이 "결과 없음" 보고 일반 답변 생성
   ↓
8. 최종 응답: "현재 데이터를 조회할 수 없습니다..."
```

---

## 10. 핵심 문제점 요약

1. **에이전트 미구현**: 4개 에이전트 노드 없음
2. **Send 메커니즘 무용**: 타겟 노드 부재
3. **도구 시스템 부재**: DB 연동, API 호출 불가
4. **LLM 의존도**: 실제 데이터 없이 LLM만으로 응답

이 시스템은 **프레임워크는 완성**되었으나 **비즈니스 로직이 없는** 상태입니다.