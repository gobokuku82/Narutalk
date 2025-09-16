"""
Hybrid Search Service
Combines SQL and Vector search for comprehensive results
"""

from typing import List, Dict, Any, Optional
import logging
from sqlalchemy.ext.asyncio import AsyncSession

from .sql_service import SQLService
from .vector_service import VectorService

logger = logging.getLogger(__name__)


class HybridSearchService:
    """Service for hybrid search combining SQL and vector search"""

    def __init__(self):
        """Initialize Hybrid Search Service"""
        self.sql_service = SQLService()
        self.vector_service = VectorService()

    async def hybrid_search(
        self,
        query: str,
        databases: Optional[List[str]] = None,
        collections: Optional[List[str]] = None,
        session: Optional[AsyncSession] = None,
        sql_weight: float = 0.5,
        vector_weight: float = 0.5,
        top_k: int = 10
    ) -> Dict[str, Any]:
        """
        Perform hybrid search across SQL and vector databases

        Args:
            query: Search query
            databases: List of SQL databases to search
            collections: List of vector collections to search
            session: Database session for SQL queries
            sql_weight: Weight for SQL results (0-1)
            vector_weight: Weight for vector results (0-1)
            top_k: Number of final results

        Returns:
            Combined search results
        """
        try:
            results = {
                "query": query,
                "sql_results": [],
                "vector_results": [],
                "combined_results": [],
                "metadata": {
                    "sql_weight": sql_weight,
                    "vector_weight": vector_weight
                }
            }

            # Normalize weights
            total_weight = sql_weight + vector_weight
            if total_weight > 0:
                sql_weight = sql_weight / total_weight
                vector_weight = vector_weight / total_weight

            # SQL Search
            if databases and session:
                sql_results = await self._perform_sql_search(
                    query, databases, session
                )
                results["sql_results"] = sql_results

            # Vector Search
            if collections:
                vector_results = await self._perform_vector_search(
                    query, collections
                )
                results["vector_results"] = vector_results

            # Combine and rank results
            combined = self._combine_results(
                results["sql_results"],
                results["vector_results"],
                sql_weight,
                vector_weight
            )

            # Sort by combined score and limit
            combined.sort(key=lambda x: x["score"], reverse=True)
            results["combined_results"] = combined[:top_k]

            return results

        except Exception as e:
            logger.error(f"Error in hybrid search: {e}")
            return {
                "error": str(e),
                "sql_results": [],
                "vector_results": [],
                "combined_results": []
            }

    async def _perform_sql_search(
        self,
        query: str,
        databases: List[str],
        session: AsyncSession
    ) -> List[Dict[str, Any]]:
        """
        Perform SQL search across multiple databases

        Args:
            query: Search query
            databases: List of databases
            session: Database session

        Returns:
            SQL search results
        """
        all_results = []

        for db in databases:
            try:
                # Process question through Text2SQL
                result = await self.sql_service.process_question(
                    query, db, session
                )

                if not result.get("error") and result.get("data"):
                    for item in result["data"]:
                        all_results.append({
                            "source": f"sql_{db}",
                            "database": db,
                            "data": item,
                            "sql": result.get("sql", ""),
                            "score": 1.0  # SQL results get full score
                        })

            except Exception as e:
                logger.error(f"Error searching database {db}: {e}")

        return all_results

    async def _perform_vector_search(
        self,
        query: str,
        collections: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Perform vector search across multiple collections

        Args:
            query: Search query
            collections: List of collection names

        Returns:
            Vector search results
        """
        all_results = []

        for collection in collections:
            try:
                # Determine collection type
                if "compliance" in collection.lower() or "rules" in collection.lower():
                    result = await self.vector_service.search_compliance_rules(
                        query=query,
                        use_reranker=True,
                        top_k=5
                    )
                elif "hr" in collection.lower() or "internal" in collection.lower():
                    result = await self.vector_service.search_hr_rules(
                        query=query,
                        use_reranker=True,
                        top_k=5
                    )
                else:
                    result = await self.vector_service.general_vector_search(
                        query=query,
                        collection_name=collection,
                        use_reranker=True,
                        top_k=5
                    )

                if not result.get("error") and result.get("results"):
                    for item in result["results"]:
                        all_results.append({
                            "source": f"vector_{collection}",
                            "collection": collection,
                            "text": item.get("text", ""),
                            "metadata": item.get("metadata", {}),
                            "score": item.get("score", 0.5)
                        })

            except Exception as e:
                logger.error(f"Error searching collection {collection}: {e}")

        return all_results

    def _combine_results(
        self,
        sql_results: List[Dict],
        vector_results: List[Dict],
        sql_weight: float,
        vector_weight: float
    ) -> List[Dict[str, Any]]:
        """
        Combine and score SQL and vector results

        Args:
            sql_results: SQL search results
            vector_results: Vector search results
            sql_weight: Weight for SQL results
            vector_weight: Weight for vector results

        Returns:
            Combined results with weighted scores
        """
        combined = []

        # Add SQL results with weighted scores
        for result in sql_results:
            combined.append({
                **result,
                "type": "sql",
                "score": result.get("score", 1.0) * sql_weight
            })

        # Add vector results with weighted scores
        for result in vector_results:
            combined.append({
                **result,
                "type": "vector",
                "score": result.get("score", 0.5) * vector_weight
            })

        return combined

    async def search_employee_compliance(
        self,
        employee_name: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Search employee information and related compliance rules

        Args:
            employee_name: Employee name
            session: Database session

        Returns:
            Employee info with applicable compliance rules
        """
        try:
            # Get employee information from SQL
            employee_query = f"{employee_name}의 정보를 조회해주세요"
            employee_info = await self.sql_service.process_question(
                employee_query,
                "hr_data",
                session
            )

            # Extract employee details
            employee_data = {}
            if employee_info.get("data") and len(employee_info["data"]) > 0:
                employee_data = employee_info["data"][0]

            # Search relevant compliance rules based on position/department
            compliance_results = []
            if employee_data:
                position = employee_data.get("직급", "")
                department = employee_data.get("부서", "")

                # Search compliance rules
                compliance_query = f"{position} {department} 관련 규정"
                compliance = await self.vector_service.search_compliance_rules(
                    query=compliance_query,
                    use_reranker=True,
                    top_k=5
                )

                if compliance.get("results"):
                    compliance_results = compliance["results"]

            return {
                "employee": employee_data,
                "compliance_rules": compliance_results,
                "query": employee_name
            }

        except Exception as e:
            logger.error(f"Error in employee compliance search: {e}")
            return {
                "error": str(e),
                "employee": {},
                "compliance_rules": []
            }

    async def search_sales_with_context(
        self,
        query: str,
        session: AsyncSession,
        include_targets: bool = True,
        include_rules: bool = True
    ) -> Dict[str, Any]:
        """
        Search sales data with contextual information

        Args:
            query: Search query
            session: Database session
            include_targets: Include sales targets
            include_rules: Include relevant rules

        Returns:
            Sales data with context
        """
        try:
            results = {
                "query": query,
                "sales_data": [],
                "targets": [],
                "applicable_rules": []
            }

            # Search sales performance
            sales_result = await self.sql_service.process_question(
                query,
                "sales_performance",
                session
            )

            if not sales_result.get("error"):
                results["sales_data"] = sales_result.get("data", [])

            # Get related targets if requested
            if include_targets and results["sales_data"]:
                # Extract person/branch from results
                persons = set()
                branches = set()
                for record in results["sales_data"][:5]:  # Limit to avoid too many queries
                    if "담당자" in record:
                        persons.add(record["담당자"])
                    if "지점" in record:
                        branches.add(record["지점"])

                # Query targets
                if branches:
                    branch_list = "', '".join(branches)
                    target_query = f"SELECT * FROM 지점별목표 WHERE 지점 IN ('{branch_list}')"
                    target_result = await self.sql_service.execute_query(
                        target_query,
                        "sales_target",
                        session
                    )
                    if not target_result.get("error"):
                        results["targets"] = target_result.get("data", [])

            # Get applicable rules if requested
            if include_rules:
                rules_query = "영업 실적 관련 규정"
                rules_result = await self.vector_service.search_compliance_rules(
                    query=rules_query,
                    activity_type="영업",
                    use_reranker=True,
                    top_k=3
                )
                if not rules_result.get("error"):
                    results["applicable_rules"] = rules_result.get("results", [])

            return results

        except Exception as e:
            logger.error(f"Error in sales context search: {e}")
            return {
                "error": str(e),
                "sales_data": [],
                "targets": [],
                "applicable_rules": []
            }