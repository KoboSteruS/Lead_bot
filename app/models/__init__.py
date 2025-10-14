"""
Модели для LeadBot.
"""

from .base import BaseModel
from .user import User, UserStatus
from .lead_magnet import LeadMagnet, LeadMagnetType, UserLeadMagnet
from .product import Product, ProductOffer, ProductType, Currency, UserProductOffer
from .warmup import (
    WarmupScenario, WarmupMessage, WarmupMessageType, 
    UserWarmup, UserWarmupMessage
)
from .mailing import Mailing, MailingRecipient, MailingStatus
from .user_followup import UserFollowUp
from .admin import Admin

__all__ = [
    "BaseModel",
    "User", 
    "UserStatus",
    "LeadMagnet",
    "LeadMagnetType",
    "UserLeadMagnet",
    "Product",
    "ProductOffer",
    "ProductType",
    "Currency",
    "UserProductOffer",
    "WarmupScenario",
    "WarmupMessage",
    "WarmupMessageType",
    "UserWarmup",
    "UserWarmupMessage",
    "Mailing",
    "MailingRecipient",
    "MailingStatus",
    "UserFollowUp",
    "Admin"
]
