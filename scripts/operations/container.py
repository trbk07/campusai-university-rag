"""Private container transport; publish port 8000 on host loopback only."""
import argparse
import os
import signal
import threading
from wsgiref.simple_server import make_server

from campusai.deployment.local_server import LocalHTTPServer,LocalRequestHandler
from campusai.web import make_wsgi_app
from .local import ROOT,configure_local,LocalSetupError
from .local_state import prepare_state
from .serve import build_application


def main(argv=None):
    argparse.ArgumentParser(description=__doc__).parse_args(argv)
    os.chdir(ROOT)
    try:
        configure_local()
        prepare_state(os.environ)
    except (LocalSetupError,ValueError) as error:
        raise SystemExit(str(error)) from None
    application=build_application()
    try:
        # Internal bridge binding is separate from the unchanged local launcher.
        # The same loopback Host validation and bounded handlers remain active.
        with make_server('0.0.0.0',8000,make_wsgi_app(application,
                max_concurrent_queries=int(os.getenv('CAMPUSAI_QUERY_WORKERS','4')),
                enable_query_streaming=os.getenv('CAMPUSAI_QUERY_STREAMING','0')=='1'),
                server_class=LocalHTTPServer,handler_class=LocalRequestHandler) as server:
            signal.signal(signal.SIGTERM,lambda *_:threading.Thread(target=server.shutdown,daemon=True).start())
            print('CampusAI container ready on internal port 8000',flush=True)
            server.serve_forever()
    finally:
        application.close()


if __name__=='__main__':main()
