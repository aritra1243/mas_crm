from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='allocater_dashboard'),
    path('job/<str:job_id>/', views.view_job, name='allocater_view_job'),

    # section pages
    path('in-progress/', views.in_progress, name='allocater_in_progress'),
    path('assigned/', views.assigned, name='allocater_assigned'),
    path('completed/', views.completed, name='allocater_completed'),

    path('notifications/', views.notifications, name='allocater_notifications'),
    path('notifications/mark-all-read/', views.mark_all_read, name='allocater_mark_all_read'),
    path('profile/', views.profile, name='allocater_profile'),
]
