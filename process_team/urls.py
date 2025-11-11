# process_team/urls.py
from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='process_team_dashboard'),
    path('dashboard/', views.dashboard, name='process_team_dashboard_alt'),
    path('job/<str:job_id>/upload/', views.job_upload, name='process_team_job_upload'),
    path('notifications/', views.notifications, name='process_team_notifications'),
    path('notifications/mark-all-read/', views.mark_all_read, name='process_team_mark_all_read'),
    path('notifications/mark-read/<int:note_id>/', views.mark_read, name='process_team_mark_read'),
    path('profile/', views.profile, name='process_team_profile'),
]
