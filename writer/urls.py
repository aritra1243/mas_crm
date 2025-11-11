# File: writer/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path('home/', views.home, name='writer_home'),
    path('dashboard/', views.dashboard, name='writer_dashboard'),
    path('job/<int:job_id>/upload/', views.job_upload, name='writer_job_upload'),
    path('job/<int:job_id>/', views.open_job_detail, name='writer_open_job_detail'),
    
    # Notifications
    path('notifications/', views.notifications, name='writer_notifications'),
    path('notifications/read-all/', views.read_all_notifications, name='writer_notifications_read_all'),
    
    # Profile
    path('profile/', views.profile, name='writer_profile'),
    
    # New sections
    path('complete-jobs/', views.complete_jobs, name='writer_complete_jobs'),
    path('open-issues/', views.open_issues_list, name='writer_open_issues'),
    path('close-issues/', views.close_issues_list, name='writer_close_issues'),
]
