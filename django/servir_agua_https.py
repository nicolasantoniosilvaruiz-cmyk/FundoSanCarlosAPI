"""Sirve la app en loopback detrás de un proxy HTTPS de confianza."""
import argparse
import os
import re

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from waitress import serve


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url', help='URL pública HTTPS, sin ruta.')
    parser.add_argument('--contacto', required=True, help='Correo de contacto para Web Push.')
    args = parser.parse_args()
    origin = args.url.rstrip('/')
    if not re.fullmatch(r'https://[a-zA-Z0-9.-]+', origin):
        parser.error('Ingresa una URL HTTPS sin ruta ni puerto.')
    if not re.fullmatch(r'[^@\s]+@[^@\s]+\.[^@\s]+', args.contacto):
        parser.error('Ingresa un correo de contacto válido.')
    os.environ.update({
        'DJANGO_SETTINGS_MODULE': 'config.settings', 'DJANGO_DEBUG': '0',
        'DJANGO_PUBLIC_ORIGIN': origin,
        'DJANGO_ALLOWED_HOSTS': origin.removeprefix('https://'),
        'PUSH_CONTACT': 'mailto:' + args.contacto,
    })
    application = get_wsgi_application()
    from django.contrib.auth import get_user_model

    # Evita que el arranque público exponga las contraseñas incluidas en el README.
    conocidos = {'admin': 'FundoDemo2026!', 'trabajador': 'CampoDemo2026!'}
    for user in get_user_model().objects.filter(username__in=conocidos, is_active=True):
        if user.check_password(conocidos[user.username]):
            parser.error(f"Cambia primero la contraseña de {user.username} con manage.py changepassword.")
    call_command('collectstatic', interactive=False, verbosity=0)
    print(f'Abre {origin}/agua/ en el teléfono. Ctrl+C para detener.', flush=True)
    serve(application, host='127.0.0.1', port=8000,
          trusted_proxy='127.0.0.1', trusted_proxy_headers={'x-forwarded-proto'},
          clear_untrusted_proxy_headers=True)


if __name__ == '__main__':
    main()
