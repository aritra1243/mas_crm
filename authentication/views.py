# authentication/views.py
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.utils.http import url_has_allowed_host_and_scheme
from django.conf import settings

from .models import User


def register_view(request):
    """User registration view"""
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        phone_number = request.POST.get('phone_number')
        password = request.POST.get('password')
        confirm_password = request.POST.get('confirm_password')

        # Validation
        if password != confirm_password:
            messages.error(request, 'Passwords do not match!')
            return render(request, 'authentication/register.html')

        if User.objects.filter(username=email).exists() or User.objects.filter(email=email).exists():
            messages.error(request, 'Email already registered!')
            return render(request, 'authentication/register.html')

        # Create user
        try:
            User.objects.create_user(
                username=email,
                email=email,
                password=password,
                first_name=name,
                phone_number=phone_number,
                is_approved=False,  # waits for approval
                role='marketing'    # default role
            )
            messages.success(request, 'Registration successful! Please wait for admin approval.')
            return redirect('login')
        except Exception as e:
            messages.error(request, f'Registration failed: {str(e)}')
            return render(request, 'authentication/register.html')

    return render(request, 'authentication/register.html')


def _role_route(user):
    """Map role to landing route. Writers go to Home."""
    return {
        'writer': 'writer_home',
        'marketing': 'marketing_dashboard',
        'allocater': 'allocater_dashboard',
        'process_team': 'process_team_dashboard',
        'admin': 'admin_dashboard',
        'super_admin': 'super_admin_dashboard',
        'manager': 'manager_dashboard',
        'accounts': 'accounts_dashboard',
    }.get(getattr(user, 'role', ''), 'login')


def login_view(request):
    """User login view"""
    if request.user.is_authenticated:
        return redirect('dashboard_redirect')

    if request.method == 'POST':
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = authenticate(request, username=email, password=password)

        if user is not None:
            if user.is_approved or user.role == 'super_admin':
                login(request, user)
                messages.success(request, f'Welcome {user.first_name or user.username}!')

                # Respect ?next= if safe
                nxt = request.POST.get('next') or request.GET.get('next')
                if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
                    return redirect(nxt)

                return redirect(_role_route(user))
            else:
                messages.warning(request, 'Please wait for admin approval!')
        else:
            messages.error(request, 'Invalid email or password!')

    return render(request, 'authentication/login.html')


@login_required
def logout_view(request):
    """User logout view"""
    logout(request)
    messages.success(request, 'Logged out successfully!')
    return redirect('login')


@login_required
def dashboard_redirect(request):
    """Redirect user to appropriate dashboard based on role"""
    route = _role_route(request.user)

    if route == 'login':
        messages.error(request, 'Invalid user role. Please contact administrator.')
        logout(request)
        return redirect('login')

    return redirect(route)
