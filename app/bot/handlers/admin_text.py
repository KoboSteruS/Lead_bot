"""
Обработчики текстовых сообщений для админ панели.

Обрабатывает ввод данных в формах создания и редактирования.
"""

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters
from loguru import logger

from app.services import LeadMagnetService
from app.core.database import get_database


async def admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений в админ панели."""
    try:
        # Проверяем, что пользователь в процессе создания лид магнита, сценария прогрева, текстового шаблона или редактирования сценария
        if ('creating_lead_magnet' not in context.user_data and 
            'creating_warmup_scenario' not in context.user_data and
            'creating_message_template' not in context.user_data and
            'editing_warmup_scenario' not in context.user_data):
            return
        
        # Проверяем, что сообщение еще не обработано
        if hasattr(update.message, '_admin_processed'):
            return
        
        text = update.message.text.strip()
        
        if not text:
            await update.message.reply_text("❌ Пожалуйста, введите текст.")
            return
        
        # Обрабатываем создание лид магнита
        if 'creating_lead_magnet' in context.user_data:
            creating_data = context.user_data['creating_lead_magnet']
            current_step = creating_data.get('step', 'name')
            
            if current_step == 'name':
                await _handle_lead_magnet_name_input(update, context, text)
            elif current_step == 'description':
                await _handle_lead_magnet_description_input(update, context, text)
            elif current_step == 'file_url':
                await _handle_lead_magnet_file_url_input(update, context, text)
            elif current_step == 'message':
                await _handle_lead_magnet_message_input(update, context, text)
            else:
                await update.message.reply_text("❌ Неизвестный шаг создания лид магнита.")
        
        # Обрабатываем создание сценария прогрева
        elif 'creating_warmup_scenario' in context.user_data:
            creating_data = context.user_data['creating_warmup_scenario']
            current_step = creating_data.get('step', 'name')
            
            if current_step == 'name':
                await _handle_warmup_scenario_name_input(update, context, text)
            elif current_step == 'description':
                await _handle_warmup_scenario_description_input(update, context, text)
            else:
                await update.message.reply_text("❌ Неизвестный шаг создания сценария прогрева.")
        
        # Обрабатываем создание текстового шаблона
        elif 'creating_message_template' in context.user_data:
            creating_data = context.user_data['creating_message_template']
            current_step = creating_data.get('step', 'name')
            
            if current_step == 'name':
                await _handle_message_template_name_input(update, context, text)
            elif current_step == 'content':
                await _handle_message_template_content_input(update, context, text)
            elif current_step == 'category':
                await _handle_message_template_category_input(update, context, text)
            else:
                await update.message.reply_text("❌ Неизвестный шаг создания текстового шаблона.")
        
        # Обрабатываем редактирование сценария прогрева
        elif 'editing_warmup_scenario' in context.user_data:
            editing_data = context.user_data['editing_warmup_scenario']
            edit_type = editing_data.get('type', 'name')
            
            if edit_type == 'name':
                await _handle_warmup_edit_name_input(update, context, text)
            elif edit_type == 'description':
                await _handle_warmup_edit_desc_input(update, context, text)
            else:
                await update.message.reply_text("❌ Неизвестный тип редактирования сценария.")
            
    except Exception as e:
        logger.error(f"Ошибка обработки текстового сообщения в админ панели: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке сообщения.")


async def _handle_lead_magnet_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода названия лид магнита."""
    try:
        # Сохраняем название
        context.user_data['creating_lead_magnet']['name'] = text
        context.user_data['creating_lead_magnet']['step'] = 'description'
        
        await update.message.reply_text(
            f"✅ <b>Название сохранено:</b> {text}\n\n"
            "📝 <b>Следующий шаг: Описание</b>\n\n"
            "Введите описание лид магнита или нажмите кнопку для пропуска.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для следующего шага
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить описание", callback_data="admin_lead_magnet_create_file_url")],
            [InlineKeyboardButton("🔙 Назад к названию", callback_data="admin_lead_magnet_create_name")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 <b>Что включить в описание:</b>\n"
            "• Что получит пользователь\n"
            "• Как это поможет в развитии\n"
            "• Формат и объем материала\n"
            "• Время на изучение",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки названия: {e}")
        await update.message.reply_text("❌ Ошибка сохранения названия.")


async def _handle_lead_magnet_description_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода описания лид магнита."""
    try:
        # Сохраняем описание
        context.user_data['creating_lead_magnet']['description'] = text
        context.user_data['creating_lead_magnet']['step'] = 'file_url'
        
        await update.message.reply_text(
            f"✅ <b>Описание сохранено</b>\n\n"
            "🔗 <b>Следующий шаг: Ссылка на файл</b>\n\n"
            "Введите ссылку на файл или нажмите кнопку для пропуска.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для следующего шага
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить ссылку", callback_data="admin_lead_magnet_create_message")],
            [InlineKeyboardButton("🔙 Назад к описанию", callback_data="admin_lead_magnet_create_description")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 <b>Требования к ссылкам:</b>\n"
            "• Должна быть публично доступной\n"
            "• Для Google Drive: настройте доступ 'Кто угодно с ссылкой'\n"
            "• Для PDF: убедитесь, что файл не требует авторизации",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки описания: {e}")
        await update.message.reply_text("❌ Ошибка сохранения описания.")


async def _handle_lead_magnet_file_url_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода ссылки на файл лид магнита."""
    try:
        # Проверяем, что это похоже на ссылку
        if not (text.startswith('http://') or text.startswith('https://')):
            await update.message.reply_text(
                "❌ <b>Неверный формат ссылки</b>\n\n"
                "Ссылка должна начинаться с http:// или https://\n"
                "Попробуйте еще раз или пропустите этот шаг.",
                parse_mode='HTML'
            )
            return
        
        # Сохраняем ссылку
        context.user_data['creating_lead_magnet']['file_url'] = text
        context.user_data['creating_lead_magnet']['step'] = 'message'
        
        await update.message.reply_text(
            f"✅ <b>Ссылка сохранена</b>\n\n"
            "💬 <b>Следующий шаг: Текст сообщения</b>\n\n"
            "Введите текст, который будет показан при выдаче лид магнита.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для следующего шага
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Использовать шаблон", callback_data="admin_lead_magnet_create_confirm")],
            [InlineKeyboardButton("🔙 Назад к ссылке", callback_data="admin_lead_magnet_create_file_url")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 <b>Что включить в сообщение:</b>\n"
            "• Благодарность за интерес\n"
            "• Краткое описание ценности\n"
            "• Инструкции по использованию\n"
            "• Призыв к действию",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки ссылки: {e}")
        await update.message.reply_text("❌ Ошибка сохранения ссылки.")


async def _handle_lead_magnet_message_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода текста сообщения лид магнита."""
    try:
        # Сохраняем текст сообщения
        context.user_data['creating_lead_magnet']['message_text'] = text
        context.user_data['creating_lead_magnet']['step'] = 'confirm'
        
        await update.message.reply_text(
            "✅ <b>Текст сообщения сохранен</b>\n\n"
            "🎯 <b>Все данные собраны!</b>\n\n"
            "Теперь вы можете просмотреть и подтвердить создание лид магнита.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для подтверждения
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить создание", callback_data="admin_lead_magnet_create_confirm")],
            [InlineKeyboardButton("🔙 Назад к сообщению", callback_data="admin_lead_magnet_create_message")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_leadmagnets")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 <b>Следующий шаг:</b> Просмотр и подтверждение всех данных",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки сообщения: {e}")
        await update.message.reply_text("❌ Ошибка сохранения текста сообщения.")


# Функции для создания сценариев прогрева

async def _handle_warmup_scenario_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода названия сценария прогрева."""
    try:
        # Сохраняем название
        context.user_data['creating_warmup_scenario']['name'] = text
        context.user_data['creating_warmup_scenario']['step'] = 'description'
        
        await update.message.reply_text(
            f"✅ <b>Название сценария сохранено:</b> {text}\n\n"
            "📝 <b>Следующий шаг: Описание</b>\n\n"
            "Введите описание сценария или нажмите кнопку для пропуска.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для следующего шага
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("⏭️ Пропустить описание", callback_data="admin_warmup_create_scenario_final")],
            [InlineKeyboardButton("🔙 Назад к названию", callback_data="admin_warmup_create_scenario")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_warmup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 <b>Что включить в описание:</b>\n"
            "• Цель и задачи сценария\n"
            "• Целевая аудитория\n"
            "• Ожидаемые результаты\n"
            "• Особенности и нюансы",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки названия сценария: {e}")
        await update.message.reply_text("❌ Ошибка сохранения названия сценария.")


async def _handle_warmup_scenario_description_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода описания сценария прогрева."""
    try:
        # Сохраняем описание
        context.user_data['creating_warmup_scenario']['description'] = text
        
        await update.message.reply_text(
            "✅ <b>Описание сценария сохранено</b>\n\n"
            "🎯 <b>Все данные собраны!</b>\n\n"
            "Теперь вы можете создать сценарий прогрева.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для создания
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("✅ Создать сценарий", callback_data="admin_warmup_create_scenario_final")],
            [InlineKeyboardButton("🔙 Назад к описанию", callback_data="admin_warmup_create_scenario")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_warmup")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 <b>Следующий шаг:</b> Создание сценария с базовыми настройками",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки описания сценария: {e}")
        await update.message.reply_text("❌ Ошибка сохранения описания сценария.")


# Функции для создания текстовых шаблонов

async def _handle_message_template_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода названия текстового шаблона."""
    try:
        # Сохраняем название
        context.user_data['creating_message_template']['name'] = text
        context.user_data['creating_message_template']['step'] = 'category'
        
        await update.message.reply_text(
            f"✅ <b>Название шаблона сохранено:</b> {text}\n\n"
            "📝 <b>Следующий шаг: Категория</b>\n\n"
            "Введите категорию шаблона или выберите из предложенных.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для выбора категории
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("👋 Приветствие", callback_data="admin_messages_category_welcome")],
            [InlineKeyboardButton("❌ Ошибка", callback_data="admin_messages_category_error")],
            [InlineKeyboardButton("🔔 Уведомление", callback_data="admin_messages_category_notification")],
            [InlineKeyboardButton("📝 Системное", callback_data="admin_messages_category_system")],
            [InlineKeyboardButton("🔙 Назад к названию", callback_data="admin_messages_create")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 <b>Популярные категории:</b>\n"
            "• Приветствие - для новых пользователей\n"
            "• Ошибка - для системных ошибок\n"
            "• Уведомление - для важных событий\n"
            "• Системное - для технических сообщений",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки названия шаблона: {e}")
        await update.message.reply_text("❌ Ошибка сохранения названия шаблона.")


async def _handle_message_template_category_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода категории текстового шаблона."""
    try:
        # Сохраняем категорию
        context.user_data['creating_message_template']['category'] = text
        context.user_data['creating_message_template']['step'] = 'content'
        
        await update.message.reply_text(
            f"✅ <b>Категория сохранена:</b> {text}\n\n"
            "📝 <b>Следующий шаг: Содержимое шаблона</b>\n\n"
            "Введите текст шаблона. Можно использовать HTML-разметку для форматирования.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для следующего шага
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("💡 Примеры HTML", callback_data="admin_messages_html_examples")],
            [InlineKeyboardButton("🔙 Назад к категории", callback_data="admin_messages_create")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "💡 <b>Поддерживаемые HTML-теги:</b>\n"
            "• <b>жирный текст</b>\n"
            "• <i>курсив</i>\n"
            "• <code>моноширинный</code>\n"
            "• <pre>блок кода</pre>\n"
            "• <a href='ссылка'>ссылка</a>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки категории шаблона: {e}")
        await update.message.reply_text("❌ Ошибка сохранения категории шаблона.")


async def _handle_message_template_content_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода содержимого текстового шаблона."""
    try:
        # Сохраняем содержимое
        context.user_data['creating_message_template']['content'] = text
        
        await update.message.reply_text(
            "✅ <b>Содержимое шаблона сохранено</b>\n\n"
            "🎯 <b>Все данные собраны!</b>\n\n"
            "Теперь вы можете создать текстовый шаблон.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для создания
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("✅ Создать шаблон", callback_data="admin_messages_create_final")],
            [InlineKeyboardButton("🔙 Назад к содержимому", callback_data="admin_messages_create")],
            [InlineKeyboardButton("❌ Отменить создание", callback_data="admin_content_messages")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 <b>Следующий шаг:</b> Создание шаблона с указанными параметрами",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки содержимого шаблона: {e}")
        await update.message.reply_text("❌ Ошибка сохранения содержимого шаблона.")


# Функции для редактирования сценариев прогрева

async def _handle_warmup_edit_name_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода нового названия сценария прогрева."""
    try:
        # Получаем данные редактирования
        editing_data = context.user_data.get('editing_warmup_scenario', {})
        short_id = editing_data.get('short_id', '')
        
        if not short_id:
            await update.message.reply_text("❌ Ошибка: данные редактирования не найдены")
            return
        
        # Сохраняем новое название
        editing_data['new_name'] = text
        editing_data['step'] = 'confirm'
        
        await update.message.reply_text(
            f"✅ <b>Новое название сохранено:</b> {text}\n\n"
            "🎯 <b>Следующий шаг:</b> Подтверждение изменения\n\n"
            "Теперь вы можете подтвердить изменение названия сценария.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для подтверждения
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить изменение", callback_data=f"admin_warmup_edit_name_confirm_{short_id}")],
            [InlineKeyboardButton("🔙 Назад к редактированию", callback_data=f"admin_warmup_scenario_{short_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 <b>Подтвердите изменение названия</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки нового названия: {e}")
        await update.message.reply_text("❌ Ошибка сохранения нового названия")


async def _handle_warmup_edit_desc_input(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    """Обработка ввода нового описания сценария прогрева."""
    try:
        # Получаем данные редактирования
        editing_data = context.user_data.get('editing_warmup_scenario', {})
        short_id = editing_data.get('short_id', '')
        
        if not short_id:
            await update.message.reply_text("❌ Ошибка: данные редактирования не найдены")
            return
        
        # Сохраняем новое описание
        editing_data['new_description'] = text
        editing_data['step'] = 'confirm'
        
        await update.message.reply_text(
            "✅ <b>Новое описание сохранено</b>\n\n"
            "🎯 <b>Следующий шаг:</b> Подтверждение изменения\n\n"
            "Теперь вы можете подтвердить изменение описания сценария.",
            parse_mode='HTML'
        )
        
        # Показываем кнопки для подтверждения
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить изменение", callback_data=f"admin_warmup_edit_desc_confirm_{short_id}")],
            [InlineKeyboardButton("🔙 Назад к редактированию", callback_data=f"admin_warmup_scenario_{short_id}")]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "📋 <b>Подтвердите изменение описания</b>",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка обработки нового описания: {e}")
        await update.message.reply_text("❌ Ошибка сохранения нового описания")


# Создание обработчика текстовых сообщений для регистрации
admin_text = MessageHandler(filters.TEXT & ~filters.COMMAND, admin_text_handler)
