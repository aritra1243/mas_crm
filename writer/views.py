# File: writer/views.py

from datetime import datetime, timedelta, timezone as dt_timezone
from decimal import Decimal
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from authentication.decorators import role_required
from authentication.models import Job, User, Notification

def _now():
    try:
        return timezone.now()
    except Exception:
        return datetime.now(dt_timezone.utc)

def _get_unread_count_from_session(request):
    me = request.user
    seen_key = 'writer_seen_allocs'
    seen_ids = set(request.session.get(seen_key, []))
    unread_count = Job.objects.filter(
        allocated_to=me,
        status='allocated'
    ).exclude(id__in=seen_ids).count()
    return unread_count

def notify_allocaters_about_writer_update(job, message):
    try:
        all_allocaters = list(User.objects.filter(role='allocater').only('id', 'is_approved'))
        for allocater in all_allocaters:
            if getattr(allocater, 'is_approved', False):
                try:
                    Notification.objects.create(
                        user=allocater,
                        job=job,
                        message=message,
                        is_read=False
                    )
                except Exception:
                    continue
    except Exception:
        pass

from decimal import Decimal
def _safe_decimal_convert(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    try:
        if hasattr(value, 'to_decimal'):
            return value.to_decimal()
    except:
        pass
    try:
        return Decimal(str(value))
    except:
        return value

def _prepare_job_for_save(job):
    update_fields = {}
    for field in job._meta.get_fields():
        if field.__class__.__name__ == 'DecimalField':
            field_name = field.name
            if hasattr(job, field_name):
                value = getattr(job, field_name)
                if value is not None:
                    converted = _safe_decimal_convert(value)
                    if converted is not None:
                        update_fields[field_name] = converted
    return update_fields

@role_required(allowed_roles=['writer'])
def home(request):
    me = request.user
    my_all = Job.objects.filter(allocated_to=me).order_by('-created_at')

    open_jobs = []
    for j in my_all:
        if j.status == 'allocated':
            open_jobs.append(j)
        elif j.status == 'process' and getattr(j, 'writer_status', '') != 'closed':
            open_jobs.append(j)

    closed_jobs = []
    for j in my_all:
        if j.status == 'completed':
            closed_jobs.append(j)
        elif getattr(j, 'writer_status', '') == 'closed':
            closed_jobs.append(j)

    open_issues = [j for j in my_all if j.status == 'query']
    close_issues = [j for j in my_all if j.status != 'query' and (j.status_note or '').strip()]

    now = _now()
    due_soon = []
    for j in open_jobs:
        if j.strict_deadline:
            delta = (j.strict_deadline - now).total_seconds()
            if 0 < delta <= 600:
                due_soon.append({
                    'id': j.id,
                    'job_id': getattr(j, 'job_id', f'JOB-{j.id}'),
                    'masked_job_id': j.get_masked_job_id(),
                    'seconds': int(delta),
                })

    seen_key = 'writer_seen_allocs'
    seen_ids = set(request.session.get(seen_key, []))
    newly_allocated = [j for j in open_jobs if (j.status == 'allocated' and j.id not in seen_ids)]
    request.session.setdefault(seen_key, list(seen_ids))

    unread_count = _get_unread_count_from_session(request)

    context = {
        'writer_name': me.first_name or me.username,
        'writer_email': me.email or '',
        'open_jobs': open_jobs,
        'closed_jobs': closed_jobs,
        'open_issues': open_issues,
        'close_issues': close_issues,
        'counts': {
            'total_job': len(my_all),
            'open_job': len(open_jobs),
            'close_job': len(closed_jobs),
            'open_issue': len(open_issues),
            'close_issue': len(close_issues),
        },
        'due_soon': due_soon,
        'newly_allocated': newly_allocated,
        'server_now_iso': now.isoformat(),
        'unread_count': unread_count,
    }
    return render(request, 'writer/home.html', context)

@role_required(allowed_roles=['writer'])
def complete_jobs(request):
    me = request.user
    my_all = Job.objects.filter(allocated_to=me).order_by('-updated_at')

    closed_jobs = []
    for j in my_all:
        if j.status == 'completed':
            closed_jobs.append(j)
        elif getattr(j, 'writer_status', '') == 'closed':
            closed_jobs.append(j)

    unread_count = _get_unread_count_from_session(request)
    return render(request, 'writer/complete_jobs.html', {
        'closed_jobs': closed_jobs,
        'unread_count': unread_count,
    })

@role_required(allowed_roles=['writer'])
def open_issues_list(request):
    me = request.user
    my_all = Job.objects.filter(allocated_to=me).order_by('-updated_at')
    open_issues = [j for j in my_all if j.status == 'query']
    unread_count = _get_unread_count_from_session(request)
    return render(request, 'writer/open_issues.html', {
        'open_issues': open_issues,
        'unread_count': unread_count,
    })

@role_required(allowed_roles=['writer'])
def close_issues_list(request):
    me = request.user
    my_all = Job.objects.filter(allocated_to=me).order_by('-updated_at')
    close_issues = [j for j in my_all if j.status != 'query' and (j.status_note or '').strip()]
    unread_count = _get_unread_count_from_session(request)
    return render(request, 'writer/close_issues.html', {
        'close_issues': close_issues,
        'unread_count': unread_count,
    })

@role_required(allowed_roles=['writer'])
def read_all_notifications(request):
    my_ids = list(
        Job.objects.filter(allocated_to=request.user, status='allocated').values_list('id', flat=True)
    )
    request.session['writer_seen_allocs'] = my_ids
    request.session.modified = True
    messages.success(request, 'All notifications marked as read.')
    return redirect('writer_notifications')

@role_required(allowed_roles=['writer'])
def notifications(request):
    me = request.user
    jobs = Job.objects.filter(allocated_to=me).order_by('-created_at')

    now = _now()
    due_soon_list = []
    for j in jobs:
        is_open = (j.status == 'allocated' or 
                   (j.status == 'process' and getattr(j, 'writer_status', '') != 'closed'))
        if is_open and j.strict_deadline:
            delta = (j.strict_deadline - now).total_seconds()
            if 0 < delta <= 600:
                minutes_left = int(delta / 60)
                due_soon_list.append({
                    'id': j.id,
                    'job_id': getattr(j, 'job_id', f'JOB-{j.id}'),
                    'masked_job_id': j.get_masked_job_id(),
                    'seconds': int(delta),
                    'minutes_left': minutes_left,
                    'strict_deadline': j.strict_deadline,
                    'status': j.status,
                })

    seen_key = 'writer_seen_allocs'
    seen_ids = set(request.session.get(seen_key, []))
    newly_allocated = []
    for j in jobs:
        if j.status == 'allocated' and j.id not in seen_ids:
            j.is_read = False
            newly_allocated.append(j)
        elif j.status == 'allocated':
            j.is_read = True

    unread_count = _get_unread_count_from_session(request)
    return render(request, 'writer/notifications.html', {
        'newly_allocated': newly_allocated,
        'due_soon': due_soon_list,
        'unread_count': unread_count,
    })

@role_required(allowed_roles=['writer'])
def profile(request):
    u = request.user
    joined = getattr(u, 'date_joined', None)
    years = months = days = 0
    if joined:
        now = _now()
        delta_days = (now.date() - joined.date()).days
        years = delta_days // 365
        rem = delta_days % 365
        months = rem // 30
        days = rem % 30
    unread_count = _get_unread_count_from_session(request)
    return render(request, 'writer/profile.html', {
        'email': u.email,
        'username': u.username,
        'org_id': getattr(u, 'org_id', None),
        'external_user_id': getattr(u, 'external_user_id', None),
        'date_joined': joined,
        'tenure': {'years': years, 'months': months, 'days': days},
        'unread_count': unread_count,
    })

@role_required(allowed_roles=['writer'])
def open_job_detail(request, job_id):
    job = get_object_or_404(Job, id=job_id, allocated_to=request.user)

    is_open = (job.status == 'allocated' or 
               (job.status == 'process' and getattr(job, 'writer_status', '') != 'closed'))
    if not is_open:
        messages.info(request, 'This job is not open for work.')
        return redirect('writer_home')

    if job.status == 'process' and getattr(job, 'writer_status', '') == 'in_progress':
        return redirect('writer_dashboard')

    if request.method == 'POST':
        if job.status == 'allocated':
            decimal_updates = _prepare_job_for_save(job)
            Job.objects.filter(id=job.id).update(
                status='process',
                writer_status='in_progress',
                start_time=_now(),
                **decimal_updates
            )
            job.refresh_from_db()

            # NEW: remember this job so dashboard focuses it
            request.session['writer_focus_job_id'] = job.id
            request.session.modified = True

            notify_allocaters_about_writer_update(
                job,
                f"Writer started working on job {job.get_masked_job_id()}"
            )
            messages.success(request, f'Job {job.get_masked_job_id()} is now In progress.')
            return redirect('writer_dashboard')

    unread_count = _get_unread_count_from_session(request)
    return render(request, 'writer/open_job_detail.html', {
        'job': job,
        'status_label': 'Open',
        'status_class': 'warning',
        'can_start': True,
        'unread_count': unread_count,
    })

@role_required(allowed_roles=['writer'])
def dashboard(request):
    """
    Show exactly one job while active.
    If a job was just started, honor the focus set in session.
    Otherwise, prefer the most recently started in-progress job.
    Fallback to the earliest allocated one.
    """
    all_jobs_qs = Job.objects.filter(
        allocated_to=request.user,
        status__in=['allocated', 'process'],
    ).order_by('strict_deadline')

    my_jobs = []
    for j in all_jobs_qs:
        if j.status == 'allocated':
            my_jobs.append(j)
        elif j.status == 'process' and getattr(j, 'writer_status', '') != 'closed':
            my_jobs.append(j)

    current_job = None

    # 1) Focused job after "Mark as In progress"
    focus_id = request.session.pop('writer_focus_job_id', None)
    if focus_id:
        for j in my_jobs:
            if j.id == focus_id:
                current_job = j
                break

    # 2) Otherwise, pick the most recent in-progress job by start_time
    if current_job is None:
        in_prog = [j for j in my_jobs if j.status == 'process' and getattr(j, 'writer_status', '') == 'in_progress']
        if in_prog:
            current_job = sorted(in_prog, key=lambda x: (x.start_time or _now()), reverse=True)[0]

    # 3) Otherwise, pick the nearest-deadline allocated job
    if current_job is None and my_jobs:
        allocated = [j for j in my_jobs if j.status == 'allocated']
        if allocated:
            current_job = allocated[0]
        else:
            current_job = my_jobs[0]

    unread_count = _get_unread_count_from_session(request)
    return render(request, 'writer/dashboard.html', {
        'current_job': current_job,
        'all_jobs': my_jobs,
        'unread_count': unread_count,
    })


@role_required(allowed_roles=['writer'])
def job_upload(request, job_id):
    job = get_object_or_404(Job, id=job_id, allocated_to=request.user)

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == 'query':
            decimal_updates = _prepare_job_for_save(job)
            Job.objects.filter(id=job.id).update(
                status='query',
                writer_status='pending',
                status_note=request.POST.get('query_note', ''),
                **decimal_updates
            )
            job.refresh_from_db()
            notify_allocaters_about_writer_update(
                job,
                f"Writer raised query for job {job.get_masked_job_id()}: {job.status_note[:100]}"
            )
            messages.success(request, 'Query submitted.')
            return redirect('writer_dashboard')

        if action == 'upload':
            structure_file = request.FILES.get('structure_file')
            final_copy = request.FILES.get('final_copy')
            software_files = request.FILES.get('software_files')

            if structure_file:
                job.structure_file = structure_file
            if final_copy:
                job.final_copy = final_copy
            if software_files:
                job.software_files = software_files

            try:
                job.save(update_fields=['structure_file', 'final_copy', 'software_files'])
            except Exception:
                job.save()

            decimal_updates = _prepare_job_for_save(job)
            Job.objects.filter(id=job.id).update(
                final_copy_summary=request.POST.get('final_copy_summary', ''),
                status='process',
                writer_status='closed',
                process_team_status='pending',
                end_time=_now(),
                **decimal_updates
            )
            job.refresh_from_db()

            notify_allocaters_about_writer_update(
                job,
                f"Writer completed job {job.get_masked_job_id()} and submitted for processing"
            )

            if job.process_team_member:
                try:
                    Notification.objects.create(
                        user=job.process_team_member,
                        job=job,
                        message=f"New job ready for processing: {job.get_masked_job_id()}",
                        is_read=False
                    )
                except Exception:
                    pass
            else:
                try:
                    all_process_members = list(User.objects.filter(role='process_team').only('id', 'is_approved'))
                    for member in all_process_members:
                        if getattr(member, 'is_approved', False):
                            try:
                                Notification.objects.create(
                                    user=member,
                                    job=job,
                                    message=f"New job ready for processing: {job.get_masked_job_id()}",
                                    is_read=False
                                )
                            except Exception:
                                continue
                except Exception:
                    pass

            messages.success(request, 'Work submitted successfully! Job moved to Process Team.')
            return redirect('writer_home')

    unread_count = _get_unread_count_from_session(request)
    return render(request, 'writer/job_upload.html', {
        'job': job,
        'unread_count': unread_count,
    })
