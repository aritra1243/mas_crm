from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db.models import Q
from authentication.decorators import role_required
from authentication.models import Job, User, Notification
from django.utils import timezone

# --------------------------
# Dashboard with POST actions
# --------------------------
@role_required(allowed_roles=['allocater', 'admin', 'manager'])
def dashboard(request):
    if request.method == 'POST':
        job_id = request.POST.get('job_id')
        action = request.POST.get('action')
        writer_id = request.POST.get('writer_id')
        process_team_id = request.POST.get('process_team_id')
        status_note = request.POST.get('status_note', '').strip()

        job = get_object_or_404(Job, id=job_id)

        if action == 'allocate_to_writer':
            if not writer_id:
                messages.error(request, 'Please select a writer to allocate.')
                return redirect('allocater_dashboard')

            writer = get_object_or_404(User, id=writer_id, role='writer')
            if not getattr(writer, 'is_approved', False):
                messages.error(request, 'Selected writer is not approved.')
                return redirect('allocater_dashboard')

            current_time = timezone.now()
            Job.objects.filter(id=job.id).update(
                allocated_to_id=writer.id,
                writer_status='open',
                status='allocated',
                status_note=status_note if status_note else '',
                start_time=current_time,
                end_time=job.strict_deadline
            )

            Notification.objects.create(
                user=writer, message=f'New job assigned: {job.job_id}', job=job, is_read=False
            )
            Notification.objects.create(
                user=request.user,
                message=f'Job {job.job_id} allocated to writer {writer.first_name or writer.username}',
                job=job,
                is_read=False
            )
            messages.success(request, f'Job {job.job_id} allocated to {writer.first_name or writer.username}.')

        elif action == 'allocate_to_process_team':
            if not process_team_id:
                messages.error(request, 'Please select a process team member.')
                return redirect('allocater_dashboard')

            process_member = get_object_or_404(User, id=process_team_id, role='process_team')
            if not getattr(process_member, 'is_approved', False):
                messages.error(request, 'Selected process team member is not approved.')
                return redirect('allocater_dashboard')

            Job.objects.filter(id=job.id).update(
                process_team_member_id=process_member.id,
                process_team_status='pending',
                status_note=status_note if status_note else ''
            )

            Notification.objects.create(
                user=process_member, message=f'Job assigned for processing: {job.job_id}', job=job, is_read=False
            )
            Notification.objects.create(
                user=request.user,
                message=f'Job {job.job_id} assigned to process team member {process_member.first_name or process_member.username}',
                job=job, is_read=False
            )
            messages.success(request, f'Job {job.job_id} assigned to {process_member.first_name or process_member.username}.')

        elif action == 'change_writer':
            if not writer_id:
                messages.error(request, 'Please select a new writer.')
                return redirect('allocater_dashboard')

            writer = get_object_or_404(User, id=writer_id, role='writer')
            if not getattr(writer, 'is_approved', False):
                messages.error(request, 'Selected writer is not approved.')
                return redirect('allocater_dashboard')

            old_writer = job.allocated_to
            current_time = timezone.now()

            Job.objects.filter(id=job.id).update(
                allocated_to_id=writer.id,
                writer_status='open',
                status='allocated',
                status_note=status_note,
                start_time=current_time,
                end_time=job.strict_deadline
            )

            Notification.objects.create(
                user=writer, message=f'Job reassigned to you: {job.job_id}', job=job, is_read=False
            )
            if old_writer:
                Notification.objects.create(
                    user=old_writer,
                    message=f'Job {job.job_id} has been reassigned to another writer.',
                    job=job,
                    is_read=False
                )
            Notification.objects.create(
                user=request.user, message=f'Writer changed for job {job.job_id}', job=job, is_read=False
            )
            messages.success(request, f'Job {job.job_id} reassigned to {writer.first_name or writer.username}.')

        elif action == 'change_process_team':
            if not process_team_id:
                messages.error(request, 'Please select a process team member.')
                return redirect('allocater_dashboard')

            process_member = get_object_or_404(User, id=process_team_id, role='process_team')
            if not getattr(process_member, 'is_approved', False):
                messages.error(request, 'Selected process team member is not approved.')
                return redirect('allocater_dashboard')

            old_process = job.process_team_member

            Job.objects.filter(id=job.id).update(
                process_team_member_id=process_member.id,
                process_team_status='pending',
                status_note=status_note
            )

            Notification.objects.create(
                user=process_member, message=f'Job assigned for processing: {job.job_id}', job=job, is_read=False
            )
            if old_process:
                Notification.objects.create(
                    user=old_process,
                    message=f'Job {job.job_id} has been reassigned to another team member.',
                    job=job,
                    is_read=False
                )
            Notification.objects.create(
                user=request.user, message=f'Process team member changed for job {job.job_id}', job=job, is_read=False
            )
            messages.success(request, f'Job {job.job_id} reassigned to {process_member.first_name or process_member.username}.')

        elif action == 'cancel':
            Job.objects.filter(id=job.id).update(
                status='cancel', writer_status='closed', process_team_status='closed', status_note=status_note
            )
            if job.allocated_to:
                Notification.objects.create(
                    user=job.allocated_to, message=f'Job {job.job_id} has been cancelled.', job=job, is_read=False
                )
            if job.process_team_member:
                Notification.objects.create(
                    user=job.process_team_member, message=f'Job {job.job_id} has been cancelled.', job=job, is_read=False
                )
            Notification.objects.create(
                user=request.user, message=f'Job {job.job_id} has been cancelled.', job=job, is_read=False
            )
            messages.success(request, f'Job {job.job_id} has been cancelled.')

        elif action in ['query', 'hold']:
            Job.objects.filter(id=job.id).update(status=action, status_note=status_note)
            if job.allocated_to:
                Notification.objects.create(
                    user=job.allocated_to, message=f'Job {job.job_id} status changed to {action.upper()}.', job=job, is_read=False
                )
            Notification.objects.create(
                user=request.user, message=f'Job {job.job_id} status updated to {action}.', job=job, is_read=False
            )
            messages.success(request, f'Job {job.job_id} status updated to {action}.')
        else:
            messages.error(request, 'Unknown action.')

        return redirect('allocater_dashboard')

    # stats
    total_jobs = Job.objects.count()
    total_assigned = Job.objects.filter(status='allocated').count()
    total_hold = Job.objects.filter(status='hold').count()
    total_cancel = Job.objects.filter(status='cancel').count()
    total_completed = Job.objects.filter(status='completed').count()
    total_in_progress = Job.objects.filter(
        Q(writer_status='in_progress') | Q(process_team_status='in_progress')
    ).count()

    stats = {
        'total_jobs': total_jobs,
        'total_assigned': total_assigned,
        'total_hold': total_hold,
        'total_cancel': total_cancel,
        'total_completed': total_completed,
        'total_in_progress': total_in_progress,
    }

    jobs = (
        Job.objects
        .filter(status__in=['drop', 'allocated', 'query', 'hold', 'cancel', 'completed'])
        .select_related('created_by', 'allocated_to', 'process_team_member')
        .order_by('-created_at')
    )

    writers = [u for u in User.objects.filter(role='writer') if getattr(u, 'is_approved', False)]
    process_team_members = [u for u in User.objects.filter(role='process_team') if getattr(u, 'is_approved', False)]

    try:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    except Exception:
        unread_count = 0

    return render(request, 'allocater/dashboard.html', {
        'jobs': jobs,
        'writers': writers,
        'process_team_members': process_team_members,
        'stats': stats,
        'unread_count': unread_count
    })

# --------------------------
# Detail page
# --------------------------
@role_required(allowed_roles=['allocater', 'admin', 'manager'])
def view_job(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    try:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    except Exception:
        unread_count = 0
    return render(request, 'allocater/view_job.html', {'job': job, 'unread_count': unread_count})

# --------------------------
# In Progress page with modal
# --------------------------
@role_required(allowed_roles=['allocater', 'admin', 'manager'])
def in_progress(request):
    writer_progress = (
        Job.objects.filter(writer_status='in_progress')
        .select_related('allocated_to', 'process_team_member')
        .order_by('-updated_at', '-created_at')
    )
    process_progress = (
        Job.objects.filter(process_team_status='in_progress')
        .select_related('allocated_to', 'process_team_member')
        .order_by('-updated_at', '-created_at')
    )
    writer_ids = set(writer_progress.values_list('id', flat=True))
    process_ids = set(process_progress.values_list('id', flat=True))
    total_in_progress = len(writer_ids | process_ids)

    writers = [u for u in User.objects.filter(role='writer') if getattr(u, 'is_approved', False)]
    process_team_members = [u for u in User.objects.filter(role='process_team') if getattr(u, 'is_approved', False)]

    try:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    except Exception:
        unread_count = 0

    return render(request, 'allocater/in_progress.html', {
        'writer_progress': writer_progress,
        'process_progress': process_progress,
        'total_in_progress': total_in_progress,
        'writers': writers,
        'process_team_members': process_team_members,
        'unread_count': unread_count
    })

# --------------------------
# Assigned page with modal
# --------------------------
@role_required(allowed_roles=['allocater', 'admin', 'manager'])
def assigned(request):
    jobs = (
        Job.objects.filter(status='allocated')
        .select_related('allocated_to', 'process_team_member')
        .order_by('-updated_at', '-created_at')
    )
    total_assigned = jobs.count()

    writers = [u for u in User.objects.filter(role='writer') if getattr(u, 'is_approved', False)]
    process_team_members = [u for u in User.objects.filter(role='process_team') if getattr(u, 'is_approved', False)]

    try:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    except Exception:
        unread_count = 0

    return render(request, 'allocater/assigned.html', {
        'jobs': jobs,
        'total_assigned': total_assigned,
        'writers': writers,
        'process_team_members': process_team_members,
        'unread_count': unread_count
    })

# --------------------------
# Completed page
# --------------------------
@role_required(allowed_roles=['allocater', 'admin', 'manager'])
def completed(request):
    jobs = (
        Job.objects.filter(status='completed')
        .select_related('allocated_to', 'process_team_member')
        .order_by('-updated_at', '-created_at')
    )
    total_completed = jobs.count()
    try:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    except Exception:
        unread_count = 0
    return render(request, 'allocater/completed.html', {
        'jobs': jobs, 'total_completed': total_completed, 'unread_count': unread_count
    })

# --------------------------
# Notifications
# --------------------------
@role_required(allowed_roles=['allocater', 'admin', 'manager'])
def notifications(request):
    all_notifications = Notification.objects.filter(
        user=request.user
    ).select_related('job').order_by('-created_at')
    unread_count = all_notifications.filter(is_read=False).count()

    return render(request, 'allocater/notifications.html', {
        'notifications': all_notifications,
        'unread_count': unread_count
    })

@role_required(allowed_roles=['allocater', 'admin', 'manager'])
def mark_all_read(request):
    if request.method == 'POST':
        updated_count = Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
        if updated_count > 0:
            messages.success(request, f'{updated_count} notification(s) marked as read.')
        else:
            messages.info(request, 'No unread notifications.')
    return redirect('allocater_notifications')

# --------------------------
# Profile
# --------------------------
@role_required(allowed_roles=['allocater', 'admin', 'manager'])
def profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', '')
        user.last_name = request.POST.get('last_name', '')
        user.email = request.POST.get('email', '')
        user.phone_number = request.POST.get('phone_number', '')
        user.save()
        messages.success(request, 'Profile updated successfully.')
        return redirect('allocater_profile')

    if request.user.date_joined:
        tenure_delta = timezone.now() - request.user.date_joined
        years = tenure_delta.days // 365
        months = (tenure_delta.days % 365) // 30
        days = (tenure_delta.days % 365) % 30
        tenure = f"{years} year(s), {months} month(s), {days} day(s)"
    else:
        tenure = "Not available"

    try:
        unread_count = Notification.objects.filter(user=request.user, is_read=False).count()
    except Exception:
        unread_count = 0

    return render(request, 'allocater/profile.html', {
        'user': request.user, 'tenure': tenure, 'unread_count': unread_count
    })
