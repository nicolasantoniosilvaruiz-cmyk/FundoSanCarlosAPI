"""Configuración independiente para alojar la demo detrás de un proxy HTTPS."""
import os
from urllib.parse import unquote, urlsplit

from django.core.exceptions import ImproperlyConfigured


def https_origin(value):
    url = urlsplit(value.strip())
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.path not in ('', '/') or url.query or url.fragment):
        raise ImproperlyConfigured('Configura la URL HTTPS pública sin rutas.')
    return f'https://{url.netloc}'


raw_origin = os.environ.get('DJANGO_PUBLIC_ORIGIN') or os.environ.get('RENDER_EXTERNAL_URL', '')
origin = https_origin(raw_origin)
if len(os.environ.get('DJANGO_SECRET_KEY', '')) < 32:
    raise ImproperlyConfigured('Configura una clave Django privada de al menos 32 caracteres.')

database = urlsplit(os.environ.get('DATABASE_URL', ''))
if database.scheme not in ('postgres', 'postgresql') or not (database.hostname and database.username and database.path.strip('/')):
    raise ImproperlyConfigured('DATABASE_URL debe apuntar a PostgreSQL persistente.')

from .settings import *  # noqa: E402,F403

DEBUG = False
PUBLIC_ORIGIN = origin
ALLOWED_HOSTS = [urlsplit(origin).hostname]
CSRF_TRUSTED_ORIGINS = [origin]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_REDIRECT_EXEMPT = [r'^salud/$']
# Este perfil se usa detrás del proxy HTTPS del alojamiento.
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SECURE_HSTS_SECONDS = 86400
SECURE_REFERRER_POLICY = 'same-origin'
DATABASES = {'default': {
    'ENGINE': 'django.db.backends.postgresql',
    'NAME': unquote(database.path.strip('/')),
    'USER': unquote(database.username),
    'PASSWORD': unquote(database.password or ''),
    'HOST': database.hostname,
    'PORT': database.port or 5432,
    'CONN_MAX_AGE': 60,
    'CONN_HEALTH_CHECKS': True,
    'OPTIONS': {'sslmode': 'require'},
}}
