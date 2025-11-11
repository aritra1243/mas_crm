from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from authentication.decorators import role_required
from authentication.models import Job, User

@role_required(allowed_roles=['manager'])
def dashboard(request):
    """
    Manager Dashboard:
    - Allocate a job to a writer
    - Set status to query, cancel, or hold with an optional note
    """
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        action = request.POST.get('action')
        writer_id = request.POST.get('writer_id')
        status_note = request.POST.get('status_note', '').strip()

        job = get_object_or_404(Job, id=job_id)

        if action == 'allocate':
            if writer_id:
                # Fetch writer and verify manually to avoid Djongo boolean filter issues
                try:
                    writer = User.objects.get(id=writer_id)
                    if writer.role != 'writer' or not getattr(writer, 'is_approved', False):
                        messages.error(request, 'Selected writer is not approved or invalid.')
                        return redirect('manager_dashboard')
                    
                    job.allocated_to = writer
                    job.status = 'allocated'
                    job.status_note = ''
                    job.save()
                    who = writer.first_name or writer.username
                    messages.success(request, f'Job {job.job_id} allocated to {who}.')
                except User.DoesNotExist:
                    messages.error(request, 'Writer not found.')
            else:
                messages.error(request, 'Please select a writer to allocate.')
        elif action in ['query', 'cancel', 'hold']:
            job.status = action
            job.status_note = status_note
            job.save()
            messages.success(request, f'Job {job.job_id} status updated to {action}.')
        else:
            messages.error(request, 'Unknown action.')

        return redirect('manager_dashboard')

    # Fetch all users and filter approved ones in Python to avoid Djongo boolean filter issues
    all_users = [u for u in User.objects.all() if getattr(u, 'is_approved', False)]
    
    marketing_agents = [user for user in all_users if user.role == 'marketing']
    allocaters = [user for user in all_users if user.role == 'allocater']
    writers = [user for user in all_users if user.role == 'writer']
    process_team = [user for user in all_users if user.role == 'process_team']

    # Get all jobs
    jobs = Job.objects.select_related('allocated_to', 'created_by').order_by('-created_at')

    context = {
        'jobs': jobs,
        'marketing_agents': marketing_agents,
        'allocaters': allocaters,
        'writers': writers,
        'process_team': process_team,
        'total_jobs': jobs.count(),
        'marketing_count': len(marketing_agents),
        'allocater_count': len(allocaters),
        'writer_count': len(writers),
        'process_team_count': len(process_team),
    }
    return render(request, 'manager/dashboard.html', context)