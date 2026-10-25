"""Gold-free reprocessing of real, hash-bound native HTTP capture checkpoints.

Recorded responses are cached inference inputs, never fresh provider outputs.
Missing inputs raise outside LLMError so an offline miss cannot become abstention.
"""
from dataclasses import asdict
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import MethodType

from campusai.llm.client import LLMResponse, LLMResponseError, _validate_schema
from campusai.llm.factory import create_llm, _read_config
from campusai.rag.grounding import GroundedAnswerGenerator
from campusai.rag.service import CampusAIQueryService
from campusai.rag.document_scope import RegisteredDocumentScopeReader
from campusai.retrieval.hybrid import HybridRetriever
from evaluation.grounding.native_artifacts import load_native_run
from evaluation.grounding.repair_benchmark import stable_hash


PROTOCOL = 'native-http-checkpoint-v1'
REQUEST_FIELDS = frozenset({'question','language','doc_ids','history','selected_text','filters'})


def validate_request(request):
    if (not isinstance(request,dict) or not {'question','language'} <= request.keys()
            or request.keys()-REQUEST_FIELDS or not isinstance(request['question'],str)):
        raise ValueError('Checkpoint accepts only the user-input inference projection')


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class CaptureMissing(Exception):
    def __init__(self, identifier, endpoint, body_sha256):
        self.request = {'id': identifier, 'endpoint': endpoint, 'body_sha256': body_sha256}
        super().__init__('No matching genuine native HTTP response checkpoint')


class NativeCapturePool:
    """Select by request identity and completion/time, never gold or correctness."""
    def __init__(self, client, *, config_sha256, index_sha256, requests, dev_anchors=None):
        self.client = client
        self.config_sha256, self.index_sha256 = config_sha256, index_sha256
        for request in requests.values():validate_request(request)
        self.requests, self.dev_anchors = deepcopy(requests), deepcopy(dev_anchors or {})
        self.records, self.bindings = {}, {}
        self.rejected = []
        self.schema = GroundedAnswerGenerator(client, source_citations=True).response_schema()

    def add(self, directory):
        directory = Path(directory).resolve()
        run, predictions, raw, posts = load_native_run(directory)
        if (run.get('model') != self.client.model or run.get('config_sha256') != self.config_sha256
                or run.get('index_manifest_sha256') != self.index_sha256):
            return
        run_path = directory/'run.json'
        selected = {prediction['id']: prediction for prediction in predictions}
        for index, capture in enumerate(raw):
            identifier = capture['id']
            if (identifier not in self.requests or selected[identifier]['request'] != self.requests[identifier]
                    or not capture.get('success') or capture.get('cached') is not False):
                continue
            anchor = self.dev_anchors.get(identifier)
            if anchor is not None and run_path != Path(anchor).resolve():
                continue
            # Reproduce the final attempt of the already selected successful
            # pipeline, rather than an earlier prefix abandoned on a503.
            failures = selected[identifier].get('recovered_http503_capture_indices', [])
            if run['stop_reason'] is None and failures and index <= max(failures):
                continue
            try:
                _validate_schema(capture.get('parsed_model_json'), self.schema)
            except LLMResponseError:
                self.rejected.append({'run':str(run_path),'capture_index':index,'reason':'invalid_schema'})
                continue
            body = self.client.prepare_request(capture['prompt'], **capture['generation_arguments'])
            body_sha = stable_hash(body)
            if not any(post['id'] == identifier and post['endpoint'] == self.client.endpoint
                       and post['request_body_sha256'] == body_sha for post in posts):
                self.rejected.append({'run':str(run_path),'capture_index':index,'reason':'HTTP_body_mismatch'})
                continue
            binding = {'path':str(run_path),'sha256':digest(run_path)}
            self.bindings[str(run_path)] = binding
            origin = {**binding, 'capture_index':index,
                      'raw_sha256':run['artifacts']['raw-model.jsonl'],
                      'artifacts':run['artifacts'],
                      'text_sha256':hashlib.sha256(capture['raw_model_text'].encode()).hexdigest(),
                      'source_identity':run['source_identity']}
            key = (identifier, self.client.endpoint, body_sha)
            priority = (run['stop_reason'] is not None, capture['started_at'], str(run_path), index)
            if key not in self.records or priority < self.records[key]['priority']:
                response = {key:capture.get(key) for key in
                            ('raw_model_text','usage','finish_reason','model_version','input_measurements')}
                self.records[key] = {'priority':priority,'origin':origin,'capture':response}

    def lookup(self, identifier, endpoint, body_sha256):
        value = self.records.get((identifier, endpoint, body_sha256))
        if value is None:
            raise CaptureMissing(identifier, endpoint, body_sha256)
        # Check the original immutable artifacts again before serving a record.
        origin = value['origin']
        if digest(origin['path']) != origin['sha256']:
            raise ValueError('Native checkpoint source run changed')
        if any(digest(Path(origin['path']).parent/name) != expected
               for name,expected in origin['artifacts'].items()):
            raise ValueError('Native checkpoint source artifacts changed')
        return deepcopy(value)


class CheckpointClient:
    """Use production Gemini JSON preparation/parsing with no offline transport."""
    def __init__(self, client, pool):
        self.client, self.pool = client, pool
        self.identifier, self.uses = None, []
        self.original_generate = client.generate
        client.generate = MethodType(self._generate, client)

    def begin(self, identifier):
        self.identifier, self.uses = identifier, []

    def _generate(self, client, prompt, **kwargs):
        body_sha = stable_hash(client.prepare_request(prompt, **kwargs))
        value = self.pool.lookup(self.identifier, client.endpoint, body_sha)
        capture = value['capture']
        self.uses.append({'id':self.identifier,'endpoint':client.endpoint,'body_sha256':body_sha,
                          'origin':value['origin']})
        return LLMResponse(capture['raw_model_text'], capture['usage'], 0.0, True,
                           capture.get('finish_reason'), capture.get('model_version'),
                           (capture.get('input_measurements') or [{}])[-1].get('response'))


def make_service(config_path, index_path, store_path, source_roots, pool,
                 *, calibration=None):
    """All paths/parameters are frozen inputs; no benchmark annotations here."""
    import os
    os.environ.setdefault('HF_HUB_OFFLINE','1')
    os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
    config = _read_config(config_path)
    client = create_llm(config_path, environ={'GEMINI_API_KEY':'offline-capture-only'})
    checkpoint = CheckpointClient(client, pool)
    rag = config['rag']
    service = CampusAIQueryService(HybridRetriever(index_path, dense_device='cpu'),
        GroundedAnswerGenerator(client, max_context_chars=rag['max_context_chars'],
            balanced_context=rag['balanced_context'], source_citations=rag['source_citations'],
            calibrator=calibration), context_candidates=rag['context_candidates'], default_mode='auto',
        document_scope_reader=RegisteredDocumentScopeReader(store_path, source_roots=source_roots,
                                                           allow_pdf_scope=True))
    return service, checkpoint


def reprocess(service, checkpoint, identifier, request):
    """The request argument must be the user-input-only inference projection."""
    validate_request(request)
    if request != checkpoint.pool.requests.get(identifier):
        raise ValueError('Checkpoint request differs from its bound user input')
    checkpoint.begin(identifier)
    answer = service.ask(**request)
    if answer.provider_failure:
        raise ValueError('A provider/schema failure is not an official negative prediction')
    return {'id':identifier,'request':request,'internal_response':answer.to_dict(),
            'public_response':answer.to_public_dict(),
            'retrieved_evidence':[asdict(item) for item in service.last_retrieval],
            'document_scope_audit':getattr(service._request_local,'document_scope_audit',None),
            'capture_uses':list(checkpoint.uses),'protocol':PROTOCOL,
            'fresh_provider_posts':0,'fresh_model_outputs':0}


def main():
    """Offline collection only. Scoring/gold review is a separate process."""
    import argparse
    import os
    from datetime import datetime, timezone
    from evaluation.common.release_artifacts import source_identity, verify_index_files, write_json
    from evaluation.grounding.collect_native_predictions import inference_request, verify_runtime_checkout
    from campusai.rag.calibration import load_calibration_artifact
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('benchmark','config','index','store','dev-score','calibration','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--source-root',type=Path,action='append',required=True)
    parser.add_argument('--native-campaign',type=Path,action='append',required=True)
    args=parser.parse_args()
    os.environ.setdefault('HF_HUB_OFFLINE','1')
    os.environ.setdefault('TRANSFORMERS_OFFLINE','1')
    root=Path(__file__).resolve().parents[2]
    verify_runtime_checkout(root)
    assert verify_index_files(args.index)
    identity=source_identity(root)
    rows=[json.loads(line) for line in args.benchmark.read_text(encoding='utf8').splitlines()]
    requests={row['id']:inference_request(row) for row in rows}
    anchors={}
    training=json.loads(args.dev_score.read_text(encoding='utf8'))
    for binding in training['generation']['native_runs']:
        path=Path(binding['path'])
        assert digest(path)==binding['sha256']
        for prediction in load_native_run(path.parent)[1]:anchors[prediction['id']]=str(path.resolve())
    reference=create_llm(args.config,environ={'GEMINI_API_KEY':'offline-capture-only'})
    pool=NativeCapturePool(reference,config_sha256=digest(args.config),
        index_sha256=digest(args.index/'manifest.json'),requests=requests,dev_anchors=anchors)
    for campaign in args.native_campaign:
        for path in sorted(campaign.rglob('run.json')):
            try:
                candidate=json.loads(path.read_text(encoding='utf8'))
                if candidate.get('generation_kind')=='native':pool.add(path.parent)
            except (ValueError,KeyError,OSError,TypeError) as error:
                pool.rejected.append({'run':str(path),'reason':type(error).__name__})
    args.output.mkdir(parents=True,exist_ok=False)
    write_json(args.output/'source-pool.json',{'protocol':PROTOCOL,'runs':list(pool.bindings.values()),
        'dev_anchors':anchors,'rejected':pool.rejected,'response_keys':len(pool.records)})
    calibrator,calibration_sha=load_calibration_artifact(args.calibration)
    services={}
    for stage in ('dev','heldout'):
        services[stage]=make_service(args.config,args.index,args.store,args.source_root,pool,
                                    calibration=None if stage=='dev' else calibrator)
    complete,pending=0,0
    try:
        with (args.output/'predictions.jsonl').open('x',encoding='utf8') as outputs, \
             (args.output/'pending.jsonl').open('x',encoding='utf8') as misses:
            for row in rows:
                service,checkpoint=services['dev' if row['split']=='dev' else 'heldout']
                try:
                    prediction=reprocess(service,checkpoint,row['id'],requests[row['id']])
                except CaptureMissing as error:
                    misses.write(json.dumps({'id':row['id'],'request':requests[row['id']],
                        'missing':error.request,'capture_uses':checkpoint.uses},ensure_ascii=False)+'\n')
                    misses.flush();pending+=1
                else:
                    outputs.write(json.dumps(prediction,ensure_ascii=False)+'\n');outputs.flush();complete+=1
                print(json.dumps({'complete':complete,'pending':pending,'last_id':row['id']}),flush=True)
    finally:
        for service,_checkpoint in services.values():service.close()
    assert source_identity(root)==identity
    write_json(args.output/'run.json',{'protocol':PROTOCOL,'generation_kind':'native_checkpoint',
        'source_identity':identity,'benchmark_path':str(args.benchmark.resolve()),
        'benchmark_sha256':digest(args.benchmark),'config_path':str(args.config.resolve()),
        'config_sha256':digest(args.config),'index_path':str(args.index.resolve()),
        'index_manifest_sha256':digest(args.index/'manifest.json'),
        'calibration_artifact_path':str(args.calibration.resolve()),
        'calibration_artifact_sha256':calibration_sha,'pipeline_predictions':complete,'pending':pending,
        'fresh_provider_posts':0,'fresh_model_outputs':0,'official_predictions':0,
        'diagnostic_only':True,'completed_at':datetime.now(timezone.utc).isoformat(),
        'artifacts':{name:digest(args.output/name) for name in
                     ('source-pool.json','predictions.jsonl','pending.jsonl')}})


if __name__=='__main__':
    main()
