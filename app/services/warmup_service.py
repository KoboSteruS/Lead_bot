"""
Сервис для работы с системой прогрева пользователей.

Управляет автоматической отправкой последовательности сообщений для прогрева.
"""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models import (
    WarmupScenario, 
    WarmupMessage, 
    UserWarmup, 
    UserWarmupMessage,
    User,
    WarmupMessageType
)
from app.schemas.warmup import (
    WarmupScenarioCreate,
    WarmupMessageCreate,
    UserWarmupResponse
)
from app.core.exceptions import WarmupException


class WarmupService:
    """Сервис для работы с системой прогрева."""
    
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса."""
        self.session = session
    
    async def get_active_scenario(self) -> Optional[WarmupScenario]:
        """Получить активный сценарий прогрева."""
        try:
            stmt = (
                select(WarmupScenario)
                .where(WarmupScenario.is_active == True)
                .options(selectinload(WarmupScenario.messages))
                .order_by(WarmupScenario.created_at.desc())
            )
            result = await self.session.execute(stmt)
            scenario = result.scalar_one_or_none()
            
            if scenario:
                logger.debug(f"Найден активный сценарий: {scenario.name}")
            else:
                logger.warning("Активный сценарий прогрева не найден")
            
            return scenario
            
        except Exception as e:
            logger.error(f"Ошибка получения активного сценария: {e}")
            raise WarmupException(f"Ошибка получения активного сценария: {e}")
    
    async def start_warmup_for_user(self, user_id: str) -> Optional[UserWarmup]:
        """Запустить прогрев для пользователя."""
        try:
            # Проверяем, нет ли уже активного прогрева
            existing_warmup = await self.get_user_active_warmup(user_id)
            if existing_warmup:
                logger.info(f"Пользователь {user_id} уже имеет активный прогрев")
                return existing_warmup
            
            # Получаем активный сценарий
            scenario = await self.get_active_scenario()
            if not scenario:
                logger.warning("Нет активного сценария для запуска прогрева")
                return None
            
            # Создаем запись прогрева для пользователя
            user_warmup = UserWarmup(
                user_id=user_id,
                scenario_id=scenario.id.hex,
                current_step=0,
                started_at=datetime.utcnow(),
                is_completed=False,
                is_stopped=False
            )
            
            self.session.add(user_warmup)
            await self.session.commit()
            await self.session.refresh(user_warmup)
            
            logger.info(f"Запущен прогрев для пользователя {user_id}, сценарий: {scenario.name}")
            return user_warmup
            
        except Exception as e:
            logger.error(f"Ошибка запуска прогрева для пользователя {user_id}: {e}")
            await self.session.rollback()
            raise WarmupException(f"Ошибка запуска прогрева: {e}")
    
    async def get_user_active_warmup(self, user_id: str) -> Optional[UserWarmup]:
        """Получить активный прогрев пользователя."""
        try:
            stmt = (
                select(UserWarmup)
                .where(
                    and_(
                        UserWarmup.user_id == user_id,
                        UserWarmup.is_completed == False,
                        UserWarmup.is_stopped == False
                    )
                )
                .options(selectinload(UserWarmup.scenario))
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none()
            
        except Exception as e:
            logger.error(f"Ошибка получения активного прогрева для пользователя {user_id}: {e}")
            return None
    
    async def get_users_ready_for_next_message(self) -> List[Dict[str, Any]]:
        """Получить пользователей, готовых к следующему сообщению прогрева."""
        try:
            current_time = datetime.utcnow()
            
            # Получаем пользователей с активными прогревами
            stmt = (
                select(UserWarmup, WarmupScenario, User)
                .join(WarmupScenario, UserWarmup.scenario_id == WarmupScenario.id)
                .join(User, UserWarmup.user_id == User.id)
                .where(
                    and_(
                        UserWarmup.is_completed == False,
                        UserWarmup.is_stopped == False,
                        WarmupScenario.is_active == True
                    )
                )
                .options(
                    selectinload(UserWarmup.scenario).selectinload(WarmupScenario.messages)
                )
            )
            result = await self.session.execute(stmt)
            warmups = result.all()
            
            ready_users = []
            
            for user_warmup, scenario, user in warmups:
                # Получаем все сообщения сценария, отсортированные по порядку
                messages = sorted(scenario.messages, key=lambda x: x.order)
                
                if user_warmup.current_step >= len(messages):
                    # Прогрев завершен
                    await self._complete_warmup(user_warmup)
                    continue
                
                # Получаем следующее сообщение
                next_message = messages[user_warmup.current_step]
                
                # Определяем время для отправки
                if user_warmup.current_step == 0:
                    # Первое сообщение - отправляем сразу
                    send_time = user_warmup.started_at
                else:
                    # Следующие сообщения - с задержкой
                    if user_warmup.last_message_at:
                        send_time = user_warmup.last_message_at + timedelta(hours=next_message.delay_hours)
                    else:
                        send_time = user_warmup.started_at + timedelta(hours=next_message.delay_hours)
                
                # Проверяем, пора ли отправлять
                if current_time >= send_time:
                    # Проверяем, не отправляли ли уже это сообщение
                    sent_message = await self._check_message_sent(user.id, next_message.id)
                    if not sent_message:
                        ready_users.append({
                            'user': user,
                            'user_warmup': user_warmup,
                            'message': next_message,
                            'scenario': scenario
                        })
            
            logger.info(f"Найдено {len(ready_users)} пользователей готовых для следующего сообщения прогрева")
            return ready_users
            
        except Exception as e:
            logger.error(f"Ошибка получения пользователей для прогрева: {e}")
            return []
    
    async def mark_message_sent(self, user_id: str, warmup_message_id: str, success: bool = True, error_message: str = None) -> None:
        """Отметить сообщение как отправленное."""
        try:
            # Создаем запись об отправке
            sent_message = UserWarmupMessage(
                user_id=user_id,
                warmup_message_id=warmup_message_id,
                sent_at=datetime.utcnow(),
                is_sent=success,
                error_message=error_message
            )
            
            self.session.add(sent_message)
            
            if success:
                # Обновляем прогресс прогрева
                await self._update_warmup_progress(user_id)
            
            await self.session.commit()
            
            logger.info(f"Отмечено сообщение прогрева для пользователя {user_id}: {'успешно' if success else 'ошибка'}")
            
        except Exception as e:
            logger.error(f"Ошибка отметки сообщения прогрева: {e}")
            await self.session.rollback()
    
    async def stop_warmup_for_user(self, user_id: str) -> bool:
        """Остановить прогрев для пользователя."""
        try:
            user_warmup = await self.get_user_active_warmup(user_id)
            if not user_warmup:
                return False
            
            user_warmup.is_stopped = True
            await self.session.commit()
            
            logger.info(f"Остановлен прогрев для пользователя {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка остановки прогрева для пользователя {user_id}: {e}")
            await self.session.rollback()
            return False
    
    async def create_default_scenario(self) -> WarmupScenario:
        """Создать сценарий прогрева по умолчанию."""
        try:
            # Создаем сценарий
            scenario = WarmupScenario(
                name="Основа Пути - Прогрев",
                description="Основной сценарий прогрева для проекта Основа Пути",
                is_active=True
            )
            
            self.session.add(scenario)
            await self.session.flush()  # Получаем ID
            
            # Создаем сообщения
            messages = [
                {
                    "type": WarmupMessageType.PAIN_POINT,
                    "title": "Почему нет изменений?",
                    "text": (
                        "🔥 <b>Почему у большинства людей нет изменений в жизни?</b>\n\n"
                        "90% людей живут на автомате:\n"
                        "• Встал — кофе — работа — дом — сериал — сон\n"
                        "• Одни и те же мысли\n"
                        "• Одни и те же действия\n"
                        "• Одни и те же результаты\n\n"
                        "Но есть другой путь. Путь СИСТЕМЫ."
                    ),
                    "order": 1,
                    "delay_hours": 0  # Первое сообщение сразу
                },
                {
                    "type": WarmupMessageType.SOLUTION,
                    "title": "Что такое система?",
                    "text": (
                        "⚡ <b>СИСТЕМА vs МОТИВАЦИЯ</b>\n\n"
                        "Мотивация — это эмоция. Она приходит и уходит.\n"
                        "Система — это структура. Она работает независимо от настроения.\n\n"
                        "🎯 СИСТЕМА включает:\n"
                        "• Ритуалы силы (утром и вечером)\n"
                        "• Цели и отчётность\n"
                        "• Развитие через дисциплину\n\n"
                        "Когда у тебя есть система — ты непобедим."
                    ),
                    "order": 2,
                    "delay_hours": 24  # Через день
                },
                {
                    "type": WarmupMessageType.SOCIAL_PROOF,
                    "title": "База знаний",
                    "text": (
                        "📚 <b>В основе всего — книга «Думай и богатей»</b>\n\n"
                        "Наполеон Хилл 20 лет изучал самых успешных людей планеты.\n"
                        "Результат: 13 принципов достижения любых целей.\n\n"
                        "💎 Эта книга изменила жизни миллионов людей:\n"
                        "• Дональд Трамп\n"
                        "• Роберт Кийосаки\n"
                        "• Тысячи предпринимателей\n\n"
                        "Вопрос: готов ли ты применить эти принципы на практике?"
                    ),
                    "order": 3,
                    "delay_hours": 48  # Через два дня
                },
                {
                    "type": WarmupMessageType.OFFER,
                    "title": "Твой шанс",
                    "text": (
                        "🚀 <b>30 дней по книге Наполеона Хилла</b>\n\n"
                        "Что ты получишь:\n"
                        "• 30 практических заданий на каждый день\n"
                        "• Пошаговое внедрение 13 принципов\n"
                        "• Систему отчётности и контроля\n"
                        "• Поддержку и мотивацию\n"
                        "• Доступ к закрытому чату участников\n\n"
                        "💰 <b>Цена: 9€</b>\n"
                        "Это меньше, чем чашка кофе в день.\n"
                        "Но результат может изменить твою жизнь навсегда.\n\n"
                        "Готов начать?"
                    ),
                    "order": 4,
                    "delay_hours": 72  # Через три дня
                },
                {
                    "type": WarmupMessageType.FOLLOW_UP,
                    "title": "Последний шанс",
                    "text": (
                        "☕ <b>9€ — меньше, чем чашка кофе в день</b>\n\n"
                        "Подумай об этом:\n"
                        "• Чашка кофе даёт бодрость на 2 часа\n"
                        "• Эта программа даст тебе систему на всю жизнь\n\n"
                        "🎯 <b>За 30 дней ты:</b>\n"
                        "• Создашь чёткий план достижения целей\n"
                        "• Разовьёшь дисциплину и силу воли\n"
                        "• Изменишь мышление на успех\n\n"
                        "Результат может изменить твою жизнь.\n\n"
                        "Это твой последний шанс войти в программу по этой цене."
                    ),
                    "order": 5,
                    "delay_hours": 120  # Через 5 дней
                }
            ]
            
            # Добавляем сообщения
            for msg_data in messages:
                message = WarmupMessage(
                    scenario_id=scenario.id.hex,
                    message_type=msg_data["type"],
                    title=msg_data["title"],
                    text=msg_data["text"],
                    order=msg_data["order"],
                    delay_hours=msg_data["delay_hours"],
                    is_active=True
                )
                self.session.add(message)
            
            await self.session.commit()
            await self.session.refresh(scenario)
            
            logger.info(f"Создан сценарий прогрева по умолчанию: {scenario.name}")
            return scenario
            
        except Exception as e:
            logger.error(f"Ошибка создания сценария по умолчанию: {e}")
            await self.session.rollback()
            raise WarmupException(f"Ошибка создания сценария: {e}")
    
    # Методы для админ панели
    
    async def get_all_scenarios(self) -> List[WarmupScenario]:
        """Получить все сценарии прогрева."""
        try:
            stmt = (
                select(WarmupScenario)
                .options(selectinload(WarmupScenario.messages))
                .order_by(WarmupScenario.created_at.desc())
            )
            result = await self.session.execute(stmt)
            scenarios = result.scalars().all()
            logger.info(f"Получено {len(scenarios)} сценариев прогрева")
            return scenarios
        except Exception as e:
            logger.error(f"Ошибка получения всех сценариев: {e}")
            return []
    
    async def get_active_warmup_users(self) -> List[UserWarmup]:
        """Получить всех пользователей с активными прогревами."""
        try:
            stmt = (
                select(UserWarmup)
                .where(
                    and_(
                        UserWarmup.is_completed == False,
                        UserWarmup.is_stopped == False
                    )
                )
                .options(selectinload(UserWarmup.user), selectinload(UserWarmup.scenario))
            )
            result = await self.session.execute(stmt)
            warmups = result.scalars().all()
            
            # Фильтруем только те прогревы, где есть и пользователь, и сценарий
            valid_warmups = []
            for warmup in warmups:
                if warmup.user and warmup.scenario:
                    valid_warmups.append(warmup)
                else:
                    logger.warning(f"Найден неполный прогрев: user_id={warmup.user_id}, scenario_id={warmup.scenario_id}")
                    # Можно также пометить такие прогревы как завершенные
                    if not warmup.user or not warmup.scenario:
                        warmup.is_completed = True
                        warmup.is_stopped = True
            
            if valid_warmups != warmups:
                await self.session.commit()
                logger.info(f"Очищено {len(warmups) - len(valid_warmups)} неполных прогрева")
            
            logger.info(f"Получено {len(valid_warmups)} валидных активных прогрева")
            return valid_warmups
        except Exception as e:
            logger.error(f"Ошибка получения активных прогрева: {e}")
            return []
    
    async def create_scenario(self, name: str, description: str = None) -> WarmupScenario:
        """Создать новый сценарий прогрева."""
        try:
            # Деактивируем все существующие сценарии
            await self.deactivate_all_scenarios()
            
            # Создаем новый сценарий
            scenario = WarmupScenario(
                name=name,
                description=description,
                is_active=True
            )
            
            self.session.add(scenario)
            await self.session.commit()
            await self.session.refresh(scenario)
            
            logger.info(f"Создан новый сценарий прогрева: {scenario.name}")
            return scenario
        except Exception as e:
            logger.error(f"Ошибка создания сценария: {e}")
            await self.session.rollback()
            raise WarmupException(f"Ошибка создания сценария: {e}")
    
    async def deactivate_all_scenarios(self) -> None:
        """Деактивировать все сценарии прогрева."""
        try:
            stmt = (
                update(WarmupScenario)
                .where(WarmupScenario.is_active == True)
                .values(is_active=False)
            )
            await self.session.execute(stmt)
            await self.session.commit()
            logger.info("Все сценарии прогрева деактивированы")
        except Exception as e:
            logger.error(f"Ошибка деактивации сценариев: {e}")
            await self.session.rollback()
    
    async def get_scenario_by_id(self, scenario_id: str) -> Optional[WarmupScenario]:
        """Получить сценарий по ID (поддерживает короткие UUID - первые 8 символов)."""
        try:
            # Если передан короткий UUID (8 символов), ищем по LIKE
            if len(scenario_id) == 8:
                from sqlalchemy import String, cast
                stmt = (
                    select(WarmupScenario)
                    .where(cast(WarmupScenario.id, String).like(f"{scenario_id}%"))
                    .options(selectinload(WarmupScenario.messages))
                )
            else:
                # Полный UUID
                from uuid import UUID
                scenario_uuid = UUID(scenario_id) if isinstance(scenario_id, str) else scenario_id
                stmt = (
                    select(WarmupScenario)
                    .where(WarmupScenario.id == scenario_uuid)
                    .options(selectinload(WarmupScenario.messages))
                )
            
            result = await self.session.execute(stmt)
            scenario = result.scalar_one_or_none()
            return scenario
        except Exception as e:
            logger.error(f"Ошибка получения сценария {scenario_id}: {e}")
            return None
    
    async def delete_scenario(self, scenario_id: str) -> bool:
        """Удалить сценарий прогрева."""
        try:
            scenario = await self.get_scenario_by_id(scenario_id)
            if not scenario:
                return False
            
            # Удаляем все сообщения сценария
            for message in scenario.messages:
                await self.session.delete(message)
            
            # Удаляем сам сценарий
            await self.session.delete(scenario)
            await self.session.commit()
            
            logger.info(f"Удален сценарий прогрева: {scenario.name}")
            return True
        except Exception as e:
            logger.error(f"Ошибка удаления сценария {scenario_id}: {e}")
            await self.session.rollback()
            return False
    
    async def add_message_to_scenario(self, scenario_id: str, message_type: str, title: str, 
                                    text: str, order: int, delay_hours: int = 24) -> Optional[WarmupMessage]:
        """Добавить сообщение в сценарий."""
        try:
            scenario = await self.get_scenario_by_id(scenario_id)
            if not scenario:
                return None
            
            message = WarmupMessage(
                scenario_id=scenario_id,
                message_type=WarmupMessageType(message_type),
                title=title,
                text=text,
                order=order,
                delay_hours=delay_hours,
                is_active=True
            )
            
            self.session.add(message)
            await self.session.commit()
            await self.session.refresh(message)
            
            logger.info(f"Добавлено сообщение в сценарий {scenario.name}: {title}")
            return message
        except Exception as e:
            logger.error(f"Ошибка добавления сообщения: {e}")
            await self.session.rollback()
            return None
    
    async def get_warmup_stats(self) -> Dict[str, Any]:
        """Получить статистику прогрева."""
        try:
            # Общая статистика
            total_scenarios = await self.get_all_scenarios()
            active_users = await self.get_active_warmup_users()
            
            # Статистика по типам сообщений
            message_stats = {}
            for scenario in total_scenarios:
                for message in scenario.messages:
                    msg_type = message.message_type.value if hasattr(message.message_type, 'value') else message.message_type
                    if msg_type not in message_stats:
                        message_stats[msg_type] = 0
                    message_stats[msg_type] += 1
            
            stats = {
                'total_scenarios': len(total_scenarios),
                'active_scenarios': len([s for s in total_scenarios if s.is_active]),
                'total_messages': sum(len(s.messages) for s in total_scenarios),
                'active_users': len(active_users),
                'message_types': message_stats
            }
            
            return stats
        except Exception as e:
            logger.error(f"Ошибка получения статистики прогрева: {e}")
            return {}
    
    # Приватные методы
    
    async def _check_message_sent(self, user_id: str, warmup_message_id: str) -> bool:
        """Проверить, отправлялось ли сообщение."""
        try:
            stmt = select(UserWarmupMessage).where(
                and_(
                    UserWarmupMessage.user_id == user_id,
                    UserWarmupMessage.warmup_message_id == warmup_message_id
                )
            )
            result = await self.session.execute(stmt)
            return result.scalar_one_or_none() is not None
            
        except Exception as e:
            logger.error(f"Ошибка проверки отправки сообщения: {e}")
            return False
    
    async def _update_warmup_progress(self, user_id: str) -> None:
        """Обновить прогресс прогрева пользователя."""
        try:
            user_warmup = await self.get_user_active_warmup(user_id)
            if user_warmup:
                user_warmup.current_step += 1
                user_warmup.last_message_at = datetime.utcnow()
                
        except Exception as e:
            logger.error(f"Ошибка обновления прогресса прогрева: {e}")
    
    async def _complete_warmup(self, user_warmup: UserWarmup) -> None:
        """Завершить прогрев пользователя."""
        try:
            user_warmup.is_completed = True
            await self.session.commit()
            logger.info(f"Завершен прогрев для пользователя {user_warmup.user_id}")
            
        except Exception as e:
            logger.error(f"Ошибка завершения прогрева: {e}")
