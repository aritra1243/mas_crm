from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from authentication.decorators import role_required
from authentication.models import User, Job

@role_required(allowed_roles=['super_admin'])
def dashboard(request):
    """Super Admin Dashboard - View overall statistics and role distribution"""

    # Calculate all counts in Python to avoid Djongo boolean filter issues
    all_users = list(User.objects.all())
    total_users = len(all_users)
    pending_approvals = len([u for u in all_users if not getattr(u, 'is_approved', False)])
    total_jobs = Job.objects.count()

    # Get role distribution (avoiding using Djongo-related aggregation issues)
    role_distribution = {}
    for role, label in User.ROLE_CHOICES:
        role_distribution[label] = len([u for u in all_users if u.role == role])

    context = {
        'total_users': total_users,
        'pending_approvals': pending_approvals,
        'total_jobs': total_jobs,
        'role_distribution': role_distribution,
    }
    return render(request, 'super_admin/dashboard.html', context)


@role_required(allowed_roles=['super_admin'])
def pending_users(request):
    """Super Admin - Manage pending user approvals"""

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')

        user = get_object_or_404(User, id=user_id)

        if action == 'approve':
            user.is_approved = True
            user.save()
            messages.success(request, f'User {user.first_name} approved successfully!')
        elif action == 'reject':
            user_name = user.first_name
            user.delete()
            messages.success(request, f'User {user_name} rejected and removed!')

        return redirect('super_admin_pending')

    # Get all users and filter pending ones in Python to avoid Djongo boolean filter issues
    all_users = list(User.objects.all().order_by('-created_at'))
    pending = [u for u in all_users if not getattr(u, 'is_approved', False)]
    
    context = {'pending_users': pending}
    return render(request, 'super_admin/pending.html', context)


@role_required(allowed_roles=['super_admin'])
def manage_roles(request):
    """Super Admin - Manage user roles"""

    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        new_role = request.POST.get('role')

        user = get_object_or_404(User, id=user_id)
        user.role = new_role
        user.save()

        messages.success(request, f'Role updated successfully for {user.first_name}!')
        return redirect('super_admin_roles')

    # Get all users and filter approved ones in Python to avoid Djongo boolean filter issues
    all_users = list(User.objects.all().order_by('role', 'first_name'))
    approved_users = [u for u in all_users if getattr(u, 'is_approved', False)]
    
    context = {
        'users': approved_users,
        'role_choices': User.ROLE_CHOICES,
    }
    return render(request, 'super_admin/role.html', context)