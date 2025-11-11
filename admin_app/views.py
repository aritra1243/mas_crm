from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from authentication.decorators import role_required
from authentication.models import Job, User

@role_required(allowed_roles=['admin'])
def dashboard(request):
    """
    Admin Dashboard:
    - Allocate a job to a writer
    - Set status to query, cancel, or hold with an optional note
    Posts back to the same view from the modal.
    """
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        action = request.POST.get('action')
        writer_id = request.POST.get('writer_id') or ''
        status_note = (request.POST.get('status_note') or '').strip()

        job = get_object_or_404(Job, id=job_id)

        if action == 'allocate':
            if not writer_id:
                messages.error(request, 'Please select a writer to allocate.')
                return redirect('admin_dashboard')
            # Keep boolean filters out of the SQL query to avoid Djongo hiccups
            writer = get_object_or_404(User, id=writer_id, role='writer')
            if not getattr(writer, 'is_approved', False):
                messages.error(request, 'Selected writer is not approved.')
                return redirect('admin_dashboard')

            job.allocated_to = writer
            job.status = 'allocated'
            job.status_note = ''
            job.save(update_fields=['allocated_to', 'status', 'status_note', 'updated_at'])
            messages.success(request, f'Job {job.job_id} allocated to {writer.first_name or writer.username}.')
        elif action in ['query', 'cancel', 'hold']:
            job.status = action
            job.status_note = status_note
            job.save(update_fields=['status', 'status_note', 'updated_at'])
            messages.success(request, f'Job {job.job_id} status updated to {action}.')
        else:
            messages.error(request, 'Unknown action.')

        return redirect('admin_dashboard')

    # ===== Lists for dashboard =====
    jobs = Job.objects.select_related('allocated_to', 'created_by').order_by('-created_at')

    # Pre-filter approved in Python to avoid Djongo boolean-where conversions
    approved_users = [u for u in User.objects.all() if getattr(u, 'is_approved', False)]
    marketing_agents = [u for u in approved_users if u.role == 'marketing']
    allocaters = [u for u in approved_users if u.role == 'allocater']
    writers = [u for u in approved_users if u.role == 'writer']
    process_team = [u for u in approved_users if u.role == 'process_team']

    context = {
        'jobs': jobs,
        'writers': writers,                # for the job-edit modal dropdown
        'marketing_agents': marketing_agents,
        'allocaters': allocaters,
        'process_team': process_team,

        # Precomputed counts to avoid .count() evaluation in template
        'total_jobs': len(list(jobs)),
        'marketing_count': len(marketing_agents),
        'writer_count': len(writers),
        'allocater_count': len(allocaters),
    }
    return render(request, 'admin_app/dashboard.html', context)
