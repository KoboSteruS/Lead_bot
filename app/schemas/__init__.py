"""
Pydantic схемы для LeadBot.
"""

from .user import UserCreate, UserUpdate, UserResponse
from .lead_magnet import LeadMagnetCreate, LeadMagnetUpdate, LeadMagnetResponse
from .product import ProductCreate, ProductUpdate, ProductResponse, ProductOfferCreate
from .warmup import (
    WarmupScenarioCreate, 
    WarmupScenarioUpdate, 
    WarmupMessageCreate,
    UserWarmupResponse
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    
    # Lead Magnet schemas
    "LeadMagnetCreate",
    "LeadMagnetUpdate",
    "LeadMagnetResponse",
    
    # Product schemas
    "ProductCreate",
    "ProductUpdate",
    "ProductResponse",
    "ProductOfferCreate",
    
    # Warmup schemas
    "WarmupScenarioCreate",
    "WarmupScenarioUpdate",
    "WarmupMessageCreate",
    "UserWarmupResponse"
]



