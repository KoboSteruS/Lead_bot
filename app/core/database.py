"""
Настройки базы данных с использованием SQLAlchemy.

Содержит конфигурацию подключения к базе данных и сессии.
"""

from typing import AsyncGenerator
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from loguru import logger

from config.settings import settings
from app.models.base import BaseModel

# Используем BaseModel как базу
Base = BaseModel

# Импортируем все модели для регистрации в metadata
from app.models.user import User
from app.models.lead_magnet import LeadMagnet, UserLeadMagnet
from app.models.warmup import WarmupScenario, WarmupMessage, UserWarmup, UserWarmupMessage
from app.models.product import Product, ProductOffer, UserProductOffer


# Создание асинхронного движка базы данных
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_pre_ping=True,
    pool_recycle=300,
)

# Создание фабрики сессий
async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_database() -> AsyncGenerator[AsyncSession, None]:
    """
    Получение сессии базы данных.
    
    Yields:
        AsyncSession: Асинхронная сессия базы данных
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Ошибка в сессии базы данных: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


from contextlib import asynccontextmanager

@asynccontextmanager
async def get_db_session():
    """
    Получение сессии базы данных (контекстный менеджер).
    
    Yields:
        AsyncSession: Асинхронная сессия базы данных
    """
    async with async_session_maker() as session:
        try:
            yield session
        except Exception as e:
            logger.error(f"Ошибка в сессии базы данных: {e}")
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_database() -> None:
    """Инициализация базы данных."""
    try:
        async with engine.begin() as conn:
            # Создание всех таблиц (модели уже импортированы выше)
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка инициализации базы данных: {e}")
        raise


async def close_database() -> None:
    """Закрытие соединения с базой данных."""
    await engine.dispose()
    logger.info("Соединение с базой данных закрыто")
