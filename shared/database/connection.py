"""
Database connection management
Handles multiple SQLite databases with async support
"""

import os
from typing import Dict, Any, AsyncGenerator
from pathlib import Path
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine
)
from sqlalchemy.orm import declarative_base
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Base class for SQLAlchemy models
Base = declarative_base()

# Database configurations
DATABASE_CONFIGS = {
    "hr_data": {
        "path": os.getenv("HR_DB_PATH", "database/hr_information/hr_data.db"),
        "description": "Human Resources Database"
    },
    "sales_performance": {
        "path": os.getenv("SALES_DB_PATH", "database/sales_performance_db/sales_performance_db.db"),
        "description": "Sales Performance Database"
    },
    "clients_info": {
        "path": os.getenv("CLIENTS_DB_PATH", "database/sales_performance_db/clients_info.db"),
        "description": "Client Information Database"
    },
    "sales_target": {
        "path": os.getenv("TARGET_DB_PATH", "database/sales_performance_db/sales_target_db.db"),
        "description": "Sales Target Database"
    }
}

# Store database engines
_engines: Dict[str, AsyncEngine] = {}
_session_factories: Dict[str, async_sessionmaker] = {}


def get_database_url(db_name: str) -> str:
    """
    Get SQLite database URL for async connection

    Args:
        db_name: Name of the database from DATABASE_CONFIGS

    Returns:
        SQLite async URL
    """
    if db_name not in DATABASE_CONFIGS:
        raise ValueError(f"Unknown database: {db_name}")

    db_path = DATABASE_CONFIGS[db_name]["path"]
    # Convert to absolute path
    abs_path = Path(db_path).absolute()

    # Ensure database exists
    if not abs_path.exists():
        logger.warning(f"Database file not found: {abs_path}")

    # Use aiosqlite for async SQLite support
    return f"sqlite+aiosqlite:///{abs_path}"


async def init_databases():
    """
    Initialize all database connections
    Creates async engines and session factories
    """
    global _engines, _session_factories

    for db_name in DATABASE_CONFIGS:
        try:
            # Create async engine
            engine = create_async_engine(
                get_database_url(db_name),
                echo=os.getenv("SQL_ECHO", "false").lower() == "true",
                pool_pre_ping=True,
                pool_size=5,
                max_overflow=10
            )

            _engines[db_name] = engine

            # Create session factory
            _session_factories[db_name] = async_sessionmaker(
                engine,
                class_=AsyncSession,
                expire_on_commit=False
            )

            logger.info(f"Initialized database: {db_name}")

        except Exception as e:
            logger.error(f"Failed to initialize database {db_name}: {e}")


async def close_databases():
    """
    Close all database connections
    """
    global _engines

    for db_name, engine in _engines.items():
        await engine.dispose()
        logger.info(f"Closed database: {db_name}")

    _engines.clear()
    _session_factories.clear()


def get_db_engine(db_name: str) -> AsyncEngine:
    """
    Get database engine by name

    Args:
        db_name: Name of the database

    Returns:
        AsyncEngine instance
    """
    if db_name not in _engines:
        raise ValueError(f"Database {db_name} not initialized")

    return _engines[db_name]


@asynccontextmanager
async def get_async_session(db_name: str) -> AsyncGenerator[AsyncSession, None]:
    """
    Get async database session

    Args:
        db_name: Name of the database

    Yields:
        AsyncSession instance
    """
    if db_name not in _session_factories:
        raise ValueError(f"Database {db_name} not initialized")

    async with _session_factories[db_name]() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ChromaDB connection
class ChromaDBConnection:
    """
    ChromaDB connection manager
    """

    def __init__(self):
        import chromadb
        from chromadb.config import Settings

        self.rules_db_path = os.getenv("RULES_CHROMADB_PATH", "./database/rules_DB/chromadb")
        self.hr_rules_db_path = os.getenv("HR_RULES_CHROMADB_PATH", "./database/hr_rules_db/chromadb")

        # Initialize ChromaDB clients
        self.rules_client = chromadb.PersistentClient(
            path=self.rules_db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        self.hr_rules_client = chromadb.PersistentClient(
            path=self.hr_rules_db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        self._collections = {}

    def get_collection(self, db_type: str, collection_name: str):
        """
        Get ChromaDB collection

        Args:
            db_type: 'rules' or 'hr_rules'
            collection_name: Name of the collection

        Returns:
            ChromaDB collection
        """
        key = f"{db_type}_{collection_name}"

        if key not in self._collections:
            client = self.rules_client if db_type == "rules" else self.hr_rules_client

            try:
                self._collections[key] = client.get_collection(name=collection_name)
                logger.info(f"Loaded collection: {key}")
            except Exception as e:
                logger.error(f"Failed to load collection {key}: {e}")
                return None

        return self._collections[key]


# Global ChromaDB connection instance
chromadb_conn = ChromaDBConnection()


# Dependency injection for FastAPI
async def get_hr_session() -> AsyncGenerator[AsyncSession, None]:
    """Get HR database session for dependency injection"""
    async with get_async_session("hr_data") as session:
        yield session


async def get_sales_session() -> AsyncGenerator[AsyncSession, None]:
    """Get sales database session for dependency injection"""
    async with get_async_session("sales_performance") as session:
        yield session


async def get_clients_session() -> AsyncGenerator[AsyncSession, None]:
    """Get clients database session for dependency injection"""
    async with get_async_session("clients_info") as session:
        yield session


async def get_target_session() -> AsyncGenerator[AsyncSession, None]:
    """Get target database session for dependency injection"""
    async with get_async_session("sales_target") as session:
        yield session