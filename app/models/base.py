"""
Базовая модель для LeadBot.
"""

import uuid
from datetime import datetime
from sqlalchemy import Column, DateTime, func, String
from sqlalchemy.orm import DeclarativeBase, declared_attr


class BaseModel(DeclarativeBase):
    """Базовая модель для всех сущностей LeadBot."""
    
    __abstract__ = True
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    
    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id={self.id})>"
