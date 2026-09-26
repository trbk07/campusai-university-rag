"""Run the dependency-free local WSGI shell.

This command is a transport smoke test. Production deployments should inject
real CampusAIApplication dependencies through their process entrypoint.
"""

from wsgiref.simple_server import make_server

from campusai.api import CampusAIApplication
from campusai.rag.service import CampusAIQueryService
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.retrieval.hybrid import HybridRetriever
from campusai.web import make_wsgi_app


class NoProvider:
    def generate_json(self, *_args, **_kwargs):
        raise RuntimeError("LLM provider is not configured")


def main():
    service = CampusAIQueryService(HybridRetriever(), GroundedAnswerGenerator(NoProvider()))
    app = CampusAIApplication(service)
    with make_server("127.0.0.1", 8000, make_wsgi_app(app)) as server:
        print("CampusAI listening on http://127.0.0.1:8000")
        server.serve_forever()


if __name__ == "__main__":
    main()
