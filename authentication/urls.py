from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),  # Root URL goes to login view
    path('register/', views.register_view, name='register'),  # Registration view
    path('login/', views.login_view, name='login'),  # Login view
    path('logout/', views.logout_view, name='logout'),  # Logout view
    path('dashboard/', views.dashboard_redirect, name='dashboard_redirect'),  # Dashboard redirection based on user role
]
