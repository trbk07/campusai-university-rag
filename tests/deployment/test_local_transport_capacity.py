"""Real loopback admission under simultaneous requests, without an AI provider."""
from concurrent.futures import ThreadPoolExecutor
import threading
from urllib.error import HTTPError
from urllib.request import urlopen

import pytest

from campusai.deployment.local_server import make_local_server


def test_local_transport_rejects_untrusted_missing_and_duplicate_host_headers():
    from http.client import HTTPConnection

    received = []
    private = b'private document fixture'
    def application(environ, start_response):
        received.append(environ.get('HTTP_HOST'))
        start_response('200 OK', [('Content-Type', 'text/plain'),
                                  ('Content-Length', str(len(private)))])
        return [private]

    with make_local_server('127.0.0.1', 0, application) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        def request(hosts):
            connection = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                connection.putrequest('GET', '/api/documents', skip_host=True)
                for host in hosts: connection.putheader('Host', host)
                connection.endheaders()
                response = connection.getresponse()
                return response.status, response.read()
            finally:
                connection.close()
        port = server.server_port
        invalid = [[], ['attacker.example:' + str(port)],
            ['localhost.attacker.example:' + str(port)],
            ['127.0.0.1.attacker.example:' + str(port)],
            ['localhost:' + str(port + 1)], ['user@localhost:' + str(port)],
            ['localhost:' + str(port), 'attacker.example:' + str(port)],
            ['localhost:' + str(port), 'localhost:' + str(port)]]
        try:
            rejected = [request(hosts) for hosts in invalid]
            assert [status for status, _body in rejected] == [403] * len(invalid)
            assert all(private not in body for _status, body in rejected)
            assert received == []
            for name in ('127.0.0.1', 'localhost', 'LOCALHOST', '[::1]'):
                assert request([f'{name}:{port}']) == (200, private)
            assert len(received) == 4
        finally:
            server.shutdown()
            thread.join(5)
        assert not thread.is_alive()


@pytest.mark.parametrize('active_requests', [20, 32])
def test_concurrent_users_and_bounded_transport_admission(active_requests):
    release = threading.Event()
    entered = threading.Condition()
    active = 0

    def application(environ, start_response):
        nonlocal active
        if environ['PATH_INFO'] == '/hold':
            with entered:
                active += 1
                entered.notify_all()
            assert release.wait(10)
        body = b'ok'
        start_response('200 OK', [('Content-Type', 'text/plain'),
                                  ('Content-Length', str(len(body)))])
        return [body]

    with make_local_server('127.0.0.1', 0, application) as server:
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        base = f'http://127.0.0.1:{server.server_port}'

        def request(path):
            with urlopen(base+path, timeout=5) as response:
                return response.status, response.read()

        with ThreadPoolExecutor(max_workers=active_requests) as pool:
            pending = [pool.submit(request, '/hold') for _ in range(active_requests)]
            try:
                with entered:
                    assert entered.wait_for(lambda: active == active_requests, timeout=5)
                if active_requests == 20:
                    # Health/UI remain usable while twenty clients are waiting.
                    assert request('/health') == (200, b'ok')
                else:
                    try:
                        request('/health')
                    except HTTPError as full:
                        assert full.code == 503
                        assert full.headers['Retry-After'] == '1'
                        assert b'query_busy' in full.read()
                    except ConnectionError:
                        # Windows may reset a rejected socket with unread input.
                        # This is beyond the32-handler limit, not the20-user SLO.
                        pass
                    else:
                        pytest.fail('An over-capacity request entered the app')
                    assert active == active_requests
            finally:
                release.set()
            assert all(future.result() == (200, b'ok') for future in pending)
        # Completed requests must release every transport lease.
        assert request('/health') == (200, b'ok')
        server.shutdown()
        server_thread.join(5)
        assert not server_thread.is_alive()
