"""Intranet PMS service. Database stays on the management PC."""
import hmac
import json
import logging
from pathlib import Path
import secrets
import threading
from urllib.parse import parse_qs

from . import pms


class PMSApplication:
    def __init__(self, access_code):
        self.access_code = access_code

    def __call__(self, environ, start_response):
        def response(status, value, content_type='application/json; charset=utf-8'):
            data = value if isinstance(value, bytes) else json.dumps(value, ensure_ascii=False).encode('utf-8')
            start_response(status, [('Content-Type', content_type), ('Content-Length', str(len(data))),
                                    ('Cache-Control', 'no-store'), ('X-Content-Type-Options', 'nosniff'),
                                    ('X-Frame-Options', 'DENY'), ('Referrer-Policy', 'no-referrer'),
                                    ('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; frame-ancestors 'none'")])
            return [data]

        path = environ.get('PATH_INFO', '/')
        method = environ.get('REQUEST_METHOD', 'GET')
        assets = {'/': ('pms.html', 'text/html; charset=utf-8'),
                  '/pms.js': ('pms.js', 'application/javascript; charset=utf-8'),
                  '/pms.css': ('pms.css', 'text/css; charset=utf-8')}
        if path in assets and method == 'GET':
            filename, mime = assets[path]
            return response('200 OK', (Path(__file__).parent / 'web' / filename).read_bytes(), mime)
        if not path.startswith('/api/'):
            return response('404 Not Found', {'error': '페이지가 없습니다.'})
        credential = environ.get('HTTP_AUTHORIZATION', '')
        if not hmac.compare_digest(credential.encode('utf-8'), ('Bearer ' + self.access_code).encode('utf-8')):
            return response('401 Unauthorized', {'error': '접속 코드가 올바르지 않습니다.'})
        try:
            if path == '/api/status' and method == 'GET':
                return response('200 OK', {'equipment': pms.equipment_ids(), 'tasks': pms.TASKS,
                                           'cycle_days': pms.CYCLE_DAYS, 'status': pms.task_status()})
            if path == '/api/history' and method == 'GET':
                query = parse_qs(environ.get('QUERY_STRING', ''))
                filters = {key: query[key][0] for key in ('equipment_id', 'task', 'start', 'end') if key in query}
                return response('200 OK', {'records': pms.list_records(**filters)})
            if path == '/api/history' and method == 'POST':
                if environ.get('CONTENT_TYPE', '').split(';')[0] != 'application/json':
                    return response('415 Unsupported Media Type', {'error': 'JSON 형식으로 입력하세요.'})
                size = int(environ.get('CONTENT_LENGTH') or 0)
                if not 0 < size <= 16384:
                    return response('413 Payload Too Large', {'error': '입력 크기가 너무 큽니다.'})
                data = json.loads(environ['wsgi.input'].read(size))
                if not isinstance(data, dict):
                    raise ValueError('입력 값을 확인하세요.')
                # Browser clients may add completed work; corrections remain on the management PC.
                fields = ('equipment_id', 'task', 'maintenance_date', 'workers', 'notes')
                record_id = pms.save_record(**{k: data[k] for k in fields if k in data})
                return response('201 Created', {'id': record_id})
            return response('405 Method Not Allowed', {'error': '지원하지 않는 요청입니다.'})
        except (ValueError, TypeError, KeyError, OverflowError):
            import sys
            exc = sys.exc_info()[1]
            message = str(exc) if isinstance(exc, ValueError) and not isinstance(exc, json.JSONDecodeError) else '입력 값을 확인하세요.'
            return response('400 Bad Request', {'error': message})
        except Exception:
            logging.exception('PMS request failed')
            return response('503 Service Unavailable', {'error': '저장소에 연결할 수 없습니다. 관리 PC를 확인한 뒤 다시 시도하세요.'})


class PMSService:
    def __init__(self):
        self.server = None
        self.thread = None
        self.access_code = None
        self.port = None
        self.stop_event = threading.Event()

    @property
    def running(self):
        return self.thread is not None and self.thread.is_alive()

    def start(self, host='0.0.0.0', port=8765):
        if self.running:
            return
        from waitress import create_server
        self.access_code = secrets.token_urlsafe(18)
        self.server = create_server(PMSApplication(self.access_code), host=host, port=port,
                                    threads=4, max_request_body_size=16384,
                                    channel_timeout=30, clear_untrusted_proxy_headers=True)
        self.port = int(self.server.effective_port)
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._serve, args=(self.server, self.stop_event), daemon=True, name='QC-PMS')
        self.thread.start()

    @staticmethod
    def _serve(server, stop_event):
        try:
            # Keep select() and socket closure on the same thread on Windows.
            while not stop_event.is_set():
                server.asyncore.loop(timeout=0.2, map=server._map,
                                     use_poll=server.adj.asyncore_use_poll, count=1)
        except Exception:
            logging.exception('PMS service stopped unexpectedly')
        finally:
            server.task_dispatcher.shutdown()
            server.asyncore.close_all(map=server._map)

    def stop(self):
        if self.server:
            self.stop_event.set()
            if self.thread:
                self.thread.join(timeout=7)
                if self.thread.is_alive():
                    raise RuntimeError('서버가 요청을 마무리하고 있습니다. 잠시 후 다시 중지하세요.')
        self.server = self.thread = self.access_code = None
