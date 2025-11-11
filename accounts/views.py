# accounts/views.py
from decimal import Decimal
from django.shortcuts import render
from authentication.decorators import role_required
from authentication.models import Job

@role_required(allowed_roles=['accounts'])
def dashboard(request):
    completed_jobs = Job.objects.filter(status='completed').order_by('-updated_at')

    # Sum safely as Decimal and compute average
    total_jobs = completed_jobs.count()
    total_value = sum((job.value or Decimal('0')) for job in completed_jobs) if total_jobs else Decimal('0')
    avg_value = (total_value / Decimal(total_jobs)) if total_jobs else Decimal('0')

    context = {
        'jobs': completed_jobs,
        'total_value': total_value,
        'total_jobs': total_jobs,
        'avg_value': avg_value,
    }
    return render(request, 'accounts/dashboard.html', context)
