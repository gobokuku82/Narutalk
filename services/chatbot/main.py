"""
FastAPI Chatbot Service with LangGraph
WebSocket support for multi-agent orchestration
"""

import os
import sys
import json
import logging
from typing import Dict, Any, Optional
from contextlib import asynccontextmanager
from datetime import datetime
import uuid
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from langgraph.types import Command
from services.chatbot.agents.supervisor import SupervisorAgent
from services.chatbot.schemas.context import AgentContext
from services.chatbot.schemas.state import create_initial_state
from services.chatbot.persistence.checkpointer import checkpointer_manager, DurabilityMode

# Load environment variables
load_dotenv()

# Logging configuration
logging.basicConfig(
    level=getattr(logging, os.getenv("LOG_LEVEL", "INFO")),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# Lifespan management
@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI Lifespan - Initialize and cleanup checkpointer"""
    # Startup
    logger.info("Starting up Chatbot Service")
    await checkpointer_manager.initialize()

    # Compile graph
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
    logger.info("Shutting down Chatbot Service")
    await checkpointer_manager.cleanup()


# Create FastAPI app
app = FastAPI(
    title="Pharmaceutical Chatbot Service",
    description="LangGraph based Multi-Agent System",
    version="1.0.0",
    lifespan=lifespan
)

# CORS configuration
cors_origins = json.loads(os.getenv("CORS_ORIGINS", '["http://localhost:3000"]'))
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class ChatRequest(BaseModel):
    """Chat request model"""
    query: str = Field(..., description="User query")
    user_id: str = Field(..., description="User ID")
    company_id: str = Field(..., description="Company ID")
    session_id: Optional[str] = Field(None, description="Session ID")
    context_override: Optional[Dict[str, Any]] = Field(None, description="Context override")


class ChatResponse(BaseModel):
    """Chat response model"""
    response: str = Field(..., description="AI response")
    session_id: str = Field(..., description="Session ID")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Metadata")


class InterruptResponse(BaseModel):
    """Interrupt response model"""
    action: str = Field(..., description="Approval/rejection action")
    value: Optional[Any] = Field(None, description="Interrupt value")
    session_id: str = Field(..., description="Session ID")


# WebSocket connection manager
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


# API Endpoints
@app.get("/")
async def root():
    """Health check"""
    return {
        "service": "chatbot",
        "status": "healthy",
        "version": "1.0.0",
        "langgraph_version": "0.6.7"
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Synchronous chat endpoint"""
    try:
        # Generate session ID
        session_id = request.session_id or str(uuid.uuid4())

        # Create context
        context = AgentContext(
            user_id=request.user_id,
            company_id=request.company_id,
            session_id=session_id
        )

        # Apply context override
        if request.context_override:
            for key, value in request.context_override.items():
                if hasattr(context, key):
                    setattr(context, key, value)

        # Create initial state
        initial_state = create_initial_state(request.query)

        # Execute graph
        config = checkpointer_manager.get_config(session_id)
        result = await app.state.graph.ainvoke(
            initial_state,
            context=context,
            config=config
        )

        return ChatResponse(
            response=result.get("final_response", "Unable to generate response."),
            session_id=session_id,
            metadata=result.get("metadata", {})
        )

    except Exception as e:
        logger.error(f"Chat error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """WebSocket endpoint for real-time streaming"""
    await manager.connect(websocket, session_id)

    try:
        while True:
            # Receive message from client
            data = await websocket.receive_json()

            if data.get("type") == "chat":
                # Process chat
                await process_chat_stream(session_id, data, websocket)

            elif data.get("type") == "interrupt_response":
                # Handle interrupt response
                await process_interrupt_response(session_id, data)

            elif data.get("type") == "get_state":
                # Get current state
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
    """Process streaming chat"""
    try:
        # Create context
        context = AgentContext(
            user_id=data.get("user_id"),
            company_id=data.get("company_id"),
            session_id=session_id
        )

        # Create initial state
        initial_state = create_initial_state(data.get("query"))

        # Stream execution
        config = checkpointer_manager.get_config(session_id)

        async for chunk in app.state.graph.astream(
            initial_state,
            context=context,
            config=config,
            stream_mode="updates"
        ):
            # Send updates to client
            await websocket.send_json({
                "type": "update",
                "data": chunk,
                "timestamp": datetime.now().isoformat()
            })

            # Check for interrupts
            if chunk.get("interrupt_data"):
                await websocket.send_json({
                    "type": "interrupt",
                    "data": chunk["interrupt_data"],
                    "timestamp": datetime.now().isoformat()
                })

        # Send final state
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
    """Process interrupt response"""
    try:
        config = checkpointer_manager.get_config(session_id)

        # Resume with command
        command = Command(
            resume=data.get("value"),
            update=data.get("update")
        )

        # Resume graph
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
    """Resume interrupt (REST API)"""
    try:
        config = checkpointer_manager.get_config(response.session_id)

        # Resume with command
        command = Command(resume=response.value)

        # Resume graph
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
    """Get session checkpoints"""
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
    """Delete session"""
    try:
        success = await checkpointer_manager.delete_thread(session_id)
        if success:
            return {"status": "deleted", "session_id": session_id}
        else:
            raise HTTPException(status_code=404, detail="Session not found")
    except Exception as e:
        logger.error(f"Delete session error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("CHATBOT_HOST", "0.0.0.0"),
        port=int(os.getenv("CHATBOT_PORT", 8001)),
        reload=os.getenv("API_RELOAD", "true").lower() == "true"
    )