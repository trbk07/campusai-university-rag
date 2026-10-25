"""Measure actual loopback upload-to-ready, deleting only this owned fixture."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import time
from urllib.request import Request, urlopen


BASE = 'http://127.0.0.1:8000'
ACTIVE = {'staging','queued','running'}


def request(path, *, data=None, method=None, headers=None):
    with urlopen(Request(BASE+path,data=data,method=method,headers=headers or {}),timeout=30) as response:
        return json.load(response)


def measure(source, count, output):
    if output.exists():
        raise ValueError('Preserve prior measurements; select a new output')
    payload=source.read_bytes();identifier=hashlib.sha256(payload).hexdigest()
    if not source.name.startswith('QA-native100-'):
        raise ValueError('Only a deliberately named QA fixture may be uploaded/deleted')
    listing=request('/api/documents')
    original={row['doc_id'] for row in listing['documents']}
    if identifier in original or any(j.get('document_id')==identifier for j in listing['jobs']):
        raise ValueError('Fixture already exists; never delete or benchmark a pre-existing document')
    result={'scope':'Actual warm local app; upload, parsing and real index readiness; no answer-provider requests',
        'source_name':source.name,'source_sha256':identifier,'source_bytes':len(payload),
        'original_document_ids':sorted(original),'requested_runs':count,'runs':[],
        'additional_answer_provider_calls':0,'complete':False,'poll_interval_seconds':.1,
        'driver_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    output.parent.mkdir(parents=True,exist_ok=True)

    def save():
        temporary=output.with_suffix(output.suffix+'.tmp')
        temporary.write_text(json.dumps(result,indent=2),encoding='utf-8')
        temporary.replace(output)

    for number in range(1,count+1):
        started=time.perf_counter();owned=False;row={'run':number}
        try:
            response=request('/api/documents/upload',data=payload,method='POST',
                headers={'Content-Type':'application/pdf','X-Filename':source.name})
            job=response['job'];row['upload_accepted_seconds']=time.perf_counter()-started
            if job['document_id']!=identifier:
                raise ValueError('Uploaded fixture identity differs; refusing cleanup')
            if response.get('duplicate'):
                raise ValueError('A cached upload is not a fresh processing observation')
            owned=True
            deadline=time.monotonic()+180
            while job['state'] in ACTIVE:
                if time.monotonic()>deadline:
                    raise TimeoutError('Owned fixture observation deadline')
                time.sleep(.1)
                job=request('/api/jobs/'+job['job_id'])['job']
            row.update(state=job['state'],ready=job.get('ready'),
                observed_ready_seconds=time.perf_counter()-started)
            if job['state']!='succeeded' or not job.get('ready'):
                raise ValueError('Owned fixture did not become ready')
            document=next(d for d in request('/api/documents')['documents'] if d['doc_id']==identifier)
            row['physical_pages']=document['page_count']
            with urlopen(BASE+'/api/documents/'+identifier+'/file',timeout=30) as stream:
                row['stored_source_sha256']=hashlib.sha256(stream.read()).hexdigest()
            if row['stored_source_sha256']!=identifier:
                raise ValueError('Stored source bytes changed')
        except Exception as error:
            row['error']=type(error).__name__
            raise
        finally:
            try:
                if owned:
                    request('/api/documents/'+identifier,method='DELETE')
                    deadline=time.monotonic()+15
                    while True:
                        listing=request('/api/documents')
                        remaining={d['doc_id'] for d in listing['documents']}
                        if identifier not in remaining and not any(j.get('document_id')==identifier for j in listing['jobs']):
                            break
                        if time.monotonic()>deadline:
                            raise TimeoutError('Owned fixture cleanup did not finish')
                        time.sleep(.1)
                    row['original_document_inventory_unchanged']=remaining==original
                    if remaining!=original:
                        raise ValueError('Document inventory changed during measurement')
                    row['owned_fixture_removed']=True
            finally:
                result['runs'].append(row);save()
        print(json.dumps(row),flush=True)
    values=sorted(row['observed_ready_seconds'] for row in result['runs'])
    result.update(complete=True,p95_seconds=values[max(0,math.ceil(len(values)*.95)-1)],
        maximum_seconds=max(values),minimum_seconds=min(values))
    save()
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--runs',type=int,default=3)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not 1<=args.runs<=30:parser.error('Select1 to30 independent runs')
    result=measure(args.source,args.runs,args.output)
    print(json.dumps({k:result[k] for k in ('complete','p95_seconds','maximum_seconds','source_bytes')}))


if __name__=='__main__':main()
