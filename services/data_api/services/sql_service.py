"""
SQL Service for Text2SQL functionality
Converts natural language queries to SQL and executes them
"""

import re
import json
from typing import Dict, Any, List, Optional
from pathlib import Path
import logging
import yaml

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from sqlalchemy.ext.asyncio import AsyncSession

from services.data_api.repositories.hr_repository import HRRepository
from services.data_api.repositories.sales_repository import SalesRepository

logger = logging.getLogger(__name__)


class SQLService:
    """Service for Text2SQL operations"""

    def __init__(self):
        """Initialize SQL Service with LLM and metadata"""
        # Initialize LLM for Text2SQL
        self.llm = ChatOpenAI(
            model="gpt-4o-mini",
            temperature=0,
            max_tokens=500
        )

        # Load database metadata
        self.metadata = self._load_metadata()

        # SQL validation patterns
        self.forbidden_keywords = [
            "drop", "delete", "truncate", "alter", "create",
            "insert", "update", "replace", "grant", "revoke"
        ]

    def _load_metadata(self) -> Dict[str, Any]:
        """
        Load database metadata from configuration

        Returns:
            Database metadata dictionary
        """
        try:
            metadata_path = Path("backend/config/database_metadata.yaml")
            if metadata_path.exists():
                with open(metadata_path, 'r', encoding='utf-8') as f:
                    return yaml.safe_load(f)
            else:
                # Default metadata if file doesn't exist
                return {
                    "databases": {
                        "hr_data": {
                            "description": "인사 정보 데이터베이스",
                            "tables": {
                                "인사자료": {
                                    "columns": {
                                        "성명": "직원 이름",
                                        "직급": "직원의 직급/직책",
                                        "부서": "소속 부서",
                                        "담당구역": "담당 영업 구역"
                                    }
                                },
                                "지점연락처": {
                                    "columns": {
                                        "지점명": "지점 이름",
                                        "지점장": "지점장 이름",
                                        "연락처": "지점 연락처"
                                    }
                                }
                            }
                        },
                        "sales_performance": {
                            "description": "매출 실적 데이터베이스",
                            "tables": {
                                "sales_performance": {
                                    "columns": {
                                        "담당자": "영업 담당자 이름",
                                        "지점": "소속 지점",
                                        "년월": "년월 (YYYY-MM 형식)",
                                        "매출액": "매출 금액",
                                        "목표액": "목표 금액",
                                        "달성률": "목표 달성률 (%)"
                                    }
                                }
                            }
                        }
                    }
                }
        except Exception as e:
            logger.error(f"Error loading metadata: {e}")
            return {}

    def _validate_sql(self, sql: str) -> bool:
        """
        Validate SQL query for safety

        Args:
            sql: SQL query string

        Returns:
            True if query is safe, False otherwise
        """
        sql_lower = sql.lower()

        # Check for forbidden keywords
        for keyword in self.forbidden_keywords:
            if keyword in sql_lower:
                logger.warning(f"Forbidden keyword '{keyword}' found in query")
                return False

        # Must be a SELECT statement
        if not sql_lower.strip().startswith("select"):
            logger.warning("Query is not a SELECT statement")
            return False

        return True

    async def text_to_sql(
        self,
        question: str,
        database: str,
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Convert natural language question to SQL query

        Args:
            question: Natural language question
            database: Target database name
            context: Additional context for query generation

        Returns:
            Dictionary with SQL query and metadata
        """
        try:
            # Get database schema information
            db_metadata = self.metadata.get("databases", {}).get(database, {})

            if not db_metadata:
                return {
                    "error": f"Database '{database}' metadata not found",
                    "sql": None
                }

            # Build schema context for prompt
            schema_context = self._build_schema_context(database, db_metadata)

            # Create prompt for Text2SQL
            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a SQL expert. Convert the natural language question to a SQL query.

Database Schema:
{schema}

Rules:
1. Only generate SELECT queries
2. Use exact table and column names from the schema
3. Handle Korean column names properly
4. Return only the SQL query without explanations
5. For date comparisons, use YYYY-MM format for 년월 columns
6. Use appropriate aggregation functions when needed"""),
                ("user", "{question}")
            ])

            # Generate SQL
            response = await self.llm.ainvoke(
                prompt.format_messages(
                    schema=schema_context,
                    question=question
                )
            )

            sql = response.content.strip()

            # Remove markdown code blocks if present
            sql = re.sub(r'```sql\s*', '', sql)
            sql = re.sub(r'```\s*$', '', sql)
            sql = sql.strip()

            # Validate SQL
            if not self._validate_sql(sql):
                return {
                    "error": "Generated SQL contains forbidden operations",
                    "sql": None
                }

            return {
                "sql": sql,
                "database": database,
                "question": question,
                "metadata": db_metadata
            }

        except Exception as e:
            logger.error(f"Error in text_to_sql: {e}")
            return {
                "error": str(e),
                "sql": None
            }

    def _build_schema_context(self, database: str, metadata: Dict) -> str:
        """
        Build schema context string for LLM

        Args:
            database: Database name
            metadata: Database metadata

        Returns:
            Schema context string
        """
        context_parts = [f"Database: {database}"]
        context_parts.append(f"Description: {metadata.get('description', '')}")
        context_parts.append("\nTables:")

        for table_name, table_info in metadata.get("tables", {}).items():
            context_parts.append(f"\n  Table: {table_name}")
            context_parts.append("  Columns:")

            for col_name, col_desc in table_info.get("columns", {}).items():
                context_parts.append(f"    - {col_name}: {col_desc}")

        return "\n".join(context_parts)

    async def execute_query(
        self,
        sql: str,
        database: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Execute SQL query safely

        Args:
            sql: SQL query to execute
            database: Database name
            session: Database session

        Returns:
            Query results
        """
        try:
            # Validate SQL again before execution
            if not self._validate_sql(sql):
                return {
                    "error": "SQL validation failed",
                    "data": []
                }

            # Choose repository based on database
            if database == "hr_data":
                repo = HRRepository(session)
            elif database in ["sales_performance", "clients_info", "sales_target"]:
                repo = SalesRepository(session, database)
            else:
                return {
                    "error": f"Unknown database: {database}",
                    "data": []
                }

            # Execute query
            results = await repo.execute_raw_query(sql)

            return {
                "sql": sql,
                "data": results,
                "count": len(results),
                "database": database
            }

        except Exception as e:
            logger.error(f"Error executing query: {e}")
            return {
                "error": str(e),
                "data": []
            }

    async def process_question(
        self,
        question: str,
        database: str,
        session: AsyncSession
    ) -> Dict[str, Any]:
        """
        Process a natural language question end-to-end

        Args:
            question: Natural language question
            database: Target database
            session: Database session

        Returns:
            Complete response with data
        """
        try:
            # Step 1: Convert to SQL
            sql_result = await self.text_to_sql(question, database)

            if sql_result.get("error") or not sql_result.get("sql"):
                return sql_result

            # Step 2: Execute SQL
            execution_result = await self.execute_query(
                sql_result["sql"],
                database,
                session
            )

            # Step 3: Format response
            if execution_result.get("error"):
                return execution_result

            # Generate natural language answer
            answer = await self._generate_answer(
                question,
                execution_result["data"]
            )

            return {
                "question": question,
                "sql": sql_result["sql"],
                "data": execution_result["data"],
                "answer": answer,
                "count": execution_result["count"],
                "database": database
            }

        except Exception as e:
            logger.error(f"Error processing question: {e}")
            return {
                "error": str(e),
                "data": []
            }

    async def _generate_answer(
        self,
        question: str,
        data: List[Dict]
    ) -> str:
        """
        Generate natural language answer from query results

        Args:
            question: Original question
            data: Query results

        Returns:
            Natural language answer
        """
        try:
            if not data:
                return "조회된 데이터가 없습니다."

            # Limit data for LLM context
            sample_data = data[:10] if len(data) > 10 else data

            prompt = ChatPromptTemplate.from_messages([
                ("system", """You are a helpful assistant.
Generate a natural Korean language answer based on the query results.
Be concise and informative. If there are many results, summarize key points."""),
                ("user", """Question: {question}

Query Results:
{results}

Please provide a natural language answer in Korean.""")
            ])

            response = await self.llm.ainvoke(
                prompt.format_messages(
                    question=question,
                    results=json.dumps(sample_data, ensure_ascii=False, indent=2)
                )
            )

            return response.content

        except Exception as e:
            logger.error(f"Error generating answer: {e}")
            return "결과를 자연어로 변환하는 중 오류가 발생했습니다."

    async def get_schema_info(self, database: str) -> Dict[str, Any]:
        """
        Get schema information for a database

        Args:
            database: Database name

        Returns:
            Schema information
        """
        try:
            db_metadata = self.metadata.get("databases", {}).get(database, {})

            if not db_metadata:
                return {
                    "error": f"Database '{database}' not found",
                    "tables": []
                }

            tables_info = []
            for table_name, table_data in db_metadata.get("tables", {}).items():
                tables_info.append({
                    "name": table_name,
                    "description": table_data.get("description", ""),
                    "columns": table_data.get("columns", {})
                })

            return {
                "database": database,
                "description": db_metadata.get("description", ""),
                "tables": tables_info
            }

        except Exception as e:
            logger.error(f"Error getting schema info: {e}")
            return {
                "error": str(e),
                "tables": []
            }