"""
Модели данных для трекера задач.
Использует принципы ООП: инкапсуляция, наследование, абстракция.
"""

from django.db import models
from django.utils import timezone
from datetime import timedelta


class BaseModel(models.Model):
    """
    Базовая модель с общими полями.
    Реализует принцип DRY (Don't Repeat Yourself).
    """
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        abstract = True  # Не создаёт таблицу в БД, только для наследования


class Habit(BaseModel):
    """
    Модель привычки.
    Инкапсулирует данные о привычке и методах работы с ней.
    """
    name = models.CharField(max_length=200, verbose_name="Название привычки")
    dates_completed = models.JSONField(default=list, verbose_name="Даты выполнения")

    class Meta:
        verbose_name = "Привычка"
        verbose_name_plural = "Привычки"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def mark_completed(self, date_str: str):
        """Отметить привычку выполненной в указанную дату."""
        if date_str not in self.dates_completed:
            self.dates_completed.append(date_str)
            self.save()

    def unmark_completed(self, date_str: str):
        """Убрать отметку о выполнении."""
        if date_str in self.dates_completed:
            self.dates_completed.remove(date_str)
            self.save()

    def is_completed_today(self):
        """Проверить, выполнена ли привычка сегодня."""
        today = timezone.now().strftime('%Y-%m-%d')
        return today in self.dates_completed

    def get_streak(self):
        """Вычислить текущую серию выполнений (дней подряд)."""
        if not self.dates_completed:
            return 0
        
        sorted_dates = sorted(self.dates_completed, reverse=True)
        streak = 0
        current_date = timezone.now().date()
        
        for date_str in sorted_dates:
            try:
                date_obj = timezone.datetime.strptime(date_str, '%Y-%m-%d').date()
                if current_date - date_obj == timedelta(days=streak):
                    streak += 1
                else:
                    break
            except ValueError:
                continue
        
        return streak


class Transaction(BaseModel):
    """
    Модель финансовой транзакции.
    """
    TYPE_CHOICES = [
        ('income', 'Доход'),
        ('expense', 'Расход'),
    ]

    transaction_type = models.CharField(
        max_length=10,
        choices=TYPE_CHOICES,
        verbose_name="Тип транзакции"
    )
    amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Сумма"
    )
    description = models.CharField(
        max_length=300,
        blank=True,
        default='',
        verbose_name="Описание"
    )

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ['-created_at']

    def __str__(self):
        sign = '+' if self.transaction_type == 'income' else '-'
        return f"{sign}{self.amount} ₽ - {self.description or self.get_transaction_type_display()}"


class WeekTask(BaseModel):
    """
    Модель задачи недельного расписания.
    """
    task_id = models.CharField(max_length=50, unique=True, verbose_name="ID задачи")
    date = models.DateField(verbose_name="Дата задачи")
    text = models.CharField(max_length=500, verbose_name="Текст задачи")
    is_done = models.BooleanField(default=False, verbose_name="Выполнено")
    time_start = models.TimeField(null=True, blank=True, verbose_name="Время начала")
    time_end = models.TimeField(null=True, blank=True, verbose_name="Время окончания")

    class Meta:
        verbose_name = "Задача недели"
        verbose_name_plural = "Задачи недели"
        ordering = ['date', 'time_start']

    def __str__(self):
        status = "✓" if self.is_done else "○"
        return f"[{status}] {self.date}: {self.text[:30]}..."

    def toggle_done(self):
        """Переключить статус выполнения."""
        self.is_done = not self.is_done
        self.save()


class WeekArchive(models.Model):
    """
    Модель архива завершённых недель.
    """
    week_key = models.CharField(max_length=100, unique=True, verbose_name="Ключ недели")
    start_date = models.DateField(verbose_name="Дата начала недели")
    end_date = models.DateField(verbose_name="Дата окончания недели")
    tasks_data = models.JSONField(default=list, verbose_name="Данные задач")
    total_tasks = models.IntegerField(default=0, verbose_name="Всего задач")
    completed_tasks = models.IntegerField(default=0, verbose_name="Выполнено задач")
    progress_percent = models.IntegerField(default=0, verbose_name="Процент выполнения")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Архив недели"
        verbose_name_plural = "Архивы недель"
        ordering = ['-start_date']

    def __str__(self):
        return f"Неделя {self.start_date} - {self.end_date}"

    def calculate_progress(self):
        """Вычислить процент выполнения."""
        if self.total_tasks > 0:
            self.progress_percent = round((self.completed_tasks / self.total_tasks) * 100)
        else:
            self.progress_percent = 0
        self.save()
