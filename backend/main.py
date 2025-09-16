"""
FastAPI main application with WebSocket support
LangGraph 0.6.7 integration with AsyncSqliteSaver
"""

import os
import json
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime
import uuid

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langgraph.types import Command
from agents.supervisor import SupervisorAgent
from schemas.context import AgentContext
from schemas.state import create_initial_state
from persistence.checkpointer import checkpointer_manager, DurabilityMode

# Database integration imports
from database.connection import init_databases, close_databases
from routers import data_router

# 환경 변수 로드
load_dotenv()

# 로깅 설정
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan 관리
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan 패턴 - 체크포인터 및 데이터베이스 초기화/정리"""
    # Startup
    logger.info("Starting up FastAPI application")

    # Initialize databases
    await init_databases()
    logger.info("Databases initialized")

    # Initialize checkpointer
    await checkpointer_manager.initialize()

    # 그래프 컴파일
    supervisor = SupervisorAgent()
    builder = supervisor.create_graph()

    durability_mode = DurabilityMode.get_mode(
        os.getenv("ENVIRONMENT", "development")
    )

    app.state.graph = builder.compile(
        checkpointer=checkpointer_manager.checkpointer,
        durability=durability_mode
    )
    logger.info(f"Graph compiled with durability mode: {durability_mode}")

    yield

    # Shutdown
    logger.info("Shutting down FastAPI application")
    await checkpointer_manager.cleanup()
    await close_databases()
    logger.info("Cleanup completed")


# FastAPI 앱 생성
app = FastAPI(
    title="Pharmaceutical Chatbot API",
    description="LangGraph 0.6.7 based Multi-Agent System for Pharmaceutical Company",
    version="0.0.1",
    lifespan=lifespan
)

# CORS 설정
cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response 모델
class ChatRequest(BaseModel):
    """채팅 요청 모델"""
    query: str = Field(..., description="사용자 질의")
    user_id: str = Field(..., description="사용자 ID")
    company_id: str = Field(..., description="회사 ID")
    session_id: Optional[str] = Field(None, description="세션 ID")
    context_override: Optional[Dict[str, Any]] = Field(None, description="컨텍스트 오버라이드")


class ChatResponse(BaseModel):
    """채팅 응답 모델"""
    response: str = Field(..., description="AI 응답")
    session_id: str = Field(..., description="세션 ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="메타데이터")


class InterruptResponse(BaseModel):
    """인터럽트 응답 모델"""
    action: str = Field(..., description="승인/거부 액션")
    value: Optional[Any] = Field(None, description="인터럽트 값")
    session_id: str = Field(..., description="세션 ID")


# WebSocket 연결 관리
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        logger.info(f"WebSocket connected: {session_id}")
    
    def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected: {session_id}")
    
    async def send_json(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)
    
    async def broadcast(self, data: dict):
        for connection in self.active_connections.values():
            await connection.send_json(data)


manager = ConnectionManager()


# API 엔드포인트
@app.get("/")
async def root():
    """헬스 체크"""
    return {
        "status": "healthy",
        "version": "0.0.1",
        "langgraph_version": "0.6.7"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """동기식 채팅 엔드포인트"""
    try:
        # 세션 ID 생성
        session_id = request.session_id or str(uuid.uuid4())
        
        # Context 생성
        context = AgentContext(
            user_id=request.user_id,
            company_id=request.company_id,
            session_id=session_id
        )
        
        # 컨텍스트 오버라이드 적용
        if request.context_override:
            for key, value in request.context_override.items():
                if hasattr(context, key):
                    setattr(context, key, value)
        
        # 초기 상태 생성
        initial_state = create_initial_state(request.query)
        
        # 그래프 실행
        config = checkpointer_manager.get_config(session_id)
        result = await app.state.graph.ainvoke(
            initial_state,
            context=context,
            config=config
        )
        
        return ChatResponse(
            response=result.get("final_response", "응답을 생성할 수 없습니다."),
            session_id=session_id,
            metadata=result.get("metadata", {})
        )
    
    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket 엔드포인트 - 실시간 스트리밍"""
    await manager.connect(websocket, session_id)
    
    try:
        while True:
            # 클라이언트로부터 메시지 수신
            data = await websocket.receive_json()
            
            if data.get("type") == "chat":
                # 채팅 처리
                await process_chat_stream(session_id, data, websocket)
            
            elif data.get("type") == "interrupt_response":
                # 인터럽트 응답 처리
                await process_interrupt_response(session_id, data)
            
            elif data.get("type") == "get_state":
                # 현재 상태 조회
                state = await checkpointer_manager.get_thread_state(session_id)
                await websocket.send_json({
                    "type": "state",
                    "data": state
                })
    
    except WebSocketDisconnect:
        manager.disconnect(session_id)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })
        manager.disconnect(session_id)


async def process_chat_stream(session_id: str, data: dict, websocket: WebSocket):
    """스트리밍 채팅 처리"""
    try:
        # Context 생성
        context = AgentContext(
            user_id=data.get("user_id"),
            company_id=data.get("company_id"),
            session_id=session_id
        )
        
        # 초기 상태 생성
        initial_state = create_initial_state(data.get("query"))
        
        # 스트리밍 실행
        config = checkpointer_manager.get_config(session_id)
        
        async for chunk in app.state.graph.astream(
            initial_state,
            context=context,
            config=config,
            stream_mode="updates"
        ):
            # 각 업데이트를 클라이언트로 전송
            await websocket.send_json({
                "type": "update",
                "data": chunk,
                "timestamp": datetime.now().isoformat()
            })
            
            # 인터럽트 확인
            if chunk.get("interrupt_data"):
                await websocket.send_json({
                    "type": "interrupt",
                    "data": chunk["interrupt_data"],
                    "timestamp": datetime.now().isoformat()
                })
        
        # 최종 상태 전송
        final_state = await app.state.graph.aget_state(config)
        await websocket.send_json({
            "type": "complete",
            "data": {
                "response": final_state.values.get("final_response"),
                "metadata": final_state.values.get("metadata")
            },
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Stream processing error: {e}")
        await websocket.send_json({
            "type": "error",
            "message": str(e)
        })


async def process_interrupt_response(session_id: str, data: dict):
    """인터럽트 응답 처리"""
    try:
        config = checkpointer_manager.get_config(session_id)
        
        # Command를 사용한 재개
        command = Command(
            resume=data.get("value"),
            update=data.get("update")
        )
        
        # 그래프 재개
        await app.state.graph.ainvoke(
            command,
            config=config
        )
        
        await manager.send_json(session_id, {
            "type": "resumed",
            "timestamp": datetime.now().isoformat()
        })
    
    except Exception as e:
        logger.error(f"Interrupt response error: {e}")
        await manager.send_json(session_id, {
            "type": "error",
            "message": str(e)
        })


@app.post("/interrupt/resume")
async def resume_interrupt(response: InterruptResponse):
    """인터럽트 재개 (REST API)"""
    try:
        config = checkpointer_manager.get_config(response.session_id)
        
        # Command를 사용한 재개
        command = Command(resume=response.value)
        
        # 그래프 재개
        result = await app.state.graph.ainvoke(
            command,
            config=config
        )
        
        return {
            "status": "resumed",
            "session_id": response.session_id,
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Resume error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sessions/{session_id}/checkpoints")
async def get_checkpoints(session_id: str, limit: int = 10):
    """세션의 체크포인트 목록 조회"""
    try:
        checkpoints = await checkpointer_manager.list_checkpoints(session_id, limit)
        return {
            "session_id": session_id,
            "checkpoints": checkpoints
        }
    except Exception as e:
        logger.error(f"Get checkpoints error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sessions/{session_id}")
async def delete_session(session_id: str):
    """세션 삭제"""
    try:
        success = await checkpointer_manager.delete_thread(session_id)
        if success:
            return {"status": "deleted", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Include data router
app.include_router(data_router, prefix="")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=os.getenv("API_HOST", "0.0.0.0"),
        port=int(os.getenv("API_PORT", 8000)),
        reload=os.getenv("API_RELOAD", "true").lower() == "true"
    )