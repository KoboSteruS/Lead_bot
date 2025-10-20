"""
Обработчики для управления диалогами в админ-панели.

Содержит логику создания, редактирования и удаления диалогов.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from loguru import logger

from app.core.database import get_db_session
from app.services.dialog_service import DialogService
from app.schemas.dialog import DialogCreate, DialogQuestionCreate, DialogAnswerCreate
from app.bot.utils.admin_check import is_admin


async def admin_dialogs_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик кнопки 'Диалоги' в админ-панели."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет прав администратора")
        return
    
    try:
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            dialogs = await dialog_service.get_all_dialogs()
            stats = await dialog_service.get_dialog_stats()
            
            # Формируем сообщение
            message_text = (
                "💬 <b>Управление диалогами</b>\n\n"
                f"📊 <b>Статистика:</b>\n"
                f"• Всего диалогов: {stats['total_dialogs']}\n"
                f"• Активных: {stats['active_dialogs']}\n"
                f"• Вопросов: {stats['total_questions']}\n"
                f"• Ответов: {stats['total_answers']}\n\n"
                f"📋 <b>Диалоги:</b>\n"
            )
            
            if dialogs:
                for i, dialog in enumerate(dialogs[:10], 1):  # Показываем первые 10
                    status_emoji = "✅" if dialog.status == "active" else "❌"
                    message_text += f"{i}. {status_emoji} {dialog.name}\n"
                
                if len(dialogs) > 10:
                    message_text += f"... и еще {len(dialogs) - 10} диалогов\n"
            else:
                message_text += "Диалоги не найдены\n"
            
            # Создаем клавиатуру
            keyboard = [
                [InlineKeyboardButton("➕ Создать диалог", callback_data="create_dialog")],
                [InlineKeyboardButton("📝 Редактировать", callback_data="edit_dialog_select")],
                [InlineKeyboardButton("🗑️ Удалить", callback_data="delete_dialog_select")],
                [InlineKeyboardButton("📊 Статистика", callback_data="dialog_stats")],
                [InlineKeyboardButton("🔙 Назад", callback_data="admin_panel")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    message_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    await query.answer("Диалоги обновлены")
                else:
                    raise edit_error
                    
    except Exception as e:
        logger.error(f"Ошибка получения диалогов: {e}")
        await query.edit_message_text("❌ Ошибка получения диалогов")


async def create_dialog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик создания диалога."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет прав администратора")
        return
    
    # Устанавливаем состояние создания диалога
    context.user_data['action'] = 'creating_dialog'
    context.user_data['dialog_data'] = {
        'questions': [],
        'current_question': None
    }
    
    keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "💬 <b>Создание диалога</b>\n\n"
        "📝 Отправьте название диалога:",
        parse_mode="HTML",
        reply_markup=reply_markup
    )


async def edit_dialog_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора диалога для редактирования."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет прав администратора")
        return
    
    try:
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            dialogs = await dialog_service.get_all_dialogs()
            
            if not dialogs:
                await query.edit_message_text(
                    "❌ Диалоги не найдены",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")]])
                )
                return
            
            # Создаем клавиатуру с диалогами
            keyboard = []
            for dialog in dialogs[:10]:  # Показываем первые 10
                status_emoji = "✅" if dialog.status == "active" else "❌"
                button_text = f"{status_emoji} {dialog.name[:30]}"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"edit_dialog_{str(dialog.id)[:8]}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "📝 <b>Выберите диалог для редактирования:</b>",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения диалогов для редактирования: {e}")
        await query.edit_message_text("❌ Ошибка получения диалогов")


async def edit_dialog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик редактирования диалога."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет прав администратора")
        return
    
    # Извлекаем ID диалога из callback_data
    dialog_id = query.data.replace("edit_dialog_", "")
    
    try:
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            dialog = await dialog_service.get_dialog_by_id(dialog_id)
            
            if not dialog:
                await query.edit_message_text(
                    "❌ Диалог не найден",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")]])
                )
                return
            
            # Формируем сообщение с информацией о диалоге
            message_text = (
                f"📝 <b>Редактирование диалога</b>\n\n"
                f"📋 <b>Название:</b> {dialog.name}\n"
                f"📄 <b>Описание:</b> {dialog.description or 'Не указано'}\n"
                f"🔄 <b>Статус:</b> {dialog.status}\n"
                f"📊 <b>Вопросов:</b> {len(dialog.questions)}\n\n"
                f"📝 <b>Вопросы:</b>\n"
            )
            
            for i, question in enumerate(dialog.questions[:5], 1):
                message_text += f"{i}. {question.question_text[:50]}...\n"
            
            if len(dialog.questions) > 5:
                message_text += f"... и еще {len(dialog.questions) - 5} вопросов\n"
            
            # Создаем клавиатуру
            keyboard = [
                [InlineKeyboardButton("✏️ Изменить название", callback_data=f"edit_dialog_name_{dialog_id}")],
                [InlineKeyboardButton("📄 Изменить описание", callback_data=f"edit_dialog_desc_{dialog_id}")],
                [InlineKeyboardButton("🔄 Изменить статус", callback_data=f"edit_dialog_status_{dialog_id}")],
                [InlineKeyboardButton("❓ Управление вопросами", callback_data=f"manage_questions_{dialog_id}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="edit_dialog_select")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            try:
                await query.edit_message_text(
                    message_text,
                    parse_mode="HTML",
                    reply_markup=reply_markup
                )
            except Exception as edit_error:
                if "Message is not modified" in str(edit_error):
                    await query.answer("Диалог обновлен")
                else:
                    raise edit_error
                    
    except Exception as e:
        logger.error(f"Ошибка редактирования диалога: {e}")
        await query.edit_message_text("❌ Ошибка редактирования диалога")


async def delete_dialog_select_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выбора диалога для удаления."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет прав администратора")
        return
    
    try:
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            dialogs = await dialog_service.get_all_dialogs()
            
            if not dialogs:
                await query.edit_message_text(
                    "❌ Диалоги не найдены",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")]])
                )
                return
            
            # Создаем клавиатуру с диалогами
            keyboard = []
            for dialog in dialogs[:10]:  # Показываем первые 10
                status_emoji = "✅" if dialog.status == "active" else "❌"
                button_text = f"{status_emoji} {dialog.name[:30]}"
                keyboard.append([InlineKeyboardButton(
                    button_text,
                    callback_data=f"delete_dialog_{str(dialog.id)[:8]}"
                )])
            
            keyboard.append([InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")])
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "🗑️ <b>Выберите диалог для удаления:</b>",
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения диалогов для удаления: {e}")
        await query.edit_message_text("❌ Ошибка получения диалогов")


async def confirm_delete_dialog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик подтверждения удаления диалога."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет прав администратора")
        return
    
    # Извлекаем ID диалога из callback_data
    dialog_id = query.data.replace("delete_dialog_", "")
    
    try:
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            dialog = await dialog_service.get_dialog_by_id(dialog_id)
            
            if not dialog:
                await query.edit_message_text(
                    "❌ Диалог не найден",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")]])
                )
                return
            
            # Формируем сообщение подтверждения
            message_text = (
                f"🗑️ <b>Подтверждение удаления</b>\n\n"
                f"📋 <b>Диалог:</b> {dialog.name}\n"
                f"📊 <b>Вопросов:</b> {len(dialog.questions)}\n"
                f"📊 <b>Ответов:</b> {sum(len(q.answers) for q in dialog.questions)}\n\n"
                f"⚠️ <b>ВНИМАНИЕ!</b> Это действие нельзя отменить.\n"
                f"Все вопросы и ответы будут удалены навсегда.\n\n"
                f"Вы уверены, что хотите удалить этот диалог?"
            )
            
            # Создаем клавиатуру подтверждения
            keyboard = [
                [InlineKeyboardButton("✅ Да, удалить", callback_data=f"confirm_delete_dialog_{dialog_id}")],
                [InlineKeyboardButton("❌ Отмена", callback_data="admin_dialogs")]
            ]
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка подтверждения удаления диалога: {e}")
        await query.edit_message_text("❌ Ошибка подтверждения удаления")


async def execute_delete_dialog_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик выполнения удаления диалога."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет прав администратора")
        return
    
    # Извлекаем ID диалога из callback_data
    dialog_id = query.data.replace("confirm_delete_dialog_", "")
    
    try:
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            dialog = await dialog_service.get_dialog_by_id(dialog_id)
            
            if not dialog:
                await query.edit_message_text(
                    "❌ Диалог не найден",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")]])
                )
                return
            
            dialog_name = dialog.name
            
            # Удаляем диалог
            success = await dialog_service.delete_dialog(dialog_id)
            
            if success:
                await query.edit_message_text(
                    f"✅ Диалог '{dialog_name}' успешно удален",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 К диалогам", callback_data="admin_dialogs")]])
                )
                logger.info(f"Админ {query.from_user.id} удалил диалог: {dialog_name}")
            else:
                await query.edit_message_text(
                    "❌ Ошибка удаления диалога",
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")]])
                )
                
    except Exception as e:
        logger.error(f"Ошибка удаления диалога: {e}")
        await query.edit_message_text("❌ Ошибка удаления диалога")


async def dialog_stats_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик статистики диалогов."""
    query = update.callback_query
    await query.answer()
    
    if not await is_admin(query.from_user.id):
        await query.edit_message_text("❌ У вас нет прав администратора")
        return
    
    try:
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            stats = await dialog_service.get_dialog_stats()
            
            # Формируем сообщение со статистикой
            message_text = (
                "📊 <b>Статистика диалогов</b>\n\n"
                f"💬 <b>Диалоги:</b>\n"
                f"• Всего: {stats['total_dialogs']}\n"
                f"• Активных: {stats['active_dialogs']}\n"
                f"• Неактивных: {stats['total_dialogs'] - stats['active_dialogs']}\n\n"
                f"❓ <b>Вопросы:</b>\n"
                f"• Всего: {stats['total_questions']}\n"
                f"• Активных: {stats['active_questions']}\n"
                f"• Неактивных: {stats['total_questions'] - stats['active_questions']}\n\n"
                f"💬 <b>Ответы:</b>\n"
                f"• Всего: {stats['total_answers']}\n"
                f"• Активных: {stats['active_answers']}\n"
                f"• Неактивных: {stats['total_answers'] - stats['active_answers']}\n\n"
                f"📈 <b>Средние показатели:</b>\n"
                f"• Вопросов на диалог: {stats['total_questions'] / max(stats['total_dialogs'], 1):.1f}\n"
                f"• Ответов на вопрос: {stats['total_answers'] / max(stats['total_questions'], 1):.1f}"
            )
            
            keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="admin_dialogs")]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                message_text,
                parse_mode="HTML",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка получения статистики диалогов: {e}")
        await query.edit_message_text("❌ Ошибка получения статистики")


# Создание callback handlers
from telegram.ext import CallbackQueryHandler

admin_dialogs_callback = CallbackQueryHandler(admin_dialogs_handler, pattern="^admin_dialogs$")
create_dialog_callback = CallbackQueryHandler(create_dialog_handler, pattern="^create_dialog$")
edit_dialog_select_callback = CallbackQueryHandler(edit_dialog_select_handler, pattern="^edit_dialog_select$")
edit_dialog_callback = CallbackQueryHandler(edit_dialog_handler, pattern="^edit_dialog_")
delete_dialog_select_callback = CallbackQueryHandler(delete_dialog_select_handler, pattern="^delete_dialog_select$")
confirm_delete_dialog_callback = CallbackQueryHandler(confirm_delete_dialog_handler, pattern="^delete_dialog_")
execute_delete_dialog_callback = CallbackQueryHandler(execute_delete_dialog_handler, pattern="^confirm_delete_dialog_")
dialog_stats_callback = CallbackQueryHandler(dialog_stats_handler, pattern="^dialog_stats$")
