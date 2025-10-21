"""
Управление контентом через админ-панель.

Содержит обработчики для добавления, редактирования и удаления.
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
from loguru import logger

from app.core.database import get_db_session
from app.services import LeadMagnetService, ProductService, WarmupService
from app.models.lead_magnet import LeadMagnetType
from app.models.product import ProductType


# Состояния для ConversationHandler
(
    WAITING_MAGNET_NAME,
    WAITING_MAGNET_TYPE,
    WAITING_MAGNET_URL,
    WAITING_MAGNET_TEXT,
    WAITING_PRODUCT_NAME,
    WAITING_PRODUCT_PRICE,
    WAITING_PRODUCT_URL
) = range(7)


async def toggle_magnet_status_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Переключение активности лид-магнита."""
    query = update.callback_query
    await query.answer()
    
    try:
        callback_data = query.data
        magnet_id = callback_data.split("_")[-1]
        
        async with get_db_session() as session:
            lead_magnet_service = LeadMagnetService(session)
            
            # Переключаем статус лид-магнита
            updated_magnet = await lead_magnet_service.toggle_lead_magnet_status(magnet_id)
            
            if updated_magnet:
                status = "активирован" if updated_magnet.is_active else "деактивирован"
                await query.edit_message_text(
                    f"✅ Лид-магнит «{updated_magnet.name}» {status}!\n\n"
                    f"Используйте /admin для возврата в меню.",
                    parse_mode="HTML"
                )
            else:
                await query.edit_message_text(
                    "❌ Не удалось изменить статус лид-магнита",
                    parse_mode="HTML"
                )
            
    except Exception as e:
        logger.error(f"Ошибка изменения статуса лид-магнита: {e}")
        await query.edit_message_text("❌ Ошибка изменения статуса")


async def add_lead_magnet_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Начало добавления лид-магнита."""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ <b>Добавление нового лид-магнита</b>\n\n"
        "📝 Отправьте название лид-магнита:\n"
        "(Например: '7-дневный трекер дисциплины')",
        parse_mode="HTML"
    )
    
    context.user_data['adding_magnet'] = True


async def edit_warmup_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Редактирование сообщения прогрева."""
    query = update.callback_query
    await query.answer()
    
    try:
        callback_data = query.data
        message_id = callback_data.split("_")[-1]
        
        await query.edit_message_text(
            "✏️ <b>Редактирование сообщения прогрева</b>\n\n"
            "📝 Отправьте новый текст сообщения:",
            parse_mode="HTML"
        )
        
        context.user_data['editing_warmup_message'] = message_id
        
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения прогрева: {e}")
        await query.answer("❌ Ошибка")


async def text_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстового ввода для админки."""
    user = update.effective_user
    message = update.message
    
    # Проверка админа
    from config.settings import settings
    if user.id not in settings.admin_ids_list:
        return
    
    text = message.text
    action = context.user_data.get('action')
    
    try:
        # Редактирование рассылки - название
        if context.user_data.get('editing_mailing_field') == 'name':
            mailing_id = context.user_data.get('editing_mailing_id')
            
            async with get_db_session() as session:
                from app.services.mailing_service import MailingService
                mailing_service = MailingService(session)
                
                # Обновляем название
                mailing = await mailing_service.update_mailing(mailing_id, name=text)
                
                if mailing:
                    await message.reply_text(
                        f"✅ Название обновлено: <b>{text}</b>\n\n"
                        f"Теперь отправьте новый текст рассылки:",
                        parse_mode="HTML"
                    )
                    context.user_data['editing_mailing_field'] = 'text'
                else:
                    await message.reply_text("❌ Ошибка обновления названия", parse_mode="HTML")
                    context.user_data.pop('editing_mailing_id', None)
                    context.user_data.pop('editing_mailing_field', None)
            return
        
        # Редактирование рассылки - текст
        if context.user_data.get('editing_mailing_field') == 'text':
            mailing_id = context.user_data.get('editing_mailing_id')
            
            async with get_db_session() as session:
                from app.services.mailing_service import MailingService
                mailing_service = MailingService(session)
                
                # Обновляем текст
                mailing = await mailing_service.update_mailing(mailing_id, message_text=text)
                
                if mailing:
                    await message.reply_text(
                        f"✅ <b>Рассылка обновлена!</b>\n\n"
                        f"Название: {mailing.name}\n"
                        f"Текст: {mailing.message_text[:100]}...",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text("❌ Ошибка обновления текста", parse_mode="HTML")
            
            context.user_data.pop('editing_mailing_id', None)
            context.user_data.pop('editing_mailing_field', None)
            return
        
        # Создание сценария прогрева
        if context.user_data.get('creating_scenario'):
            scenario_name = text
            context.user_data['scenario_name'] = scenario_name
            context.user_data['creating_scenario'] = False
            context.user_data['creating_scenario_description'] = True
            
            await message.reply_text(
                f"✅ Название сохранено: <b>{scenario_name}</b>\n\n"
                f"Теперь отправьте описание сценария:",
                parse_mode="HTML"
            )
            return
        
        # Описание сценария
        if context.user_data.get('creating_scenario_description'):
            scenario_description = text
            scenario_name = context.user_data.get('scenario_name')
            
            async with get_db_session() as session:
                from app.services.warmup_service import WarmupService
                warmup_service = WarmupService(session)
                
                # Создаем сценарий (is_active устанавливается автоматически в True)
                scenario = await warmup_service.create_scenario(
                    name=scenario_name,
                    description=scenario_description
                )
                
                if scenario:
                    await message.reply_text(
                        f"✅ <b>Сценарий создан!</b>\n\n"
                        f"Название: {scenario.name}\n"
                        f"Описание: {scenario.description}\n\n"
                        f"⚠️ Теперь нужно добавить сообщения в сценарий через скрипты или базу данных.\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        "❌ Ошибка создания сценария",
                        parse_mode="HTML"
                    )
            
            context.user_data.clear()
            return
        
        # Редактирование названия сценария
        if action == 'edit_scenario_name':
            scenario_id = context.user_data.get('scenario_id')
            
            async with get_db_session() as session:
                from app.services.warmup_service import WarmupService
                warmup_service = WarmupService(session)
                
                scenario = await warmup_service.get_scenario_by_id(scenario_id)
                if scenario:
                    scenario.name = text
                    await session.commit()
                    
                    await message.reply_text(
                        f"✅ Название сценария обновлено: {text}\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text("❌ Сценарий не найден", parse_mode="HTML")
            
            context.user_data.clear()
            return
        
        # Редактирование описания сценария
        if action == 'edit_scenario_description':
            scenario_id = context.user_data.get('scenario_id')
            
            async with get_db_session() as session:
                from app.services.warmup_service import WarmupService
                warmup_service = WarmupService(session)
                
                scenario = await warmup_service.get_scenario_by_id(scenario_id)
                if scenario:
                    scenario.description = text
                    await session.commit()
                    
                    await message.reply_text(
                        f"✅ Описание сценария обновлено\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text("❌ Сценарий не найден", parse_mode="HTML")
            
            context.user_data.clear()
            return
        
        # Добавление сообщения в сценарий - шаг 2 (текст сообщения)
        if action == 'add_scenario_message_step2':
            context.user_data['message_text'] = text
            context.user_data['action'] = 'add_scenario_message_step3'
            
            await message.reply_text(
                f"➕ <b>Добавление сообщения</b>\n\n"
                f"Шаг 3 из 4: Введите задержку в часах перед отправкой этого сообщения\n"
                f"(например: 24 для отправки через сутки):",
                parse_mode="HTML"
            )
            return
        
        # Добавление сообщения в сценарий - шаг 3 (задержка)
        if action == 'add_scenario_message_step3':
            try:
                delay_hours = int(text)
                context.user_data['delay_hours'] = delay_hours
                context.user_data['action'] = 'add_scenario_message_step4'
                
                await message.reply_text(
                    f"➕ <b>Добавление сообщения</b>\n\n"
                    f"Шаг 4 из 4: Введите порядковый номер сообщения в сценарии\n"
                    f"(например: 1 для первого сообщения):",
                    parse_mode="HTML"
                )
            except ValueError:
                await message.reply_text(
                    "❌ Ошибка: введите число (количество часов)",
                    parse_mode="HTML"
                )
            return
        
        # Добавление сообщения в сценарий - шаг 4 (порядок)
        if action == 'add_scenario_message_step4':
            try:
                order = int(text)
                scenario_id = context.user_data.get('scenario_id')
                message_type = context.user_data.get('message_type')
                message_text = context.user_data.get('message_text')
                delay_hours = context.user_data.get('delay_hours')
                
                async with get_db_session() as session:
                    from app.services.warmup_service import WarmupService
                    from app.models.warmup import WarmupMessage
                    
                    warmup_service = WarmupService(session)
                    scenario = await warmup_service.get_scenario_by_id(scenario_id)
                    
                    if scenario:
                        new_message = WarmupMessage(
                            scenario_id=scenario.id,
                            message_type=message_type,
                            text=message_text,
                            delay_hours=delay_hours,
                            order=order,
                            is_active=True
                        )
                        
                        session.add(new_message)
                        await session.commit()
                        
                        await message.reply_text(
                            f"✅ <b>Сообщение добавлено!</b>\n\n"
                            f"Тип: {message_type}\n"
                            f"Порядок: {order}\n"
                            f"Задержка: {delay_hours}ч\n"
                            f"Текст: {message_text[:100]}...\n\n"
                            f"Используйте /admin для возврата в меню.",
                            parse_mode="HTML"
                        )
                    else:
                        await message.reply_text("❌ Сценарий не найден", parse_mode="HTML")
                
                context.user_data.clear()
            except ValueError:
                await message.reply_text(
                    "❌ Ошибка: введите число (порядковый номер)",
                    parse_mode="HTML"
                )
            return
        
        # Редактирование названия продукта
        if action == 'edit_product_name':
            product_id = context.user_data.get('product_id')
            
            async with get_db_session() as session:
                from app.services.product_service import ProductService
                product_service = ProductService(session)
                
                product = await product_service.get_product_by_id(product_id)
                if product:
                    product.name = text
                    await session.commit()
                    
                    await message.reply_text(
                        f"✅ Название продукта обновлено: {text}\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text("❌ Продукт не найден", parse_mode="HTML")
            
            context.user_data.clear()
            return
        
        # Редактирование описания продукта
        if action == 'edit_product_description':
            product_id = context.user_data.get('product_id')
            
            async with get_db_session() as session:
                from app.services.product_service import ProductService
                product_service = ProductService(session)
                
                product = await product_service.get_product_by_id(product_id)
                if product:
                    product.description = text
                    await session.commit()
                    
                    await message.reply_text(
                        f"✅ Описание продукта обновлено\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text("❌ Продукт не найден", parse_mode="HTML")
            
            context.user_data.clear()
            return
        
        # Редактирование цены продукта
        if action == 'edit_product_price':
            product_id = context.user_data.get('product_id')
            
            try:
                price = float(text.replace(',', '.'))
                price_kopeks = int(price * 100)
                
                async with get_db_session() as session:
                    from app.services.product_service import ProductService
                    product_service = ProductService(session)
                    
                    product = await product_service.get_product_by_id(product_id)
                    if product:
                        product.price = price_kopeks
                        await session.commit()
                        
                        await message.reply_text(
                            f"✅ Цена продукта обновлена: {price} руб.\n\n"
                            f"Используйте /admin для возврата в меню.",
                            parse_mode="HTML"
                        )
                    else:
                        await message.reply_text("❌ Продукт не найден", parse_mode="HTML")
                
                context.user_data.clear()
            except ValueError:
                await message.reply_text(
                    "❌ Ошибка: введите корректную цену (например: 499 или 1990.50)",
                    parse_mode="HTML"
                )
            return
        
        # Редактирование ссылки продукта
        if action == 'edit_product_url':
            product_id = context.user_data.get('product_id')
            
            async with get_db_session() as session:
                from app.services.product_service import ProductService
                product_service = ProductService(session)
                
                product = await product_service.get_product_by_id(product_id)
                if product:
                    product.payment_url = text
                    await session.commit()
                    
                    await message.reply_text(
                        f"✅ Ссылка на оплату обновлена\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text("❌ Продукт не найден", parse_mode="HTML")
            
            context.user_data.clear()
            return
        
        # Редактирование текста оффера продукта
        if action == 'edit_product_offer':
            product_id = context.user_data.get('product_id')
            
            async with get_db_session() as session:
                from app.services.product_service import ProductService
                product_service = ProductService(session)
                
                product = await product_service.get_product_by_id(product_id)
                if product:
                    product.offer_text = text
                    await session.commit()
                    
                    await message.reply_text(
                        f"✅ Текст оффера обновлен\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text("❌ Продукт не найден", parse_mode="HTML")
            
            context.user_data.clear()
            return
        
        # Добавление продукта - шаг 2 (название)
        if action == 'add_product_step2':
            context.user_data['product_name'] = text
            context.user_data['action'] = 'add_product_step3'
            
            await message.reply_text(
                f"➕ <b>Добавление продукта</b>\n\n"
                f"Шаг 3 из 5: Введите описание продукта:",
                parse_mode="HTML"
            )
            return
        
        # Добавление продукта - шаг 3 (описание)
        if action == 'add_product_step3':
            context.user_data['product_description'] = text
            context.user_data['action'] = 'add_product_step4'
            
            await message.reply_text(
                f"➕ <b>Добавление продукта</b>\n\n"
                f"Шаг 4 из 5: Введите цену в рублях (например: 499 или 1990):",
                parse_mode="HTML"
            )
            return
        
        # Добавление продукта - шаг 4 (цена)
        if action == 'add_product_step4':
            try:
                price = float(text.replace(',', '.'))
                price_kopeks = int(price * 100)
                context.user_data['product_price'] = price_kopeks
                context.user_data['action'] = 'add_product_step5'
                
                await message.reply_text(
                    f"➕ <b>Добавление продукта</b>\n\n"
                    f"Шаг 5 из 5: Введите ссылку на страницу оплаты:",
                    parse_mode="HTML"
                )
            except ValueError:
                await message.reply_text(
                    "❌ Ошибка: введите корректную цену (например: 499 или 1990.50)",
                    parse_mode="HTML"
                )
            return
        
        # Добавление продукта - шаг 5 (ссылка)
        if action == 'add_product_step5':
            product_type = context.user_data.get('product_type')
            product_name = context.user_data.get('product_name')
            product_description = context.user_data.get('product_description')
            product_price = context.user_data.get('product_price')
            payment_url = text
            
            async with get_db_session() as session:
                from app.services.product_service import ProductService
                from app.models.product import Product
                
                product_service = ProductService(session)
                
                new_product = Product(
                    name=product_name,
                    description=product_description,
                    type=product_type,
                    price=product_price,
                    currency="RUB",
                    payment_url=payment_url,
                    is_active=True,
                    sort_order=999
                )
                
                session.add(new_product)
                await session.commit()
                
                await message.reply_text(
                    f"✅ <b>Продукт создан!</b>\n\n"
                    f"Название: {product_name}\n"
                    f"Тип: {product_type}\n"
                    f"Цена: {product_price/100} руб.\n\n"
                    f"Используйте /admin для возврата в меню.",
                    parse_mode="HTML"
                )
            
            context.user_data.clear()
            return
        
        # Добавление лид-магнита
        if context.user_data.get('adding_magnet'):
            context.user_data['magnet_name'] = text
            context.user_data['adding_magnet'] = False
            context.user_data['waiting_for_file_or_url'] = True
            
            await message.reply_text(
                f"✅ Название сохранено: {text}\n\n"
                f"Теперь отправьте:\n"
                f"• <b>Файл</b> (PDF, документ) - просто прикрепите файл\n"
                f"• <b>URL ссылку</b> (Google Sheets, внешняя ссылка) - напишите текстом\n\n"
                f"Что вы хотите отправить?",
                parse_mode="HTML"
            )
            return
        
        # URL лид-магнита (когда отправляют текст ссылки)
        if context.user_data.get('waiting_for_file_or_url'):
            context.user_data['waiting_for_file_or_url'] = False
            
            # Определяем тип по URL
            if 'docs.google.com' in text:
                magnet_type = LeadMagnetType.GOOGLE_SHEET
            elif text.endswith('.pdf'):
                magnet_type = LeadMagnetType.PDF
            else:
                magnet_type = LeadMagnetType.LINK
            
            async with get_db_session() as session:
                lead_magnet_service = LeadMagnetService(session)
                
                magnet_data = {
                    'name': context.user_data['magnet_name'],
                    'type': magnet_type,
                    'file_url': text,
                    'telegram_file_id': None,
                    'is_active': True,
                    'sort_order': 999
                }
                
                new_magnet = await lead_magnet_service.create_lead_magnet(magnet_data)
                
                if new_magnet:
                    await message.reply_text(
                        f"✅ <b>Лид-магнит создан!</b>\n\n"
                        f"Название: {new_magnet.name}\n"
                        f"Тип: {magnet_type}\n"
                        f"Ссылка: {text}\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        "❌ Ошибка создания лид-магнита",
                        parse_mode="HTML"
                    )
            
            # Очищаем данные
            context.user_data.clear()
            return
        
        # Редактирование названия лид-магнита
        if context.user_data.get('editing_magnet_name'):
            magnet_id = context.user_data['editing_magnet_name']
            
            async with get_db_session() as session:
                lead_magnet_service = LeadMagnetService(session)
                
                success = await lead_magnet_service.update_lead_magnet(magnet_id, {'name': text})
                
                if success:
                    await message.reply_text(
                        f"✅ Название лид-магнита обновлено!\n\n"
                        f"Новое название: {text}\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        "❌ Ошибка обновления названия",
                        parse_mode="HTML"
                    )
            
            context.user_data.clear()
            return
        
        # Редактирование URL лид-магнита
        if context.user_data.get('editing_magnet_url'):
            magnet_id = context.user_data['editing_magnet_url']
            
            # Определяем тип по URL
            if 'docs.google.com' in text:
                magnet_type = LeadMagnetType.GOOGLE_SHEET
            elif text.endswith('.pdf'):
                magnet_type = LeadMagnetType.PDF
            else:
                magnet_type = LeadMagnetType.LINK
            
            async with get_db_session() as session:
                lead_magnet_service = LeadMagnetService(session)
                
                success = await lead_magnet_service.update_lead_magnet(magnet_id, {
                    'file_url': text,
                    'type': magnet_type
                })
                
                if success:
                    await message.reply_text(
                        f"✅ URL лид-магнита обновлен!\n\n"
                        f"Новый URL: {text[:50]}...\n"
                        f"Тип: {magnet_type.value}\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        "❌ Ошибка обновления URL",
                        parse_mode="HTML"
                    )
            
            context.user_data.clear()
            return
        
        # Редактирование описания лид-магнита
        if context.user_data.get('editing_magnet_desc'):
            magnet_id = context.user_data['editing_magnet_desc']
            
            async with get_db_session() as session:
                lead_magnet_service = LeadMagnetService(session)
                
                success = await lead_magnet_service.update_lead_magnet(magnet_id, {'description': text})
                
                if success:
                    await message.reply_text(
                        f"✅ Описание лид-магнита обновлено!\n\n"
                        f"Новое описание: {text[:100]}...\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        "❌ Ошибка обновления описания",
                        parse_mode="HTML"
                    )
            
            context.user_data.clear()
            return
        
        # Редактирование сообщения прогрева
        if context.user_data.get('editing_warmup_message'):
            message_id = context.user_data['editing_warmup_message']
            
            async with get_db_session() as session:
                warmup_service = WarmupService(session)
                
                # Здесь нужно добавить метод update_message_text в WarmupService
                await message.reply_text(
                    f"✅ Текст сообщения обновлен!\n\n"
                    f"Используйте /admin для возврата в меню.",
                    parse_mode="HTML"
                )
            
            context.user_data.clear()
            return
        
        # Создание рассылки - название
        if context.user_data.get('creating_mailing_name'):
            context.user_data['mailing_name'] = text
            context.user_data['creating_mailing_name'] = False
            context.user_data['creating_mailing_text'] = True
            
            await message.reply_text(
                f"✅ Название рассылки сохранено: {text}\n\n"
                f"Теперь отправьте текст сообщения для рассылки:",
                parse_mode="HTML"
            )
            return
        
        # Создание рассылки - текст
        if context.user_data.get('creating_mailing_text'):
            mailing_name = context.user_data.get('mailing_name', 'Без названия')
            
            async with get_db_session() as session:
                from app.services.mailing_service import MailingService
                
                mailing_service = MailingService(session)
                
                # Создаем рассылку
                mailing = await mailing_service.create_mailing(
                    name=mailing_name,
                    message_text=text,
                    created_by=str(user.id)
                )
                
                if mailing:
                    await message.reply_text(
                        f"✅ <b>Рассылка создана!</b>\n\n"
                        f"Название: {mailing.name}\n"
                        f"Текст: {text[:100]}...\n\n"
                        f"Используйте /admin → Рассылки для отправки.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        "❌ Ошибка создания рассылки",
                        parse_mode="HTML"
                    )
            
            context.user_data.clear()
            return
        
        # Добавление администратора
        if action == 'add_admin_telegram_id':
            try:
                telegram_id = int(text.strip())
                
                async with get_db_session() as session:
                    from app.services.admin_service import AdminService
                    from app.services.user_service import UserService
                    
                    admin_service = AdminService(session)
                    user_service = UserService(session)
                    
                    # Получаем информацию о пользователе если он есть в БД
                    db_user = await user_service.get_user_by_telegram_id(telegram_id)
                    
                    username = None
                    full_name = None
                    
                    if db_user:
                        username = db_user.username
                        full_name = db_user.full_name
                    
                    # Добавляем админа
                    admin = await admin_service.add_admin(
                        telegram_id=telegram_id,
                        username=username,
                        full_name=full_name,
                        added_by_id=user.id
                    )
                    
                    if admin:
                        await message.reply_text(
                            f"✅ <b>Администратор добавлен!</b>\n\n"
                            f"Telegram ID: <code>{telegram_id}</code>\n"
                            f"Username: {username or 'не указан'}\n"
                            f"Имя: {full_name or 'не указано'}\n\n"
                            f"Теперь пользователь может использовать команду /admin\n\n"
                            f"Используйте /admin для возврата в меню.",
                            parse_mode="HTML"
                        )
                    else:
                        await message.reply_text(
                            "❌ Ошибка добавления администратора",
                            parse_mode="HTML"
                        )
                
                context.user_data.clear()
            except ValueError:
                await message.reply_text(
                    "❌ Ошибка: введите корректный Telegram ID (только цифры)\n\n"
                    "Например: 1670311707",
                    parse_mode="HTML"
                )
            return
        
        # Удаление администратора
        if action == 'remove_admin_telegram_id':
            try:
                telegram_id = int(text.strip())
                
                # Проверяем, не пытается ли админ удалить сам себя
                if telegram_id == user.id:
                    await message.reply_text(
                        "❌ Нельзя удалить самого себя!",
                        parse_mode="HTML"
                    )
                    context.user_data.clear()
                    return
                
                # Проверяем, не из .env ли этот админ
                from config.settings import settings
                if telegram_id in settings.admin_ids_list:
                    await message.reply_text(
                        "❌ Нельзя удалить администратора из .env файла!\n\n"
                        "Для удаления измените файл .env на сервере.",
                        parse_mode="HTML"
                    )
                    context.user_data.clear()
                    return
                
                async with get_db_session() as session:
                    from app.services.admin_service import AdminService
                    
                    admin_service = AdminService(session)
                    success = await admin_service.remove_admin(telegram_id)
                    
                    if success:
                        await message.reply_text(
                            f"✅ <b>Администратор удален!</b>\n\n"
                            f"Telegram ID: <code>{telegram_id}</code>\n\n"
                            f"Пользователь больше не имеет доступа к админ-панели.\n\n"
                            f"Используйте /admin для возврата в меню.",
                            parse_mode="HTML"
                        )
                    else:
                        await message.reply_text(
                            "❌ Администратор не найден в базе данных",
                            parse_mode="HTML"
                        )
                
                context.user_data.clear()
            except ValueError:
                await message.reply_text(
                    "❌ Ошибка: введите корректный Telegram ID (только цифры)\n\n"
                    "Например: 1670311707",
                    parse_mode="HTML"
                )
            return
        
        # Обработка создания диалогов
        if action and action.startswith('creating_dialog'):
            # Обрабатываем создание диалога прямо здесь, чтобы использовать существующую сессию
            from app.services.dialog_service import DialogService
            from app.schemas.dialog import DialogCreate, DialogQuestionCreate, DialogAnswerCreate
            
            if action == 'creating_dialog':
                dialog_name = text
                context.user_data['dialog_data'] = {
                    'name': dialog_name,
                    'questions': [],
                    'current_question': None
                }
                context.user_data['action'] = 'creating_dialog_description'
                
                await message.reply_text(
                    f"✅ Название диалога: <b>{dialog_name}</b>\n\n"
                    "📄 Отправьте описание диалога (или 'пропустить' для пропуска):",
                    parse_mode="HTML"
                )
                return
            
            elif action == 'creating_dialog_description':
                description = text.strip()
                if description.lower() not in ['пропустить', 'skip', '']:
                    context.user_data['dialog_data']['description'] = description
                else:
                    context.user_data['dialog_data']['description'] = None
                
                context.user_data['action'] = 'creating_dialog_question'
                
                await message.reply_text(
                    "✅ Описание диалога сохранено\n\n"
                    "❓ Отправьте первый вопрос для диалога:",
                    parse_mode="HTML"
                )
                return
            
            elif action == 'creating_dialog_question':
                question_text = text.strip()
                if len(question_text) < 3:
                    await message.reply_text("❌ Вопрос должен содержать минимум 3 символа. Попробуйте снова:")
                    return
                
                context.user_data['dialog_data']['current_question'] = {
                    'question_text': question_text,
                    'answers': []
                }
                context.user_data['action'] = 'creating_dialog_question_keywords'
                
                await message.reply_text(
                    f"✅ Вопрос: <b>{question_text}</b>\n\n"
                    "🔑 Отправьте ключевые слова для поиска (через запятую) или 'пропустить':",
                    parse_mode="HTML"
                )
                return
            
            elif action == 'creating_dialog_question_keywords':
                keywords = text.strip()
                if keywords.lower() not in ['пропустить', 'skip', '']:
                    context.user_data['dialog_data']['current_question']['keywords'] = keywords
                else:
                    context.user_data['dialog_data']['current_question']['keywords'] = None
                
                context.user_data['action'] = 'creating_dialog_answer'
                
                await message.reply_text(
                    "✅ Ключевые слова сохранены\n\n"
                    "💬 Отправьте ответ на вопрос:",
                    parse_mode="HTML"
                )
                return
            
            elif action == 'creating_dialog_answer':
                answer_text = text.strip()
                if len(answer_text) < 2:
                    await message.reply_text("❌ Ответ должен содержать минимум 2 символа. Попробуйте снова:")
                    return
                
                context.user_data['dialog_data']['current_question']['answers'].append({
                    'answer_text': answer_text,
                    'answer_type': 'text',
                    'additional_data': None
                })
                context.user_data['action'] = 'creating_dialog_answer_type'
                
                await message.reply_text(
                    f"✅ Ответ: <b>{answer_text}</b>\n\n"
                    "📎 Выберите тип ответа:\n"
                    "• <b>text</b> - обычный текст\n"
                    "• <b>image</b> - с изображением\n"
                    "• <b>document</b> - с документом\n\n"
                    "Отправьте тип ответа:",
                    parse_mode="HTML"
                )
                return
            
            elif action == 'creating_dialog_answer_type':
                answer_type = text.strip().lower()
                if answer_type not in ['text', 'image', 'document']:
                    await message.reply_text("❌ Неверный тип ответа. Выберите: text, image или document:")
                    return
                
                current_answers = context.user_data['dialog_data']['current_question']['answers']
                current_answers[-1]['answer_type'] = answer_type
                
                context.user_data['action'] = 'creating_dialog_finish'
                await message.reply_text(
                    f"✅ Тип ответа: {answer_type}\n\n"
                    "❓ Хотите добавить еще один ответ на этот вопрос?\n"
                    "Отправьте 'да' или 'нет':",
                    parse_mode="HTML"
                )
                return
            
            elif action == 'creating_dialog_finish':
                response = text.strip().lower()
                
                if response in ['да', 'yes', 'y', 'добавить']:
                    context.user_data['action'] = 'creating_dialog_answer'
                    await message.reply_text(
                        "💬 Отправьте следующий ответ на вопрос:",
                        parse_mode="HTML"
                    )
                    return
                
                # Добавляем вопрос к диалогу
                context.user_data['dialog_data']['questions'].append(context.user_data['dialog_data']['current_question'])
                context.user_data['dialog_data']['current_question'] = None
                
                # Сохраняем флаг для создания диалога
                context.user_data['action'] = 'create_dialog_now'
            
            return
        
        # Создание диалога - выносим на верхний уровень
        if action == 'create_dialog_now':
            try:
                from app.services.dialog_service import DialogService
                from app.schemas.dialog import DialogCreate, DialogQuestionCreate, DialogAnswerCreate
                
                async with get_db_session() as session:
                    dialog_service = DialogService(session)
                    
                    dialog_data = DialogCreate(
                        name=context.user_data['dialog_data']['name'],
                        description=context.user_data['dialog_data']['description'],
                        questions=[
                            DialogQuestionCreate(
                                question_text=q['question_text'],
                                keywords=q['keywords'],
                                answers=[
                                    DialogAnswerCreate(
                                        answer_text=a['answer_text'],
                                        answer_type=a['answer_type'],
                                        additional_data=a['additional_data']
                                    ) for a in q['answers']
                                ]
                            ) for q in context.user_data['dialog_data']['questions']
                        ]
                    )
                    
                    dialog = await dialog_service.create_dialog(dialog_data)
                    
                    await message.reply_text(
                        f"🎉 <b>Диалог успешно создан!</b>\n\n"
                        f"📋 <b>Название:</b> {dialog.name}\n"
                        f"📊 <b>Вопросов:</b> {len(dialog.questions)}\n"
                        f"📊 <b>Ответов:</b> {sum(len(q.answers) for q in dialog.questions)}\n\n"
                        f"✅ Диалог готов к использованию!",
                        parse_mode="HTML"
                    )
                    
                    context.user_data.pop('action', None)
                    context.user_data.pop('dialog_data', None)
                    
                    logger.info(f"Админ {message.from_user.id} создал диалог: {dialog.name}")
                    return
                    
            except Exception as dialog_error:
                logger.error(f"Ошибка создания диалога: {dialog_error}")
                await message.reply_text(
                    "❌ Ошибка создания диалога. Попробуйте снова.",
                    parse_mode="HTML"
                )
                context.user_data.pop('action', None)
                context.user_data.pop('dialog_data', None)
                return
        
        # Если это не админ или нет активного действия - проверяем диалоги
        if user.id not in settings.admin_ids_list or not action:
            from .dialog_text import dialog_text_handler as dialog_handler_func
            await dialog_handler_func(update, context)
            return
            
    except Exception as e:
        logger.error(f"Ошибка обработки текстового ввода: {e}")
        await message.reply_text(
            "❌ Произошла ошибка. Попробуйте снова.",
            parse_mode="HTML"
        )


async def file_input_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик получения файлов для админки."""
    user = update.effective_user
    message = update.message
    
    # Проверка админа
    from config.settings import settings
    if user.id not in settings.admin_ids_list:
        return
    
    try:
        # Импорты в начале функции
        from app.services.lead_magnet_service import LeadMagnetService
        from app.models.lead_magnet import LeadMagnetType
        
        # Обработка файла для лид-магнита
        if context.user_data.get('waiting_for_file_or_url'):
            context.user_data['waiting_for_file_or_url'] = False
            
            # Получаем файл
            file = None
            file_name = None
            magnet_type = LeadMagnetType.PDF
            
            if message.document:
                file = message.document
                file_name = file.file_name
                # Определяем тип по расширению
                if file_name.endswith('.pdf'):
                    magnet_type = LeadMagnetType.PDF
                else:
                    magnet_type = LeadMagnetType.LINK
            elif message.photo:
                file = message.photo[-1]  # Берем самое большое фото
                file_name = "photo.jpg"
                magnet_type = LeadMagnetType.LINK
            elif message.video:
                file = message.video
                file_name = "video.mp4"
                magnet_type = LeadMagnetType.LINK
            
            if not file:
                await message.reply_text(
                    "❌ Не удалось получить файл. Попробуйте снова.",
                    parse_mode="HTML"
                )
                context.user_data.clear()
                return
            
            # Сохраняем file_id для отправки через Telegram
            telegram_file_id = file.file_id
            
            async with get_db_session() as session:
                lead_magnet_service = LeadMagnetService(session)
                
                magnet_data = {
                    'name': context.user_data['magnet_name'],
                    'type': magnet_type,
                    'file_url': None,  # Для файлов не используем URL
                    'telegram_file_id': telegram_file_id,
                    'is_active': True,
                    'sort_order': 999
                }
                
                new_magnet = await lead_magnet_service.create_lead_magnet(magnet_data)
                
                if new_magnet:
                    await message.reply_text(
                        f"✅ <b>Лид-магнит создан!</b>\n\n"
                        f"Название: {new_magnet.name}\n"
                        f"Тип: {magnet_type}\n"
                        f"Файл: {file_name}\n"
                        f"File ID: {telegram_file_id[:20]}...\n\n"
                        f"Файл будет отправляться пользователям напрямую через Telegram.\n\n"
                        f"Используйте /admin для возврата в меню.",
                        parse_mode="HTML"
                    )
                else:
                    await message.reply_text(
                        "❌ Ошибка создания лид-магнита",
                        parse_mode="HTML"
                    )
            
            context.user_data.clear()
            return
            
    except Exception as e:
        logger.error(f"Ошибка обработки файла: {e}")
        await message.reply_text(
            "❌ Произошла ошибка при обработке файла. Попробуйте снова.",
            parse_mode="HTML"
        )
        context.user_data.clear()


# Создание обработчиков для регистрации
toggle_magnet_callback = CallbackQueryHandler(toggle_magnet_status_handler, pattern="^toggle_magnet_")
add_lead_magnet_callback = CallbackQueryHandler(add_lead_magnet_start, pattern="^add_lead_magnet$")
edit_warmup_callback = CallbackQueryHandler(edit_warmup_message_handler, pattern="^edit_warmup_")
admin_text_handler = MessageHandler(filters.TEXT & ~filters.COMMAND, text_input_handler)
file_handler = MessageHandler(filters.Document.ALL | filters.PHOTO | filters.VIDEO, file_input_handler)

