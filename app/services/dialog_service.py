"""
Сервис для работы с системой диалогов.

Управляет настраиваемыми вопросами и ответами.
"""

import re
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, and_, or_, func, String, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from loguru import logger

from app.models.dialog import Dialog, DialogQuestion, DialogAnswer, DialogStatus
from app.schemas.dialog import (
    DialogCreate, DialogUpdate, DialogQuestionCreate, DialogAnswerCreate,
    DialogSearchRequest, DialogSearchResult
)
from app.core.exceptions import DialogException


class DialogService:
    """Сервис для работы с диалогами."""
    
    def __init__(self, session: AsyncSession):
        """Инициализация сервиса."""
        self.session = session
    
    async def create_dialog(self, dialog_data: DialogCreate) -> Dialog:
        """Создать новый диалог."""
        try:
            # Создаем диалог
            dialog = Dialog(
                name=dialog_data.name,
                description=dialog_data.description,
                status=dialog_data.status,
                sort_order=dialog_data.sort_order
            )
            
            self.session.add(dialog)
            await self.session.flush()  # Получаем ID
            
            # Создаем вопросы
            for question_data in dialog_data.questions:
                question = DialogQuestion(
                    dialog_id=str(dialog.id),
                    question_text=question_data.question_text,
                    keywords=question_data.keywords,
                    is_active=question_data.is_active,
                    sort_order=question_data.sort_order
                )
                
                self.session.add(question)
                await self.session.flush()  # Получаем ID
                
                # Создаем ответы
                for answer_data in question_data.answers:
                    answer = DialogAnswer(
                        question_id=str(question.id),
                        answer_text=answer_data.answer_text,
                        answer_type=answer_data.answer_type,
                        additional_data=answer_data.additional_data,
                        is_active=answer_data.is_active,
                        sort_order=answer_data.sort_order
                    )
                    self.session.add(answer)
            
            await self.session.commit()
            await self.session.refresh(dialog)
            
            logger.info(f"Создан диалог: {dialog.name}")
            return dialog
            
        except Exception as e:
            logger.error(f"Ошибка создания диалога: {e}")
            await self.session.rollback()
            raise DialogException(f"Ошибка создания диалога: {e}")
    
    async def get_all_dialogs(self) -> List[Dialog]:
        """Получить все диалоги."""
        try:
            stmt = (
                select(Dialog)
                .options(
                    selectinload(Dialog.questions).selectinload(DialogQuestion.answers)
                )
                .order_by(Dialog.sort_order.asc(), Dialog.created_at.asc())
            )
            result = await self.session.execute(stmt)
            dialogs = result.scalars().all()
            
            logger.info(f"Получено {len(dialogs)} диалогов")
            return dialogs
            
        except Exception as e:
            logger.error(f"Ошибка получения диалогов: {e}")
            return []
    
    async def get_active_dialogs(self) -> List[Dialog]:
        """Получить активные диалоги."""
        try:
            stmt = (
                select(Dialog)
                .where(Dialog.status == DialogStatus.ACTIVE)
                .options(
                    selectinload(Dialog.questions).selectinload(DialogQuestion.answers)
                )
                .order_by(Dialog.sort_order.asc(), Dialog.created_at.asc())
            )
            result = await self.session.execute(stmt)
            dialogs = result.scalars().all()
            
            logger.info(f"Получено {len(dialogs)} активных диалогов")
            return dialogs
            
        except Exception as e:
            logger.error(f"Ошибка получения активных диалогов: {e}")
            return []
    
    async def get_dialog_by_id(self, dialog_id: str) -> Optional[Dialog]:
        """Получить диалог по ID (поддерживает короткие UUID)."""
        try:
            # Если передан короткий UUID (8 символов), ищем по LIKE
            if len(dialog_id) == 8:
                stmt = (
                    select(Dialog)
                    .where(cast(Dialog.id, String).like(f"{dialog_id}%"))
                    .options(
                        selectinload(Dialog.questions).selectinload(DialogQuestion.answers)
                    )
                )
            else:
                # Полный ID
                stmt = (
                    select(Dialog)
                    .where(Dialog.id == dialog_id)
                    .options(
                        selectinload(Dialog.questions).selectinload(DialogQuestion.answers)
                    )
                )
            
            result = await self.session.execute(stmt)
            dialog = result.scalar_one_or_none()
            return dialog
            
        except Exception as e:
            logger.error(f"Ошибка получения диалога {dialog_id}: {e}")
            return None
    
    async def update_dialog(self, dialog_id: str, update_data: DialogUpdate) -> Optional[Dialog]:
        """Обновить диалог."""
        try:
            dialog = await self.get_dialog_by_id(dialog_id)
            if not dialog:
                return None
            
            # Обновляем поля
            for field, value in update_data.model_dump(exclude_unset=True).items():
                if hasattr(dialog, field) and value is not None:
                    setattr(dialog, field, value)
            
            await self.session.commit()
            await self.session.refresh(dialog)
            
            logger.info(f"Обновлен диалог: {dialog.name}")
            return dialog
            
        except Exception as e:
            logger.error(f"Ошибка обновления диалога {dialog_id}: {e}")
            await self.session.rollback()
            return None
    
    async def delete_dialog(self, dialog_id: str) -> bool:
        """Удалить диалог."""
        try:
            dialog = await self.get_dialog_by_id(dialog_id)
            if not dialog:
                return False
            
            # Удаляем диалог (каскадное удаление через foreign key)
            await self.session.delete(dialog)
            await self.session.commit()
            
            logger.info(f"Удален диалог: {dialog.name}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка удаления диалога {dialog_id}: {e}")
            await self.session.rollback()
            return False
    
    async def search_dialogs(self, search_request: DialogSearchRequest) -> List[DialogSearchResult]:
        """Поиск диалогов по запросу."""
        try:
            query = search_request.query.lower().strip()
            if not query:
                return []
            
            # Получаем все активные диалоги с вопросами
            stmt = (
                select(Dialog, DialogQuestion, DialogAnswer)
                .join(DialogQuestion, Dialog.id == DialogQuestion.dialog_id)
                .join(DialogAnswer, DialogQuestion.id == DialogAnswer.question_id)
                .where(
                    and_(
                        Dialog.status == DialogStatus.ACTIVE,
                        DialogQuestion.is_active == True,
                        DialogAnswer.is_active == True
                    )
                )
                .options(
                    selectinload(Dialog.questions).selectinload(DialogQuestion.answers)
                )
            )
            result = await self.session.execute(stmt)
            rows = result.all()
            
            # Группируем результаты по вопросам
            question_results = {}
            for dialog, question, answer in rows:
                question_key = str(question.id)
                if question_key not in question_results:
                    question_results[question_key] = {
                        'dialog': dialog,
                        'question': question,
                        'answers': []
                    }
                question_results[question_key]['answers'].append(answer)
            
            # Вычисляем релевантность и сортируем
            search_results = []
            for question_data in question_results.values():
                relevance_score = self._calculate_relevance(query, question_data['question'])
                if relevance_score > 0:
                    search_results.append(DialogSearchResult(
                        question=question_data['question'],
                        dialog=question_data['dialog'],
                        answers=question_data['answers'],
                        relevance_score=relevance_score
                    ))
            
            # Сортируем по релевантности
            search_results.sort(key=lambda x: x.relevance_score, reverse=True)
            
            # Ограничиваем количество результатов
            limited_results = search_results[:search_request.limit]
            
            logger.info(f"Найдено {len(limited_results)} релевантных диалогов для запроса: {query}")
            return limited_results
            
        except Exception as e:
            logger.error(f"Ошибка поиска диалогов: {e}")
            return []
    
    def _calculate_relevance(self, query: str, question: DialogQuestion) -> float:
        """Вычислить релевантность вопроса к запросу."""
        try:
            score = 0.0
            
            # Поиск в тексте вопроса
            question_text = question.question_text.lower()
            if query in question_text:
                # Точное совпадение
                if query == question_text:
                    score += 1.0
                # Частичное совпадение
                else:
                    score += 0.8
            
            # Поиск по ключевым словам
            if question.keywords:
                keywords = [kw.strip().lower() for kw in question.keywords.split(',')]
                query_words = query.split()
                
                for query_word in query_words:
                    for keyword in keywords:
                        if query_word in keyword or keyword in query_word:
                            score += 0.3
                        elif self._fuzzy_match(query_word, keyword):
                            score += 0.2
            
            # Поиск отдельных слов в тексте вопроса
            question_words = re.findall(r'\b\w+\b', question_text)
            query_words = re.findall(r'\b\w+\b', query)
            
            for query_word in query_words:
                for question_word in question_words:
                    if query_word == question_word:
                        score += 0.1
                    elif self._fuzzy_match(query_word, question_word):
                        score += 0.05
            
            return min(score, 1.0)  # Ограничиваем максимальной оценкой 1.0
            
        except Exception as e:
            logger.error(f"Ошибка вычисления релевантности: {e}")
            return 0.0
    
    def _fuzzy_match(self, word1: str, word2: str) -> bool:
        """Нечеткое сравнение слов."""
        try:
            if len(word1) < 3 or len(word2) < 3:
                return False
            
            # Простое сравнение по первым символам
            if word1[:3] == word2[:3]:
                return True
            
            # Проверка на опечатки (одна буква различается)
            if len(word1) == len(word2):
                diff_count = sum(c1 != c2 for c1, c2 in zip(word1, word2))
                if diff_count <= 1:
                    return True
            
            return False
            
        except Exception:
            return False
    
    async def get_dialog_stats(self) -> Dict[str, Any]:
        """Получить статистику диалогов."""
        try:
            # Общее количество диалогов
            total_dialogs_result = await self.session.execute(select(func.count(Dialog.id)))
            total_dialogs = total_dialogs_result.scalar()
            
            # Активные диалоги
            active_dialogs_result = await self.session.execute(
                select(func.count(Dialog.id)).where(Dialog.status == DialogStatus.ACTIVE)
            )
            active_dialogs = active_dialogs_result.scalar()
            
            # Общее количество вопросов
            total_questions_result = await self.session.execute(select(func.count(DialogQuestion.id)))
            total_questions = total_questions_result.scalar()
            
            # Активные вопросы
            active_questions_result = await self.session.execute(
                select(func.count(DialogQuestion.id)).where(DialogQuestion.is_active == True)
            )
            active_questions = active_questions_result.scalar()
            
            # Общее количество ответов
            total_answers_result = await self.session.execute(select(func.count(DialogAnswer.id)))
            total_answers = total_answers_result.scalar()
            
            # Активные ответы
            active_answers_result = await self.session.execute(
                select(func.count(DialogAnswer.id)).where(DialogAnswer.is_active == True)
            )
            active_answers = active_answers_result.scalar()
            
            stats = {
                'total_dialogs': total_dialogs,
                'active_dialogs': active_dialogs,
                'total_questions': total_questions,
                'active_questions': active_questions,
                'total_answers': total_answers,
                'active_answers': active_answers
            }
            
            logger.info(f"Получена статистика диалогов: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Ошибка получения статистики диалогов: {e}")
            return {
                'total_dialogs': 0,
                'active_dialogs': 0,
                'total_questions': 0,
                'active_questions': 0,
                'total_answers': 0,
                'active_answers': 0
            }
