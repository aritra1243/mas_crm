# process_team/views.py - COMPLETE UPDATED FILE
from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from authentication.decorators import role_required
from authentication.models import Job, Notification, User
from authentication.utils import bundle_uploaded_files, FileBundleError

# ---------------- HELPERS ----------------
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

# ---------------- DASHBOARD ----------------
@role_required(allowed_roles=['process_team'])
def dashboard(request):
    """
    Show jobs that need process team work with writer-style metrics.
    """
    me = request.user

    # Jobs that currently need processing (assigned to me or unassigned pool)
    jobs_in_process = (
        Job.objects
        .filter(
            Q(process_team_member=me, status__in=['process', 'decoration'],
              process_team_status__in=['pending', 'in_progress']) |
            Q(process_team_member__isnull=True, status__in=['process', 'decoration'],
              process_team_status='pending')
        )
        .select_related('allocated_to', 'process_team_member', 'decoration_assigned_to')
        .order_by('strict_deadline')
    )

    # Decoration work assigned specifically to this process team member
    decoration_queue_qs = Job.objects.filter(
        decoration_assigned_to=me,
        decoration_status__in=['pending', 'in_progress'],
        decoration_assigned_type='process_team'
    )
    decoration_queue = (
        decoration_queue_qs
        .select_related('allocated_to', 'process_team_member')
        .order_by('strict_deadline')
    )

    # Recently completed or wrapped up items (either processing or decoration)
    completed_queryset = Job.objects.filter(
        Q(process_team_member=me, process_team_status='completed') |
        Q(decoration_assigned_to=me, decoration_status='completed')
    ).select_related('allocated_to', 'process_team_member', 'decoration_assigned_to')
    jobs_completed = completed_queryset.order_by('-updated_at', '-created_at')[:10]

    # Totals for dashboard cards
    total_pipeline_count = Job.objects.filter(
        Q(process_team_member=me) |
        Q(process_team_member__isnull=True, status__in=['process', 'decoration'],
          process_team_status='pending') |
        Q(decoration_assigned_to=me, decoration_status__in=['pending', 'in_progress'],
          decoration_assigned_type='process_team')
    ).count()

    my_assigned = Job.objects.filter(process_team_member=me)
    status_breakdown = {
        'pending': my_assigned.filter(process_team_status='pending').count(),
        'in_progress': my_assigned.filter(process_team_status='in_progress').count(),
        'completed': my_assigned.filter(process_team_status='completed').count(),
    }

    awaiting_pool_count = jobs_in_process.filter(process_team_member__isnull=True).count()
    awaiting_assigned_count = jobs_in_process.count() - awaiting_pool_count

    return render(
        request,
        'process_team/dashboard.html',
        {
            'jobs_in_process': jobs_in_process,
            'jobs_completed': jobs_completed,
            'decoration_queue': decoration_queue,
            'counts': {
                'total_jobs': total_pipeline_count,
                'in_process': jobs_in_process.count(),
                'decoration': decoration_queue.count(),
                'completed': completed_queryset.count(),
            },
            'status_breakdown': status_breakdown,
            'awaiting_pool_count': awaiting_pool_count,
            'awaiting_assigned_count': awaiting_assigned_count,
            'process_unread_count': _pt_unread_count(request.user),
        },
    )

# ---------------- JOB UPLOAD ----------------
@role_required(allowed_roles=['process_team'])
def job_upload(request, job_id):
    job = get_object_or_404(Job, id=job_id)
    is_decoration_assignment = (
        job.decoration_assigned_to == request.user and
        job.decoration_assigned_type == 'process_team' and
        job.status == 'decoration'
    )
    
    # Allow jobs in 'decoration' status to be processed
    if job.status not in ('decoration', 'process', 'completed'):
        job.status = 'decoration'  # Changed from 'process' to 'decoration'
        job.save(update_fields=['status', 'updated_at'])
    
    if request.method == 'POST':
        upload_type = request.POST.get('upload_type')
        
        if upload_type == 'ai_plag':
            # AI/Plag stage - update files but keep in decoration status
            update_fields = []
            if request.FILES.get('final_file'):
                job.ai_plag_final_file = request.FILES['final_file']
                update_fields.append('ai_plag_final_file')
            if request.FILES.get('ai_report'):
                job.ai_plag_ai_report = request.FILES['ai_report']
                update_fields.append('ai_plag_ai_report')
            if request.FILES.get('plag_report'):
                job.ai_plag_plag_report = request.FILES['plag_report']
                update_fields.append('ai_plag_plag_report')
            software_files = request.FILES.getlist('software')
            if software_files:
                try:
                    bundled = bundle_uploaded_files(
                        software_files,
                        f"{job.job_id}_process_ai_software"
                    )
                except FileBundleError as exc:
                    messages.error(request, str(exc))
                    return redirect('process_team_job_upload', job_id=job.id)
                job.ai_plag_software = bundled
                update_fields.append('ai_plag_software')
            
            # Update process team status to in_progress
            job.process_team_status = 'in_progress'
            update_fields.append('process_team_status')
            if job.process_team_member is None:
                job.process_team_member = request.user
                update_fields.append('process_team_member')

            # If this process team member is also handling decoration, mark decoration in progress
            if (
                job.decoration_assigned_to == request.user and
                job.decoration_assigned_type == 'process_team' and
                job.decoration_status != 'in_progress'
            ):
                job.decoration_status = 'in_progress'
                update_fields.append('decoration_status')

            job.updated_at = timezone.now()
            update_fields.append('updated_at')
            job.save(update_fields=update_fields)
            
            # Notify allocaters about progress
            try:
                allocaters = User.objects.filter(role__in=['allocater', 'admin', 'manager'])
                for allocater in allocaters:
                    if getattr(allocater, 'is_approved', False):
                        Notification.objects.create(
                            user=allocater,
                            job=job,
                            message=f"Process team uploaded AI/Plag files for job {job.get_masked_job_id()}.",
                            is_read=False
                        )
            except Exception:
                pass
            
            messages.success(request, 'AI/Plag files uploaded. Job remains in decoration queue.')
            return redirect('process_team_job_upload', job_id=job.id)
        
        elif upload_type == 'decoration':
            # Final decoration stage - upload and complete
            update_fields = []
            final_file = (
                request.FILES.get('decoration_final') or
                request.FILES.get('final_file')
            )
            if final_file:
                job.decoration_final_file = final_file
                update_fields.append('decoration_final_file')
            ai_report_file = (
                request.FILES.get('decoration_ai_report') or
                request.FILES.get('ai_report')
            )
            if ai_report_file:
                job.decoration_ai_report = ai_report_file
                update_fields.append('decoration_ai_report')
            plag_report_file = (
                request.FILES.get('decoration_plag_report') or
                request.FILES.get('plag_report')
            )
            if plag_report_file:
                job.decoration_plag_report = plag_report_file
                update_fields.append('decoration_plag_report')
            final_software_files = request.FILES.getlist('decoration_software')
            if not final_software_files:
                final_software_files = request.FILES.getlist('software')
            if final_software_files:
                try:
                    bundled = bundle_uploaded_files(
                        final_software_files,
                        f"{job.job_id}_process_decor_software"
                    )
                except FileBundleError as exc:
                    messages.error(request, str(exc))
                    return redirect('process_team_job_upload', job_id=job.id)
                job.decoration_software = bundled
                update_fields.append('decoration_software')
            decorated_alt = (
                request.FILES.get('decoration_alternative') or
                request.FILES.get('decorated_file')
            )
            if decorated_alt:
                job.decoration_decorated_file = decorated_alt
                update_fields.append('decoration_decorated_file')
            
            # Mark process team work as completed
            job.process_team_status = 'completed'
            update_fields.append('process_team_status')

            is_process_team_decorator = (
                job.decoration_assigned_to == request.user and
                job.decoration_assigned_type == 'process_team'
            )

            if is_process_team_decorator:
                if job.decoration_status != 'completed':
                    job.decoration_status = 'completed'
                    update_fields.append('decoration_status')
                if job.status != 'completed':
                    job.status = 'completed'
                    update_fields.append('status')
            else:
                # Keep job in decoration queue until allocator assigns a decorator
                if job.status != 'decoration':
                    job.status = 'decoration'
                    update_fields.append('status')
                if job.decoration_status not in ['pending', 'in_progress']:
                    job.decoration_status = 'pending'
                    update_fields.append('decoration_status')

            job.updated_at = timezone.now()
            update_fields.append('updated_at')
            job.save(update_fields=update_fields)
            
            # Notify allocaters
            try:
                allocaters = User.objects.filter(role__in=['allocater', 'admin', 'manager'])
                for allocater in allocaters:
                    if getattr(allocater, 'is_approved', False):
                        Notification.objects.create(
                            user=allocater,
                            job=job,
                            message=(
                                f"Process team completed job {job.get_masked_job_id()}."
                                if is_process_team_decorator
                                else f"Process team uploaded final files for job {job.get_masked_job_id()}. Ready for decoration assignment."
                            ),
                            is_read=False
                        )
                # Notify allocated writer if present when fully completed
                if is_process_team_decorator and job.allocated_to:
                    Notification.objects.create(
                        user=job.allocated_to,
                        job=job,
                        message=f"Process team has completed decoration for job {job.get_masked_job_id()}.",
                        is_read=False
                    )
                if is_process_team_decorator:
                    Notification.objects.create(
                        user=request.user,
                        job=job,
                        message=f"You completed decoration for job {job.get_masked_job_id()}.",
                        is_read=False
                    )
            except Exception:
                pass
            
            if is_process_team_decorator:
                messages.success(request, 'Decoration files uploaded. Job marked as completed and sent to Allocater.')
            else:
                messages.success(request, 'Final files uploaded. Awaiting decoration assignment.')
            return redirect('process_team_dashboard')
        
        messages.error(request, 'Select a valid upload type.')
    
    return render(
        request,
        'process_team/job_upload.html',
        {
            'job': job,
            'is_decoration_assignment': is_decoration_assignment,
            'process_unread_count': _pt_unread_count(request.user),
        }
    )

# ---------------- NOTIFICATIONS ----------------
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
    for j in Job.objects.filter(
        process_team_member=me, 
        status__in=['process', 'decoration']
    ).only('id', 'job_id', 'strict_deadline'):
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
    Djongo dislikes boolean filters, so collect ids in Python first.
    """
    if request.method == 'POST':
        updated = 0
        try:
            qs = (
                Notification.objects
                .filter(user=request.user)
                .only('id', 'is_read')
            )
            for note in qs:
                if getattr(note, 'is_read', False):
                    continue
                note.is_read = True
                note.save(update_fields=['is_read'])
                updated += 1
        except Exception:
            updated = 0
        
        if updated:
            request.session['process_last_mark_all'] = timezone.now().isoformat()
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

# ---------------- PROFILE ----------------
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
