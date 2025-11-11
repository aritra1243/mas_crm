from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='manager_dashboard'),
]