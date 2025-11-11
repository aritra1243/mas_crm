# marketing/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from authentication.decorators import role_required
from authentication.models import Job
import uuid

def _is_admin(user):
    """Allow only Admin or Super Admin, or Django superuser."""
    return getattr(user, 'role', '') in ('admin', 'super_admin') or getattr(user, 'is_superuser', False)

@role_required(allowed_roles=['marketing'])
def dashboard(request):
    """Only the current marketing agent’s jobs and summaries."""
    my_jobs = Job.objects.filter(created_by=request.user).order_by('-created_at')

    context = {
        'jobs': my_jobs,
        'total_jobs': my_jobs.count(),
        'dropped': my_jobs.filter(status='drop').count(),
        'allocated': my_jobs.filter(status='allocated').count(),
        'completed': my_jobs.filter(status='completed').count(),
        'hold': my_jobs.filter(status='hold').count(),
    }
    return render(request, 'marketing/dashboard.html', context)

@role_required(allowed_roles=['marketing'])
def job_drop(request):
    """Create a job. Accept optional Job ID, otherwise auto-generate."""
    if request.method == 'POST':
        provided = (request.POST.get('job_id') or '').strip()
        if provided:
            job_id = provided.upper()
            if not job_id.startswith('JOB-'):
                job_id = f'JOB-{job_id}'
            if Job.objects.filter(job_id=job_id).exists():
                messages.error(request, f'Job ID {job_id} already exists. Please choose another.')
                return render(request, 'marketing/job_drop.html')
        else:
            job_id = f"JOB-{uuid.uuid4().hex[:8].upper()}"

        topic = request.POST.get('topic', '')
        word_count = request.POST.get('word_count') or 0
        referencing_style = request.POST.get('referencing_style', '')
        writing_style = request.POST.get('writing_style', '')
        instruction = request.POST.get('instruction')
        expected_deadline = request.POST.get('expected_deadline')
        strict_deadline = request.POST.get('strict_deadline')
        value = request.POST.get('value') or 0
        attachment = request.FILES.get('attachment')

        Job.objects.create(
            job_id=job_id,
            created_by=request.user,
            topic=topic,
            word_count=int(word_count),
            referencing_style=referencing_style,
            writing_style=writing_style,
            instruction=instruction,
            expected_deadline=expected_deadline,
            strict_deadline=strict_deadline,
            value=value,
            attachment=attachment,
            status='drop'
        )

        messages.success(request, f'Job {job_id} created successfully!')
        return redirect('marketing_dashboard')

    return render(request, 'marketing/job_drop.html')

@role_required(allowed_roles=['marketing'])
def my_dropped_jobs(request):
    """List only this agent’s dropped jobs."""
    dropped_jobs = Job.objects.filter(created_by=request.user, status='drop').order_by('-created_at')
    return render(request, 'marketing/view_dropped.html', {'jobs': dropped_jobs})

@role_required(allowed_roles=['marketing', 'admin', 'super_admin'])
def edit_job(request, job_id):
    """Edit a job. Only Admin or Super Admin may actually save changes."""
    job = get_object_or_404(Job, id=job_id)

    if not _is_admin(request.user):
        messages.error(request, 'Only Admin can edit jobs.')
        return redirect('marketing_my_dropped')

    if request.method == 'POST':
        job.topic = request.POST.get('topic', job.topic)
        wc = request.POST.get('word_count')
        job.word_count = int(wc) if wc else job.word_count
        job.referencing_style = request.POST.get('referencing_style', job.referencing_style)
        job.writing_style = request.POST.get('writing_style', job.writing_style)
        job.instruction = request.POST.get('instruction', job.instruction)
        job.expected_deadline = request.POST.get('expected_deadline', job.expected_deadline)
        job.strict_deadline = request.POST.get('strict_deadline', job.strict_deadline)
        job.value = request.POST.get('value', job.value)
        if request.FILES.get('attachment'):
            job.attachment = request.FILES.get('attachment')
        job.save()
        messages.success(request, f'Job {job.job_id} updated.')
        return redirect('marketing_my_dropped')

    return render(request, 'marketing/job_edit.html', {'job': job})

@role_required(allowed_roles=['marketing', 'admin', 'super_admin'])
def delete_job(request, job_id):
    """Delete a job. Only Admin or Super Admin may delete."""
    job = get_object_or_404(Job, id=job_id)

    if not _is_admin(request.user):
        messages.error(request, 'Only Admin can delete jobs.')
        return redirect('marketing_my_dropped')

    if request.method == 'POST':
        jid = job.job_id
        job.delete()
        messages.success(request, f'Job {jid} deleted.')
        return redirect('marketing_my_dropped')

    messages.info(request, 'Send a POST to delete this job.')
    return redirect('marketing_my_dropped')
