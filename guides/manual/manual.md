# LangGraph 0.6.7 Multi-Agent System 구축 매뉴얼

## 📋 시스템 개요

본 매뉴얼은 LangGraph 0.6.7을 기반으로 한 계층적 Multi-Agent System 구축을 위한 상세 가이드입니다.

## 🏗️ 아키텍처 구조

```
┌─────────────────────────────────────────────────────┐
│                   Frontend (React)                   │
│              ProgressFlow Component                  │
└────────────────────┬───────────────────────────────┘
                     │ WebSocket/REST API
┌────────────────────▼───────────────────────────────┐
│                 FastAPI Backend                     │
│              with Lifespan Manager                  │
└────────────────────┬───────────────────────────────┘
                     │
┌────────────────────▼───────────────────────────────┐
│              Supervisor Agent                       │
│          (StateGraph + Runtime[Context])            │
└──────┬──────────┬──────────┬──────────┬───────────┘
       │          │          │          │
   ┌───▼───┐ ┌───▼───┐ ┌───▼───┐ ┌───▼───┐
   │Analysis│ │Search │ │Document│ │Customer│
   │ Agent  │ │ Agent │ │ Agent  │ │ Agent  │
   └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
       │          │          │          │
   ┌───▼─────────▼──────────▼──────────▼───┐
   │           Tool Repository              │
   │  (Text2SQL, Search, Analysis, etc.)    │
   └────────────────────────────────────────┘
```

## 🛠️ 구현 가이드

### 1. 환경 설정

#### 필요 패키지 설치
```bash
# 백엔드 패키지
pip install langgraph==0.6.7
pip install langgraph-checkpoint-sqlite==2.0.11
pip install langchain-openai
pip install langchain-anthropic
pip install fastapi uvicorn
pip install aiosqlite

# 프론트엔드 패키지
npm install react
npm install @tanstack/react-query
npm install socket.io-client
npm install framer-motion
```

### 2. Context Schema 정의

```python
# backend/schemas/context.py
from dataclasses import dataclass
from typing import Optional, Dict, Any

@dataclass
class AgentContext:
    """에이전트 실행 컨텍스트"""
    user_id: str
    session_id: str
    db_connection: Any
    user_profile: Optional[Dict] = None
    company_info: Optional[Dict] = None
    interrupt_enabled: bool = True
    max_iterations: int = 10
```

### 3. State 정의

```python
# backend/schemas/state.py
from typing import TypedDict, List, Dict, Optional, Annotated
from langgraph.graph import add_messages

class AgentState(TypedDict):
    """전체 에이전트 상태"""
    messages: Annotated[List, add_messages]
    user_query: str
    analysis_plan: Optional[str]
    agent_outputs: Dict[str, Any]
    current_agent: Optional[str]
    iteration: int
    final_answer: Optional[str]
    error: Optional[str]
```

### 4. Supervisor Agent 구현

```python
# backend/agents/supervisor.py
from langgraph.graph import StateGraph, END
from langgraph.runtime import Runtime
from langgraph.types import interrupt, Command
from typing import Literal

class SupervisorAgent:
    def __init__(self):
        self.builder = StateGraph(
            state_schema=AgentState,
            context_schema=AgentContext
        )
        self._setup_graph()
    
    def analyze_query(self, state: AgentState, runtime: Runtime[AgentContext]):
        """사용자 질의 분석 및 계획 수립"""
        # LLM을 사용한 질의 분석
        analysis = self._analyze_with_llm(state["user_query"])
        
        # Human-in-the-loop: 계획 승인
        if runtime.context.interrupt_enabled:
            approved = interrupt({
                "type": "approval_request",
                "plan": analysis["plan"],
                "agents_to_call": analysis["agents"]
            })
            if not approved:
                return {"error": "Plan rejected by user"}
        
        return {
            "analysis_plan": analysis["plan"],
            "current_agent": analysis["first_agent"]
        }
    
    def route_to_agent(self, state: AgentState) -> Literal["analysis", "search", "document", "customer", END]:
        """다음 실행할 에이전트 결정"""
        if state.get("error"):
            return END
        
        if state["current_agent"] == "analysis":
            return "analysis"
        elif state["current_agent"] == "search":
            return "search"
        elif state["current_agent"] == "document":
            return "document"
        elif state["current_agent"] == "customer":
            return "customer"
        else:
            return END
    
    def _setup_graph(self):
        """그래프 구성"""
        # 노드 추가
        self.builder.add_node("analyze", self.analyze_query)
        self.builder.add_node("analysis", self.analysis_agent)
        self.builder.add_node("search", self.search_agent)
        self.builder.add_node("document", self.document_agent)
        self.builder.add_node("customer", self.customer_agent)
        self.builder.add_node("synthesize", self.synthesize_results)
        
        # 엣지 추가
        self.builder.set_entry_point("analyze")
        self.builder.add_conditional_edges(
            "analyze",
            self.route_to_agent,
            {
                "analysis": "analysis",
                "search": "search",
                "document": "document",
                "customer": "customer",
                END: END
            }
        )
        
        # 각 에이전트에서 synthesize로
        for agent in ["analysis", "search", "document", "customer"]:
            self.builder.add_edge(agent, "synthesize")
        
        self.builder.add_edge("synthesize", END)
```

### 5. 개별 에이전트 구현

```python
# backend/agents/analysis.py
from langgraph.runtime import Runtime
from langgraph.types import interrupt

class AnalysisAgent:
    def __init__(self, tools):
        self.tools = tools
    
    async def execute(self, state: AgentState, runtime: Runtime[AgentContext]):
        """분석 에이전트 실행"""
        # Text2SQL로 데이터 조회
        query = self._generate_sql_query(state["user_query"])
        
        # 인터럽트 포인트: SQL 쿼리 검토
        if runtime.context.interrupt_enabled:
            approved_query = interrupt({
                "type": "sql_review",
                "original_query": query,
                "editable": True
            })
            query = approved_query or query
        
        # 쿼리 실행
        results = await self._execute_query(query, runtime.context.db_connection)
        
        # 분석 수행
        analysis = self._perform_analysis(results)
        
        return {
            "agent_outputs": {
                "analysis": analysis
            }
        }
```

### 6. CheckPointer 설정

```python
# backend/persistence/checkpointer.py
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from contextlib import asynccontextmanager
import aiosqlite

class CheckpointerManager:
    def __init__(self, db_path: str = "backend/checkpoint/graph_state.db"):
        self.db_path = db_path
    
    @asynccontextmanager
    async def get_checkpointer(self):
        """체크포인터 컨텍스트 매니저"""
        async with aiosqlite.connect(self.db_path) as conn:
            checkpointer = AsyncSqliteSaver(conn)
            try:
                yield checkpointer
            finally:
                await conn.commit()
```

### 7. FastAPI 통합

```python
# backend/main.py
from fastapi import FastAPI, WebSocket
from contextlib import asynccontextmanager
from langgraph.types import Command
import json

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan 관리"""
    # 시작 시 초기화
    app.state.checkpointer_manager = CheckpointerManager()
    async with app.state.checkpointer_manager.get_checkpointer() as checkpointer:
        supervisor = SupervisorAgent()
        app.state.graph = supervisor.builder.compile(
            checkpointer=checkpointer,
            durability="async"  # 비동기 체크포인트 저장
        )
    yield
    # 종료 시 정리
    # 필요한 정리 작업

app = FastAPI(lifespan=lifespan)

@app.websocket("/ws/agent")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "start":
                # 새로운 대화 시작
                config = {
                    "configurable": {
                        "thread_id": data["thread_id"]
                    }
                }
                context = AgentContext(
                    user_id=data["user_id"],
                    session_id=data["session_id"],
                    db_connection=app.state.db_conn
                )
                
                # 스트리밍으로 실행
                async for chunk in app.state.graph.astream(
                    {"user_query": data["query"]},
                    config=config,
                    context=context,
                    stream_mode="updates"
                ):
                    await websocket.send_json({
                        "type": "update",
                        "data": chunk
                    })
            
            elif data["type"] == "resume":
                # 인터럽트 재개
                config = {
                    "configurable": {
                        "thread_id": data["thread_id"]
                    }
                }
                command = Command(resume=data["value"])
                
                async for chunk in app.state.graph.astream(
                    command,
                    config=config,
                    stream_mode="updates"
                ):
                    await websocket.send_json({
                        "type": "update",
                        "data": chunk
                    })
    
    except Exception as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
    finally:
        await websocket.close()
```

### 8. Frontend Progress Flow

```typescript
// frontend/components/ProgressFlow.tsx
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { io, Socket } from 'socket.io-client';

interface AgentStep {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'error';
  output?: any;
}

export const ProgressFlow: React.FC = () => {
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [interrupted, setInterrupted] = useState(false);
  const [interruptData, setInterruptData] = useState<any>(null);

  useEffect(() => {
    const newSocket = io('ws://localhost:8000/ws/agent');
    
    newSocket.on('update', (data) => {
      if (data.type === 'agent_start') {
        setSteps(prev => [...prev, {
          id: data.agent_id,
          name: data.agent_name,
          status: 'running'
        }]);
      } else if (data.type === 'agent_complete') {
        setSteps(prev => prev.map(step => 
          step.id === data.agent_id 
            ? { ...step, status: 'completed', output: data.output }
            : step
        ));
      } else if (data.type === 'interrupt') {
        setInterrupted(true);
        setInterruptData(data.data);
      }
    });

    setSocket(newSocket);
    return () => { newSocket.close(); };
  }, []);

  const handleInterruptResponse = (value: any) => {
    socket?.emit('resume', { value });
    setInterrupted(false);
    setInterruptData(null);
  };

  return (
    <div className="progress-flow">
      <div className="steps-container">
        <AnimatePresence>
          {steps.map((step, index) => (
            <motion.div
              key={step.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ delay: index * 0.1 }}
              className={`step step-${step.status}`}
            >
              <div className="step-header">
                <span className="step-name">{step.name}</span>
                <StatusIcon status={step.status} />
              </div>
              {step.output && (
                <div className="step-output">
                  {JSON.stringify(step.output, null, 2)}
                </div>
              )}
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {interrupted && (
        <InterruptModal
          data={interruptData}
          onResponse={handleInterruptResponse}
        />
      )}
    </div>
  );
};

const StatusIcon: React.FC<{ status: string }> = ({ status }) => {
  switch(status) {
    case 'running':
      return <Spinner />;
    case 'completed':
      return <CheckIcon />;
    case 'error':
      return <ErrorIcon />;
    default:
      return <PendingIcon />;
  }
};
```

## 🔧 고급 기능

### 1. 동적 에이전트 구성

```python
def dynamic_agent_selection(state: AgentState, runtime: Runtime[AgentContext]):
    """사용자 질의에 따른 동적 에이전트 선택"""
    query_type = analyze_query_type(state["user_query"])
    
    if query_type == "complex":
        # 복잡한 질의: 모든 에이전트 활용
        return ["analysis", "search", "document", "customer"]
    elif query_type == "simple":
        # 단순 질의: 단일 에이전트
        return ["search"]
    else:
        # 중간 복잡도: 선택적 활용
        return select_relevant_agents(state["user_query"])
```

### 2. 에러 복구 메커니즘

```python
async def with_retry(func, max_retries=3):
    """자동 재시도 로직"""
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            await asyncio.sleep(2 ** attempt)  # 지수 백오프
```

### 3. 성능 최적화

```python
# 캐싱 전략
from functools import lru_cache

@lru_cache(maxsize=100)
def cached_analysis(query_hash: str):
    """분석 결과 캐싱"""
    return perform_analysis(query_hash)

# 병렬 실행
async def parallel_agent_execution(agents, state, runtime):
    """독립적인 에이전트 병렬 실행"""
    tasks = [
        agent.execute(state, runtime) 
        for agent in agents
    ]
    results = await asyncio.gather(*tasks)
    return merge_results(results)
```

## 📊 모니터링 및 디버깅

### LangSmith 통합
```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-api-key"
os.environ["LANGCHAIN_PROJECT"] = "multi-agent-system"
```

### 커스텀 로깅
```python
import logging
from datetime import datetime

class AgentLogger:
    def __init__(self):
        self.logger = logging.getLogger("agent_system")
    
    def log_agent_start(self, agent_name: str, state: dict):
        self.logger.info(f"[{datetime.now()}] Agent {agent_name} started")
        self.logger.debug(f"State: {state}")
    
    def log_interrupt(self, interrupt_data: dict):
        self.logger.warning(f"Interrupt triggered: {interrupt_data}")
```

## 🚀 배포 체크리스트

- [ ] PostgreSQL Checkpointer로 마이그레이션
- [ ] Redis를 사용한 캐싱 레이어 구현
- [ ] 로드밸런싱 및 오토스케일링 설정
- [ ] 에러 트래킹 시스템 통합 (Sentry 등)
- [ ] API 레이트 리미팅 구현
- [ ] 보안 헤더 및 CORS 설정
- [ ] 환경별 설정 분리 (dev/staging/prod)
- [ ] 백업 및 복구 전략 수립
- [ ] 모니터링 대시보드 구축
- [ ] 성능 테스트 및 최적화

## 📚 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [FastAPI Lifespan Events](https://fastapi.tiangolo.com/advanced/events/)
- [React Query 문서](https://tanstack.com/query/latest)
- [WebSocket Best Practices](https://socket.io/docs/v4/)
