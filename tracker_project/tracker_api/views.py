"""
API Views для трекера.
Использует класс-based views (CBV) и function-based views (FBV).
Реализует принципы ООП через наследование и полиморфизм.
"""

import json
from datetime import datetime
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone

from .models import Habit, Transaction, WeekTask, WeekArchive
from .services import (
    MatryoshkaService,
    HabitService,
    TransactionService,
    WeekTaskService,
    ArchiveService
)


# === API для привычек ===

@csrf_exempt
@require_http_methods(["GET", "POST"])
def habits_api(request):
    """API endpoint для работы с привычками."""
    
    if request.method == "GET":
        habits = HabitService.get_all_habits()
        today_str = timezone.now().strftime('%Y-%m-%d')
        stats = HabitService.get_stats(habits, today_str)
        
        habits_data = []
        for habit in habits:
            habits_data.append({
                "id": habit.id,
                "name": habit.name,
                "dates": habit.dates_completed,
                "streak": habit.get_streak(),
                "is_completed_today": today_str in habit.dates_completed
            })
        
        return JsonResponse({
            "habits": habits_data,
            "stats": stats
        })
    
    elif request.method == "POST":
        data = json.loads(request.body)
        name = data.get("name", "").strip()
        
        if not name:
            return JsonResponse({"error": "Название привычки обязательно"}, status=400)
        
        habit = HabitService.create_habit(name)
        return JsonResponse({
            "id": habit.id,
            "name": habit.name,
            "dates": habit.dates_completed
        }, status=201)


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def habit_detail_api(request, habit_id):
    """API endpoint для конкретной привычки."""
    
    try:
        habit = Habit.objects.get(id=habit_id)
    except Habit.DoesNotExist:
        return JsonResponse({"error": "Привычка не найдена"}, status=404)
    
    if request.method == "POST":
        # Переключение статуса
        today_str = timezone.now().strftime('%Y-%m-%d')
        habit = HabitService.toggle_habit(habit, today_str)
        
        matryoshka_state = get_matryoshka_state_for_response('success')
        
        return JsonResponse({
            "id": habit.id,
            "is_completed_today": today_str in habit.dates_completed,
            "matryoshka": matryoshka_state
        })
    
    elif request.method == "DELETE":
        HabitService.delete_habit(habit)
        return JsonResponse({"message": "Привычка удалена"})


# === API для транзакций ===

@csrf_exempt
@require_http_methods(["GET", "POST"])
def transactions_api(request):
    """API endpoint для работы с транзакциями."""
    
    if request.method == "GET":
        transactions = TransactionService.get_all_transactions()
        stats = TransactionService.get_stats()
        
        transactions_data = []
        for t in transactions:
            transactions_data.append({
                "id": t.id,
                "type": t.transaction_type,
                "amount": float(t.amount),
                "description": t.description,
                "date": t.created_at.strftime('%Y-%m-%d %H:%M')
            })
        
        return JsonResponse({
            "transactions": transactions_data,
            "stats": stats
        })
    
    elif request.method == "POST":
        data = json.loads(request.body)
        transaction_type = data.get("type")
        amount = data.get("amount")
        description = data.get("description", "")
        
        if not transaction_type or transaction_type not in ['income', 'expense']:
            return JsonResponse({"error": "Неверный тип транзакции"}, status=400)
        
        try:
            amount = float(amount)
            if amount <= 0:
                raise ValueError()
        except (TypeError, ValueError):
            return JsonResponse({"error": "Неверная сумма"}, status=400)
        
        transaction = TransactionService.create_transaction(transaction_type, amount, description)
        
        return JsonResponse({
            "id": transaction.id,
            "type": transaction.transaction_type,
            "amount": float(transaction.amount),
            "description": transaction.description
        }, status=201)


@csrf_exempt
@require_http_methods(["DELETE"])
def transaction_detail_api(request, transaction_id):
    """API endpoint для удаления транзакции."""
    
    try:
        transaction = Transaction.objects.get(id=transaction_id)
    except Transaction.DoesNotExist:
        return JsonResponse({"error": "Транзакция не найдена"}, status=404)
    
    TransactionService.delete_transaction(transaction)
    return JsonResponse({"message": "Транзакция удалена"})


# === API для недельного расписания ===

@csrf_exempt
@require_http_methods(["GET"])
def week_schedule_api(request):
    """API endpoint для получения недельного расписания."""
    
    offset = int(request.GET.get("offset", 0))
    week_dates = WeekTaskService.get_week_dates(offset)
    
    # Авто-архивация прошлых недель
    ArchiveService.auto_archive_past_weeks()
    
    today_str = timezone.now().strftime('%Y-%m-%d')
    
    # Находим индекс сегодняшнего дня
    today_idx = next((i for i, d in enumerate(week_dates) if d["date_str"] == today_str), -1)
    
    # Статистика текущего дня
    day_stats = {"total": 0, "done": 0, "progress": 0}
    if today_idx >= 0:
        day_stats = WeekTaskService.get_day_stats(today_str)
    
    # Собираем задачи по дням
    tasks_by_date = {}
    for date_info in week_dates:
        tasks = WeekTaskService.get_tasks_for_date(date_info["date_str"])
        tasks_by_date[date_info["date_str"]] = [
            {
                "id": t.task_id,
                "text": t.text,
                "is_done": t.is_done,
                "time_start": t.time_start.strftime('%H:%M') if t.time_start else None,
                "time_end": t.time_end.strftime('%H:%M') if t.time_end else None
            }
            for t in tasks
        ]
    
    # Формируем данные о неделе
    week_label = f"{week_dates[0]['date_obj'].strftime('%d %b')} — {week_dates[6]['date_obj'].strftime('%d %b %Y')}"
    if offset == 0:
        week_label = f"Эта неделя ({week_dates[0]['date_obj'].strftime('%d %b')} — {week_dates[6]['date_obj'].strftime('%d %b %Y')})"
    
    return JsonResponse({
        "week_dates": week_dates,
        "week_label": week_label,
        "today_idx": today_idx,
        "day_stats": day_stats,
        "tasks_by_date": tasks_by_date
    })


@csrf_exempt
@require_http_methods(["POST"])
def create_week_task_api(request):
    """API endpoint для создания задачи недели."""
    
    data = json.loads(request.body)
    text = data.get("text", "").strip()
    date_str = data.get("date")
    time_start = data.get("time_start")
    time_end = data.get("time_end")
    
    if not text or not date_str:
        return JsonResponse({"error": "Текст и дата обязательны"}, status=400)
    
    task_id = str(int(timezone.now().timestamp() * 1000))
    
    task = WeekTaskService.create_task(task_id, date_str, text, time_start, time_end)
    
    matryoshka_state = get_matryoshka_state_for_response('success')
    
    return JsonResponse({
        "id": task.task_id,
        "date": task.date.strftime('%Y-%m-%d'),
        "text": task.text,
        "is_done": task.is_done,
        "time_start": task.time_start.strftime('%H:%M') if task.time_start else None,
        "time_end": task.time_end.strftime('%H:%M') if task.time_end else None,
        "matryoshka": matryoshka_state
    }, status=201)


@csrf_exempt
@require_http_methods(["POST"])
def toggle_week_task_api(request, task_id):
    """API endpoint для переключения статуса задачи."""
    
    try:
        task = WeekTask.objects.get(task_id=task_id)
    except WeekTask.DoesNotExist:
        return JsonResponse({"error": "Задача не найдена"}, status=404)
    
    task = WeekTaskService.toggle_task(task)
    
    matryoshka_state = get_matryoshka_state_for_response('success')
    
    return JsonResponse({
        "id": task.task_id,
        "is_done": task.is_done,
        "matryoshka": matryoshka_state
    })


@csrf_exempt
@require_http_methods(["DELETE"])
def delete_week_task_api(request, task_id):
    """API endpoint для удаления задачи."""
    
    try:
        task = WeekTask.objects.get(task_id=task_id)
    except WeekTask.DoesNotExist:
        return JsonResponse({"error": "Задача не найдена"}, status=404)
    
    WeekTaskService.delete_task(task)
    return JsonResponse({"message": "Задача удалена"})


# === API для архива ===

@csrf_exempt
@require_http_methods(["GET"])
def archive_api(request):
    """API endpoint для получения архива."""
    
    ArchiveService.auto_archive_past_weeks()
    archives = ArchiveService.get_all_archives()
    
    archives_data = []
    for archive in archives:
        archives_data.append({
            "week_key": archive.week_key,
            "start_date": archive.start_date.strftime('%Y-%m-%d'),
            "end_date": archive.end_date.strftime('%Y-%m-%d'),
            "total_tasks": archive.total_tasks,
            "completed_tasks": archive.completed_tasks,
            "progress_percent": archive.progress_percent
        })
    
    return JsonResponse({"archives": archives_data})


@csrf_exempt
@require_http_methods(["POST"])
def clear_archive_api(request):
    """API endpoint для очистки архива."""
    
    ArchiveService.clear_archive()
    return JsonResponse({"message": "Архив очищен"})


# === Вспомогательные функции ===

def get_matryoshka_state_for_response(event_type: str = "init") -> dict:
    """Получить состояние Матрёшки для ответа API."""
    today_str = timezone.now().strftime('%Y-%m-%d')
    
    # Считаем все задачи на сегодня
    habits = list(Habit.objects.all())
    today_tasks = list(WeekTask.objects.filter(date=today_str))
    
    completed_habits = sum(1 for h in habits if today_str in h.dates_completed)
    completed_week_tasks = sum(1 for t in today_tasks if t.is_done)
    
    total_tasks = len(habits) + len(today_tasks)
    completed_tasks = completed_habits + completed_week_tasks
    
    completion_rate = completed_tasks / total_tasks if total_tasks > 0 else 1.0
    
    # Определяем fail streak (упрощённо)
    fail_streak = 0
    if completion_rate < 0.5:
        fail_streak = 1
    
    level = MatryoshkaService.get_level(completion_rate, total_tasks, fail_streak)
    
    phrase_type = "daily"
    if event_type == "success" and level <= 1:
        phrase_type = "success"
    elif event_type == "fail" or (completion_rate < 0.5 and level > 0):
        if level == 1:
            phrase_type = "warning"
        elif level == 2:
            phrase_type = "threat"
        elif level == 3:
            phrase_type = "harsh"
    
    return MatryoshkaService.get_state(level, phrase_type)


@csrf_exempt
@require_http_methods(["GET"])
def matryoshka_state_api(request):
    """API endpoint для получения состояния Матрёшки."""
    state = get_matryoshka_state_for_response("init")
    return JsonResponse(state)
