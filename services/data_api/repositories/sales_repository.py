"""
Sales Database Repository
Handles CRUD operations for sales-related data
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, date
from sqlalchemy import select, and_, or_, text, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from shared.models import SalesPerformance, ClientInfo, SalesTarget
import logging

logger = logging.getLogger(__name__)


class SalesRepository:
    """Repository for sales database operations"""

    def __init__(self, session: AsyncSession, db_name: str = "sales_performance"):
        self.session = session
        self.db_name = db_name

    # ============= Sales Performance Operations =============

    async def get_sales_by_person(
        self,
        person_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sales performance by person

        Args:
            person_name: Sales person name
            start_date: Start date (YYYY-MM format)
            end_date: End date (YYYY-MM format)

        Returns:
            List of sales records
        """
        try:
            query = select(SalesPerformance).where(
                SalesPerformance.담당자 == person_name
            )

            if start_date:
                query = query.where(SalesPerformance.년월 >= start_date)
            if end_date:
                query = query.where(SalesPerformance.년월 <= end_date)

            query = query.order_by(desc(SalesPerformance.년월))

            result = await self.session.execute(query)
            records = result.scalars().all()

            return [
                {
                    "담당자": rec.담당자,
                    "지점": rec.지점,
                    "년월": rec.년월,
                    "매출액": rec.매출액,
                    "목표액": rec.목표액,
                    "달성률": rec.달성률,
                    "제품군": rec.제품군,
                    "거래처수": rec.거래처수
                }
                for rec in records
            ]

        except Exception as e:
            logger.error(f"Error getting sales by person: {e}")
            return []

    async def get_sales_by_branch(
        self,
        branch_name: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sales performance by branch

        Args:
            branch_name: Branch name
            start_date: Start date (YYYY-MM format)
            end_date: End date (YYYY-MM format)

        Returns:
            List of sales records
        """
        try:
            query = select(SalesPerformance).where(
                SalesPerformance.지점 == branch_name
            )

            if start_date:
                query = query.where(SalesPerformance.년월 >= start_date)
            if end_date:
                query = query.where(SalesPerformance.년월 <= end_date)

            query = query.order_by(desc(SalesPerformance.년월))

            result = await self.session.execute(query)
            records = result.scalars().all()

            return [
                {
                    "담당자": rec.담당자,
                    "지점": rec.지점,
                    "년월": rec.년월,
                    "매출액": rec.매출액,
                    "목표액": rec.목표액,
                    "달성률": rec.달성률,
                    "제품군": rec.제품군
                }
                for rec in records
            ]

        except Exception as e:
            logger.error(f"Error getting sales by branch: {e}")
            return []

    async def get_top_performers(
        self,
        period: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get top performing sales people for a period

        Args:
            period: Period (YYYY-MM format)
            limit: Number of top performers to return

        Returns:
            List of top performers
        """
        try:
            result = await self.session.execute(
                select(
                    SalesPerformance.담당자,
                    SalesPerformance.지점,
                    func.sum(SalesPerformance.매출액).label("총매출액"),
                    func.avg(SalesPerformance.달성률).label("평균달성률")
                )
                .where(SalesPerformance.년월 == period)
                .group_by(SalesPerformance.담당자, SalesPerformance.지점)
                .order_by(desc("총매출액"))
                .limit(limit)
            )

            rows = result.all()
            return [
                {
                    "담당자": row[0],
                    "지점": row[1],
                    "총매출액": row[2],
                    "평균달성률": row[3]
                }
                for row in rows
            ]

        except Exception as e:
            logger.error(f"Error getting top performers: {e}")
            return []

    async def get_sales_summary(
        self,
        start_date: str,
        end_date: str,
        group_by: str = "branch"  # "branch", "person", "product"
    ) -> Dict[str, Any]:
        """
        Get sales summary with aggregations

        Args:
            start_date: Start date
            end_date: End date
            group_by: Grouping criteria

        Returns:
            Summary statistics
        """
        try:
            if group_by == "branch":
                group_col = SalesPerformance.지점
            elif group_by == "person":
                group_col = SalesPerformance.담당자
            else:
                group_col = SalesPerformance.제품군

            result = await self.session.execute(
                select(
                    group_col,
                    func.sum(SalesPerformance.매출액).label("총매출"),
                    func.sum(SalesPerformance.목표액).label("총목표"),
                    func.avg(SalesPerformance.달성률).label("평균달성률"),
                    func.count(SalesPerformance.id).label("건수")
                )
                .where(
                    and_(
                        SalesPerformance.년월 >= start_date,
                        SalesPerformance.년월 <= end_date
                    )
                )
                .group_by(group_col)
                .order_by(desc("총매출"))
            )

            rows = result.all()
            return {
                "period": f"{start_date} ~ {end_date}",
                "group_by": group_by,
                "data": [
                    {
                        group_by: row[0],
                        "총매출": row[1],
                        "총목표": row[2],
                        "평균달성률": row[3],
                        "건수": row[4]
                    }
                    for row in rows
                ]
            }

        except Exception as e:
            logger.error(f"Error getting sales summary: {e}")
            return {}

    # ============= Client Operations =============

    async def get_client_by_code(self, client_code: str) -> Optional[Dict[str, Any]]:
        """
        Get client information by code

        Args:
            client_code: Client code

        Returns:
            Client data or None
        """
        try:
            result = await self.session.execute(
                select(ClientInfo).where(ClientInfo.거래처코드 == client_code)
            )
            client = result.scalar_one_or_none()

            if client:
                return {
                    "거래처코드": client.거래처코드,
                    "거래처명": client.거래처명,
                    "대표자": client.대표자,
                    "사업자번호": client.사업자번호,
                    "업종": client.업종,
                    "주소": client.주소,
                    "연락처": client.연락처,
                    "담당자": client.담당자,
                    "거래시작일": client.거래시작일,
                    "신용등급": client.신용등급,
                    "비고": client.비고
                }
            return None

        except Exception as e:
            logger.error(f"Error getting client by code: {e}")
            return None

    async def search_clients(
        self,
        name: Optional[str] = None,
        manager: Optional[str] = None,
        industry: Optional[str] = None,
        credit_grade: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search clients with multiple criteria

        Args:
            name: Client name (partial match)
            manager: Manager name
            industry: Industry type
            credit_grade: Credit grade

        Returns:
            List of matching clients
        """
        try:
            query = select(ClientInfo)
            conditions = []

            if name:
                conditions.append(ClientInfo.거래처명.like(f"%{name}%"))
            if manager:
                conditions.append(ClientInfo.담당자 == manager)
            if industry:
                conditions.append(ClientInfo.업종 == industry)
            if credit_grade:
                conditions.append(ClientInfo.신용등급 == credit_grade)

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            clients = result.scalars().all()

            return [
                {
                    "거래처코드": client.거래처코드,
                    "거래처명": client.거래처명,
                    "담당자": client.담당자,
                    "업종": client.업종,
                    "신용등급": client.신용등급,
                    "연락처": client.연락처
                }
                for client in clients
            ]

        except Exception as e:
            logger.error(f"Error searching clients: {e}")
            return []

    # ============= Target Operations =============

    async def get_targets_by_branch(
        self,
        branch_name: str,
        year_month: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get sales targets by branch

        Args:
            branch_name: Branch name
            year_month: Specific month (YYYYMM format)

        Returns:
            List of targets
        """
        try:
            query = select(SalesTarget).where(SalesTarget.지점 == branch_name)
            result = await self.session.execute(query)
            targets = result.scalars().all()

            # Convert to dictionary format
            target_list = []
            for target in targets:
                target_dict = {
                    "지점": target.지점,
                    "담당자": target.담당자
                }

                # Add monthly target columns dynamically
                for col in target.__table__.columns:
                    if col.name not in ["지점", "담당자"]:
                        value = getattr(target, col.name)
                        if year_month and col.name == year_month:
                            target_dict["목표액"] = value
                        else:
                            target_dict[col.name] = value

                target_list.append(target_dict)

            return target_list

        except Exception as e:
            logger.error(f"Error getting targets by branch: {e}")
            return []

    # ============= Raw SQL Operations =============

    async def execute_raw_query(self, query: str, params: Optional[Dict] = None) -> List[Dict]:
        """
        Execute raw SQL query (read-only)

        Args:
            query: SQL query string
            params: Query parameters

        Returns:
            Query results as list of dictionaries
        """
        try:
            # Ensure query is read-only
            query_lower = query.lower().strip()
            if any(keyword in query_lower for keyword in ["insert", "update", "delete", "drop", "alter", "create"]):
                raise ValueError("Only SELECT queries are allowed")

            result = await self.session.execute(text(query), params or {})
            rows = result.fetchall()

            # Convert to list of dictionaries
            if rows and result.keys():
                return [dict(zip(result.keys(), row)) for row in rows]
            return []

        except Exception as e:
            logger.error(f"Error executing raw query: {e}")
            raise