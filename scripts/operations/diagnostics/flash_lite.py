"""Check the owner-requested Gemini Flash-Lite candidate using at most two live calls."""
import hashlib
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError

from scripts.operations.local import configure_local
from campusai.api import CampusAIApplication
from campusai.llm.factory import create_llm
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.retrieval.hybrid import HybridRetriever


def main():
    root = Path.cwd()
    evidence = root/'docs/deployment/phase13/evidence/flash-lite-candidate'
    profile = evidence/'candidate.yaml'
    runtime_env = dict(os.environ)
    configure_local(environ=runtime_env)
    client = create_llm(profile,environ=runtime_env)
    original = client.generate
    measurements = []

    def generate(prompt, **kwargs):
        row = {'prompt_sha256':hashlib.sha256(prompt.encode()).hexdigest()}
        measurements.append(row)
        try:
            response = original(prompt,**kwargs)
            row.update(usage=response.usage,latency_ms=response.latency_ms,
                       finish_reason=response.finish_reason,model_version=response.model_version)
            return response
        except Exception as error:
            cause = error.__cause__
            row.update(error_type=type(error).__name__,
                upstream_status=cause.code if isinstance(cause,HTTPError) else None,
                quota_limit_zero=bool(re.search(r'limit\s*:\s*0(?:\D|$)',str(error),re.I)))
            raise

    client.generate = generate
    retriever = HybridRetriever(root/'data/index',dense_device='cpu')
    service = CampusAIQueryService(retriever,GroundedAnswerGenerator(client),default_mode='bm25')
    application = CampusAIApplication(service)
    doc_ids = [p.name for p in (root/'data/index').iterdir()
               if p.is_dir() and re.fullmatch(r'[a-f0-9]{64}',p.name)]
    assert doc_ids, 'Use an existing ready document; no upload is performed.'
    cases = [('What order do stack push and pop operations use?','en'),
             ('Stack thực hiện thao tác push và pop theo nguyên tắc nào?','vi')]
    results = []
    try:
        for question,language in cases:
            response = application.query(question,doc_ids=doc_ids,language=language,history=[])
            results.append({'question':question,'language':language,'response':response})
            if not response.get('ok') or response.get('answer',{}).get('abstained'):
                break  # No retry, key rotation, fallback model or closed-run resume.
    finally:
        application.close()
    report = {'status':'PASS' if len(results)==2 and all(r['response'].get('ok') and
              not r['response']['answer']['abstained'] for r in results) else 'NOT_PASSED',
        'model':'gemini-3.5-flash-lite','thinkingLevel':'minimal','call_cap':2,
        'profile_sha256':hashlib.sha256(profile.read_bytes()).hexdigest(),
        'retrieval':'BM25 diagnostic on existing user scope; no dense model duplication',
        'calls':measurements,'cases':results,'not_a_quality_or_availability_SLO':True,
        'token_comparison':'No paired 3.8 run; minimal thinking does not guarantee zero reasoning tokens.'}
    (evidence/'candidate-smoke.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':report['status'],'calls':measurements,
        'results':[{'language':r['language'],'ok':r['response'].get('ok'),
                    'error_code':r['response'].get('error_code'),
                    'abstained':r['response'].get('answer',{}).get('abstained')} for r in results]},ensure_ascii=False))
    return 0 if report['status']=='PASS' else 1


if __name__ == '__main__':
    raise SystemExit(main())
