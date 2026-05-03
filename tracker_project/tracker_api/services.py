"""
Сервисный слой для бизнес-логики трекера.
Инкапсулирует сложную логику работы с данными.
"""

from datetime import datetime, timedelta
from django.utils import timezone
from .models import Habit, Transaction, WeekTask, WeekArchive


class MatryoshkaService:
    """
    Сервис для управления состоянием "Матрёшки".
    Реализует логику определения уровня настроения.
    """
    
    LEVELS = {
        0: {"title": "Настроение: Суровая, но справедливая", "emoji": "🪆"},
        1: {"title": "Настроение: Хмурится", "emoji": "😟"},
        2: {"title": "Настроение: Злится", "emoji": "😠"},
        3: {"title": "Настроение: В БЕШЕНСТВЕ", "emoji": "🤬"},
    }
    
    PHRASES = {
        0: {
            "success": ["Красавчик! Так держать!", "Молодец, но не расслабляйся.", "Дисциплина — дело тонкое."],
            "daily": "День начинается. Матрёшка следит."
        },
        1: {
            "warning": ["Тянешь резину?", "Дело не ждёт.", "Задача висит."],
            "daily": "Вижу недочёты."
        },
        2: {
            "threat": ["Отговорки не слушу!", "Задача не сделана!", "Хватит лениться!"],
            "daily": "Просрочки копятся."
        },
        3: {
            "harsh": ["Будешь отлынивать!", "Делай или уходи!", "Терпение лопнуло!"],
            "daily": "Всё, терпение лопнуло."
        }
    }
    
    @classmethod
    def get_level(cls, completion_rate: float, total_tasks: int, fail_streak: int = 0) -> int:
        """Определить уровень Матрёшки на основе статистики."""
        if total_tasks == 0:
            return 0
        if completion_rate >= 0.8 and fail_streak == 0:
            return 0
        if completion_rate >= 0.5 or fail_streak == 1:
            return 1
        if completion_rate >= 0.2 or fail_streak <= 2:
            return 2
        return 3
    
    @classmethod
    def get_phrase(cls, level: int, phrase_type: str) -> str:
        """Получить фразу Матрёшки."""
        phrases = cls.PHRASES.get(level, {})
        phrase_list = phrases.get(phrase_type, ["..."])
        import random
        return random.choice(phrase_list) if phrase_list else "..."
    
    @classmethod
    def get_state(cls, level: int, phrase_type: str = "daily") -> dict:
        """Получить полное состояние Матрёшки."""
        level_data = cls.LEVELS.get(level, cls.LEVELS[0])
        return {
            "level": level,
            "title": level_data["title"],
            "emoji": level_data["emoji"],
            "text": cls.get_phrase(level, phrase_type)
        }


class HabitService:
    """Сервис для работы с привычками."""
    
    @staticmethod
    def get_all_habits():
        """Получить все привычки."""
        return Habit.objects.all()
    
    @staticmethod
    def create_habit(name: str) -> Habit:
        """Создать новую привычку."""
        return Habit.objects.create(name=name)
    
    @staticmethod
    def toggle_habit(habit: Habit, date_str: str):
        """Переключить статус выполнения привычки."""
        if date_str in habit.dates_completed:
            habit.unmark_completed(date_str)
        else:
            habit.mark_completed(date_str)
        return habit
    
    @staticmethod
    def delete_habit(habit: Habit):
        """Удалить привычку."""
        habit.delete()
    
    @staticmethod
    def get_stats(habits, today_str: str):
        """Получить статистику по привычкам."""
        total = len(habits)
        done_today = sum(1 for h in habits if today_str in h.dates_completed)
        
        max_streak = 0
        for habit in habits:
            streak = habit.get_streak()
            if streak > max_streak:
                max_streak = streak
        
        return {
            "total": total,
            "done_today": done_today,
            "max_streak": max_streak
        }


class TransactionService:
    """Сервис для работы с транзакциями."""
    
    @staticmethod
    def get_all_transactions():
        """Получить все транзакции."""
        return Transaction.objects.all().order_by('-created_at')
    
    @staticmethod
    def create_transaction(transaction_type: str, amount: float, description: str = "") -> Transaction:
        """Создать транзакцию."""
        return Transaction.objects.create(
            transaction_type=transaction_type,
            amount=amount,
            description=description
        )
    
    @staticmethod
    def delete_transaction(transaction: Transaction):
        """Удалить транзакцию."""
        transaction.delete()
    
    @staticmethod
    def get_stats():
        """Получить финансовую статистику."""
        income = sum(t.amount for t in Transaction.objects.filter(transaction_type='income'))
        expense = sum(t.amount for t in Transaction.objects.filter(transaction_type='expense'))
        balance = income - expense
        
        return {
            "balance": balance,
            "income": income,
            "expense": expense
        }


class WeekTaskService:
    """Сервис для работы с задачами недели."""
    
    @staticmethod
    def get_week_dates(offset: int = 0):
        """Получить даты текущей недели со смещением."""
        now = timezone.now()
        day_of_week = now.weekday()  # 0 = понедельник
        monday = now - timedelta(days=day_of_week) + timedelta(weeks=offset)
        monday = monday.replace(hour=0, minute=0, second=0, microsecond=0)
        
        dates = []
        for i in range(7):
            date = monday + timedelta(days=i)
            dates.append({
                "date_obj": date,
                "date_str": date.strftime('%Y-%m-%d'),
                "day": date.day,
                "month": date.month,
                "weekday": date.weekday()
            })
        return dates
    
    @staticmethod
    def get_tasks_for_date(date_str: str):
        """Получить задачи для конкретной даты."""
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
            return WeekTask.objects.filter(date=date_obj).order_by('time_start')
        except ValueError:
            return WeekTask.objects.none()
    
    @staticmethod
    def create_task(task_id: str, date_str: str, text: str, 
                    time_start: str = None, time_end: str = None) -> WeekTask:
        """Создать задачу."""
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        task = WeekTask.objects.create(
            task_id=task_id,
            date=date_obj,
            text=text,
            time_start=datetime.strptime(time_start, '%H:%M').time() if time_start else None,
            time_end=datetime.strptime(time_end, '%H:%M').time() if time_end else None
        )
        return task
    
    @staticmethod
    def toggle_task(task: WeekTask):
        """Переключить статус задачи."""
        task.toggle_done()
        return task
    
    @staticmethod
    def delete_task(task: WeekTask):
        """Удалить задачу."""
        task.delete()
    
    @staticmethod
    def get_day_stats(date_str: str):
        """Получить статистику для дня."""
        tasks = list(WeekTaskService.get_tasks_for_date(date_str))
        total = len(tasks)
        done = sum(1 for t in tasks if t.is_done)
        progress = round((done / total) * 100) if total > 0 else 0
        
        return {
            "total": total,
            "done": done,
            "progress": progress
        }


class ArchiveService:
    """Сервис для работы с архивом недель."""
    
    @staticmethod
    def is_week_finished(week_dates: list) -> bool:
        """Проверить, закончилась ли неделя."""
        if not week_dates:
            return False
        sunday_str = week_dates[6]["date_str"]
        today_str = timezone.now().strftime('%Y-%m-%d')
        return today_str > sunday_str
    
    @staticmethod
    def archive_week(week_dates: list):
        """Архивировать завершённую неделю."""
        week_key = f"week-{week_dates[0]['date_str']}-to-{week_dates[6]['date_str']}"
        
        # Проверяем, не заархивирована ли уже
        if WeekArchive.objects.filter(week_key=week_key).exists():
            return
        
        # Собираем задачи за эту неделю
        date_strings = [d["date_str"] for d in week_dates]
        tasks = list(WeekTask.objects.filter(date__in=date_strings))
        
        if not tasks:
            return
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.is_done)
        
        # Сохраняем данные задач
        tasks_data = []
        for task in tasks:
            tasks_data.append({
                "task_id": task.task_id,
                "date": task.date.strftime('%Y-%m-%d'),
                "text": task.text,
                "is_done": task.is_done,
                "time_start": task.time_start.strftime('%H:%M') if task.time_start else None,
                "time_end": task.time_end.strftime('%H:%M') if task.time_end else None
            })
        
        archive = WeekArchive.objects.create(
            week_key=week_key,
            start_date=week_dates[0]["date_obj"].date(),
            end_date=week_dates[6]["date_obj"].date(),
            tasks_data=tasks_data,
            total_tasks=total,
            completed_tasks=completed,
            progress_percent=round((completed / total) * 100) if total > 0 else 0
        )
        
        # Удаляем задачи из активной таблицы
        WeekTask.objects.filter(date__in=date_strings).delete()
        
        return archive
    
    @staticmethod
    def auto_archive_past_weeks():
        """Автоматически архивировать прошлые недели."""
        offset = -1
        while offset >= -52:
            week_dates = WeekTaskService.get_week_dates(offset)
            if ArchiveService.is_week_finished(week_dates):
                ArchiveService.archive_week(week_dates)
            else:
                break
            offset -= 1
    
    @staticmethod
    def get_all_archives():
        """Получить все архивы."""
        return WeekArchive.objects.all().order_by('-start_date')
    
    @staticmethod
    def clear_archive():
        """Очистить весь архив."""
        WeekArchive.objects.all().delete()
