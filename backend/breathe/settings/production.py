from .base import *
import urllib.parse as urlparse

DEBUG = False

SECRET_KEY = os.getenv('SECRET_KEY', SECRET_KEY)
if SECRET_KEY == 'django-insecure-development-secret-key-breathe-esg':
    raise ValueError('Set SECRET_KEY in production')

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', '*').split(',')

db_url = os.getenv('DATABASE_URL')
if db_url:
    url = urlparse.urlparse(db_url)
    DATABASES['default'] = {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': url.path[1:],
        'USER': url.username,
        'PASSWORD': url.password,
        'HOST': url.hostname,
        'PORT': url.port,
        # Supabase free tier kills idle connections and Django will get connection closed errors on reuse
        'CONN_MAX_AGE': 0,
        'OPTIONS': {
            'connect_timeout': 10,
            'options': '-c statement_timeout=30000',
        },
    }
else:
    # Supabase free tier kills idle connections and Django will get connection closed errors on reuse
    DATABASES['default']['CONN_MAX_AGE'] = 0
    DATABASES['default']['OPTIONS'] = {
        'connect_timeout': 10,
        'options': '-c statement_timeout=30000',
    }

# Register DatabaseHealthMiddleware before CommonMiddleware
MIDDLEWARE = list(MIDDLEWARE)
common_middleware_index = MIDDLEWARE.index('django.middleware.common.CommonMiddleware')
MIDDLEWARE.insert(common_middleware_index, 'breathe.middleware.DatabaseHealthMiddleware')

CORS_ALLOWED_ORIGINS = os.getenv('CORS_ALLOWED_ORIGINS', '').split(',')
if not CORS_ALLOWED_ORIGINS or CORS_ALLOWED_ORIGINS == ['']:
    CORS_ALLOW_ALL_ORIGINS = True
else:
    CORS_ALLOW_ALL_ORIGINS = False
