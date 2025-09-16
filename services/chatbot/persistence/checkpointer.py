"""
Checkpointer configuration for LangGraph 0.6.7
Using AsyncSqliteSaver for dynamic state management
"""

import os
from pathlib import Path
from typing import Optional, AsyncContextManager
from contextlib import asynccontextmanager
import logging

from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from langgraph.checkpoint.base import BaseCheckpointSaver

logger = logging.getLogger(__name__)


class CheckpointerManager:
    """
    체크포인터 관리 클래스
    AsyncSqliteSaver를 사용한 동적 상태 관리
    """
    
    def __init__(self, db_path: Optional[str] = None):
        """
        Args:
            db_path: SQLite 데이터베이스 경로 (기본값: backend/checkpoint/state.db)
        """
        if db_path is None:
            # 기본 경로 설정
            checkpoint_dir = Path(__file__).parent.parent / "checkpoint"
            checkpoint_dir.mkdir(exist_ok=True)
            db_path = str(checkpoint_dir / "state.db")
        
        self.db_path = db_path
        self.checkpointer: Optional[AsyncSqliteSaver] = None
        logger.info(f"Checkpointer database path: {self.db_path}")
    
    @asynccontextmanager
    async def get_checkpointer(self) -> AsyncContextManager[AsyncSqliteSaver]:
        """
        AsyncSqliteSaver 컨텍스트 매니저 반환
        
        Usage:
            async with manager.get_checkpointer() as checkpointer:
                graph = builder.compile(checkpointer=checkpointer)
        """
        async with AsyncSqliteSaver.from_conn_string(self.db_path) as checkpointer:
            logger.info("AsyncSqliteSaver initialized")
            yield checkpointer
    
    async def initialize(self) -> AsyncSqliteSaver:
        """
        체크포인터 초기화 (FastAPI Lifespan에서 사용)
        """
        self.checkpointer = await AsyncSqliteSaver.from_conn_string(self.db_path).__aenter__()
        logger.info("Checkpointer initialized for FastAPI lifespan")
        return self.checkpointer
    
    async def cleanup(self):
        """
        체크포인터 정리 (FastAPI Lifespan에서 사용)
        """
        if self.checkpointer:
            await self.checkpointer.__aexit__(None, None, None)
            logger.info("Checkpointer cleaned up")
    
    async def get_thread_state(self, thread_id: str, checkpoint_ns: str = "") -> dict:
        """
        특정 스레드의 현재 상태 조회
        
        Args:
            thread_id: 스레드 ID
            checkpoint_ns: 체크포인트 네임스페이스
        
        Returns:
            현재 상태 딕셔너리
        """
        if not self.checkpointer:
            raise RuntimeError("Checkpointer not initialized")
        
        config = {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns
            }
        }
        
        checkpoint = await self.checkpointer.aget(config)
        if checkpoint:
            return checkpoint.get("channel_values", {})
        return {}
    
    async def list_checkpoints(self, thread_id: str, limit: int = 10) -> list:
        """
        특정 스레드의 체크포인트 목록 조회
        
        Args:
            thread_id: 스레드 ID
            limit: 조회할 체크포인트 수
        
        Returns:
            체크포인트 목록
        """
        if not self.checkpointer:
            raise RuntimeError("Checkpointer not initialized")
        
        config = {
            "configurable": {
                "thread_id": thread_id
            }
        }
        
        checkpoints = []
        async for checkpoint in self.checkpointer.alist(config, limit=limit):
            checkpoints.append({
                "id": checkpoint.get("id"),
                "thread_id": checkpoint.get("thread_id"),
                "checkpoint_ns": checkpoint.get("checkpoint_ns"),
                "created_at": checkpoint.get("created_at"),
                "metadata": checkpoint.get("metadata", {})
            })
        
        return checkpoints
    
    async def delete_thread(self, thread_id: str) -> bool:
        """
        특정 스레드의 모든 체크포인트 삭제
        
        Args:
            thread_id: 삭제할 스레드 ID
        
        Returns:
            삭제 성공 여부
        """
        if not self.checkpointer:
            raise RuntimeError("Checkpointer not initialized")
        
        try:
            # SQLite 직접 접근하여 삭제 (AsyncSqliteSaver 내부 구조 활용)
            import aiosqlite
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    "DELETE FROM checkpoints WHERE thread_id = ?",
                    (thread_id,)
                )
                await db.commit()
            logger.info(f"Deleted all checkpoints for thread: {thread_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete thread {thread_id}: {e}")
            return False
    
    def get_config(self, thread_id: str, checkpoint_ns: str = "") -> dict:
        """
        LangGraph 실행을 위한 config 생성
        
        Args:
            thread_id: 스레드 ID (세션 ID)
            checkpoint_ns: 체크포인트 네임스페이스
        
        Returns:
            LangGraph config 딕셔너리
        """
        return {
            "configurable": {
                "thread_id": thread_id,
                "checkpoint_ns": checkpoint_ns,
                "checkpoint_id": None  # 최신 체크포인트 사용
            }
        }


# 전역 체크포인터 매니저 인스턴스
checkpointer_manager = CheckpointerManager()


class DurabilityMode:
    """
    LangGraph 0.6.7 Durability Mode 설정
    """
    
    EXIT = "exit"      # 노드 종료 시에만 저장 (빠름, 안정성 낮음)
    ASYNC = "async"    # 비동기 저장 (균형)
    SYNC = "sync"      # 동기 저장 (느림, 안정성 높음)
    
    @staticmethod
    def get_mode(context_mode: str = "production") -> str:
        """
        컨텍스트에 따른 durability mode 선택
        
        Args:
            context_mode: development, staging, production
        
        Returns:
            적절한 durability mode
        """
        modes = {
            "development": DurabilityMode.EXIT,
            "staging": DurabilityMode.ASYNC,
            "production": DurabilityMode.SYNC
        }
        return modes.get(context_mode, DurabilityMode.ASYNC)