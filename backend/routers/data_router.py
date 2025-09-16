"""
FastAPI router for data access endpoints
Provides API endpoints for SQL, Vector, and Hybrid search
"""

from typing import List, Optional
import time
import logging
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from database.connection import (
    get_hr_session,
    get_sales_session,
    get_clients_session,
    get_target_session
)
from services import SQLService, VectorService, HybridSearchService
from schemas.data_schemas import (
    SQLQueryRequest,
    SQLQueryResponse,
    VectorSearchRequest,
    VectorSearchResponse,
    HybridSearchRequest,
    HybridSearchResponse,
    SchemaInfoResponse,
    ErrorResponse
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/v1/data",
    tags=["data"],
    responses={
        404: {"description": "Not found"},
        500: {"description": "Internal server error"}
    }
)

# Initialize services
sql_service = SQLService()
vector_service = VectorService()
hybrid_service = HybridSearchService()


# ============= SQL Endpoints =============

@router.post("/sql/query", response_model=SQLQueryResponse)
async def execute_sql_query(
    request: SQLQueryRequest,
    hr_session: AsyncSession = Depends(get_hr_session),
    sales_session: AsyncSession = Depends(get_sales_session),
    clients_session: AsyncSession = Depends(get_clients_session),
    target_session: AsyncSession = Depends(get_target_session)
) -> SQLQueryResponse:
    """
    Execute natural language query on SQL database

    Converts natural language to SQL and executes on specified database.
    """
    start_time = time.time()

    try:
        # Select appropriate session based on database
        session_map = {
            "hr_data": hr_session,
            "sales_performance": sales_session,
            "clients_info": clients_session,
            "sales_target": target_session
        }

        session = session_map.get(request.database)
        if not session:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown database: {request.database}"
            )

        # Process question
        result = await sql_service.process_question(
            question=request.question,
            database=request.database,
            session=session
        )

        if result.get("error"):
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        execution_time = time.time() - start_time

        return SQLQueryResponse(
            question=result["question"],
            sql=result["sql"],
            database=result["database"],
            data=result["data"],
            answer=result.get("answer"),
            count=result["count"],
            execution_time=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"SQL query error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/sql/schema/{database}", response_model=SchemaInfoResponse)
async def get_database_schema(
    database: str
) -> SchemaInfoResponse:
    """
    Get schema information for a database

    Returns table and column information with descriptions.
    """
    try:
        schema_info = await sql_service.get_schema_info(database)

        if schema_info.get("error"):
            raise HTTPException(
                status_code=404,
                detail=schema_info["error"]
            )

        return SchemaInfoResponse(
            database=schema_info["database"],
            description=schema_info["description"],
            tables=schema_info["tables"]
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Schema info error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============= Vector Search Endpoints =============

@router.post("/vector/search", response_model=VectorSearchResponse)
async def vector_search(
    request: VectorSearchRequest
) -> VectorSearchResponse:
    """
    Perform vector similarity search

    Searches ChromaDB collections using semantic similarity.
    """
    start_time = time.time()

    try:
        # Perform search based on collection type
        if "compliance" in request.collection.lower():
            result = await vector_service.search_compliance_rules(
                query=request.query,
                use_reranker=request.use_reranker,
                top_k=request.top_k
            )
        elif "hr" in request.collection.lower() or "internal" in request.collection.lower():
            result = await vector_service.search_hr_rules(
                query=request.query,
                use_reranker=request.use_reranker,
                top_k=request.top_k
            )
        else:
            result = await vector_service.general_vector_search(
                query=request.query,
                collection_name=request.collection,
                db_type=request.db_type,
                filters=request.filters,
                use_reranker=request.use_reranker,
                top_k=request.top_k
            )

        if result.get("error"):
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        execution_time = time.time() - start_time

        # Format results
        formatted_results = []
        for r in result.get("results", []):
            formatted_results.append({
                "text": r.get("text", ""),
                "metadata": r.get("metadata", {}),
                "score": r.get("score", 0.0),
                "source": request.collection
            })

        return VectorSearchResponse(
            query=result["query"],
            collection=request.collection,
            results=formatted_results,
            count=result["count"],
            filters_applied=request.filters,
            execution_time=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Vector search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.get("/vector/collection/{collection}")
async def get_collection_info(
    collection: str,
    db_type: str = Query("rules", description="Database type (rules or hr_rules)")
):
    """
    Get information about a vector collection

    Returns collection statistics and sample documents.
    """
    try:
        info = await vector_service.get_collection_info(
            collection_name=collection,
            db_type=db_type
        )

        if info.get("error"):
            raise HTTPException(
                status_code=404,
                detail=info["error"]
            )

        return info

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Collection info error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============= Hybrid Search Endpoints =============

@router.post("/hybrid/search", response_model=HybridSearchResponse)
async def hybrid_search(
    request: HybridSearchRequest,
    hr_session: AsyncSession = Depends(get_hr_session),
    sales_session: AsyncSession = Depends(get_sales_session)
) -> HybridSearchResponse:
    """
    Perform hybrid search across SQL and vector databases

    Combines results from structured and unstructured data sources.
    """
    start_time = time.time()

    try:
        # Use appropriate session based on databases requested
        session = None
        if request.databases:
            if "hr_data" in request.databases:
                session = hr_session
            elif any(db in request.databases for db in ["sales_performance", "clients_info", "sales_target"]):
                session = sales_session

        # Perform hybrid search
        result = await hybrid_service.hybrid_search(
            query=request.query,
            databases=request.databases,
            collections=request.collections,
            session=session,
            sql_weight=request.sql_weight,
            vector_weight=request.vector_weight,
            top_k=request.top_k
        )

        if result.get("error"):
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        execution_time = time.time() - start_time

        return HybridSearchResponse(
            query=result["query"],
            combined_results=result["combined_results"],
            sql_results=result["sql_results"],
            vector_results=result["vector_results"],
            metadata=result["metadata"],
            count=len(result["combined_results"]),
            execution_time=execution_time
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hybrid search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/hybrid/employee-compliance")
async def search_employee_compliance(
    employee_name: str = Query(..., description="Employee name"),
    hr_session: AsyncSession = Depends(get_hr_session)
):
    """
    Search employee information with applicable compliance rules

    Combines employee data with relevant compliance regulations.
    """
    try:
        result = await hybrid_service.search_employee_compliance(
            employee_name=employee_name,
            session=hr_session
        )

        if result.get("error"):
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Employee compliance search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@router.post("/hybrid/sales-context")
async def search_sales_with_context(
    query: str = Query(..., description="Sales query"),
    include_targets: bool = Query(True, description="Include sales targets"),
    include_rules: bool = Query(True, description="Include compliance rules"),
    sales_session: AsyncSession = Depends(get_sales_session)
):
    """
    Search sales data with contextual information

    Combines sales performance with targets and compliance rules.
    """
    try:
        result = await hybrid_service.search_sales_with_context(
            query=query,
            session=sales_session,
            include_targets=include_targets,
            include_rules=include_rules
        )

        if result.get("error"):
            raise HTTPException(
                status_code=400,
                detail=result["error"]
            )

        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sales context search error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ============= Metadata Endpoints =============

@router.get("/metadata")
async def get_all_metadata():
    """
    Get metadata for all databases and collections

    Returns comprehensive metadata information.
    """
    try:
        return {
            "sql_databases": [
                {
                    "name": "hr_data",
                    "description": "인사 정보 데이터베이스",
                    "tables": ["인사자료", "지점연락처"]
                },
                {
                    "name": "sales_performance",
                    "description": "매출 실적 데이터베이스",
                    "tables": ["sales_performance"]
                },
                {
                    "name": "clients_info",
                    "description": "거래처 정보 데이터베이스",
                    "tables": ["거래처정보"]
                },
                {
                    "name": "sales_target",
                    "description": "매출 목표 데이터베이스",
                    "tables": ["지점별목표"]
                }
            ],
            "vector_collections": [
                {
                    "name": "compliance_rules",
                    "db_type": "rules",
                    "description": "제약 영업 규제 준수 규칙"
                },
                {
                    "name": "internal_regulations",
                    "db_type": "hr_rules",
                    "description": "내부 규정 및 윤리강령"
                }
            ]
        }

    except Exception as e:
        logger.error(f"Metadata error: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )