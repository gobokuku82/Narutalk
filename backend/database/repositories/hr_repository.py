"""
HR Database Repository
Handles CRUD operations for HR-related data
"""

from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import func

from ..models import HREmployee, BranchContact
import logging

logger = logging.getLogger(__name__)


class HRRepository:
    """Repository for HR database operations"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ============= Employee Operations =============

    async def get_employee_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get employee by name

        Args:
            name: Employee name

        Returns:
            Employee data or None
        """
        try:
            result = await self.session.execute(
                select(HREmployee).where(HREmployee.성명 == name)
            )
            employee = result.scalar_one_or_none()

            if employee:
                return {
                    "성명": employee.성명,
                    "직급": employee.직급,
                    "부서": employee.부서,
                    "입사일": employee.입사일,
                    "생년월일": employee.생년월일,
                    "연락처": employee.연락처,
                    "이메일": employee.이메일,
                    "주소": employee.주소,
                    "담당구역": employee.담당구역
                }
            return None

        except Exception as e:
            logger.error(f"Error getting employee by name: {e}")
            return None

    async def get_employees_by_department(self, department: str) -> List[Dict[str, Any]]:
        """
        Get all employees in a department

        Args:
            department: Department name

        Returns:
            List of employee data
        """
        try:
            result = await self.session.execute(
                select(HREmployee).where(HREmployee.부서 == department)
            )
            employees = result.scalars().all()

            return [
                {
                    "성명": emp.성명,
                    "직급": emp.직급,
                    "부서": emp.부서,
                    "담당구역": emp.담당구역,
                    "연락처": emp.연락처
                }
                for emp in employees
            ]

        except Exception as e:
            logger.error(f"Error getting employees by department: {e}")
            return []

    async def get_employees_by_position(self, position: str) -> List[Dict[str, Any]]:
        """
        Get all employees with specific position

        Args:
            position: Position/rank name

        Returns:
            List of employee data
        """
        try:
            result = await self.session.execute(
                select(HREmployee).where(HREmployee.직급 == position)
            )
            employees = result.scalars().all()

            return [
                {
                    "성명": emp.성명,
                    "직급": emp.직급,
                    "부서": emp.부서,
                    "담당구역": emp.담당구역
                }
                for emp in employees
            ]

        except Exception as e:
            logger.error(f"Error getting employees by position: {e}")
            return []

    async def search_employees(
        self,
        name: Optional[str] = None,
        department: Optional[str] = None,
        position: Optional[str] = None,
        area: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Search employees with multiple criteria

        Args:
            name: Employee name (partial match)
            department: Department name
            position: Position/rank
            area: Responsible area

        Returns:
            List of matching employees
        """
        try:
            query = select(HREmployee)
            conditions = []

            if name:
                conditions.append(HREmployee.성명.like(f"%{name}%"))
            if department:
                conditions.append(HREmployee.부서 == department)
            if position:
                conditions.append(HREmployee.직급 == position)
            if area:
                conditions.append(HREmployee.담당구역.like(f"%{area}%"))

            if conditions:
                query = query.where(and_(*conditions))

            result = await self.session.execute(query)
            employees = result.scalars().all()

            return [
                {
                    "성명": emp.성명,
                    "직급": emp.직급,
                    "부서": emp.부서,
                    "담당구역": emp.담당구역,
                    "연락처": emp.연락처,
                    "이메일": emp.이메일
                }
                for emp in employees
            ]

        except Exception as e:
            logger.error(f"Error searching employees: {e}")
            return []

    # ============= Branch Operations =============

    async def get_branch_by_name(self, branch_name: str) -> Optional[Dict[str, Any]]:
        """
        Get branch information by name

        Args:
            branch_name: Branch name

        Returns:
            Branch data or None
        """
        try:
            result = await self.session.execute(
                select(BranchContact).where(BranchContact.지점명 == branch_name)
            )
            branch = result.scalar_one_or_none()

            if branch:
                return {
                    "지점명": branch.지점명,
                    "지점장": branch.지점장,
                    "연락처": branch.연락처,
                    "주소": branch.주소,
                    "팩스": branch.팩스,
                    "이메일": branch.이메일
                }
            return None

        except Exception as e:
            logger.error(f"Error getting branch by name: {e}")
            return None

    async def get_all_branches(self) -> List[Dict[str, Any]]:
        """
        Get all branch information

        Returns:
            List of all branches
        """
        try:
            result = await self.session.execute(select(BranchContact))
            branches = result.scalars().all()

            return [
                {
                    "지점명": branch.지점명,
                    "지점장": branch.지점장,
                    "연락처": branch.연락처,
                    "주소": branch.주소
                }
                for branch in branches
            ]

        except Exception as e:
            logger.error(f"Error getting all branches: {e}")
            return []

    async def get_branches_by_manager(self, manager_name: str) -> List[Dict[str, Any]]:
        """
        Get branches managed by specific person

        Args:
            manager_name: Branch manager name

        Returns:
            List of branches
        """
        try:
            result = await self.session.execute(
                select(BranchContact).where(BranchContact.지점장 == manager_name)
            )
            branches = result.scalars().all()

            return [
                {
                    "지점명": branch.지점명,
                    "지점장": branch.지점장,
                    "연락처": branch.연락처,
                    "주소": branch.주소
                }
                for branch in branches
            ]

        except Exception as e:
            logger.error(f"Error getting branches by manager: {e}")
            return []

    # ============= Statistics Operations =============

    async def get_employee_statistics(self) -> Dict[str, Any]:
        """
        Get employee statistics

        Returns:
            Statistics dictionary
        """
        try:
            # Total employees
            total_result = await self.session.execute(
                select(func.count(HREmployee.성명))
            )
            total_count = total_result.scalar()

            # Employees by department
            dept_result = await self.session.execute(
                select(
                    HREmployee.부서,
                    func.count(HREmployee.성명).label("count")
                ).group_by(HREmployee.부서)
            )
            dept_counts = {row[0]: row[1] for row in dept_result}

            # Employees by position
            pos_result = await self.session.execute(
                select(
                    HREmployee.직급,
                    func.count(HREmployee.성명).label("count")
                ).group_by(HREmployee.직급)
            )
            pos_counts = {row[0]: row[1] for row in pos_result}

            return {
                "total_employees": total_count,
                "by_department": dept_counts,
                "by_position": pos_counts
            }

        except Exception as e:
            logger.error(f"Error getting employee statistics: {e}")
            return {}

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