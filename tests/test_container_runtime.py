"""Container startup must keep local admission and cleanup guarantees."""
from http.client import HTTPConnection
from threading import Thread
from types import SimpleNamespace
from wsgiref.simple_server import make_server

import pytest

from campusai.deployment.local_server import LocalHTTPServer, LocalRequestHandler, make_local_server
from scripts.operations import container
from scripts.release.install_cpu_runtime import cpu_plan


def test_cpu_install_preserves_pins_and_omits_gpu_dependencies():
    omitted, wheels = cpu_plan({'package': [
        {'name': 'torch', 'version': '2.14.0'},
        {'name': 'torchvision', 'version': '0.29.0'},
        {'name': 'nvidia-cublas', 'version': '13.0'},
        {'name': 'triton', 'version': '3.8.0'},
        {'name': 'sentence-transformers', 'version': '5.7.0'}]})
    assert set(omitted) == {'torch', 'torchvision', 'nvidia-cublas', 'triton'}
    assert wheels == ['torch==2.14.0', 'torchvision==0.29.0']
    with pytest.raises(ValueError, match='frozen_torch_version_required'):
        cpu_plan({'package': []})


def test_invalid_preflight_never_builds_or_binds(monkeypatch):
    def fail():
        raise container.LocalSetupError('missing_verified_assets')
    monkeypatch.setattr(container, 'configure_local', fail)
    monkeypatch.setattr(container, 'build_application', lambda: pytest.fail('model loaded'))
    monkeypatch.setattr(container, 'make_server', lambda *a, **k: pytest.fail('port opened'))
    with pytest.raises(SystemExit, match='missing_verified_assets'):
        container.main([])


def test_bind_failure_closes_application(monkeypatch):
    closed = []
    monkeypatch.setattr(container, 'configure_local', lambda: None)
    monkeypatch.setattr(container, 'prepare_state', lambda _: None)
    monkeypatch.setattr(container, 'build_application', lambda: SimpleNamespace(close=lambda: closed.append(True)))
    monkeypatch.setattr(container, 'make_wsgi_app', lambda *a, **k: object())
    def fail(*args, **kwargs):
        raise OSError('port_busy')
    monkeypatch.setattr(container, 'make_server', fail)
    with pytest.raises(OSError, match='port_busy'):
        container.main([])
    assert closed == [True]


def test_container_handler_rejects_foreign_host_and_local_launcher_stays_private():
    def app(environ, start_response):
        start_response('200 OK', [('Content-Length', '2')])
        return [b'ok']
    with pytest.raises(ValueError, match='loopback'):
        make_local_server('0.0.0.0', 0, app)
    server = make_server('127.0.0.1', 0, app,
        server_class=LocalHTTPServer, handler_class=LocalRequestHandler)
    worker = Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        for host, expected in [('untrusted.invalid', 403), (f'localhost:{server.server_port}', 200)]:
            connection = HTTPConnection('127.0.0.1', server.server_port, timeout=5)
            try:
                connection.request('GET', '/', headers={'Host': host})
                response = connection.getresponse()
                assert response.status == expected
                response.read()
            finally:
                connection.close()
    finally:
        server.shutdown()
        server.server_close()
        worker.join(timeout=5)
