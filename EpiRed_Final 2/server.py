"""Servidor HTTP de EpiRed. Requiere solo Python 3.10+.

Los cambios manuales de registros se guardan únicamente en RAM hasta reiniciar
el servidor; no se guardan datos personales ni existe acceso multiusuario.
"""
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
from pathlib import Path
from threading import RLock
import json
import os
from engine import (ENFERMEDADES, NOMBRES, crear_red, Zona,
                    plan_traslado, cobertura_alerta, continuidad_red,
                    plan_brigadas, plan_insumos)

ROOT = Path(__file__).resolve().parent
CAMBIOS = {}
LOCK = RLock()


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT / 'static'), **kwargs)

    def log_message(self, format, *args):
        super().log_message(format, *args)

    def do_GET(self):
        ruta = urlparse(self.path)
        if not ruta.path.startswith('/api/'):
            return super().do_GET()
        query = {k: v[0] for k, v in parse_qs(ruta.query, keep_blank_values=True).items()}
        try:
            with LOCK:
                cambios = CAMBIOS.copy()
            enfermedad = query.get('enfermedad', 'COVID-19')
            red = crear_red(enfermedad, cambios)
            op = ruta.path.removeprefix('/api/')
            if op in ('estado', 'red'):
                data = red.exportar(enfermedad)
                data['modificaciones'] = sum(1 for (enf, _id) in cambios if enf == enfermedad)
            elif op == 'operaciones/traslado':
                data = plan_traslado(red, query.get('origen', 'A'),
                                     query.get('destino', 'F'), query.get('via', 'D'))
            elif op == 'operaciones/alerta':
                data = cobertura_alerta(red, query.get('origen', 'A'),
                                       int(query.get('saltos', '2')))
            elif op == 'operaciones/continuidad':
                data = continuidad_red(red, query.get('desde', 'G'), query.get('hasta', 'J'))
            elif op == 'operaciones/brigadas':
                data = plan_brigadas(red)
            elif op == 'operaciones/insumos':
                destinos = query.get('destinos', 'B,C,D,E,F,G,H,I,J')
                ids = [s.strip().upper() for s in destinos.split(',') if s.strip()]
                data = plan_insumos(red, query.get('origen', 'A'), ids)
            elif op == 'bfs':
                data = red.bfs(query.get('inicio', 'A'))
            elif op == 'dfs':
                data = red.dfs(query.get('inicio', 'A'))
            elif op == 'ucs':
                data = red.ucs(query.get('inicio', 'A'), query.get('destino', 'J'))
            elif op == 'welsh-powell':
                data = red.welsh_powell()
            elif op == 'tsp':
                ids = query.get('destinos', '')
                data = red.tsp(query.get('inicio', 'A'),
                               [s.strip() for s in ids.split(',') if s.strip()] if ids.strip() else None)
            else:
                return self.responder({'error': 'Recurso no encontrado'}, 404)
            return self.responder(data, 200)
        except (ValueError, TypeError) as exc:
            return self.responder({'error': str(exc)}, 400)
        except Exception:
            return self.responder({'error': 'Error interno del servidor'}, 500)

    def do_POST(self):
        op = urlparse(self.path).path
        if op not in ('/api/registros/actualizar', '/api/registros/restablecer'):
            return self.responder({'error': 'Recurso no encontrado'}, 404)
        try:
            longitud = int(self.headers.get('Content-Length', '0'))
            if longitud < 2 or longitud > 3072:
                return self.responder({'error': 'Solicitud demasiado grande o vacía'}, 413)
            if 'application/json' not in self.headers.get('Content-Type', ''):
                return self.responder({'error': 'Se requiere JSON'}, 415)
            data = json.loads(self.rfile.read(longitud))
            if not isinstance(data, dict):
                raise ValueError('La solicitud debe ser un objeto JSON')
            if op.endswith('restablecer'):
                with LOCK:
                    CAMBIOS.clear()
                return self.responder({'ok': True, 'mensaje': 'Se restauraron los datos originales de demostración'}, 200)
            enfermedad = data.get('enfermedad')
            zona = data.get('zona')
            if enfermedad not in ENFERMEDADES or zona not in NOMBRES:
                raise ValueError('Enfermedad o municipio no reconocido')
            valores = [data.get(c) for c in ('confirmados', 'recuperados', 'fallecidos')]
            # Usar el validador de dominio; impedir floats, bool, NaN y negativos.
            Zona(zona, NOMBRES[zona], *valores, 0, 0)
            with LOCK:
                CAMBIOS[(enfermedad, zona)] = tuple(valores)
            return self.responder({'ok': True, 'mensaje': 'Reporte agregado actualizado en memoria'}, 200)
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            return self.responder({'error': str(exc)}, 400)
        except Exception:
            return self.responder({'error': 'No se pudo procesar la actualización'}, 500)

    def responder(self, obj, estado):
        contenido = json.dumps(obj, ensure_ascii=False).encode('utf-8')
        self.send_response(estado)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(contenido)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(contenido)


if __name__ == '__main__':
    puerto = int(os.environ.get('PORT', '8000'))
    print(f'EpiRed | Piloto Antioquia | http://localhost:{puerto}')
    print('Datos demostrativos: no usar para decisiones sanitarias reales.')
    ThreadingHTTPServer(('127.0.0.1', puerto), Handler).serve_forever()
