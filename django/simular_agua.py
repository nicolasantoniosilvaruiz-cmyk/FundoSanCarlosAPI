"""Envía lecturas por la misma interfaz que utilizará el ESP32."""
import argparse
import getpass
import json
import time
import uuid
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class SinRedirecciones(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8000')
    parser.add_argument('--codigo', default='agua-simulador')
    parser.add_argument('--pausa', type=float, default=4)
    parser.add_argument('niveles', nargs='*', default=['78', '25', '20', '85'])
    args = parser.parse_args()
    base = urlsplit(args.url)
    if (base.scheme not in ('http', 'https') or not base.hostname or base.username
            or base.password or base.query or base.fragment or base.path not in ('', '/')
            or (base.scheme == 'http' and base.hostname not in ('127.0.0.1', 'localhost'))):
        parser.error('Usa una URL HTTPS de la app o http://127.0.0.1:8000.')
    if args.pausa < 0:
        parser.error('La pausa no puede ser negativa.')
    token = getpass.getpass('Token del dispositivo (no se muestra): ').strip()
    opener = build_opener(SinRedirecciones)
    for index, pct in enumerate(args.niveles):
        event = {'id': str(uuid.uuid4()), 'porcentaje': pct, 'tomada_en': datetime.now(timezone.utc).isoformat()}
        req = Request(args.url.rstrip('/') + '/api/agua/mediciones/', data=json.dumps(event).encode(), headers={
            'Content-Type': 'application/json', 'Authorization': f'Bearer {token}', 'X-Dispositivo': args.codigo,
        }, method='POST')
        try:
            with opener.open(req, timeout=45) as response:
                result = json.load(response)
                print(f"{pct}% | HTTP {response.status} | alerta nueva: {'sí' if result['alerta_nueva'] else 'no'}")
        except HTTPError as exc:
            raise SystemExit(f'{pct}%: HTTP {exc.code} {exc.read(500).decode(errors="replace")}') from None
        except URLError as exc:
            raise SystemExit(f'No se pudo conectar con Django: {exc.reason}') from None
        if index < len(args.niveles) - 1:
            time.sleep(args.pausa)


if __name__ == '__main__':
    main()
