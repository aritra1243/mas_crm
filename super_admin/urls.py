from django.urls import path
from . import views

urlpatterns = [
    path('dashboard/', views.dashboard, name='super_admin_dashboard'),
    path('pending/', views.pending_users, name='super_admin_pending'),
    path('roles/', views.manage_roles, name='super_admin_roles'),
]