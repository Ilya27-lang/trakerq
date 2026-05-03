"""
URL конфигурация для API трекера.
"""

from django.urls import path
from . import views

app_name = 'tracker_api'

urlpatterns = [
    # Привычки
    path('habits/', views.habits_api, name='habits-api'),
    path('habits/<int:habit_id>/', views.habit_detail_api, name='habit-detail-api'),
    
    # Транзакции
    path('transactions/', views.transactions_api, name='transactions-api'),
    path('transactions/<int:transaction_id>/', views.transaction_detail_api, name='transaction-detail-api'),
    
    # Недельное расписание
    path('week-schedule/', views.week_schedule_api, name='week-schedule-api'),
    path('week-tasks/create/', views.create_week_task_api, name='create-week-task-api'),
    path('week-tasks/<str:task_id>/toggle/', views.toggle_week_task_api, name='toggle-week-task-api'),
    path('week-tasks/<str:task_id>/delete/', views.delete_week_task_api, name='delete-week-task-api'),
    
    # Архив
    path('archive/', views.archive_api, name='archive-api'),
    path('archive/clear/', views.clear_archive_api, name='clear-archive-api'),
    
    # Матрёшка
    path('matryoshka/', views.matryoshka_state_api, name='matryoshka-state-api'),
]
