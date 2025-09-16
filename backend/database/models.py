"""
SQLAlchemy models for existing databases
Maps existing SQLite tables to Python classes
"""

from sqlalchemy import Column, String, Integer, Float, Date, DateTime, Text
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


# ============= HR Database Models =============

class HREmployee(Base):
    """인사자료 테이블 모델"""
    __tablename__ = "인사자료"
    __table_args__ = {"extend_existing": True}

    성명 = Column(String, primary_key=True)
    직급 = Column(String)
    부서 = Column(String)
    입사일 = Column(String)
    생년월일 = Column(String)
    연락처 = Column(String)
    이메일 = Column(String)
    주소 = Column(Text)
    담당구역 = Column(String)


class BranchContact(Base):
    """지점연락처 테이블 모델"""
    __tablename__ = "지점연락처"
    __table_args__ = {"extend_existing": True}

    지점명 = Column(String, primary_key=True)
    지점장 = Column(String)
    연락처 = Column(String)
    주소 = Column(Text)
    팩스 = Column(String)
    이메일 = Column(String)


# ============= Sales Performance Models =============

class SalesPerformance(Base):
    """매출실적 테이블 모델"""
    __tablename__ = "sales_performance"
    __table_args__ = {"extend_existing": True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    담당자 = Column(String)
    지점 = Column(String)
    년월 = Column(String)
    매출액 = Column(Float)
    목표액 = Column(Float)
    달성률 = Column(Float)
    제품군 = Column(String)
    거래처수 = Column(Integer)


# ============= Clients Info Models =============

class ClientInfo(Base):
    """거래처정보 테이블 모델"""
    __tablename__ = "거래처정보"
    __table_args__ = {"extend_existing": True}

    거래처코드 = Column(String, primary_key=True)
    거래처명 = Column(String)
    대표자 = Column(String)
    사업자번호 = Column(String)
    업종 = Column(String)
    주소 = Column(Text)
    연락처 = Column(String)
    담당자 = Column(String)
    거래시작일 = Column(String)
    신용등급 = Column(String)
    비고 = Column(Text)


# ============= Sales Target Models =============

class SalesTarget(Base):
    """지점별목표 테이블 모델"""
    __tablename__ = "지점별목표"
    __table_args__ = {"extend_existing": True}

    지점 = Column(String, primary_key=True)
    담당자 = Column(String, primary_key=True)

    # Monthly target columns (dynamic based on actual database)
    # These will be mapped dynamically
    def __init__(self, **kwargs):
        """Dynamic column initialization for monthly targets"""
        super().__init__(**kwargs)


# ============= Model Metadata =============

MODEL_METADATA = {
    "hr_data": {
        "models": [HREmployee, BranchContact],
        "description": "인사 및 조직 정보 데이터베이스"
    },
    "sales_performance": {
        "models": [SalesPerformance],
        "description": "매출 실적 데이터베이스"
    },
    "clients_info": {
        "models": [ClientInfo],
        "description": "거래처 정보 데이터베이스"
    },
    "sales_target": {
        "models": [SalesTarget],
        "description": "지점별 매출 목표 데이터베이스"
    }
}


# ============= Utility Functions =============

def get_models_for_db(db_name: str):
    """
    Get SQLAlchemy models for a specific database

    Args:
        db_name: Name of the database

    Returns:
        List of model classes
    """
    if db_name not in MODEL_METADATA:
        raise ValueError(f"Unknown database: {db_name}")

    return MODEL_METADATA[db_name]["models"]


def get_table_columns(model_class):
    """
    Get column information from a model class

    Args:
        model_class: SQLAlchemy model class

    Returns:
        Dictionary of column names and types
    """
    columns = {}
    for column in model_class.__table__.columns:
        columns[column.name] = {
            "type": str(column.type),
            "nullable": column.nullable,
            "primary_key": column.primary_key
        }
    return columns