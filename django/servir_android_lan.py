"""Ejecuta San Carlos en una red privada de pruebas, sin abrir un túnel."""
import argparse
import ipaddress
import os


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('ip', nargs='?', help='IPv4 del PC en la red de prueba.')
    args = parser.parse_args()
    try:
        ip = ipaddress.IPv4Address(args.ip or input('Escribe la IPv4 del adaptador Wi-Fi: ').strip())
    except ipaddress.AddressValueError:
        parser.error('Ingresa una IPv4 válida, por ejemplo 192.168.1.25.')
    redes = ('10.0.0.0/8', '172.16.0.0/12', '192.168.0.0/16')
    if not any(ip in ipaddress.ip_network(red) for red in redes):
        parser.error('Este lanzador solo admite una IPv4 privada.')
    os.environ.update({'DJANGO_SETTINGS_MODULE': 'config.settings', 'DJANGO_DEBUG': '0',
                       'DJANGO_PUBLIC_ORIGIN': '', 'DJANGO_ALLOWED_HOSTS': str(ip)})
    from django import setup
    from django.core.management import call_command
    from django.core.wsgi import get_wsgi_application
    from waitress import serve
    setup()
    call_command('collectstatic', interactive=False, verbosity=0)
    app = get_wsgi_application()
    print(f'URL de San Carlos en la red privada: http://{ip}:8000', flush=True)
    serve(app, host=str(ip), port=8000)


if __name__ == '__main__':
    main()
