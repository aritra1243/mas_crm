# process_team/views.py
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from authentication.decorators import role_required
from authentication.models import Job, Notification

# ---------------- helpers ----------------
def _pt_unread_count(user):
    """
    Return unread notification count for the logged-in process team member.
    Avoid boolean filters so Djongo does not emit NOT in SQL.
    """
    try:
        # Get all notifications and filter in Python to avoid Djongo NOT operator issue
        all_notifs = list(
            Notification.objects
            .filter(user=user)
            .only('id', 'is_read')
        )
        return sum(1 for n in all_notifs if not getattr(n, 'is_read', False))
    except Exception:
        return 0

# ---------------- dashboard ----------------
@role_required(allowed_roles=['process_team'])
def dashboard(request):
    jobs_in_process = Job.objects.filter(status='process').order_by('strict_deadline')
    jobs_completed = Job.objects.filter(status='completed').order_by('-updated_at')[:10]
    
    return render(
        request,
        'process_team/dashboard.html',
        {
            'jobs': jobs_in_process,
            'jobs_completed': jobs_completed,
            'in_process_count': jobs_in_process.count(),
            'completed_count': Job.objects.filter(status='completed').count(),
            'process_unread_count': _pt_unread_count(request.user),
        },
    )

# ---------------- job upload ----------------
@role_required(allowed_roles=['process_team'])
def job_upload(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    
    # Allow newly-arrived jobs to open, then mark as "process"
    if job.status not in ('process', 'completed'):
        job.status = 'process'
        job.save(update_fields=['status', 'updated_at'])
    
    if request.method == 'POST':
        upload_type = request.POST.get('upload_type')
        
        if upload_type == 'ai_plag':
            job.ai_plag_final_file = request.FILES.get('final_file')
            job.ai_plag_ai_report = request.FILES.get('ai_report')
            job.ai_plag_plag_report = request.FILES.get('plag_report')
            job.ai_plag_software = request.FILES.get('software')
            job.save()
            messages.success(request, 'AI/Plag set uploaded.')
            return redirect('process_team_job_upload', job_id=job.id)
        
        elif upload_type == 'decoration':
            job.decoration_final_file = request.FILES.get('final_file')
            job.decoration_ai_report = request.FILES.get('ai_report')
            job.decoration_plag_report = request.FILES.get('plag_report')
            job.decoration_software = request.FILES.get('software')
            job.decoration_decorated_file = request.FILES.get('decorated_file')
            job.status = 'completed'
            job.save()
            messages.success(request, 'Decoration uploaded. Job marked completed.')
            return redirect('process_team_dashboard')
        
        messages.error(request, 'Select a valid upload type.')
    
    return render(
        request,
        'process_team/job_upload.html',
        {
            'job': job,
            'process_unread_count': _pt_unread_count(request.user),
        }
    )

# ---------------- notifications ----------------
@role_required(allowed_roles=['process_team'])
def notifications(request):
    me = request.user
    notes = (
        Notification.objects
        .filter(user=me)
        .select_related('job')
        .order_by('-created_at')
    )
    
    # Due in next 10 minutes for jobs in process
    now = timezone.now()
    due_soon = []
    for j in Job.objects.filter(process_team_member=me, status='process').only('id', 'job_id', 'strict_deadline'):
        if j.strict_deadline:
            delta = (j.strict_deadline - now).total_seconds()
            if 0 < delta <= 600:
                due_soon.append({
                    'id': j.id,
                    'job_id': getattr(j, 'job_id', f'JOB-{j.id}'),
                    'masked_job_id': j.get_masked_job_id(),
                    'seconds': int(delta),
                    'strict_deadline': j.strict_deadline,
                })
    
    return render(
        request,
        'process_team/notifications.html',
        {
            'notifications': notes,
            'process_unread_count': _pt_unread_count(me),
            'due_soon': due_soon,
        }
    )

@role_required(allowed_roles=['process_team'])
def mark_all_read(request):
    """
    Mark every unread notification for this user as read.
    Djongo-safe approach: never put a boolean filter in the SQL WHERE.
    """
    if request.method == 'POST':
        # 1) Collect unread ids in Python, no boolean in SQL
        unread_ids = []
        try:
            qs = (
                Notification.objects
                .filter(user=request.user)
                .only('id', 'is_read')
                .iterator(chunk_size=1000)
            )
            for obj in qs:
                if not getattr(obj, 'is_read', False):
                    unread_ids.append(obj.id)
        except Exception:
            unread_ids = []
        
        # 2) Chunked updates by id__in only
        updated = 0
        if unread_ids:
            CHUNK = 500
            for i in range(0, len(unread_ids), CHUNK):
                batch = unread_ids[i:i+CHUNK]
                Notification.objects.filter(id__in=batch).update(is_read=True)
                updated += len(batch)
        
        if updated:
            messages.success(request, f'{updated} notification(s) marked as read.')
        else:
            messages.info(request, 'No unread notifications.')
    
    return redirect('process_team_notifications')

@role_required(allowed_roles=['process_team'])
def mark_read(request, note_id):
    """Mark a single notification as read."""
    notif = get_object_or_404(Notification, id=note_id, user=request.user)
    notif.is_read = True
    notif.save(update_fields=['is_read'])
    return redirect('process_team_notifications')

# ---------------- profile ----------------
@role_required(allowed_roles=['process_team'])
def profile(request):
    me = request.user
    
    if request.method == 'POST':
        me.first_name = request.POST.get('first_name', '').strip()
        me.last_name = request.POST.get('last_name', '').strip()
        me.email = request.POST.get('email', '').strip()
        me.phone_number = request.POST.get('phone_number', '').strip()
        me.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('process_team_profile')
    
    # Tenure string
    if me.date_joined:
        delta = timezone.now().date() - me.date_joined.date()
        years = delta.days // 365
        months = (delta.days % 365) // 30
        days = (delta.days % 365) % 30
        tenure = f'{years} year(s), {months} month(s), {days} day(s)'
    else:
        tenure = 'Not available'
    
    return render(
        request,
        'process_team/profile.html',
        {
            'user': me,
            'tenure': tenure,
            'process_unread_count': _pt_unread_count(me),
        }
    )