import os
from django.core.wsgi import get_wsgi_application

if os.getenv('RENDER') or os.getenv('RAILWAY_ENVIRONMENT'):
    default_settings = 'breathe.settings.production'
else:
    default_settings = 'breathe.settings.local'

os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    os.getenv('DJANGO_SETTINGS_MODULE', default_settings),
)
application = get_wsgi_application()
