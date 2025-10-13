"""
Простая админ-панель для LeadBot.

Содержит базовые функции администрирования.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CommandHandler, CallbackQueryHandler
from loguru import logger
import asyncio

from app.core.database import get_db_session
from app.services import UserService, LeadMagnetService, WarmupService, ProductService
from app.models.lead_magnet import LeadMagnetType
from config.settings import settings


async def admin_command_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Обработчик команды /admin.
    
    Args:
        update: Обновление от Telegram
        context: Контекст бота
    """
    user = update.effective_user
    
    if not user:
        return
    
    # Проверяем, является ли пользователь админом
    if str(user.id) not in str(settings.ADMIN_IDS):
        await update.message.reply_text(
            "❌ У вас нет прав администратора.",
            parse_mode="HTML"
        )
        return
    
    # Создаем админскую клавиатуру
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🎁 Лид-магниты", callback_data="admin_lead_magnets")],
        [InlineKeyboardButton("💰 Трипвайеры", callback_data="admin_products")],
        [InlineKeyboardButton("🔥 Прогрев", callback_data="admin_warmup")],
        [InlineKeyboardButton("📢 Рассылки", callback_data="admin_mailings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "👨‍💼 <b>Админ-панель LeadBot</b>\n\n"
        "Выберите раздел:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )
    
    logger.info(f"Админ-панель открыта пользователем {user.id}")


async def admin_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик статистики."""
    query = update.callback_query
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            lead_magnet_service = LeadMagnetService(session)
            warmup_service = WarmupService(session)
            product_service = ProductService(session)
            
            # Получаем статистику
            total_users = len(await user_service.get_all_users())
            active_lead_magnets = len(await lead_magnet_service.get_active_lead_magnets())
            active_warmups = len(await warmup_service.get_active_warmup_users())
            warmup_stats = await warmup_service.get_warmup_stats()
            
            stats_text = (
                "📊 <b>Статистика LeadBot</b>\n\n"
                f"👥 <b>Пользователи:</b> {total_users}\n"
                f"🎁 <b>Активные лид-магниты:</b> {active_lead_magnets}\n"
                f"🔥 <b>Активные прогревы:</b> {active_warmups}\n"
                f"📈 <b>Всего сценариев прогрева:</b> {warmup_stats.get('total_scenarios', 0)}\n"
                f"📝 <b>Всего сообщений прогрева:</b> {warmup_stats.get('total_messages', 0)}\n"
            )
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="admin_stats")],
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                stats_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        await query.edit_message_text(
            "❌ Ошибка получения статистики",
            parse_mode="HTML"
        )


async def admin_users_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик списка пользователей."""
    query = update.callback_query
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            
            users = await user_service.get_all_users()
            
            users_text = f"👥 <b>Пользователи ({len(users)}):</b>\n\n"
            
            for user in users[:10]:  # Показываем первых 10
                status = user.status.value if hasattr(user.status, 'value') else user.status
                users_text += (
                    f"• {user.full_name} (@{user.username or 'нет'})\n"
                    f"  ID: {user.telegram_id}\n"
                    f"  Статус: {status}\n\n"
                )
            
            if len(users) > 10:
                users_text += f"... и еще {len(users) - 10} пользователей"
            
            keyboard = [
                [InlineKeyboardButton("🔄 Обновить", callback_data="admin_users")],
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_back")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                users_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения пользователей: {e}")
        await query.edit_message_text(
            "❌ Ошибка получения списка пользователей",
            parse_mode="HTML"
        )


async def admin_lead_magnets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик лид-магнитов."""
    query = update.callback_query
    await query.answer()
    
    try:
        async with get_db_session() as session:
            lead_magnet_service = LeadMagnetService(session)
            
            magnets = await lead_magnet_service.get_all_lead_magnets()
            
            magnets_text = f"🎁 <b>Лид-магниты ({len(magnets)}):</b>\n\n"
            
            keyboard = []
            
            for magnet in magnets:
                status = "✅" if magnet.is_active else "❌"
                magnet_type = magnet.type.value if hasattr(magnet.type, 'value') else magnet.type
                magnets_text += (
                    f"{status} <b>{magnet.name}</b>\n"
                    f"   Тип: {magnet_type}\n\n"
                )
                
                # Добавляем кнопки управления для каждого лид-магнита
                keyboard.append([
                    InlineKeyboardButton(
                        f"✏️ {magnet.name[:20]}...", 
                        callback_data=f"edit_magnet_{str(magnet.id)[:8]}"
                    ),
                    InlineKeyboardButton(
                        "🗑️", 
                        callback_data=f"delete_magnet_{str(magnet.id)[:8]}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("➕ Добавить лид-магнит", callback_data="add_lead_magnet")])
            keyboard.append([InlineKeyboardButton("🔄 Сбросить все выдачи", callback_data="reset_all_lead_magnets")])
            keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="admin_lead_magnets")])
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                magnets_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения лид-магнитов: {e}")
        await query.edit_message_text(
            "❌ Ошибка получения лид-магнитов",
            parse_mode="HTML"
        )


async def admin_products_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик продуктов."""
    query = update.callback_query
    await query.answer()
    
    try:
        async with get_db_session() as session:
            product_service = ProductService(session)
            
            products = await product_service.get_all_products()
            
            products_text = f"💰 <b>Продукты ({len(products)}):</b>\n\n"
            
            keyboard = []
            
            for product in products:
                status = "✅" if product.is_active else "❌"
                product_type = product.type.value if hasattr(product.type, 'value') else product.type
                products_text += (
                    f"{status} <b>{product.name}</b>\n"
                    f"   Тип: {product_type}\n"
                    f"   Цена: {product.price/100} {product.currency}\n\n"
                )
                
                # Добавляем кнопки управления для каждого продукта
                keyboard.append([
                    InlineKeyboardButton(
                        f"✏️ {product.name[:20]}...", 
                        callback_data=f"edit_product_{str(product.id)[:8]}"
                    ),
                    InlineKeyboardButton(
                        "🗑️", 
                        callback_data=f"delete_product_{str(product.id)[:8]}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("➕ Добавить продукт", callback_data="add_product")])
            keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="admin_products")])
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                products_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения продуктов: {e}")
        await query.edit_message_text(
            "❌ Ошибка получения продуктов",
            parse_mode="HTML"
        )


async def admin_warmup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик прогрева."""
    query = update.callback_query
    await query.answer()
    
    try:
        async with get_db_session() as session:
            warmup_service = WarmupService(session)
            
            scenarios = await warmup_service.get_all_scenarios()
            active_users = await warmup_service.get_active_warmup_users()
            
            warmup_text = f"🔥 <b>Система прогрева</b>\n\n"
            warmup_text += f"📋 <b>Сценариев:</b> {len(scenarios)}\n"
            warmup_text += f"👥 <b>Активных прогревов:</b> {len(active_users)}\n\n"
            
            keyboard = []
            
            for scenario in scenarios[:3]:  # Показываем первые 3
                status = "✅" if scenario.is_active else "❌"
                warmup_text += (
                    f"{status} <b>{scenario.name}</b>\n"
                    f"   Сообщений: {len(scenario.messages)}\n\n"
                )
                
                # Кнопка для просмотра сообщений сценария
                keyboard.append([
                    InlineKeyboardButton(
                        f"📝 {scenario.name[:25]}...", 
                        callback_data=f"view_scenario_{str(scenario.id)[:8]}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("➕ Создать сценарий", callback_data="add_scenario")])
            keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="admin_warmup")])
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                warmup_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения информации о прогреве: {e}")
        await query.edit_message_text(
            "❌ Ошибка получения информации о прогреве",
            parse_mode="HTML"
        )


async def admin_back_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки Назад."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Пользователи", callback_data="admin_users")],
        [InlineKeyboardButton("🎁 Лид-магниты", callback_data="admin_lead_magnets")],
        [InlineKeyboardButton("💰 Трипвайеры", callback_data="admin_products")],
        [InlineKeyboardButton("🔥 Прогрев", callback_data="admin_warmup")],
        [InlineKeyboardButton("📢 Рассылки", callback_data="admin_mailings")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "👨‍💼 <b>Админ-панель LeadBot</b>\n\n"
        "Выберите раздел:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def view_scenario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик просмотра сценария прогрева."""
    query = update.callback_query
    await query.answer()
    
    scenario_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            warmup_service = WarmupService(session)
            scenario = await warmup_service.get_scenario_by_id(scenario_id)
            
            if not scenario:
                await query.edit_message_text("❌ Сценарий не найден")
                return
            
            status = "✅ Активен" if scenario.is_active else "❌ Неактивен"
            
            scenario_text = f"🔥 <b>Сценарий: {scenario.name}</b>\n\n"
            scenario_text += f"<b>Статус:</b> {status}\n"
            scenario_text += f"<b>Описание:</b> {scenario.description or 'Нет описания'}\n"
            scenario_text += f"<b>Сообщений:</b> {len(scenario.messages)}\n\n"
            
            scenario_text += "<b>📋 Сообщения:</b>\n\n"
            
            for i, msg in enumerate(scenario.messages[:5], 1):
                msg_type = msg.message_type.value if hasattr(msg.message_type, 'value') else msg.message_type
                scenario_text += f"{i}. {msg.title} ({msg_type})\n"
                scenario_text += f"   ⏱ Задержка: {msg.delay_hours}ч\n\n"
            
            if len(scenario.messages) > 5:
                scenario_text += f"... и еще {len(scenario.messages) - 5} сообщений\n\n"
            
            keyboard = [
                [
                    InlineKeyboardButton("✏️ Редактировать", callback_data=f"edit_scenario_{scenario_id}"),
                    InlineKeyboardButton("🗑️ Удалить", callback_data=f"delete_scenario_{scenario_id}")
                ],
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_warmup")]
            ]
            
            await query.edit_message_text(
                scenario_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
    except Exception as e:
        logger.error(f"Ошибка просмотра сценария: {e}")
        await query.edit_message_text("❌ Ошибка просмотра сценария")


async def add_scenario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик создания нового сценария."""
    query = update.callback_query
    await query.answer()
    
    context.user_data['creating_scenario'] = True
    
    await query.edit_message_text(
        "➕ <b>Создание нового сценария прогрева</b>\n\n"
        "Отправьте название сценария:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data="admin_warmup")
        ]])
    )


async def edit_scenario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик редактирования сценария."""
    query = update.callback_query
    await query.answer()
    
    scenario_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            warmup_service = WarmupService(session)
            scenario = await warmup_service.get_scenario_by_id(scenario_id)
            
            if not scenario:
                await query.edit_message_text("❌ Сценарий не найден")
                return
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить название", callback_data=f"edit_scenario_name_{scenario_id}")],
                [InlineKeyboardButton("📄 Изменить описание", callback_data=f"edit_scenario_desc_{scenario_id}")],
                [InlineKeyboardButton("➕ Добавить сообщение", callback_data=f"add_scenario_msg_{scenario_id}")],
                [InlineKeyboardButton("📋 Список сообщений", callback_data=f"list_scenario_msgs_{scenario_id}")],
                [InlineKeyboardButton("◀️ Назад", callback_data=f"view_scenario_{scenario_id}")]
            ]
            
            await query.edit_message_text(
                f"✏️ <b>Редактирование сценария</b>\n\n"
                f"<b>Название:</b> {scenario.name}\n"
                f"<b>Описание:</b> {scenario.description or 'Не указано'}\n"
                f"<b>Сообщений:</b> {len(scenario.messages)}\n\n"
                f"Выберите, что хотите изменить:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Ошибка редактирования сценария: {e}")
        await query.edit_message_text("❌ Ошибка загрузки сценария")


async def edit_scenario_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения названия сценария."""
    query = update.callback_query
    await query.answer()
    
    scenario_id = query.data.split("_")[-1]
    
    # Сохраняем контекст для обработки текста
    context.user_data['action'] = 'edit_scenario_name'
    context.user_data['scenario_id'] = scenario_id
    
    await query.edit_message_text(
        "📝 <b>Изменение названия сценария</b>\n\n"
        "Введите новое название сценария:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_scenario_{scenario_id}")
        ]])
    )


async def edit_scenario_desc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения описания сценария."""
    query = update.callback_query
    await query.answer()
    
    scenario_id = query.data.split("_")[-1]
    
    # Сохраняем контекст для обработки текста
    context.user_data['action'] = 'edit_scenario_description'
    context.user_data['scenario_id'] = scenario_id
    
    await query.edit_message_text(
        "📄 <b>Изменение описания сценария</b>\n\n"
        "Введите новое описание сценария:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_scenario_{scenario_id}")
        ]])
    )


async def list_scenario_msgs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик списка сообщений сценария."""
    query = update.callback_query
    await query.answer()
    
    scenario_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            warmup_service = WarmupService(session)
            scenario = await warmup_service.get_scenario_by_id(scenario_id)
            
            if not scenario:
                await query.edit_message_text("❌ Сценарий не найден")
                return
            
            if not scenario.messages:
                await query.edit_message_text(
                    "📋 <b>Список сообщений</b>\n\n"
                    "В сценарии пока нет сообщений.\n"
                    "Нажмите 'Добавить сообщение' для создания.",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data=f"edit_scenario_{scenario_id}")
                    ]])
                )
                return
            
            messages_text = f"📋 <b>Сообщения сценария: {scenario.name}</b>\n\n"
            keyboard = []
            
            for msg in sorted(scenario.messages, key=lambda x: x.order):
                msg_type = msg.message_type.value if hasattr(msg.message_type, 'value') else msg.message_type
                msg_text_short = msg.text[:50] + "..." if len(msg.text) > 50 else msg.text
                
                messages_text += (
                    f"<b>{msg.order}.</b> {msg_type}\n"
                    f"   Задержка: {msg.delay_hours}ч\n"
                    f"   Текст: {msg_text_short}\n\n"
                )
                
                msg_id_short = str(msg.id)[:8]
                keyboard.append([
                    InlineKeyboardButton(
                        f"✏️ Редактировать {msg.order}", 
                        callback_data=f"edit_msg_{msg_id_short}"
                    ),
                    InlineKeyboardButton(
                        f"🗑 Удалить {msg.order}", 
                        callback_data=f"delete_msg_{msg_id_short}"
                    )
                ])
            
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data=f"edit_scenario_{scenario_id}")])
            
            await query.edit_message_text(
                messages_text,
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Ошибка списка сообщений: {e}")
        await query.edit_message_text("❌ Ошибка загрузки сообщений")


async def add_scenario_msg_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик добавления сообщения в сценарий."""
    query = update.callback_query
    await query.answer()
    
    scenario_id = query.data.split("_")[-1]
    
    # Сохраняем контекст
    context.user_data['action'] = 'add_scenario_message_step1'
    context.user_data['scenario_id'] = scenario_id
    
    # Определяем типы сообщений
    message_types = [
        ("🎉 Приветствие", "welcome"),
        ("⚠️ Болевая точка", "pain_point"),
        ("✨ Решение", "solution"),
        ("⭐ Социальное доказательство", "social_proof"),
        ("🎁 Оффер", "offer"),
        ("📞 Дожим", "follow_up")
    ]
    
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"msg_type_{msg_type}")]
        for name, msg_type in message_types
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data=f"edit_scenario_{scenario_id}")])
    
    await query.edit_message_text(
        "➕ <b>Добавление сообщения</b>\n\n"
        "Шаг 1 из 4: Выберите тип сообщения:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def msg_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора типа сообщения."""
    query = update.callback_query
    await query.answer()
    
    msg_type = query.data.split("_")[-1]
    scenario_id = context.user_data.get('scenario_id')
    
    # Сохраняем тип сообщения
    context.user_data['message_type'] = msg_type
    context.user_data['action'] = 'add_scenario_message_step2'
    
    await query.edit_message_text(
        "➕ <b>Добавление сообщения</b>\n\n"
        f"Тип: {msg_type}\n\n"
        "Шаг 2 из 4: Введите текст сообщения:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_scenario_{scenario_id}")
        ]])
    )


async def delete_scenario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик удаления сценария."""
    query = update.callback_query
    await query.answer()
    
    scenario_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            warmup_service = WarmupService(session)
            scenario = await warmup_service.get_scenario_by_id(scenario_id)
            
            if not scenario:
                await query.edit_message_text("❌ Сценарий не найден")
                return
            
            await query.edit_message_text(
                f"❓ <b>Подтверждение удаления</b>\n\n"
                f"Вы действительно хотите удалить сценарий <b>{scenario.name}</b>?\n\n"
                f"⚠️ Это действие необратимо!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_scenario_{scenario_id}"),
                        InlineKeyboardButton("❌ Отмена", callback_data=f"view_scenario_{scenario_id}")
                    ]
                ])
            )
            
    except Exception as e:
        logger.error(f"Ошибка удаления сценария: {e}")
        await query.edit_message_text("❌ Ошибка удаления сценария")


async def confirm_delete_scenario_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик подтверждения удаления сценария."""
    query = update.callback_query
    await query.answer()
    
    scenario_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            warmup_service = WarmupService(session)
            success = await warmup_service.delete_scenario(scenario_id)
            
            if success:
                await query.edit_message_text(
                    "✅ Сценарий успешно удален",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_warmup")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "❌ Не удалось удалить сценарий",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_warmup")
                    ]])
                )
                
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления сценария: {e}")
        await query.edit_message_text("❌ Ошибка удаления сценария")


async def edit_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик редактирования продукта."""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            product_service = ProductService(session)
            product = await product_service.get_product_by_id(product_id)
            
            if not product:
                await query.edit_message_text("❌ Продукт не найден")
                return
            
            product_type = product.type.value if hasattr(product.type, 'value') else product.type
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить название", callback_data=f"edit_product_name_{product_id}")],
                [InlineKeyboardButton("📄 Изменить описание", callback_data=f"edit_product_desc_{product_id}")],
                [InlineKeyboardButton("💰 Изменить цену", callback_data=f"edit_product_price_{product_id}")],
                [InlineKeyboardButton("🔗 Изменить ссылку", callback_data=f"edit_product_url_{product_id}")],
                [InlineKeyboardButton("📋 Изменить текст оффера", callback_data=f"edit_product_offer_{product_id}")],
                [InlineKeyboardButton("◀️ Назад", callback_data="admin_products")]
            ]
            
            await query.edit_message_text(
                f"✏️ <b>Редактирование продукта</b>\n\n"
                f"<b>Название:</b> {product.name}\n"
                f"<b>Описание:</b> {product.description or 'Не указано'}\n"
                f"<b>Тип:</b> {product_type}\n"
                f"<b>Цена:</b> {product.price/100} {product.currency}\n"
                f"<b>Ссылка:</b> {product.payment_url or 'Не указана'}\n"
                f"<b>Статус:</b> {'✅ Активен' if product.is_active else '❌ Неактивен'}\n\n"
                f"Выберите, что хотите изменить:",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    except Exception as e:
        logger.error(f"Ошибка редактирования продукта: {e}")
        await query.edit_message_text("❌ Ошибка загрузки продукта")


async def edit_product_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения названия продукта."""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    
    context.user_data['action'] = 'edit_product_name'
    context.user_data['product_id'] = product_id
    
    await query.edit_message_text(
        "📝 <b>Изменение названия продукта</b>\n\n"
        "Введите новое название продукта:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_product_{product_id}")
        ]])
    )


async def edit_product_desc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения описания продукта."""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    
    context.user_data['action'] = 'edit_product_description'
    context.user_data['product_id'] = product_id
    
    await query.edit_message_text(
        "📄 <b>Изменение описания продукта</b>\n\n"
        "Введите новое описание продукта:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_product_{product_id}")
        ]])
    )


async def edit_product_price_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения цены продукта."""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    
    context.user_data['action'] = 'edit_product_price'
    context.user_data['product_id'] = product_id
    
    await query.edit_message_text(
        "💰 <b>Изменение цены продукта</b>\n\n"
        "Введите новую цену в рублях (например: 499 или 1990):",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_product_{product_id}")
        ]])
    )


async def edit_product_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения ссылки продукта."""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    
    context.user_data['action'] = 'edit_product_url'
    context.user_data['product_id'] = product_id
    
    await query.edit_message_text(
        "🔗 <b>Изменение ссылки на оплату</b>\n\n"
        "Введите новую ссылку на страницу оплаты:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_product_{product_id}")
        ]])
    )


async def edit_product_offer_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик изменения текста оффера продукта."""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    
    context.user_data['action'] = 'edit_product_offer'
    context.user_data['product_id'] = product_id
    
    await query.edit_message_text(
        "📋 <b>Изменение текста оффера</b>\n\n"
        "Введите новый текст оффера для продажи продукта:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data=f"edit_product_{product_id}")
        ]])
    )


async def delete_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик удаления продукта."""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            product_service = ProductService(session)
            product = await product_service.get_product_by_id(product_id)
            
            if not product:
                await query.edit_message_text("❌ Продукт не найден")
                return
            
            await query.edit_message_text(
                f"❓ <b>Подтверждение удаления</b>\n\n"
                f"Вы действительно хотите удалить продукт <b>{product.name}</b>?\n\n"
                f"⚠️ Это действие необратимо!",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_product_{product_id}"),
                        InlineKeyboardButton("❌ Отмена", callback_data="admin_products")
                    ]
                ])
            )
            
    except Exception as e:
        logger.error(f"Ошибка удаления продукта: {e}")
        await query.edit_message_text("❌ Ошибка удаления продукта")


async def confirm_delete_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик подтверждения удаления продукта."""
    query = update.callback_query
    await query.answer()
    
    product_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            product_service = ProductService(session)
            success = await product_service.delete_product(product_id)
            
            if success:
                await query.edit_message_text(
                    "✅ Продукт успешно удален",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_products")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "❌ Не удалось удалить продукт",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_products")
                    ]])
                )
                
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления продукта: {e}")
        await query.edit_message_text("❌ Ошибка удаления продукта")


async def add_product_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик добавления нового продукта."""
    query = update.callback_query
    await query.answer()
    
    # Определяем типы продуктов
    product_types = [
        ("🎯 Трипвайер", "tripwire"),
        ("📚 Курс", "course"),
        ("💬 Консультация", "consultation"),
        ("⭐ Основной продукт", "main_product"),
        ("⬆️ Upsell", "upsell"),
        ("⬇️ Downsell", "downsell")
    ]
    
    context.user_data['action'] = 'add_product_step1'
    
    keyboard = [
        [InlineKeyboardButton(name, callback_data=f"product_type_{p_type}")]
        for name, p_type in product_types
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="admin_products")])
    
    await query.edit_message_text(
        "➕ <b>Добавление продукта</b>\n\n"
        "Шаг 1 из 5: Выберите тип продукта:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


async def product_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора типа продукта."""
    query = update.callback_query
    await query.answer()
    
    product_type = query.data.split("_")[-1]
    
    context.user_data['product_type'] = product_type
    context.user_data['action'] = 'add_product_step2'
    
    await query.edit_message_text(
        "➕ <b>Добавление продукта</b>\n\n"
        f"Тип: {product_type}\n\n"
        "Шаг 2 из 5: Введите название продукта:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Отмена", callback_data="admin_products")
        ]])
    )


async def edit_magnet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик редактирования лид-магнита."""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем ID из callback_data
    magnet_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            lead_magnet_service = LeadMagnetService(session)
            magnet = await lead_magnet_service.get_lead_magnet_by_id(magnet_id)
            
            if not magnet:
                await query.edit_message_text("❌ Лид-магнит не найден")
                return
            
            # Показываем информацию о лид-магните для редактирования
            magnet_type = magnet.type.value if hasattr(magnet.type, 'value') else magnet.type
            status = "✅ Активен" if magnet.is_active else "❌ Неактивен"
            
            edit_text = f"✏️ <b>Редактирование лид-магнита</b>\n\n"
            edit_text += f"<b>Название:</b> {magnet.name}\n"
            edit_text += f"<b>Тип:</b> {magnet_type}\n"
            edit_text += f"<b>Статус:</b> {status}\n"
            edit_text += f"<b>URL:</b> {magnet.file_url[:50]}...\n\n"
            edit_text += "Выберите что хотите изменить:"
            
            keyboard = [
                [InlineKeyboardButton("📝 Изменить название", callback_data=f"edit_magnet_name_{magnet_id}")],
                [InlineKeyboardButton("🔗 Изменить URL", callback_data=f"edit_magnet_url_{magnet_id}")],
                [InlineKeyboardButton("📄 Изменить описание", callback_data=f"edit_magnet_desc_{magnet_id}")],
                [InlineKeyboardButton("🔄 Переключить статус", callback_data=f"toggle_magnet_{magnet_id}")],
                [InlineKeyboardButton("◀️ Назад к лид-магнитам", callback_data="admin_lead_magnets")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                edit_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка редактирования лид-магнита: {e}")
        await query.edit_message_text("❌ Ошибка редактирования лид-магнита")


async def delete_magnet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик удаления лид-магнита."""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем ID из callback_data
    magnet_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            lead_magnet_service = LeadMagnetService(session)
            magnet = await lead_magnet_service.get_lead_magnet_by_id(magnet_id)
            
            if not magnet:
                await query.edit_message_text("❌ Лид-магнит не найден")
                return
            
            # Показываем подтверждение удаления
            delete_text = f"🗑️ <b>Подтверждение удаления</b>\n\n"
            delete_text += f"Вы действительно хотите удалить лид-магнит:\n"
            delete_text += f"<b>«{magnet.name}»</b>\n\n"
            delete_text += "⚠️ <i>Это действие нельзя отменить!</i>"
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_magnet_{magnet_id}"),
                    InlineKeyboardButton("❌ Отмена", callback_data="admin_lead_magnets")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                delete_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка удаления лид-магнита: {e}")
        await query.edit_message_text("❌ Ошибка удаления лид-магнита")


async def confirm_delete_magnet_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик подтверждения удаления лид-магнита."""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем ID из callback_data
    magnet_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            lead_magnet_service = LeadMagnetService(session)
            success = await lead_magnet_service.delete_lead_magnet(magnet_id)
            
            if success:
                await query.edit_message_text(
                    "✅ Лид-магнит успешно удален!",
                    parse_mode="HTML"
                )
                # Возвращаемся к списку лид-магнитов через 2 секунды
                import asyncio
                await asyncio.sleep(2)
                await admin_lead_magnets_handler(update, context)
            else:
                await query.edit_message_text("❌ Не удалось удалить лид-магнит")
                
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления лид-магнита: {e}")
        await query.edit_message_text("❌ Ошибка удаления лид-магнита")


# Создание обработчиков для регистрации
admin_handler = CommandHandler("admin", admin_command_handler)
admin_stats_callback = CallbackQueryHandler(admin_stats_handler, pattern="^admin_stats$")
admin_users_callback = CallbackQueryHandler(admin_users_handler, pattern="^admin_users$")
admin_lead_magnets_callback = CallbackQueryHandler(admin_lead_magnets_handler, pattern="^admin_lead_magnets$")
admin_products_callback = CallbackQueryHandler(admin_products_handler, pattern="^admin_products$")
admin_warmup_callback = CallbackQueryHandler(admin_warmup_handler, pattern="^admin_warmup$")
admin_back_callback = CallbackQueryHandler(admin_back_handler, pattern="^admin_back$")

async def edit_magnet_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик редактирования названия лид-магнита."""
    query = update.callback_query
    await query.answer()
    
    magnet_id = query.data.split("_")[-1]
    context.user_data['editing_magnet_name'] = magnet_id
    
    await query.edit_message_text(
        "📝 <b>Изменение названия лид-магнита</b>\n\n"
        "Отправьте новое название:",
        parse_mode="HTML"
    )


async def edit_magnet_url_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик редактирования URL лид-магнита."""
    query = update.callback_query
    await query.answer()
    
    magnet_id = query.data.split("_")[-1]
    context.user_data['editing_magnet_url'] = magnet_id
    
    await query.edit_message_text(
        "🔗 <b>Изменение URL лид-магнита</b>\n\n"
        "Отправьте новый URL (Google Sheets, PDF или ссылку):",
        parse_mode="HTML"
    )


async def edit_magnet_desc_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик редактирования описания лид-магнита."""
    query = update.callback_query
    await query.answer()
    
    magnet_id = query.data.split("_")[-1]
    context.user_data['editing_magnet_desc'] = magnet_id
    
    await query.edit_message_text(
        "📄 <b>Изменение описания лид-магнита</b>\n\n"
        "Отправьте новое описание:",
        parse_mode="HTML"
    )


async def reset_all_lead_magnets_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик сброса всех выданных лид-магнитов."""
    query = update.callback_query
    await query.answer()
    
    try:
        async with get_db_session() as session:
            user_service = UserService(session)
            lead_magnet_service = LeadMagnetService(session)
            
            # Получаем всех пользователей
            users = await user_service.get_all_users()
            
            reset_count = 0
            
            for user in users:
                has_magnet = await lead_magnet_service.user_has_lead_magnet(str(user.id))
                if has_magnet:
                    # Удаляем записи о выданных лид-магнитах
                    from app.models.lead_magnet import UserLeadMagnet
                    from sqlalchemy import delete
                    
                    await session.execute(
                        delete(UserLeadMagnet).where(UserLeadMagnet.user_id == str(user.id))
                    )
                    reset_count += 1
            
            await session.commit()
            
            await query.edit_message_text(
                f"✅ <b>Сброс завершен!</b>\n\n"
                f"Сброшено записей о лид-магнитах для {reset_count} пользователей.\n\n"
                f"Теперь все пользователи смогут получить лид-магнит заново.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Ошибка сброса лид-магнитов: {e}")
        await query.edit_message_text(
            "❌ Ошибка при сбросе лид-магнитов",
            parse_mode="HTML"
        )


# Обработчики для лид-магнитов
edit_magnet_callback = CallbackQueryHandler(edit_magnet_handler, pattern="^edit_magnet_")
delete_magnet_callback = CallbackQueryHandler(delete_magnet_handler, pattern="^delete_magnet_")
confirm_delete_magnet_callback = CallbackQueryHandler(confirm_delete_magnet_handler, pattern="^confirm_delete_magnet_")
edit_magnet_name_callback = CallbackQueryHandler(edit_magnet_name_handler, pattern="^edit_magnet_name_")
edit_magnet_url_callback = CallbackQueryHandler(edit_magnet_url_handler, pattern="^edit_magnet_url_")
edit_magnet_desc_callback = CallbackQueryHandler(edit_magnet_desc_handler, pattern="^edit_magnet_desc_")
reset_all_lead_magnets_callback = CallbackQueryHandler(reset_all_lead_magnets_handler, pattern="^reset_all_lead_magnets$")


async def admin_mailings_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик раздела рассылок."""
    query = update.callback_query
    await query.answer()
    
    try:
        async with get_db_session() as session:
            from app.services.mailing_service import MailingService
            
            mailing_service = MailingService(session)
            
            mailings = await mailing_service.get_all_mailings()
            total_users = await mailing_service.get_all_users_count()
            
            mailings_text = f"📢 <b>Рассылки ({len(mailings)}):</b>\n\n"
            mailings_text += f"👥 Всего пользователей: {total_users}\n\n"
            
            keyboard = []
            
            for mailing in mailings[:5]:  # Показываем первые 5
                status_emoji = {
                    "draft": "📝",
                    "scheduled": "⏰",
                    "sending": "📤",
                    "completed": "✅",
                    "failed": "❌"
                }.get(mailing.status, "❓")
                
                mailings_text += (
                    f"{status_emoji} <b>{mailing.name}</b>\n"
                    f"   Получателей: {mailing.total_recipients}\n"
                    f"   Отправлено: {mailing.sent_count}/{mailing.total_recipients}\n"
                    f"   Статус: {mailing.status}\n\n"
                )
                
                # Кнопки для управления рассылкой
                mailing_id_short = str(mailing.id)[:8]
                
                if mailing.status in ["draft", "scheduled"]:
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📤 Отправить", 
                            callback_data=f"send_mailing_{mailing_id_short}"
                        ),
                        InlineKeyboardButton(
                            f"✏️ Редактировать", 
                            callback_data=f"edit_mailing_{mailing_id_short}"
                        ),
                        InlineKeyboardButton(
                            f"🗑️ Удалить", 
                            callback_data=f"delete_mailing_{mailing_id_short}"
                        )
                    ])
                elif mailing.status == "completed":
                    keyboard.append([
                        InlineKeyboardButton(
                            f"📊 Статистика", 
                            callback_data=f"mailing_stats_{mailing_id_short}"
                        ),
                        InlineKeyboardButton(
                            f"🔄 Отправить снова", 
                            callback_data=f"resend_mailing_{mailing_id_short}"
                        ),
                        InlineKeyboardButton(
                            f"🗑️ Удалить", 
                            callback_data=f"delete_mailing_{mailing_id_short}"
                        )
                    ])
                elif mailing.status == "failed":
                    keyboard.append([
                        InlineKeyboardButton(
                            f"🔄 Отправить снова", 
                            callback_data=f"resend_mailing_{mailing_id_short}"
                        ),
                        InlineKeyboardButton(
                            f"✏️ Редактировать", 
                            callback_data=f"edit_mailing_{mailing_id_short}"
                        ),
                        InlineKeyboardButton(
                            f"🗑️ Удалить", 
                            callback_data=f"delete_mailing_{mailing_id_short}"
                        )
                    ])
            
            keyboard.append([InlineKeyboardButton("➕ Создать рассылку", callback_data="create_mailing")])
            keyboard.append([InlineKeyboardButton("🔄 Обновить", callback_data="admin_mailings")])
            keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="admin_back")])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    mailings_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    # Сообщение уже такое же, просто отвечаем на callback
                    await query.answer()
                else:
                    raise edit_error
            
    except Exception as e:
        logger.error(f"Ошибка получения рассылок: {e}")
        try:
            await query.edit_message_text(
                "❌ Ошибка получения рассылок",
                parse_mode="HTML"
            )
        except Exception as edit_error:
            if "Message is not modified" not in str(edit_error):
                await query.answer()


async def create_mailing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик создания рассылки."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📝 <b>Создание новой рассылки</b>\n\n"
        "Отправьте название рассылки:",
        parse_mode="HTML"
    )
    
    context.user_data['creating_mailing_name'] = True


async def send_mailing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик отправки рассылки."""
    query = update.callback_query
    await query.answer()
    
    mailing_id = query.data.split("_")[-1]
    
    try:
        async with get_db_session() as session:
            from app.services.mailing_service import MailingService
            
            mailing_service = MailingService(session)
            
            # Получаем рассылку
            mailing = await mailing_service.get_mailing_by_id(mailing_id)
            
            if not mailing:
                await query.edit_message_text(
                    "❌ Рассылка не найдена",
                    parse_mode="HTML"
                )
                return
            
            # Подготавливаем рассылку только если она в статусе draft
            if mailing.status == "draft":
                mailing = await mailing_service.prepare_mailing(mailing_id)
                
                if not mailing:
                    await query.edit_message_text(
                        "❌ Ошибка подготовки рассылки",
                        parse_mode="HTML"
                    )
                    return
            
            # Отправляем рассылку
            await query.edit_message_text(
                f"📤 <b>Отправка рассылки</b>\n\n"
                f"Рассылка: {mailing.name}\n"
                f"Получателей: {mailing.total_recipients}\n\n"
                f"⏳ Отправляем сообщения...",
                parse_mode="HTML"
            )
            
            # Запускаем отправку в фоне
            import asyncio
            asyncio.create_task(send_mailing_async(mailing_id, context.bot, query))
            
            await query.edit_message_text(
                f"📤 <b>Рассылка запущена!</b>\n\n"
                f"Рассылка: {mailing.name}\n"
                f"Получателей: {mailing.total_recipients}\n\n"
                f"⏳ Отправка в процессе...",
                parse_mode="HTML"
            )
            
    except Exception as e:
        logger.error(f"Ошибка отправки рассылки: {e}")
        await query.edit_message_text(
            "❌ Ошибка отправки рассылки",
            parse_mode="HTML"
        )


async def send_mailing_async(mailing_id: str, bot, query) -> None:
    """Асинхронная отправка рассылки."""
    try:
        async with get_db_session() as session:
            from app.services.mailing_service import MailingService
            
            mailing_service = MailingService(session)
            mailing = await mailing_service.send_mailing(mailing_id, bot)
            
            if mailing:
                try:
                    await query.edit_message_text(
                        f"✅ <b>Рассылка завершена!</b>\n\n"
                        f"Рассылка: {mailing.name}\n"
                        f"Отправлено: {mailing.sent_count} из {mailing.total_recipients}\n"
                        f"Ошибок: {mailing.failed_count}",
                        parse_mode="HTML"
                    )
                except Exception as edit_error:
                    if "Message is not modified" not in str(edit_error):
                        logger.error(f"Ошибка обновления сообщения: {edit_error}")
            else:
                try:
                    await query.edit_message_text(
                        "❌ Ошибка отправки рассылки",
                        parse_mode="HTML"
                    )
                except Exception as edit_error:
                    if "Message is not modified" not in str(edit_error):
                        logger.error(f"Ошибка обновления сообщения: {edit_error}")
    except Exception as e:
        logger.error(f"Ошибка асинхронной отправки рассылки: {e}")
        try:
            await query.edit_message_text(
                "❌ Ошибка отправки рассылки",
                parse_mode="HTML"
            )
        except:
            pass


async def resend_mailing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик повторной отправки рассылки."""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID рассылки
    mailing_id = query.data.replace("resend_mailing_", "")
    
    try:
        async with get_db_session() as session:
            from app.services.mailing_service import MailingService
            
            mailing_service = MailingService(session)
            
            # Сбрасываем рассылку
            mailing = await mailing_service.reset_mailing(mailing_id)
            
            if mailing:
                # Подготавливаем рассылку (используем первые 8 символов UUID)
                mailing = await mailing_service.prepare_mailing(str(mailing.id)[:8])
                
                if mailing:
                    await query.edit_message_text(
                        f"✅ Рассылка <b>{mailing.name}</b> подготовлена к повторной отправке\n\n"
                        f"Получателей: {mailing.total_recipients}\n\n"
                        f"Нажмите «Отправить» для запуска рассылки",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("📤 Отправить", callback_data=f"send_mailing_{str(mailing.id)[:8]}"),
                            InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
                        ]])
                    )
                else:
                    await query.edit_message_text(
                        "❌ Ошибка подготовки рассылки",
                        parse_mode="HTML",
                        reply_markup=InlineKeyboardMarkup([[
                            InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
                        ]])
                    )
            else:
                await query.edit_message_text(
                    "❌ Рассылка не найдена",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
                    ]])
                )
    except Exception as e:
        logger.error(f"Ошибка повторной отправки рассылки: {e}")
        await query.edit_message_text(
            f"❌ Ошибка: {e}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
            ]])
        )


async def edit_mailing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик редактирования рассылки."""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID рассылки
    mailing_id = query.data.replace("edit_mailing_", "")
    
    try:
        async with get_db_session() as session:
            from app.services.mailing_service import MailingService
            
            mailing_service = MailingService(session)
            mailing = await mailing_service.get_mailing_by_id(mailing_id)
            
            if mailing:
                # Сохраняем ID рассылки в контексте
                context.user_data["editing_mailing_id"] = str(mailing.id)
                context.user_data["editing_mailing_field"] = "name"
                
                await query.edit_message_text(
                    f"✏️ <b>Редактирование рассылки</b>\n\n"
                    f"Текущее название: <b>{mailing.name}</b>\n\n"
                    f"Отправьте новое название рассылки:",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("❌ Отмена", callback_data="admin_mailings")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "❌ Рассылка не найдена",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
                    ]])
                )
    except Exception as e:
        logger.error(f"Ошибка редактирования рассылки: {e}")
        await query.edit_message_text(
            f"❌ Ошибка: {e}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
            ]])
        )


async def delete_mailing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик удаления рассылки."""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID рассылки
    mailing_id = query.data.replace("delete_mailing_", "")
    
    try:
        async with get_db_session() as session:
            from app.services.mailing_service import MailingService
            
            mailing_service = MailingService(session)
            mailing = await mailing_service.get_mailing_by_id(mailing_id)
            
            if mailing:
                # Подтверждение удаления
                await query.edit_message_text(
                    f"❓ <b>Подтверждение удаления</b>\n\n"
                    f"Вы действительно хотите удалить рассылку <b>{mailing.name}</b>?\n\n"
                    f"Это действие необратимо!",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([
                        [
                            InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_mailing_{str(mailing.id)[:8]}"),
                            InlineKeyboardButton("❌ Отмена", callback_data="admin_mailings")
                        ]
                    ])
                )
            else:
                await query.edit_message_text(
                    "❌ Рассылка не найдена",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
                    ]])
                )
    except Exception as e:
        logger.error(f"Ошибка удаления рассылки: {e}")
        await query.edit_message_text(
            f"❌ Ошибка: {e}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
            ]])
        )


async def confirm_delete_mailing_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик подтверждения удаления рассылки."""
    query = update.callback_query
    await query.answer()
    
    # Получаем ID рассылки
    mailing_id = query.data.replace("confirm_delete_mailing_", "")
    
    try:
        async with get_db_session() as session:
            from app.services.mailing_service import MailingService
            
            mailing_service = MailingService(session)
            success = await mailing_service.delete_mailing(mailing_id)
            
            if success:
                await query.edit_message_text(
                    "✅ Рассылка успешно удалена",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
                    ]])
                )
            else:
                await query.edit_message_text(
                    "❌ Ошибка удаления рассылки",
                    parse_mode="HTML",
                    reply_markup=InlineKeyboardMarkup([[
                        InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
                    ]])
                )
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления рассылки: {e}")
        await query.edit_message_text(
            f"❌ Ошибка: {e}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("◀️ Назад", callback_data="admin_mailings")
            ]])
        )


# Обработчики для рассылок
admin_mailings_callback = CallbackQueryHandler(admin_mailings_handler, pattern="^admin_mailings$")
create_mailing_callback = CallbackQueryHandler(create_mailing_handler, pattern="^create_mailing$")
send_mailing_callback = CallbackQueryHandler(send_mailing_handler, pattern="^send_mailing_")
resend_mailing_callback = CallbackQueryHandler(resend_mailing_handler, pattern="^resend_mailing_")
edit_mailing_callback = CallbackQueryHandler(edit_mailing_handler, pattern="^edit_mailing_")
delete_mailing_callback = CallbackQueryHandler(delete_mailing_handler, pattern="^delete_mailing_")
confirm_delete_mailing_callback = CallbackQueryHandler(confirm_delete_mailing_handler, pattern="^confirm_delete_mailing_")

# Обработчики для сценариев прогрева
view_scenario_callback = CallbackQueryHandler(view_scenario_handler, pattern="^view_scenario_")
add_scenario_callback = CallbackQueryHandler(add_scenario_handler, pattern="^add_scenario$")
edit_scenario_callback = CallbackQueryHandler(edit_scenario_handler, pattern="^edit_scenario_")
delete_scenario_callback = CallbackQueryHandler(delete_scenario_handler, pattern="^delete_scenario_")
confirm_delete_scenario_callback = CallbackQueryHandler(confirm_delete_scenario_handler, pattern="^confirm_delete_scenario_")
edit_scenario_name_callback = CallbackQueryHandler(edit_scenario_name_handler, pattern="^edit_scenario_name_")
edit_scenario_desc_callback = CallbackQueryHandler(edit_scenario_desc_handler, pattern="^edit_scenario_desc_")
list_scenario_msgs_callback = CallbackQueryHandler(list_scenario_msgs_handler, pattern="^list_scenario_msgs_")
add_scenario_msg_callback = CallbackQueryHandler(add_scenario_msg_handler, pattern="^add_scenario_msg_")
msg_type_callback = CallbackQueryHandler(msg_type_handler, pattern="^msg_type_")

# Обработчики для продуктов
edit_product_callback = CallbackQueryHandler(edit_product_handler, pattern="^edit_product_")
delete_product_callback = CallbackQueryHandler(delete_product_handler, pattern="^delete_product_")
confirm_delete_product_callback = CallbackQueryHandler(confirm_delete_product_handler, pattern="^confirm_delete_product_")
edit_product_name_callback = CallbackQueryHandler(edit_product_name_handler, pattern="^edit_product_name_")
edit_product_desc_callback = CallbackQueryHandler(edit_product_desc_handler, pattern="^edit_product_desc_")
edit_product_price_callback = CallbackQueryHandler(edit_product_price_handler, pattern="^edit_product_price_")
edit_product_url_callback = CallbackQueryHandler(edit_product_url_handler, pattern="^edit_product_url_")
edit_product_offer_callback = CallbackQueryHandler(edit_product_offer_handler, pattern="^edit_product_offer_")
add_product_callback = CallbackQueryHandler(add_product_handler, pattern="^add_product$")
product_type_callback = CallbackQueryHandler(product_type_handler, pattern="^product_type_")

