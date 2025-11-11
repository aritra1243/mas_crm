from django.contrib import admin
from .models import User, Job

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ['username', 'first_name', 'email', 'role', 'is_approved', 'created_at']
    list_filter = ['role', 'is_approved']
    search_fields = ['username', 'email', 'first_name']

@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ['job_id', 'created_by', 'allocated_to', 'status', 'word_count', 'strict_deadline']
    list_filter = ['status', 'created_at']
    search_fields = ['job_id', 'topic']