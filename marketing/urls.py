from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='marketing_dashboard'),
    path('job-drop/', views.job_drop, name='marketing_job_drop'),
    path('my-dropped/', views.my_dropped_jobs, name='marketing_my_dropped'),
    path('edit/<int:job_id>/', views.edit_job, name='marketing_job_edit'),
    path('delete/<int:job_id>/', views.delete_job, name='marketing_job_delete'),
]
