"""
Заглушка для PaymentService (не используется в LeadBot).

В LeadBot оплата происходит через внешние ссылки.
"""

from sqlalchemy.ext.asyncio import AsyncSession


class PaymentService:
    """Заглушка для совместимости с admin.py."""
    
    def __init__(self, session: AsyncSession):
        """Инициализация заглушки."""
        self.session = session



