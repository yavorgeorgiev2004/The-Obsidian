"""
The Obsidian Hotel Platform — Django Settings
"""
from pathlib import Path
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

# ── SECURITY ──────────────────────────────────────────────
SECRET_KEY = config('SECRET_KEY')
DEBUG       = config('DEBUG', default=False, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost').split(',')

# ── APPLICATIONS ──────────────────────────────────────────
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
]

THIRD_PARTY_APPS = [
    'allauth',
    'allauth.account',
]

LOCAL_APPS = [
    'core',
    'accounts',
    'rooms',
    'bookings',
    'packages',
    'concierge',
    'dashboard',
    'relocations',
    'maintenance',
    'complaints',
    'memberships',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

SITE_ID = 1

# ── MIDDLEWARE ────────────────────────────────────────────
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise serves static files in production, straight after security.
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]

ROOT_URLCONF = 'obsidian_hotel.urls'

# ── TEMPLATES ─────────────────────────────────────────────
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'obsidian_hotel.wsgi.application'

# ── DATABASE ──────────────────────────────────────────────
# Use the DATABASE_URL environment variable when present (e.g. the
# Postgres database Railway provides in production); otherwise fall back
# to local SQLite for development. This keeps the data store configuration
# in a single place that can be switched by one environment variable.
import dj_database_url

DATABASES = {
    'default': dj_database_url.config(
        default=f'sqlite:///{BASE_DIR / "db.sqlite3"}',
        conn_max_age=600,
    )
}

# ── AUTH ──────────────────────────────────────────────────
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# ── ALLAUTH ───────────────────────────────────────────────
# replaced by ACCOUNT_SIGNUP_FIELDS
# replaced by ACCOUNT_SIGNUP_FIELDS
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_EMAIL_VERIFICATION    = 'none'
LOGIN_REDIRECT_URL             = '/dashboard/'
LOGOUT_REDIRECT_URL            = '/'
LOGIN_URL                      = '/accounts/login/'

# ── INTERNATIONALISATION ──────────────────────────────────
LANGUAGE_CODE = 'en-gb'
TIME_ZONE     = 'Europe/London'
USE_I18N      = True
USE_TZ        = True

# ── STATIC & MEDIA ────────────────────────────────────────
STATIC_URL   = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static']
STATIC_ROOT  = BASE_DIR / 'staticfiles'

# Let WhiteNoise compress and cache static files in production.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'},
}

MEDIA_URL    = '/media/'
MEDIA_ROOT   = BASE_DIR / 'media'

# Hosts and origins Django will trust. CSRF_TRUSTED_ORIGINS is required by
# Django for forms/logins to work on the deployed HTTPS domain. Add your
# Railway domain to both via environment variables in production.
CSRF_TRUSTED_ORIGINS = config(
    'CSRF_TRUSTED_ORIGINS',
    default='https://*.railway.app',
).split(',')

# ── STRIPE ────────────────────────────────────────────────
STRIPE_PUBLIC_KEY      = config('STRIPE_PUBLIC_KEY')
STRIPE_SECRET_KEY      = config('STRIPE_SECRET_KEY')
STRIPE_WEBHOOK_SECRET  = config('STRIPE_WEBHOOK_SECRET')

# ── MISC ──────────────────────────────────────────────────
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# allauth v0.56+ settings
ACCOUNT_SIGNUP_FIELDS = ['email*', 'password1*', 'password2*']
