from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'replace-me-with-a-secure-key-for-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = []

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'channels',

    # Local apps
    'usuarios.apps.UsuariosConfig',
    'clinica.apps.ClinicaConfig',
    'inventario.apps.InventarioConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'config_veterinaria.middleware.CurrentUserMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'config_veterinaria.middleware.MaintenanceModeMiddleware',
    'config_veterinaria.middleware.AccessLogMiddleware',
]

ROOT_URLCONF = 'config_veterinaria.urls'

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
                    'config_veterinaria.context_processors.main_nav',
            ],
        },
    },
]

WSGI_APPLICATION = 'config_veterinaria.wsgi.application'
ASGI_APPLICATION = 'config_veterinaria.asgi.application'

# Database
# https://docs.djangoproject.com/en/stable/ref/settings/#databases
DATABASES = {
    # Temporal: usar SQLite para aplicar migraciones localmente
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Si más adelante prefieres MySQL, restaura la configuración MySQL y completa la contraseña.

# Maintenance mode (returns 503 page when enabled)
MAINTENANCE_MODE = False

# Follow-up settings
FOLLOWUP_AUTO_ENABLED = True
FOLLOWUP_AUTO_DAYS = 30

# Reminder settings
REMINDER_HOURS_BEFORE = 24
REMINDER_SEND_WINDOW_MINUTES = 30
WHATSAPP_WEBHOOK_URL = ''
WHATSAPP_WEBHOOK_TOKEN = ''

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'es-ni'

TIME_ZONE = 'America/Managua'

USE_I18N = True
USE_L10N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

CHANNEL_LAYERS = {
    'default': {
        'BACKEND': 'channels.layers.InMemoryChannelLayer',
    }
}

# Auth redirects
LOGIN_REDIRECT_URL = '/'
# After logout redirect to the login page so the user can log in again
LOGOUT_REDIRECT_URL = '/accounts/login/'

# Login lockout
LOGIN_LOCKOUT_MAX_ATTEMPTS = 5
LOGIN_LOCKOUT_WINDOW_MINUTES = 15
LOGIN_LOCKOUT_BLOCK_MINUTES = 15

# Inventario alerts
INVENTARIO_ALERT_RECIPIENTS = []
INVENTARIO_STOCK_ALERT_ENABLED = True
INVENTARIO_VENCIMIENTO_ALERT_ENABLED = True
INVENTARIO_VENCIMIENTO_DIAS = 30

