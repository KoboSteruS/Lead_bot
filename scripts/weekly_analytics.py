#!/usr/bin/env python3
"""
Скрипт для генерации и отправки еженедельной аналитики.

Собирает статистику за прошлую неделю и отправляет в Telegram.
"""

import asyncio
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any

# Добавляем корневую папку проекта в путь
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from loguru import logger
from telegram import Bot
from app.core.database import get_db_session
from app.services.user_service import UserService
from app.services.lead_magnet_service import LeadMagnetService
from app.services.warmup_service import WarmupService
from app.services.mailing_service import MailingService
from app.services.product_service import ProductService
from config.settings import settings


class WeeklyAnalytics:
    """Класс для генерации еженедельной аналитики."""
    
    def __init__(self, bot_token: str):
        """Инициализация."""
        self.bot = Bot(token=bot_token)
        self.week_start = None
        self.week_end = None
    
    def _get_week_period(self) -> tuple:
        """Получить период прошлой недели."""
        today = datetime.utcnow().date()
        
        # Находим начало прошлой недели (понедельник)
        days_since_monday = today.weekday()
        last_monday = today - timedelta(days=days_since_monday + 7)
        
        # Конец прошлой недели (воскресенье)
        last_sunday = last_monday + timedelta(days=6)
        
        self.week_start = datetime.combine(last_monday, datetime.min.time())
        self.week_end = datetime.combine(last_sunday, datetime.max.time())
        
        return self.week_start, self.week_end
    
    async def get_user_analytics(self) -> Dict[str, Any]:
        """Получить аналитику пользователей за неделю."""
        try:
            async with get_db_session() as session:
                user_service = UserService(session)
                
                # Новые пользователи за неделю
                new_users = await user_service.get_users_by_date_range(
                    self.week_start, self.week_end
                )
                
                # Общая статистика
                total_users = len(await user_service.get_all_users())
                active_users = await user_service.get_active_users_count()
                
                # Статистика по дням недели
                daily_stats = {}
                for i in range(7):
                    day_start = self.week_start + timedelta(days=i)
                    day_end = day_start + timedelta(days=1)
                    
                    day_users = await user_service.get_users_by_date_range(
                        day_start, day_end
                    )
                    day_name = day_start.strftime("%A")
                    daily_stats[day_name] = len(day_users)
                
                return {
                    "new_users_week": len(new_users),
                    "total_users": total_users,
                    "active_users": active_users,
                    "daily_registrations": daily_stats,
                    "growth_rate": round((len(new_users) / max(total_users - len(new_users), 1)) * 100, 2)
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения аналитики пользователей: {e}")
            return {}
    
    async def get_lead_magnet_analytics(self) -> Dict[str, Any]:
        """Получить аналитику лид-магнитов за неделю."""
        try:
            async with get_db_session() as session:
                lead_magnet_service = LeadMagnetService(session)
                
                # Общая статистика
                total_issued = await lead_magnet_service.get_lead_magnets_issued_in_period(
                    self.week_start, self.week_end
                )
                
                # Статистика по типам
                type_stats = {}
                active_magnets = await lead_magnet_service.get_active_lead_magnets()
                
                for magnet in active_magnets:
                    issued_count = await lead_magnet_service.get_lead_magnets_issued_in_period(
                        self.week_start, self.week_end, magnet_type=magnet.type
                    )
                    type_stats[magnet.type] = issued_count
                
                # Конверсия (новые пользователи / выданные лид-магниты)
                user_analytics = await self.get_user_analytics()
                conversion_rate = 0
                if total_issued > 0:
                    conversion_rate = round((user_analytics.get("new_users_week", 0) / total_issued) * 100, 2)
                
                return {
                    "total_issued_week": total_issued,
                    "type_stats": type_stats,
                    "conversion_rate": conversion_rate,
                    "active_magnets": len(active_magnets)
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения аналитики лид-магнитов: {e}")
            return {}
    
    async def get_warmup_analytics(self) -> Dict[str, Any]:
        """Получить аналитику прогрева за неделю."""
        try:
            async with get_db_session() as session:
                warmup_service = WarmupService(session)
                
                # Активные прогревы
                active_warmups = await warmup_service.get_active_warmup_users()
                
                # Завершенные прогревы за неделю
                completed_warmups = await warmup_service.get_completed_warmups_in_period(
                    self.week_start, self.week_end
                )
                
                # Отправленные сообщения прогрева за неделю
                sent_messages = await warmup_service.get_sent_messages_in_period(
                    self.week_start, self.week_end
                )
                
                # Статистика по типам сообщений
                message_type_stats = {}
                for message_type in ["pain_point", "solution", "social_proof", "offer", "follow_up"]:
                    count = await warmup_service.get_sent_messages_in_period(
                        self.week_start, self.week_end, message_type=message_type
                    )
                    message_type_stats[message_type] = count
                
                return {
                    "active_warmups": len(active_warmups),
                    "completed_week": len(completed_warmups),
                    "messages_sent_week": sent_messages,
                    "message_type_stats": message_type_stats,
                    "completion_rate": round((len(completed_warmups) / max(len(active_warmups), 1)) * 100, 2)
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения аналитики прогрева: {e}")
            return {}
    
    async def get_mailing_analytics(self) -> Dict[str, Any]:
        """Получить аналитику рассылок за неделю."""
        try:
            async with get_db_session() as session:
                mailing_service = MailingService(session)
                
                # Рассылки за неделю
                week_mailings = await mailing_service.get_mailings_in_period(
                    self.week_start, self.week_end
                )
                
                # Статистика отправки
                total_sent = 0
                total_delivered = 0
                total_failed = 0
                
                for mailing in week_mailings:
                    total_sent += mailing.sent_count
                    total_delivered += mailing.delivered_count
                    total_failed += mailing.failed_count
                
                # Средняя доставляемость
                delivery_rate = 0
                if total_sent > 0:
                    delivery_rate = round((total_delivered / total_sent) * 100, 2)
                
                return {
                    "mailings_created_week": len(week_mailings),
                    "total_sent_week": total_sent,
                    "total_delivered_week": total_delivered,
                    "total_failed_week": total_failed,
                    "delivery_rate": delivery_rate
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения аналитики рассылок: {e}")
            return {}
    
    async def get_product_analytics(self) -> Dict[str, Any]:
        """Получить аналитику продуктов за неделю."""
        try:
            async with get_db_session() as session:
                product_service = ProductService(session)
                
                # Продажи за неделю
                week_sales = await product_service.get_sales_in_period(
                    self.week_start, self.week_end
                )
                
                # Доход за неделю
                week_revenue = sum(sale.amount for sale in week_sales)
                
                # Конверсия в продажи
                user_analytics = await self.get_user_analytics()
                sales_conversion = 0
                if user_analytics.get("new_users_week", 0) > 0:
                    sales_conversion = round((len(week_sales) / user_analytics["new_users_week"]) * 100, 2)
                
                return {
                    "sales_week": len(week_sales),
                    "revenue_week": week_revenue,
                    "avg_order_value": round(week_revenue / max(len(week_sales), 1), 2),
                    "sales_conversion": sales_conversion
                }
                
        except Exception as e:
            logger.error(f"Ошибка получения аналитики продуктов: {e}")
            return {}
    
    def format_analytics_report(self, analytics: Dict[str, Any]) -> str:
        """Форматировать отчет аналитики."""
        week_period = f"{self.week_start.strftime('%d.%m')} - {self.week_end.strftime('%d.%m.%Y')}"
        
        report = f"""
📊 <b>ЕЖЕНЕДЕЛЬНАЯ АНАЛИТИКА</b>
📅 <b>Период:</b> {week_period}

👥 <b>ПОЛЬЗОВАТЕЛИ</b>
• Новых за неделю: {analytics.get('users', {}).get('new_users_week', 0)}
• Всего пользователей: {analytics.get('users', {}).get('total_users', 0)}
• Активных: {analytics.get('users', {}).get('active_users', 0)}
• Рост: {analytics.get('users', {}).get('growth_rate', 0)}%

📈 <b>Регистрации по дням:</b>
"""
        
        # Добавляем статистику по дням
        daily_stats = analytics.get('users', {}).get('daily_registrations', {})
        for day, count in daily_stats.items():
            report += f"• {day}: {count}\n"
        
        report += f"""
🎁 <b>ЛИД-МАГНИТЫ</b>
• Выдано за неделю: {analytics.get('lead_magnets', {}).get('total_issued_week', 0)}
• Конверсия: {analytics.get('lead_magnets', {}).get('conversion_rate', 0)}%
• Активных магнитов: {analytics.get('lead_magnets', {}).get('active_magnets', 0)}

🔥 <b>ПРОГРЕВ</b>
• Активных прогрева: {analytics.get('warmup', {}).get('active_warmups', 0)}
• Завершено за неделю: {analytics.get('warmup', {}).get('completed_week', 0)}
• Сообщений отправлено: {analytics.get('warmup', {}).get('messages_sent_week', 0)}
• Процент завершения: {analytics.get('warmup', {}).get('completion_rate', 0)}%

📢 <b>РАССЫЛКИ</b>
• Создано рассылок: {analytics.get('mailings', {}).get('mailings_created_week', 0)}
• Отправлено сообщений: {analytics.get('mailings', {}).get('total_sent_week', 0)}
• Доставлено: {analytics.get('mailings', {}).get('total_delivered_week', 0)}
• Доставляемость: {analytics.get('mailings', {}).get('delivery_rate', 0)}%

💰 <b>ПРОДАЖИ</b>
• Продаж за неделю: {analytics.get('products', {}).get('sales_week', 0)}
• Доход: {analytics.get('products', {}).get('revenue_week', 0)} ₽
• Средний чек: {analytics.get('products', {}).get('avg_order_value', 0)} ₽
• Конверсия в продажи: {analytics.get('products', {}).get('sales_conversion', 0)}%

🎯 <b>КЛЮЧЕВЫЕ МЕТРИКИ</b>
• Общая конверсия лид→покупатель: {analytics.get('overall_conversion', 0)}%
• ARPU (доход на пользователя): {analytics.get('arpu', 0)} ₽
• LTV (жизненная ценность): {analytics.get('ltv', 0)} ₽
"""
        
        return report
    
    async def send_analytics_to_admins(self, report: str) -> bool:
        """Отправить аналитику администраторам."""
        try:
            # Получаем список админов
            admin_ids = settings.ADMIN_IDS.split(',') if hasattr(settings, 'ADMIN_IDS') else []
            
            if not admin_ids:
                logger.warning("Список админов не найден в настройках")
                return False
            
            sent_count = 0
            for admin_id in admin_ids:
                try:
                    admin_id = int(admin_id.strip())
                    await self.bot.send_message(
                        chat_id=admin_id,
                        text=report,
                        parse_mode="HTML"
                    )
                    sent_count += 1
                    logger.info(f"Аналитика отправлена админу {admin_id}")
                except Exception as e:
                    logger.error(f"Ошибка отправки аналитики админу {admin_id}: {e}")
            
            logger.info(f"Аналитика отправлена {sent_count} из {len(admin_ids)} админов")
            return sent_count > 0
            
        except Exception as e:
            logger.error(f"Ошибка отправки аналитики: {e}")
            return False
    
    async def generate_and_send_analytics(self) -> bool:
        """Сгенерировать и отправить еженедельную аналитику."""
        try:
            logger.info("🚀 Генерация еженедельной аналитики...")
            
            # Получаем период
            self._get_week_period()
            logger.info(f"📅 Период: {self.week_start.strftime('%d.%m.%Y')} - {self.week_end.strftime('%d.%m.%Y')}")
            
            # Собираем аналитику
            analytics = {
                "users": await self.get_user_analytics(),
                "lead_magnets": await self.get_lead_magnet_analytics(),
                "warmup": await self.get_warmup_analytics(),
                "mailings": await self.get_mailing_analytics(),
                "products": await self.get_product_analytics()
            }
            
            # Вычисляем общие метрики
            user_data = analytics.get("users", {})
            product_data = analytics.get("products", {})
            
            analytics["overall_conversion"] = 0
            if user_data.get("new_users_week", 0) > 0:
                analytics["overall_conversion"] = round(
                    (product_data.get("sales_week", 0) / user_data["new_users_week"]) * 100, 2
                )
            
            analytics["arpu"] = 0
            if user_data.get("total_users", 0) > 0:
                analytics["arpu"] = round(product_data.get("revenue_week", 0) / user_data["total_users"], 2)
            
            analytics["ltv"] = analytics["arpu"] * 3  # Примерная оценка LTV
            
            # Форматируем отчет
            report = self.format_analytics_report(analytics)
            
            # Отправляем админам
            success = await self.send_analytics_to_admins(report)
            
            if success:
                logger.info("✅ Еженедельная аналитика успешно отправлена")
            else:
                logger.error("❌ Не удалось отправить аналитику")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ Ошибка генерации аналитики: {e}")
            return False


async def main():
    """Основная функция."""
    try:
        logger.info("📊 Запуск генерации еженедельной аналитики...")
        
        # Проверяем токен бота
        if not settings.BOT_TOKEN:
            logger.error("❌ BOT_TOKEN не найден в настройках")
            return False
        
        # Создаем экземпляр аналитики
        analytics = WeeklyAnalytics(settings.BOT_TOKEN)
        
        # Генерируем и отправляем аналитику
        success = await analytics.generate_and_send_analytics()
        
        if success:
            logger.info("🎉 Еженедельная аналитика успешно сгенерирована и отправлена!")
        else:
            logger.error("❌ Ошибка генерации или отправки аналитики")
        
        return success
        
    except Exception as e:
        logger.error(f"❌ Критическая ошибка: {e}")
        return False


if __name__ == "__main__":
    # Настраиваем логирование
    logger.remove()
    logger.add(
        sys.stdout,
        level="INFO",
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        colorize=True
    )
    
    # Запускаем
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
