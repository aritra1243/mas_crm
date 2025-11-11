import os
from pathlib import Path
from decouple import config

# -------------------------
# Paths
# -------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------
# Security and Debug
# -------------------------
SECRET_KEY = config('SECRET_KEY', default='django-insecure-your-secret-key-here')
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# -------------------------
# Installed Apps
# -------------------------
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Project apps
    'authentication',
    'super_admin',
    'admin_app',
    'manager',
    'marketing',
    'allocater',
    'writer',
    'process_team',
    'accounts',
]

# -------------------------
# Middleware
# -------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -------------------------
# URLs and WSGI
# -------------------------
ROOT_URLCONF = 'mas_crm.urls'
WSGI_APPLICATION = 'mas_crm.wsgi.application'
ASGI_APPLICATION = 'mas_crm.asgi.application'

# -------------------------
# Templates
# -------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'django.template.context_processors.media',
                'process_team.context_processors.process_unread_count',
            ],
        },
    },
]

# -------------------------
# Database - MongoDB via djongo
# -------------------------
DATABASES = {
    'default': {
        'ENGINE': 'djongo',
        'NAME': config('MONGO_DB_NAME', default='mas_crm'),
        'CLIENT': {
            'host': config('MONGO_HOST', default='localhost'),
            'port': int(config('MONGO_PORT', default=27017)),
        },
    }
}

# -------------------------
# Custom User Model
# -------------------------
AUTH_USER_MODEL = 'authentication.User'

# -------------------------
# Password Validators
# -------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -------------------------
# Internationalization
# -------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Asia/Kolkata'
USE_I18N = True
USE_TZ = True

# -------------------------
# Static and Media
# -------------------------
STATIC_URL = '/static/'
STATICFILES_DIRS = [os.path.join(BASE_DIR, 'static')]
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------
# Auth redirects - FIXED TO PREVENT REDIRECT LOOP
# -------------------------
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'  # Fixed redirection after login
LOGOUT_REDIRECT_URL = '/login/'  # Correct logout redirection

# -------------------------
# Sessions
# -------------------------
SESSION_COOKIE_AGE = 86400  # 24 hours
SESSION_SAVE_EVERY_REQUEST = True

# -------------------------
# CSRF settings - FIXED FOR DEVELOPMENT
# -------------------------
CSRF_COOKIE_SECURE = False if DEBUG else True  # Disabled for local dev, enabled for production
CSRF_COOKIE_HTTPONLY = True
CSRF_HEADER_NAME = 'HTTP_X_CSRFTOKEN'

# -------------------------
# Cookie settings
# -------------------------
SESSION_COOKIE_HTTPONLY = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False  # Set to False for better user experience
