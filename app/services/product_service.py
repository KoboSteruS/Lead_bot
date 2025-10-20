"""
Сервис для работы с продуктами и трипвайерами.

Управляет созданием офферов, отслеживанием кликов и системой дожима.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from uuid import UUID
from sqlalchemy import select, and_, or_, desc, func, update, delete, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models import (
    Product,
    ProductOffer,
    UserProductOffer,
    User,
    ProductType
)
from app.schemas.product import (
    ProductCreate,
    ProductOfferCreate,
    UserProductOfferResponse
)
from app.core.exceptions import BaseException as ProductException


class ProductService:
    """Сервис для работы с продуктами и трипвайерами."""
    
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса."""
        self.session = session
    
    async def get_active_product_by_type(self, product_type: ProductType) -> Optional[Product]:
        """Получить активный продукт по типу."""
        try:
            stmt = (
                select(Product)
                .where(
                    and_(
                        Product.type == product_type,
                        Product.is_active == True
                    )
                )
                .order_by(Product.sort_order.asc())
            )
            result = await self.session.execute(stmt)
            product = result.scalar_one_or_none()
            
            if product:
                logger.debug(f"Найден активный продукт типа {product_type}: {product.name}")
            
            return product
            
        except Exception as e:
            logger.error(f"Ошибка получения продукта типа {product_type}: {e}")
            return None
    
    async def get_active_offer_for_product(self, product_id: str) -> Optional[ProductOffer]:
        """Получить активный оффер для продукта (первый по дате создания)."""
        try:
            stmt = (
                select(ProductOffer)
                .where(
                    and_(
                        ProductOffer.product_id == product_id,
                        ProductOffer.is_active == True
                    )
                )
                .options(selectinload(ProductOffer.product))
                .order_by(ProductOffer.created_at.asc())
                .limit(1)
            )
            result = await self.session.execute(stmt)
            offer = result.scalar_one_or_none()
            
            if offer:
                logger.debug(f"Найден активный оффер: {offer.name}")
            
            return offer
            
        except Exception as e:
            logger.error(f"Ошибка получения оффера для продукта {product_id}: {e}")
            return None
    
    async def has_user_seen_offer(self, user_id: str, offer_id: str) -> bool:
        """Проверить, видел ли пользователь оффер."""
        try:
            stmt = select(UserProductOffer).where(
                and_(
                    UserProductOffer.user_id == user_id,
                    UserProductOffer.offer_id == offer_id
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(f"Ошибка проверки показа оффера: {e}")
            return False
    
    async def show_offer_to_user(self, user_id: str, offer_id: str) -> Optional[UserProductOffer]:
        """Отметить показ оффера пользователю."""
        try:
            # Проверяем, не показывали ли уже этот оффер
            existing = await self.has_user_seen_offer(user_id, offer_id)
            if existing:
                logger.info(f"Оффер {offer_id} уже показывался пользователю {user_id}")
                return None
            
            # Создаем запись о показе
            user_offer = UserProductOffer(
                user_id=user_id,
                offer_id=offer_id,
                shown_at=datetime.utcnow(),
                clicked=False
            )
            
            self.session.add(user_offer)
            await self.session.commit()
            await self.session.refresh(user_offer)
            
            logger.info(f"Оффер {offer_id} показан пользователю {user_id}")
            return user_offer
            
        except Exception as e:
            logger.error(f"Ошибка показа оффера пользователю: {e}")
            await self.session.rollback()
            return None
    
    async def mark_offer_clicked(self, user_id: str, offer_id: str) -> bool:
        """Отметить клик по офферу."""
        try:
            stmt = (
                select(UserProductOffer)
                .where(
                    and_(
                        UserProductOffer.user_id == user_id,
                        UserProductOffer.offer_id == offer_id
                    )
                )
            )
            result = await self.session.execute(stmt)
            user_offer = result.scalar_one_or_none()
            
            if not user_offer:
                logger.warning(f"Запись показа оффера не найдена: user={user_id}, offer={offer_id}")
                return False
            
            # Обновляем информацию о клике
            user_offer.clicked = True
            user_offer.clicked_at = datetime.utcnow()
            
            await self.session.commit()
            
            logger.info(f"Отмечен клик по офферу {offer_id} пользователем {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отметки клика по офферу: {e}")
            await self.session.rollback()
            return False
    
    async def get_users_for_followup_offers(self, hours_since_show: int = 48) -> List[Dict[str, Any]]:
        """Получить пользователей для дожима (повторного оффера)."""
        try:
            cutoff_time = datetime.utcnow() - timedelta(hours=hours_since_show)
            
            # Ищем пользователей, которым показывали оффер, но они не кликнули
            stmt = (
                select(UserProductOffer, ProductOffer, Product, User)
                .join(ProductOffer, UserProductOffer.offer_id == ProductOffer.id)
                .join(Product, ProductOffer.product_id == Product.id)
                .join(User, UserProductOffer.user_id == User.id)
                .where(
                    and_(
                        UserProductOffer.clicked == False,
                        UserProductOffer.shown_at <= cutoff_time,
                        Product.type == ProductType.TRIPWIRE,
                        Product.is_active == True,
                        ProductOffer.is_active == True
                    )
                )
                .order_by(UserProductOffer.shown_at.asc())
            )
            
            result = await self.session.execute(stmt)
            rows = result.all()
            
            users_for_followup = []
            for user_offer, offer, product, user in rows:
                # Проверяем, не отправляли ли уже дожим
                followup_sent = await self._has_followup_been_sent(user.id, offer.id)
                if not followup_sent:
                    users_for_followup.append({
                        'user': user,
                        'offer': offer,
                        'product': product,
                        'user_offer': user_offer
                    })
            
            logger.info(f"Найдено {len(users_for_followup)} пользователей для дожима")
            return users_for_followup
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователей для дожима: {e}")
            return []
    
    async def mark_followup_sent(self, user_id: str, offer_id: str) -> bool:
        """Отметить отправку дожима."""
        try:
            # Создаем новую запись показа с пометкой о дожиме
            followup_offer = UserProductOffer(
                user_id=user_id,
                offer_id=offer_id,
                shown_at=datetime.utcnow(),
                clicked=False
            )
            
            self.session.add(followup_offer)
            await self.session.commit()
            
            logger.info(f"Отмечен дожим для пользователя {user_id}, оффер {offer_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка отметки дожима: {e}")
            await self.session.rollback()
            return False
    
    async def create_default_tripwire(self) -> Product:
        """Создать трипвайер по умолчанию."""
        try:
            # Проверяем, есть ли уже трипвайер
            existing_product = await self.get_active_product_by_type(ProductType.TRIPWIRE)
            if existing_product:
                logger.info(f"Трипвайер уже существует: {existing_product.name}")
                return existing_product
            
            # Создаем продукт
            product = Product(
                name="30 дней по книге Наполеона Хилла",
                description="Практическая программа развития по книге 'Думай и богатей'",
                type=ProductType.TRIPWIRE,
                price=99000,  # 990 рублей в копейках
                currency="RUB",
                payment_url="https://example.com/payment/tripwire",  # Заглушка, позже заменить
                offer_text=(
                    "🚀 <b>30 дней по книге Наполеона Хилла</b>\n\n"
                    "Что ты получишь:\n"
                    "• 30 практических заданий на каждый день\n"
                    "• Пошаговое внедрение 13 принципов успеха\n"
                    "• Систему отчётности и контроля\n"
                    "• Поддержку и мотивацию в закрытом чате\n"
                    "• Персональные рекомендации от наставника\n\n"
                    "💰 <b>Стоимость: 990 рублей</b>\n\n"
                    "⏰ <b>Специальное предложение действует ограниченное время!</b>"
                ),
                is_active=True,
                sort_order=1
            )
            
            self.session.add(product)
            await self.session.flush()  # Получаем ID
            
            # Создаем основной оффер
            main_offer = ProductOffer(
                product_id=product.id.hex,
                name="Основной оффер",
                text=(
                    "🚀 <b>ПРОГРАММА «30 ДНЕЙ ПО КНИГЕ ХИЛЛА»</b>\n\n"
                    "📚 <b>Что вы получите:</b>\n"
                    "• 30 практических заданий на каждый день\n"
                    "• Пошаговое внедрение 13 принципов успеха\n"
                    "• Систему отчётности и контроля\n"
                    "• Поддержку и мотивацию в закрытом чате\n"
                    "• Персональные рекомендации от наставника\n\n"
                    "💰 <b>Стоимость: 990 рублей</b>\n\n"
                    "⏰ <b>Специальное предложение действует ограниченное время!</b>\n\n"
                    "👇 Выберите удобный способ оплаты:"
                ),
                price=None,  # Используем цену продукта
                is_active=True
            )
            
            # Создаем оффер дожима
            followup_offer = ProductOffer(
                product_id=product.id.hex,
                name="Дожим оффер",
                text=(
                    "☕ <b>990 рублей — меньше, чем чашка кофе в день</b>\n\n"
                    "Подумай об этом:\n"
                    "• Чашка кофе даёт бодрость на 2 часа\n"
                    "• Эта программа даст тебе систему на всю жизнь\n\n"
                    "🎯 <b>За 30 дней ты:</b>\n"
                    "• Создашь чёткий план достижения целей\n"
                    "• Разовьёшь дисциплину и силу воли\n"
                    "• Изменишь мышление на успех\n\n"
                    "💎 <b>Результат может изменить твою жизнь.</b>\n\n"
                    "⚡ <b>Это твой последний шанс войти в программу по этой цене.</b>\n\n"
                    "👇 Не упусти возможность:"
                ),
                price=None,  # Используем цену продукта
                is_active=True
            )
            
            self.session.add(main_offer)
            self.session.add(followup_offer)
            
            await self.session.commit()
            await self.session.refresh(product)
            
            logger.info(f"Создан трипвайер по умолчанию: {product.name}")
            return product
            
        except Exception as e:
            logger.error(f"Ошибка создания трипвайера по умолчанию: {e}")
            await self.session.rollback()
            raise ProductException(f"Ошибка создания трипвайера: {e}")
    
    async def get_offer_statistics(self, offer_id: str) -> Dict[str, Any]:
        """Получить статистику по офферу."""
        try:
            # Общее количество показов
            stmt_shows = select(UserProductOffer).where(UserProductOffer.offer_id == offer_id)
            result_shows = await self.session.execute(stmt_shows)
            all_shows = result_shows.scalars().all()
            
            # Количество кликов
            clicks = [show for show in all_shows if show.clicked]
            
            # Расчет конверсии
            total_shows = len(all_shows)
            total_clicks = len(clicks)
            conversion_rate = (total_clicks / total_shows * 100) if total_shows > 0 else 0
            
            # Статистика по времени
            now = datetime.utcnow()
            today_shows = [show for show in all_shows if (now - show.shown_at).days == 0]
            week_shows = [show for show in all_shows if (now - show.shown_at).days <= 7]
            
            return {
                'total_shows': total_shows,
                'total_clicks': total_clicks,
                'conversion_rate': round(conversion_rate, 2),
                'today_shows': len(today_shows),
                'week_shows': len(week_shows),
                'avg_time_to_click': self._calculate_avg_time_to_click(clicks)
            }
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики оффера: {e}")
            return {}
    
    # Приватные методы
    
    async def _has_followup_been_sent(self, user_id: str, offer_id: str) -> bool:
        """Проверить, отправлялся ли уже дожим."""
        try:
            # Считаем количество показов оффера этому пользователю
            stmt = select(UserProductOffer).where(
                and_(
                    UserProductOffer.user_id == user_id,
                    UserProductOffer.offer_id == offer_id
                )
            )
            result = await self.session.execute(stmt)
            shows = result.scalars().all()
            
            # Если показов больше 1, значит дожим уже отправлялся
            return len(shows) > 1
            
        except Exception as e:
            logger.error(f"Ошибка проверки дожима: {e}")
            return False
    
    def _calculate_avg_time_to_click(self, clicks: List[UserProductOffer]) -> float:
        """Рассчитать среднее время до клика."""
        if not clicks:
            return 0.0
        
        times = []
        for click in clicks:
            if click.clicked_at and click.shown_at:
                delta = click.clicked_at - click.shown_at
                times.append(delta.total_seconds() / 3600)  # в часах
        
        return round(sum(times) / len(times), 2) if times else 0.0
    
    # === МЕТОДЫ ДЛЯ АДМИНКИ ===
    
    async def get_all_products(self, limit: int = 50) -> List[Product]:
        """Получить все продукты для админки."""
        try:
            stmt = (
                select(Product)
                .options(selectinload(Product.offers))
                .order_by(Product.created_at.desc())
                .limit(limit)
            )
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка получения всех продуктов: {e}")
            return []
    
    async def get_product_by_id(self, product_id: str) -> Optional[Product]:
        """Получить продукт по ID (поддерживает короткие UUID - первые 8 символов)."""
        try:
            # Если передан короткий UUID (8 символов), ищем по LIKE
            if len(product_id) == 8:
                from sqlalchemy import String, cast
                stmt = (
                    select(Product)
                    .options(selectinload(Product.offers))
                    .where(cast(Product.id, String).like(f"{product_id}%"))
                )
            else:
                # Полный UUID
                product_uuid = UUID(product_id) if isinstance(product_id, str) else product_id
                stmt = (
                    select(Product)
                    .options(selectinload(Product.offers))
                    .where(Product.id == product_uuid)
                )
            
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения продукта {product_id}: {e}")
            return None
    
    async def create_product(self, product_data: ProductCreate) -> Optional[Product]:
        """Создать новый продукт."""
        try:
            product = Product(**product_data.model_dump() if hasattr(product_data, 'model_dump') else product_data)
            self.session.add(product)
            await self.session.commit()
            await self.session.refresh(product)
            logger.info(f"Создан новый продукт: {product.name}")
            return product
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка создания продукта: {e}")
            return None
    
    async def update_product(self, product_id: str, **kwargs) -> bool:
        """Обновить продукт."""
        try:
            # Конвертируем строку в UUID если нужно
            if isinstance(product_id, str):
                product_id = UUID(product_id)
                
            stmt = (
                update(Product)
                .where(Product.id == product_id)
                .values(**kwargs)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка обновления продукта {product_id}: {e}")
            return False
    
    async def delete_product(self, product_id: str) -> bool:
        """Удалить продукт (поддерживает короткие UUID)."""
        try:
            # Сначала находим продукт (поддерживает короткие UUID)
            product = await self.get_product_by_id(product_id)
            if not product:
                logger.warning(f"Продукт {product_id} не найден для удаления")
                return False
            
            # Удаляем связанные офферы
            for offer in product.offers:
                await self.session.delete(offer)
            
            # Удаляем продукт
            await self.session.delete(product)
            await self.session.commit()
            
            logger.info(f"Продукт {product.name} успешно удален")
            return True
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка удаления продукта {product_id}: {e}")
            return False
    
    async def toggle_product_status(self, product_id: str) -> bool:
        """Переключить статус активности продукта."""
        try:
            product = await self.get_product_by_id(product_id)
            if not product:
                return False
            
            new_status = not product.is_active
            await self.update_product(product_id, is_active=new_status)
            logger.info(f"Продукт {product.name} {'активирован' if new_status else 'деактивирован'}")
            return True
        except Exception as e:
            logger.error(f"Ошибка переключения статуса продукта {product_id}: {e}")
            return False
    
    async def get_all_offers(self, product_id: str = None, limit: int = 50) -> List[ProductOffer]:
        """Получить все офферы (опционально по продукту)."""
        try:
            stmt = select(ProductOffer).options(selectinload(ProductOffer.product))
            
            if product_id:
                # Конвертируем строку в UUID если нужно
                if isinstance(product_id, str):
                    product_id = UUID(product_id)
                stmt = stmt.where(ProductOffer.product_id == product_id)
            
            stmt = stmt.order_by(ProductOffer.created_at.desc()).limit(limit)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as e:
            logger.error(f"Ошибка получения офферов: {e}")
            return []
    
    async def get_offer_by_id(self, offer_id: str) -> Optional[ProductOffer]:
        """Получить оффер по ID."""
        try:
            # Конвертируем строку в UUID если нужно
            if isinstance(offer_id, str):
                offer_id = UUID(offer_id)
                
            stmt = (
                select(ProductOffer)
                .options(selectinload(ProductOffer.product))
                .where(ProductOffer.id == offer_id)
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
        except Exception as e:
            logger.error(f"Ошибка получения оффера {offer_id}: {e}")
            return None
    
    async def create_offer(self, offer_data: ProductOfferCreate) -> Optional[ProductOffer]:
        """Создать новый оффер."""
        try:
            offer = ProductOffer(**offer_data.model_dump() if hasattr(offer_data, 'model_dump') else offer_data)
            self.session.add(offer)
            await self.session.commit()
            await self.session.refresh(offer)
            logger.info(f"Создан новый оффер для продукта {offer.product_id}")
            return offer
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка создания оффера: {e}")
            return None
    
    async def update_offer(self, offer_id: str, **kwargs) -> bool:
        """Обновить оффер."""
        try:
            # Конвертируем строку в UUID если нужно
            if isinstance(offer_id, str):
                offer_id = UUID(offer_id)
                
            stmt = (
                update(ProductOffer)
                .where(ProductOffer.id == offer_id)
                .values(**kwargs)
            )
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка обновления оффера {offer_id}: {e}")
            return False
    
    async def delete_offer(self, offer_id: str) -> bool:
        """Удалить оффер."""
        try:
            # Конвертируем строку в UUID если нужно
            if isinstance(offer_id, str):
                offer_id = UUID(offer_id)
                
            stmt = delete(ProductOffer).where(ProductOffer.id == offer_id)
            result = await self.session.execute(stmt)
            await self.session.commit()
            return result.rowcount > 0
        except Exception as e:
            await self.session.rollback()
            logger.error(f"Ошибка удаления оффера {offer_id}: {e}")
            return False
    
    async def toggle_offer_status(self, offer_id: str) -> bool:
        """Переключить статус активности оффера."""
        try:
            offer = await self.get_offer_by_id(offer_id)
            if not offer:
                return False
            
            new_status = not offer.is_active
            await self.update_offer(offer_id, is_active=new_status)
            logger.info(f"Оффер {offer.id} {'активирован' if new_status else 'деактивирован'}")
            return True
        except Exception as e:
            logger.error(f"Ошибка переключения статуса оффера {offer_id}: {e}")
            return False
    
    async def get_tripwire_statistics(self) -> Dict[str, Any]:
        """Получить статистику трипвайеров."""
        try:
            # Общая статистика продуктов
            total_products = await self.session.execute(
                select(func.count(Product.id))
            )
            active_products = await self.session.execute(
                select(func.count(Product.id)).where(Product.is_active == True)
            )
            
            # Статистика офферов
            total_offers = await self.session.execute(
                select(func.count(ProductOffer.id))
            )
            active_offers = await self.session.execute(
                select(func.count(ProductOffer.id)).where(ProductOffer.is_active == True)
            )
            
            # Статистика пользовательских офферов
            total_user_offers = await self.session.execute(
                select(func.count(UserProductOffer.id))
            )
            shown_offers = await self.session.execute(
                select(func.count(UserProductOffer.id)).where(UserProductOffer.shown_at.isnot(None))
            )
            clicked_offers = await self.session.execute(
                select(func.count(UserProductOffer.id)).where(UserProductOffer.clicked_at.isnot(None))
            )
            
            # Конверсия
            total_shown = shown_offers.scalar() or 0
            total_clicked = clicked_offers.scalar() or 0
            conversion_rate = round((total_clicked / max(total_shown, 1)) * 100, 2)
            
            # Статистика по типам продуктов
            tripwire_products = await self.session.execute(
                select(func.count(Product.id)).where(Product.type == ProductType.TRIPWIRE)
            )
            
            return {
                "products": {
                    "total": total_products.scalar() or 0,
                    "active": active_products.scalar() or 0,
                    "tripwire": tripwire_products.scalar() or 0
                },
                "offers": {
                    "total": total_offers.scalar() or 0,
                    "active": active_offers.scalar() or 0
                },
                "user_offers": {
                    "total": total_user_offers.scalar() or 0,
                    "shown": total_shown,
                    "clicked": total_clicked,
                    "conversion_rate": conversion_rate
                }
            }
        except Exception as e:
            logger.error(f"Ошибка получения статистики трипвайеров: {e}")
            return {
                "products": {"total": 0, "active": 0, "tripwire": 0},
                "offers": {"total": 0, "active": 0},
                "user_offers": {"total": 0, "shown": 0, "clicked": 0, "conversion_rate": 0}
            }
    
    async def get_top_performing_offers(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Получить топ-офферы по конверсии."""
        try:
            # Запрос для получения статистики по офферам
            stmt = (
                select(
                    ProductOffer.id,
                    Product.name.label('product_name'),
                    func.count(UserProductOffer.id).label('total_shows'),
                    func.sum(
                        case((UserProductOffer.clicked_at.isnot(None), 1), else_=0)
                    ).label('total_clicks')
                )
                .join(Product, ProductOffer.product_id == Product.id)
                .outerjoin(UserProductOffer, ProductOffer.id == UserProductOffer.offer_id)
                .where(ProductOffer.is_active == True)
                .group_by(ProductOffer.id, Product.name)
                .having(func.count(UserProductOffer.id) > 0)
                .order_by(desc(func.sum(case((UserProductOffer.clicked_at.isnot(None), 1), else_=0))))
                .limit(limit)
            )
            
            result = await self.session.execute(stmt)
            offers_data = []
            
            for row in result.all():
                conversion = round((row.total_clicks / max(row.total_shows, 1)) * 100, 2)
                offers_data.append({
                    "offer_id": row.id,
                    "product_name": row.product_name,
                    "shows": row.total_shows,
                    "clicks": row.total_clicks,
                    "conversion": conversion
                })
            
            return offers_data
        except Exception as e:
            logger.error(f"Ошибка получения топ-офферов: {e}")
            return []
    
    async def get_sales_in_period(self, start_date: datetime, end_date: datetime) -> List[UserProductOffer]:
        """Получить продажи за период."""
        try:
            # Здесь нужно будет добавить модель продаж, пока возвращаем пустой список
            # В реальном проекте здесь был бы запрос к таблице продаж/платежей
            logger.warning("Метод get_sales_in_period не реализован - нет модели продаж")
            return []
        except Exception as e:
            logger.error(f"Ошибка получения продаж за период: {e}")
            return []
