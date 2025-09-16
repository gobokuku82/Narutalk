"""
Pydantic models for data API requests and responses
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ============= Request Models =============

class SQLQueryRequest(BaseModel):
    """SQL query request model"""
    question: str = Field(..., description="Natural language question")
    database: str = Field(..., description="Target database name")
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "지난달 매출 실적은?",
                "database": "sales_performance",
                "context": {"year": 2024, "month": 11}
            }
        }


class VectorSearchRequest(BaseModel):
    """Vector search request model"""
    query: str = Field(..., description="Search query")
    collection: str = Field(..., description="Collection name")
    db_type: str = Field("rules", description="Database type (rules or hr_rules)")
    filters: Optional[Dict[str, Any]] = Field(None, description="Metadata filters")
    use_reranker: bool = Field(True, description="Use reranker for results")
    top_k: int = Field(5, description="Number of results", ge=1, le=50)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "제품설명회 식사 한도",
                "collection": "compliance_rules",
                "db_type": "rules",
                "filters": {"activity": "제품설명회"},
                "use_reranker": True,
                "top_k": 5
            }
        }


class HybridSearchRequest(BaseModel):
    """Hybrid search request model"""
    query: str = Field(..., description="Search query")
    databases: Optional[List[str]] = Field(None, description="SQL databases to search")
    collections: Optional[List[str]] = Field(None, description="Vector collections to search")
    sql_weight: float = Field(0.5, description="Weight for SQL results", ge=0, le=1)
    vector_weight: float = Field(0.5, description="Weight for vector results", ge=0, le=1)
    top_k: int = Field(10, description="Number of final results", ge=1, le=100)

    class Config:
        json_schema_extra = {
            "example": {
                "query": "김철수 직원의 작년 실적과 관련 규정",
                "databases": ["hr_data", "sales_performance"],
                "collections": ["compliance_rules"],
                "sql_weight": 0.6,
                "vector_weight": 0.4,
                "top_k": 10
            }
        }


# ============= Response Models =============

class SQLResultItem(BaseModel):
    """Single SQL result item"""
    data: Dict[str, Any] = Field(..., description="Result data")
    score: Optional[float] = Field(1.0, description="Relevance score")


class SQLQueryResponse(BaseModel):
    """SQL query response model"""
    question: str = Field(..., description="Original question")
    sql: str = Field(..., description="Generated SQL query")
    database: str = Field(..., description="Database name")
    data: List[Dict[str, Any]] = Field(..., description="Query results")
    answer: Optional[str] = Field(None, description="Natural language answer")
    count: int = Field(..., description="Number of results")
    execution_time: Optional[float] = Field(None, description="Query execution time in seconds")

    class Config:
        json_schema_extra = {
            "example": {
                "question": "지난달 매출 실적은?",
                "sql": "SELECT * FROM sales_performance WHERE 년월 = '2024-11'",
                "database": "sales_performance",
                "data": [
                    {"담당자": "김철수", "매출액": 1500000, "달성률": 105}
                ],
                "answer": "지난달 매출 실적은 1,500,000원으로 목표 대비 105% 달성했습니다.",
                "count": 1,
                "execution_time": 0.023
            }
        }


class VectorSearchResult(BaseModel):
    """Single vector search result"""
    text: str = Field(..., description="Document text")
    metadata: Dict[str, Any] = Field(..., description="Document metadata")
    score: float = Field(..., description="Similarity score")
    source: Optional[str] = Field(None, description="Source information")


class VectorSearchResponse(BaseModel):
    """Vector search response model"""
    query: str = Field(..., description="Original query")
    collection: str = Field(..., description="Collection name")
    results: List[VectorSearchResult] = Field(..., description="Search results")
    count: int = Field(..., description="Number of results")
    filters_applied: Optional[Dict[str, Any]] = Field(None, description="Applied filters")
    execution_time: Optional[float] = Field(None, description="Search execution time")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "제품설명회 식사 한도",
                "collection": "compliance_rules",
                "results": [
                    {
                        "text": "제품설명회 시 1인당 10만원 이내 식음료 제공 가능",
                        "metadata": {"law_name": "공정경쟁규약", "article": "제10조"},
                        "score": 0.95,
                        "source": "compliance_rules"
                    }
                ],
                "count": 1,
                "filters_applied": {"activity": "제품설명회"},
                "execution_time": 0.156
            }
        }


class HybridSearchResult(BaseModel):
    """Single hybrid search result"""
    type: str = Field(..., description="Result type (sql or vector)")
    source: str = Field(..., description="Source database/collection")
    data: Optional[Dict[str, Any]] = Field(None, description="SQL result data")
    text: Optional[str] = Field(None, description="Vector result text")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Result metadata")
    score: float = Field(..., description="Combined score")


class HybridSearchResponse(BaseModel):
    """Hybrid search response model"""
    query: str = Field(..., description="Original query")
    combined_results: List[HybridSearchResult] = Field(..., description="Combined results")
    sql_results: List[Dict[str, Any]] = Field(..., description="SQL search results")
    vector_results: List[Dict[str, Any]] = Field(..., description="Vector search results")
    metadata: Dict[str, Any] = Field(..., description="Search metadata")
    count: int = Field(..., description="Total result count")
    execution_time: Optional[float] = Field(None, description="Total execution time")

    class Config:
        json_schema_extra = {
            "example": {
                "query": "김철수 직원 정보와 관련 규정",
                "combined_results": [
                    {
                        "type": "sql",
                        "source": "hr_data",
                        "data": {"성명": "김철수", "직급": "과장", "부서": "영업부"},
                        "score": 0.9
                    },
                    {
                        "type": "vector",
                        "source": "compliance_rules",
                        "text": "영업부 직원 행동 규정",
                        "metadata": {"rule_type": "행동강령"},
                        "score": 0.85
                    }
                ],
                "sql_results": [],
                "vector_results": [],
                "metadata": {"sql_weight": 0.5, "vector_weight": 0.5},
                "count": 2,
                "execution_time": 0.234
            }
        }


class TableInfo(BaseModel):
    """Database table information"""
    name: str = Field(..., description="Table name")
    description: Optional[str] = Field(None, description="Table description")
    columns: Dict[str, str] = Field(..., description="Column descriptions")


class SchemaInfoResponse(BaseModel):
    """Database schema information response"""
    database: str = Field(..., description="Database name")
    description: str = Field(..., description="Database description")
    tables: List[TableInfo] = Field(..., description="Table information")

    class Config:
        json_schema_extra = {
            "example": {
                "database": "hr_data",
                "description": "인사 정보 데이터베이스",
                "tables": [
                    {
                        "name": "인사자료",
                        "description": "직원 정보 테이블",
                        "columns": {
                            "성명": "직원 이름",
                            "직급": "직원 직급",
                            "부서": "소속 부서"
                        }
                    }
                ]
            }
        }


class ErrorResponse(BaseModel):
    """Error response model"""
    error: str = Field(..., description="Error message")
    detail: Optional[str] = Field(None, description="Detailed error information")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "error": "Database not found",
                "detail": "Database 'unknown_db' does not exist",
                "timestamp": "2024-01-15T10:30:00"
            }
        }


# ============= Metadata Models =============

class DatabaseMetadata(BaseModel):
    """Database metadata model"""
    name: str = Field(..., description="Database name")
    description: str = Field(..., description="Database description")
    tables: List[str] = Field(..., description="List of table names")
    last_updated: Optional[datetime] = Field(None, description="Last update time")


class CollectionMetadata(BaseModel):
    """Vector collection metadata model"""
    name: str = Field(..., description="Collection name")
    count: int = Field(..., description="Document count")
    db_type: str = Field(..., description="Database type")
    sample_documents: Optional[List[Dict]] = Field(None, description="Sample documents")