# LangGraph Migration Rules: v0.2.x → v0.6.7

## 📌 핵심 변경사항 요약

LangGraph 0.6.7은 v1.0 출시 전 마지막 주요 버전으로, 더 직관적이고 타입 안전한 개발 경험을 제공합니다.

## ⚠️ 버전 차이 Critical Points

### Claude의 현재 지식 (0.2.x) vs 최신 버전 (0.6.7)
| 영역 | v0.2.x (Claude 기본 지식) | v0.6.7 (2024년 9월 출시) | 영향도 |
|------|---------------------------|-------------------------|--------|
| **Config 관리** | config['configurable'] 딕셔너리 | Runtime[Context] 타입 안전 | 🔴 높음 |
| **Interrupt** | NodeInterrupt 예외 방식 | interrupt() 함수 + Command | 🔴 높음 |
| **Checkpointing** | checkpoint_during 불린 플래그 | durability 3가지 모드 | 🟡 중간 |
| **Import 경로** | langgraph.pregel.types | langgraph.types | 🟡 중간 |
| **타입 체킹** | 런타임 검증 | 컴파일 타임 검증 | 🟢 낮음 |
| **API Surface** | 모든 내부 API 노출 | Public/Private 명확한 구분 | 🟡 중간 |

## 🆕 0.6.7 신규 기능 (0.2.x에 없던 기능)

### 1. Runtime 클래스
```python
# 0.6.7에서 새로 추가된 Runtime 인터페이스
from langgraph.runtime import Runtime

# Runtime이 제공하는 정보:
# - context: 정적 데이터 (구 config['configurable'])
# - store: 장기 메모리 저장소
# - stream_writer: 커스텀 스트림 출력
# - previous: 이전 실행 결과 (functional API용)
```

### 2. Command 프리미티브
```python
from langgraph.types import Command

# 0.6.7 새로운 그래프 제어 방식
Command(
    resume=value,        # interrupt 재개 값
    update=state_update, # 상태 업데이트
    goto=["node1", "node2"]  # 다음 노드 지정
)
```

### 3. Store 인터페이스 (Cross-Thread Memory)
```python
# 0.2.x: 스레드별 독립 메모리만 가능
# 0.6.7: 스레드 간 공유 메모리 지원
from langgraph.store import InMemoryStore

store = InMemoryStore()
graph = builder.compile(checkpointer=checkpointer, store=store)
```

### 4. 동적 브레이크포인트
```python
# 0.2.x: 정적 브레이크포인트만 가능
# 0.6.7: 런타임 조건부 브레이크포인트
def node(state, runtime):
    if should_pause(state):
        value = interrupt("동적 중단")
```

### 5. Deferred Nodes (지연 실행)
```python
# 0.6.7 신기능: 모든 상위 경로 완료 후 실행
builder.add_node("aggregate", aggregate_fn, deferred=True)
```

### 6. Node/Task 레벨 캐싱
```python
# 0.6.7 신기능: 개별 노드 결과 캐싱
@cached(ttl=3600)
def expensive_node(state):
    return compute_heavy_task(state)
```

## 🔄 주요 마이그레이션 포인트

### 1. Context API (최대 변경사항) ⭐

#### v0.2.x (기존 방식)
```python
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph

def node(state: State, config: RunnableConfig):
    # 복잡한 중첩 딕셔너리 접근
    user_id = config.get("configurable", {}).get("user_id")
    db_conn = config.get("configurable", {}).get("db_connection")
    ...

builder = StateGraph(state_schema=State, config_schema=Config)
result = graph.invoke(
    {'input': 'abc'},
    config={'configurable': {'user_id': '123', 'db_connection': 'conn_mock'}}
)
```

#### v0.6.7 (새로운 방식)
```python
from dataclasses import dataclass
from langgraph.graph import StateGraph
from langgraph.runtime import Runtime

@dataclass
class Context:
    """개발자가 정의하는 컨텍스트 스키마"""
    user_id: str
    db_connection: str

def node(state: State, runtime: Runtime[Context]):
    # 타입 안전한 속성 접근
    user_id = runtime.context.user_id
    db_conn = runtime.context.db_connection
    ...

builder = StateGraph(state_schema=State, context_schema=Context)
result = graph.invoke(
    {'input': 'abc'},
    context=Context(user_id='123', db_conn='conn_mock')
)
```

**마이그레이션 규칙:**
- `config_schema` → `context_schema`로 변경
- `config['configurable']` → `runtime.context`로 접근
- `get_config_jsonschema()` → `get_context_jsonschema()`로 변경
- v0.2.x 코드는 여전히 작동하지만 deprecated 경고 발생

### 2. Interrupt & Command System (Human-in-the-Loop) 🔄

#### v0.2.x (기존 방식)
```python
# NodeInterrupt 사용 (deprecated)
from langgraph.prebuilt import NodeInterrupt

def human_node(state):
    raise NodeInterrupt("Need human input")
    # 재시작 시 처음부터 다시 실행
```

#### v0.6.7 (새로운 방식)
```python
from langgraph.types import interrupt, Command

def human_node(state: State):
    answer = interrupt("What is your age?")  # 중단 지점
    print(f"Received: {answer}")
    return {"human_value": answer}

# 재개 시
graph.invoke(Command(resume="Your response here"), config)
```

**마이그레이션 규칙:**
- `NodeInterrupt` → `interrupt()` 함수 사용
- 재개 시 `Command(resume=value)` 사용
- `interrupt_before/after` → 정적 인터럽트는 유지되지만, 동적 인터럽트 권장
- Interrupt 클래스 속성 변경:
  - `when`, `resumable`, `ns` 제거
  - `id`와 `value`만 유지

### 3. Durability Mode (체크포인트 저장 방식) 💾

#### v0.2.x (기존 방식)
```python
graph = builder.compile(
    checkpointer=checkpointer,
    checkpoint_during=True  # deprecated
)
```

#### v0.6.7 (새로운 방식)
```python
graph = builder.compile(
    checkpointer=checkpointer,
    durability="async"  # "exit", "async", "sync" 중 선택
)
```

**마이그레이션 규칙:**
- `checkpoint_during=False` → `durability="exit"`
- `checkpoint_during=True` → `durability="async"`
- 새로운 `durability="sync"` 옵션 추가 (동기식 저장, 가장 안전)

### 4. AsyncSqliteSaver 사용법 변경 ✅

#### v0.2.x (기존 방식)
```python
from langgraph.checkpoint.sqlite import SqliteSaver
checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
```

#### v0.6.7 (새로운 방식)
```python
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

# async with 문 사용 권장
async with AsyncSqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    graph = builder.compile(checkpointer=checkpointer)
```

**마이그레이션 규칙:**
- 비동기 환경에서는 `AsyncSqliteSaver` 사용 필수
- `backend\checkpoint` 폴더에 저장 시 경로 명시
- FastAPI와 함께 사용 시 Lifespan 패턴 활용

### 5. Import 경로 변경 📦

#### v0.2.x (기존 경로)
```python
from langgraph.pregel.types import ...
from langgraph.constants import Send, Interrupt
from langgraph.channels import ErrorClass
```

#### v0.6.7 (새로운 경로)
```python
from langgraph.types import Send, Interrupt, ...
from langgraph.errors import ErrorClass
# langgraph.constants는 대부분 private으로 변경
```

### 6. Prebuilt Agent 동적 모델/도구 선택 🤖

#### v0.6.7 신기능
```python
from langgraph.prebuilt import create_react_agent
from dataclasses import dataclass

@dataclass
class CustomContext:
    provider: Literal["anthropic", "openai"]
    tools: list[str]

def select_model(state, runtime: Runtime[CustomContext]):
    model = {
        "openai": openai_model,
        "anthropic": anthropic_model,
    }[runtime.context.provider]
    
    selected_tools = [
        tool for tool in all_tools
        if tool.name in runtime.context.tools
    ]
    return model.bind_tools(selected_tools)

agent = create_react_agent(
    select_model,  # 함수로 전달
    tools=all_tools
)
```

### 7. 타입 안전성 강화 🔒

#### v0.6.7 개선사항
- `StateGraph`가 제네릭으로 변경됨
- 노드 시그니처가 컴파일 시점에 검증됨
- `.stream()` 메서드가 완전히 타입 안전해짐
- `input_schema`, `output_schema` 타입 체크 지원

### 8. 그래프 구성 방식 변경 📊

#### v0.2.x (기존 방식)
```python
from langgraph.graph import Graph, StateGraph

# 단순한 그래프 구성
builder = StateGraph(State)
builder.add_node("node1", node1_func)
builder.add_edge("node1", "node2")
builder.add_conditional_edges("node2", router_func)

# 컴파일
graph = builder.compile()
```

#### v0.6.7 (새로운 방식)
```python
from langgraph.graph import StateGraph
from typing import Literal

# 제네릭 타입으로 더 안전한 그래프
builder = StateGraph[State, Input, Output](
    state_schema=State,
    input_schema=Input,
    output_schema=Output,
    context_schema=Context  # 새로운 옵션
)

# 단축 문법 지원
builder.add_sequence(node1, node2, node3)  # 순차 실행
builder.add_nodes({
    "parallel1": func1,
    "parallel2": func2
})  # 병렬 노드 추가

# 향상된 라우팅
builder.add_conditional_edges(
    "router",
    route_function,
    path_map={
        "path1": "node1",
        "path2": ["node2", "node3"],  # 여러 노드로 분기
        "path3": Send("node4", data)   # 데이터와 함께 전송
    }
)
```

### 9. 스트리밍 모드 변경 🌊

#### v0.2.x
```python
# 제한된 스트리밍 옵션
for chunk in graph.stream(input):
    print(chunk)  # any 타입
```

#### v0.6.7
```python
# 타입 안전한 다양한 스트리밍 모드
for chunk in graph.stream(
    input,
    stream_mode="updates"  # 또는 "values", "messages", "custom"
):
    # chunk 타입이 stream_mode에 따라 자동 추론됨
    print(chunk)

# 새로운 스트리밍 옵션
- "values": 전체 상태 스트리밍
- "updates": 변경사항만 스트리밍  
- "messages": LLM 메시지 토큰별 스트리밍
- "custom": StreamWriter로 커스텀 스트리밍
```

### 10. 에러 처리 및 복구 🔧

#### v0.2.x
```python
# 기본적인 에러 처리
try:
    result = graph.invoke(input)
except Exception as e:
    # 전체 그래프 재실행 필요
    pass
```

#### v0.6.7
```python
# 향상된 에러 복구
# 1. 실패한 노드만 재실행
state = graph.get_state(config)
if state.tasks[0].error:
    # 실패 지점부터 재개
    graph.invoke(None, config)

# 2. Pending writes 보존
# 다른 노드가 성공한 경우 결과 유지

# 3. 에러별 핸들링
@builder.add_node
def node_with_recovery(state, runtime):
    try:
        return risky_operation(state)
    except RecoverableError:
        # 자동 복구 로직
        return fallback_operation(state)
```

### 11. 병렬 실행 개선 🚀

#### v0.2.x
```python
# 제한적인 병렬 실행
# Send를 통한 수동 구성 필요
```

#### v0.6.7
```python
# 향상된 병렬 실행
from langgraph.types import Send

# 1. 동적 병렬 실행
def dispatcher(state):
    return [
        Send("worker", {"task": task})
        for task in state["tasks"]
    ]

# 2. 병렬 인터럽트 처리
# 여러 노드가 동시에 interrupt 가능
# 각각 독립적으로 resume 가능

# 3. 자동 병렬화
builder.add_parallel_nodes(["node1", "node2", "node3"])
```

### 12. 메모리 및 스토리지 🗄️

#### v0.2.x
```python
# 스레드별 체크포인트만 지원
from langgraph.checkpoint.memory import MemorySaver
checkpointer = MemorySaver()
```

#### v0.6.7
```python
# 1. 다양한 체크포인터 옵션
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

# 2. Cross-thread Store
from langgraph.store import InMemoryStore
store = InMemoryStore()

# 3. 시리얼라이저 커스터마이징
from langgraph.checkpoint.base import JsonPlusSerializer
serializer = JsonPlusSerializer(pickle_fallback=True)

# 4. 통합 컴파일
graph = builder.compile(
    checkpointer=checkpointer,
    store=store,  # 새로운 옵션
    durability="async"  # 새로운 옵션
)
```

## 🎯 필수 체크리스트

### 즉시 변경 필요
- [ ] `config_schema` → `context_schema` 변경
- [ ] `config['configurable']` → `runtime.context` 접근 방식 변경
- [ ] `NodeInterrupt` → `interrupt()` 함수로 교체
- [ ] Import 경로 업데이트

### 점진적 마이그레이션 가능
- [ ] `checkpoint_during` → `durability` 모드 변경
- [ ] 동적 모델/도구 선택 기능 활용
- [ ] 타입 힌트 추가로 타입 안전성 향상

### 프로젝트 구조 권장사항
```
backend/
├── checkpoint/          # AsyncSqliteSaver 저장 위치
│   └── graph_state.db
├── agents/
│   ├── __init__.py
│   ├── supervisor.py    # Supervisor with Runtime[Context]
│   ├── analysis.py      # 분석 에이전트
│   ├── search.py        # 정보검색 에이전트
│   ├── document.py      # 문서생성 에이전트
│   └── customer.py      # 고객분석 에이전트
├── tools/
│   ├── __init__.py
│   ├── search_tools.py  # 검색 도구들
│   └── analysis_tools.py # 분석 도구들
└── main.py              # FastAPI with Lifespan

frontend/
├── components/
│   └── ProgressFlow.tsx  # 진행상황 표시 컴포넌트
└── pages/
    └── agent.tsx        # 에이전트 인터페이스
```

## ⚠️ 주의사항

1. **Backward Compatibility**: v0.2.x 코드는 대부분 작동하지만, v2.0에서 제거될 예정
2. **Performance**: `durability="sync"`는 가장 안전하지만 성능 저하 가능
3. **Testing**: `interrupt()` 사용 시 반드시 checkpointer 필요
4. **Production**: SQLite보다 PostgreSQL checkpointer 권장

## 📚 참고 문서
- [LangGraph 0.6.0 Release Notes](https://github.com/langchain-ai/langgraph/releases/tag/0.6.0)
- [Context API Migration Guide](https://langchain-ai.github.io/langgraph/concepts/context/)
- [Human-in-the-Loop with Interrupt](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
