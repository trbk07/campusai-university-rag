"""Bounded, concurrent loopback transport for local use, not public hosting."""
import threading
from socketserver import ThreadingMixIn
from wsgiref.simple_server import (ServerHandler, WSGIRequestHandler, WSGIServer,
                                 make_server)


class LocalRequestHandler(WSGIRequestHandler):
    def handle(self):
        self.raw_requestline = self.rfile.readline(65537)
        if len(self.raw_requestline) > 65536:
            self.requestline = self.request_version = self.command = ''
            self.send_error(414)
            return
        if not self.parse_request():
            return
        # Binding loopback alone does not make an arbitrary browser Host
        # trustworthy. Reject foreign/ambiguous authorities before WSGI can
        # expose the local document library or accept a mutation.
        names = {'127.0.0.1', 'localhost', '[::1]'}
        authorities = {f'{name}:{self.server.server_port}' for name in names}
        if self.server.server_port == 80:
            authorities.update(names)
        hosts = self.headers.get_all('Host', [])
        if len(hosts) != 1 or hosts[0].lower() not in authorities:
            self.send_error(403, 'Forbidden host')
            return
        handler = ServerHandler(self.rfile, self.wfile, self.get_stderr(),
                                self.get_environ(), multithread=True)
        handler.request_handler = self
        handler.run(self.server.get_app())


class LocalHTTPServer(ThreadingMixIn, WSGIServer):
    """Bound HTTP handlers while allowing twenty users plus control requests.

    Query and ingestion admission remain independently limited by the app.
    """
    block_on_close = True
    request_queue_size = 32

    def __init__(self, *args, **kwargs):
        self._slots = threading.BoundedSemaphore(32)
        super().__init__(*args, **kwargs)

    def get_request(self):
        request, address = super().get_request()
        request.settimeout(30)
        return request, address

    def process_request(self, request, address):
        if not self._slots.acquire(blocking=False):
            body = b'{"ok":false,"error_code":"query_busy","retry_after_seconds":1}'
            try:
                request.sendall(b'HTTP/1.1 503 Service Unavailable\r\nConnection: close\r\n'
                    b'Content-Type: application/json\r\nRetry-After: 1\r\nContent-Length: '
                    + str(len(body)).encode('ascii') + b'\r\n\r\n' + body)
            except OSError:
                pass
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, address)
        except BaseException:
            self._slots.release()
            raise

    def process_request_thread(self, request, address):
        try:
            super().process_request_thread(request, address)
        finally:
            self._slots.release()


def make_local_server(host, port, app):
    if host not in {'127.0.0.1', '::1'}:
        raise ValueError('Local transport must bind loopback')
    return make_server(host, port, app, server_class=LocalHTTPServer,
                       handler_class=LocalRequestHandler)
