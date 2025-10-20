"""
Обработчики текстовых сообщений для системы диалогов.

Содержит логику поиска и ответа на вопросы пользователей.
"""

from telegram import Update
from telegram.ext import ContextTypes
from loguru import logger

from app.core.database import get_db_session
from app.services.dialog_service import DialogService
from app.schemas.dialog import DialogSearchRequest
from app.bot.utils.admin_check import is_admin


async def dialog_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений для поиска в диалогах."""
    user = update.effective_user
    message = update.message
    
    if not user or not message or not message.text:
        return
    
    # Пропускаем команды и сообщения от админов
    if message.text.startswith('/') or await is_admin(user.id):
        return
    
    try:
        # Получаем текст сообщения
        query_text = message.text.strip()
        if len(query_text) < 2:  # Слишком короткий запрос
            return
        
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            
            # Ищем релевантные диалоги
            search_request = DialogSearchRequest(query=query_text, limit=3)
            search_results = await dialog_service.search_dialogs(search_request)
            
            if not search_results:
                # Если ничего не найдено, отправляем стандартный ответ
                await message.reply_text(
                    "🤔 Извините, я не нашел подходящего ответа на ваш вопрос.\n\n"
                    "Попробуйте переформулировать вопрос или обратитесь к администратору.",
                    parse_mode="HTML"
                )
                return
            
            # Отправляем найденные ответы
            for result in search_results:
                # Отправляем каждый ответ
                for answer in result.answers:
                    if not answer.is_active:
                        continue
                    
                    try:
                        if answer.answer_type == "text":
                            # Обычный текстовый ответ
                            await message.reply_text(
                                answer.answer_text,
                                parse_mode="HTML"
                            )
                        elif answer.answer_type == "image" and answer.additional_data:
                            # Ответ с изображением
                            await message.reply_photo(
                                photo=answer.additional_data,
                                caption=answer.answer_text,
                                parse_mode="HTML"
                            )
                        elif answer.answer_type == "document" and answer.additional_data:
                            # Ответ с документом
                            await message.reply_document(
                                document=answer.additional_data,
                                caption=answer.answer_text,
                                parse_mode="HTML"
                            )
                        else:
                            # Fallback на текстовый ответ
                            await message.reply_text(
                                answer.answer_text,
                                parse_mode="HTML"
                            )
                        
                        logger.info(f"Отправлен ответ на вопрос пользователю {user.id}: {result.question.question_text[:50]}...")
                        
                    except Exception as e:
                        logger.error(f"Ошибка отправки ответа пользователю {user.id}: {e}")
                        # Отправляем текстовый ответ как fallback
                        try:
                            await message.reply_text(
                                answer.answer_text,
                                parse_mode="HTML"
                            )
                        except Exception as fallback_error:
                            logger.error(f"Ошибка fallback ответа: {fallback_error}")
            
            # Логируем поиск
            logger.info(f"Пользователь {user.id} искал: '{query_text}', найдено {len(search_results)} результатов")
            
    except Exception as e:
        logger.error(f"Ошибка обработки текстового сообщения для диалогов: {e}")
        # Не отправляем ошибку пользователю, чтобы не нарушать UX


async def dialog_admin_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик текстовых сообщений для админов при создании/редактировании диалогов."""
    user = update.effective_user
    message = update.message
    
    if not user or not message or not message.text:
        return
    
    # Проверяем права администратора
    if not await is_admin(user.id):
        return
    
    # Проверяем, есть ли активное действие
    action = context.user_data.get('action')
    if not action or not action.startswith('creating_dialog'):
        return
    
    try:
        if action == 'creating_dialog':
            await _handle_creating_dialog_name(update, context)
        elif action == 'creating_dialog_description':
            await _handle_creating_dialog_description(update, context)
        elif action == 'creating_dialog_question':
            await _handle_creating_dialog_question(update, context)
        elif action == 'creating_dialog_question_keywords':
            await _handle_creating_dialog_question_keywords(update, context)
        elif action == 'creating_dialog_answer':
            await _handle_creating_dialog_answer(update, context)
        elif action == 'creating_dialog_answer_type':
            await _handle_creating_dialog_answer_type(update, context)
        elif action == 'creating_dialog_answer_data':
            await _handle_creating_dialog_answer_data(update, context)
        elif action == 'creating_dialog_finish':
            await _handle_creating_dialog_finish(update, context)
            
    except Exception as e:
        logger.error(f"Ошибка обработки текста для создания диалога: {e}")
        await message.reply_text("❌ Произошла ошибка. Попробуйте снова.")


async def _handle_creating_dialog_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода названия диалога."""
    message = update.message
    dialog_name = message.text.strip()
    
    if len(dialog_name) < 2:
        await message.reply_text("❌ Название диалога должно содержать минимум 2 символа. Попробуйте снова:")
        return
    
    # Сохраняем название
    context.user_data['dialog_data']['name'] = dialog_name
    context.user_data['action'] = 'creating_dialog_description'
    
    await message.reply_text(
        f"✅ Название диалога: <b>{dialog_name}</b>\n\n"
        "📄 Отправьте описание диалога (или 'пропустить' для пропуска):",
        parse_mode="HTML"
    )


async def _handle_creating_dialog_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода описания диалога."""
    message = update.message
    description = message.text.strip()
    
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


async def _handle_creating_dialog_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода вопроса диалога."""
    message = update.message
    question_text = message.text.strip()
    
    if len(question_text) < 3:
        await message.reply_text("❌ Вопрос должен содержать минимум 3 символа. Попробуйте снова:")
        return
    
    # Создаем новый вопрос
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


async def _handle_creating_dialog_question_keywords(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода ключевых слов вопроса."""
    message = update.message
    keywords = message.text.strip()
    
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


async def _handle_creating_dialog_answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка ввода ответа на вопрос."""
    message = update.message
    answer_text = message.text.strip()
    
    if len(answer_text) < 2:
        await message.reply_text("❌ Ответ должен содержать минимум 2 символа. Попробуйте снова:")
        return
    
    # Создаем новый ответ
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


async def _handle_creating_dialog_answer_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка выбора типа ответа."""
    message = update.message
    answer_type = message.text.strip().lower()
    
    if answer_type not in ['text', 'image', 'document']:
        await message.reply_text("❌ Неверный тип ответа. Выберите: text, image или document:")
        return
    
    # Обновляем тип ответа
    current_answers = context.user_data['dialog_data']['current_question']['answers']
    current_answers[-1]['answer_type'] = answer_type
    
    if answer_type == 'text':
        context.user_data['action'] = 'creating_dialog_finish'
        await message.reply_text(
            "✅ Тип ответа: текст\n\n"
            "❓ Хотите добавить еще один ответ на этот вопрос?\n"
            "Отправьте 'да' или 'нет':",
            parse_mode="HTML"
        )
    else:
        context.user_data['action'] = 'creating_dialog_answer_data'
        await message.reply_text(
            f"✅ Тип ответа: {answer_type}\n\n"
            f"📎 Отправьте {'изображение' if answer_type == 'image' else 'документ'} "
            f"или file_id для {answer_type}:",
            parse_mode="HTML"
        )


async def _handle_creating_dialog_answer_data(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка дополнительных данных ответа."""
    message = update.message
    answer_type = context.user_data['dialog_data']['current_question']['answers'][-1]['answer_type']
    
    # Получаем file_id из сообщения
    file_id = None
    if message.photo:
        file_id = message.photo[-1].file_id
    elif message.document:
        file_id = message.document.file_id
    elif message.text and message.text.startswith('BAAD'):
        file_id = message.text.strip()
    
    if not file_id:
        await message.reply_text(
            f"❌ Не удалось получить {'изображение' if answer_type == 'image' else 'документ'}. "
            f"Попробуйте снова или отправьте file_id:",
            parse_mode="HTML"
        )
        return
    
    # Сохраняем file_id
    context.user_data['dialog_data']['current_question']['answers'][-1]['additional_data'] = file_id
    context.user_data['action'] = 'creating_dialog_finish'
    
    await message.reply_text(
        f"✅ {'Изображение' if answer_type == 'image' else 'Документ'} сохранен\n\n"
        "❓ Хотите добавить еще один ответ на этот вопрос?\n"
        "Отправьте 'да' или 'нет':",
        parse_mode="HTML"
    )


async def _handle_creating_dialog_finish(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Завершение создания диалога."""
    message = update.message
    response = message.text.strip().lower()
    
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
    
    # Создаем диалог
    try:
        from app.schemas.dialog import DialogCreate, DialogQuestionCreate, DialogAnswerCreate
        
        # Формируем данные для создания диалога
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
        
        async with get_db_session() as session:
            dialog_service = DialogService(session)
            dialog = await dialog_service.create_dialog(dialog_data)
            
            await message.reply_text(
                f"🎉 <b>Диалог успешно создан!</b>\n\n"
                f"📋 <b>Название:</b> {dialog.name}\n"
                f"📊 <b>Вопросов:</b> {len(dialog.questions)}\n"
                f"📊 <b>Ответов:</b> {sum(len(q.answers) for q in dialog.questions)}\n\n"
                f"✅ Диалог готов к использованию!",
                parse_mode="HTML"
            )
            
            # Очищаем данные
            context.user_data.pop('action', None)
            context.user_data.pop('dialog_data', None)
            
            logger.info(f"Админ {message.from_user.id} создал диалог: {dialog.name}")
            
    except Exception as e:
        logger.error(f"Ошибка создания диалога: {e}")
        await message.reply_text(
            "❌ Ошибка создания диалога. Попробуйте снова.",
            parse_mode="HTML"
        )


# Обработчики экспортируются как функции, а MessageHandler создается в __init__.py
