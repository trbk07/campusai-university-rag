"""Read model metadata with the existing owner key; no inference or key rotation."""
import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from scripts.operations.local import configure_local


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('Metadata evidence already exists; do not overwrite it')
    env = dict(os.environ)
    configure_local(environ=env)
    request = Request('https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000',
                      headers={'x-goog-api-key':env['GEMINI_API_KEY']})
    try:
        with urlopen(request,timeout=15) as response:
            data = json.load(response)
        models = [{'name':model['name'],'inputTokenLimit':model.get('inputTokenLimit'),
                   'outputTokenLimit':model.get('outputTokenLimit'),
                   'supportedGenerationMethods':model.get('supportedGenerationMethods')}
                  for model in data.get('models',[])
                  if any(term in model.get('name','') for term in ('gemma-4','flash-lite','2.5-flash'))]
        report = {'date':'2026-10-15','status':'METADATA_ONLY','http_status':200,
                  'models':models,'live_inference_calls':0,'quota_or_entitlement_proven':False}
    except HTTPError as error:
        report = {'status':'METADATA_FAILED','http_status':error.code,'live_inference_calls':0}
    except (URLError,TimeoutError) as error:
        report = {'status':'NETWORK_UNAVAILABLE','error_type':type(error).__name__,'live_inference_calls':0}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
    return 0 if report['status'] == 'METADATA_ONLY' else 1


if __name__ == '__main__':
    raise SystemExit(main())
