"""Kill real isolated HTTP child processes, then recover from their SQLite state."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import subprocess
import signal
import uuid
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import pytest

from tests.test_web_documents import pdf_bytes


class Host:
    def __init__(self,root,hold='none'):
        self.root=root;root.mkdir(parents=True,exist_ok=True)
        self.instance=uuid.uuid4().hex
        env=dict(os.environ)
        for key in ('GEMINI_API_KEY','GOOGLE_API_KEY','GROQ_API_KEY','OPENAI_API_KEY','OPENROUTER_API_KEY','HF_TOKEN'):
            env.pop(key,None)
        self.log=(root/('host-'+hold+'.log')).open('w',encoding='utf-8')
        self.process=subprocess.Popen([sys.executable,'-X','utf8','-m',
            'tests.deployment.jobs.fixture_host','--root',str(root),'--hold',hold,'--instance',self.instance],
            env=env,stdout=self.log,stderr=subprocess.STDOUT)
        try:
            self.info=self.wait_json('server.json',lambda value:value.get('instance')==self.instance and
                (value['pid']==self.process.pid or value.get('parent_pid')==self.process.pid))
            self.base=f"http://127.0.0.1:{self.info['port']}"
            assert self.get('/health')[1]['status']=='ok'
        except Exception:
            self.kill();raise

    def wait_json(self,name,predicate,timeout=15):
        deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            if self.process.poll() is not None:
                pytest.fail(f'Fixture exited: {self.process.returncode}; '+(self.root/self.log.name).read_text(encoding='utf-8',errors='replace')[-1500:])
            try:
                value=json.loads((self.root/name).read_text(encoding='utf-8'))
                if predicate(value):return value
            except (OSError,ValueError):pass
            time.sleep(.03)
        pytest.fail('Confirmed-live fixture did not reach its checkpoint')

    def request(self,path,method='GET',payload=None,raw=None):
        data=raw if raw is not None else json.dumps(payload).encode() if payload is not None else None
        headers={'Content-Type':'application/pdf','X-Filename':'Enrollment.pdf'} if raw is not None else {'Content-Type':'application/json'}
        req=Request(self.base+path,method=method,data=data,headers=headers)
        try:response=urlopen(req,timeout=5)
        except HTTPError as error:response=error
        with response:
            body=response.read()
            value=json.loads(body) if response.headers.get('Content-Type','').startswith('application/json') else body
            return response.code,value

    @property
    def pid(self):return self.info['pid']

    def get(self,path):return self.request(path)

    def finish(self,job_id):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            status,value=self.get('/api/jobs/'+job_id)
            assert status==200
            if value['job']['state'] not in {'staging','queued','running'}:return value['job']
            time.sleep(.03)
        pytest.fail('Recovered job did not reach a terminal state')

    def kill(self):
        info=getattr(self,'info',None)
        if info is None:
            try:
                candidate=json.loads((self.root/'server.json').read_text(encoding='utf-8'))
                if candidate.get('instance')==self.instance and candidate.get('parent_pid')==self.process.pid:
                    info=candidate
            except (OSError,ValueError):pass
        if self.process.poll() is None and info is not None:
            try:os.kill(info['pid'],signal.SIGTERM if os.name=='nt' else signal.SIGKILL)
            except ProcessLookupError:pass
        try:self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill();self.process.wait(timeout=5)
        self.log.close()


@pytest.mark.parametrize('stage',[
    'upload_before_write','upload_partial','upload_complete','upload_renamed',
    'parsing','persisting','index_bm25','index_dense','index_published','success_persisted'])
def test_actual_kill_restart_and_source_grounded_recovery(tmp_path,stage):
    root=tmp_path/'host';data=pdf_bytes();digest=hashlib.sha256(data).hexdigest()
    first=Host(root,stage)
    with ThreadPoolExecutor(max_workers=1) as client:
        request=client.submit(first.request,'/api/documents/upload','POST',None,data)
        try:
            checkpoint=first.wait_json('checkpoint.json',lambda value:value['pid']==first.pid and value['stage']==stage)
            assert first.process.poll() is None
            assert first.get('/health')[0]==200
        finally:first.kill()
        try:request.result(timeout=6)
        except Exception:pass  # The real in-flight HTTP connection was killed.
    second=Host(root)
    receipt={'stage':stage,'first_pid':first.pid,'second_pid':second.pid,
        'checkpoint':checkpoint,'source_sha256':digest,'real_process_kill':True,
        'provider':'deterministic test fixture','Gemini_calls':0,'cloud_or_ARM64_acceptance':False}
    try:
        assert first.pid!=second.pid
        status,listing=second.get('/api/documents');assert status==200
        assert len(listing['jobs'])==1
        recovered=listing['jobs'][0]
        receipt['recovered_job']=recovered
        if stage=='success_persisted':
            assert recovered['state']=='succeeded' and recovered['ready']
            job=recovered
        else:
            assert recovered['state']=='failed' and not recovered['ready']
            assert recovered['error_code']=='processing_interrupted'
            assert all(not doc['ready'] for doc in listing['documents'])
            assert not any(job['state'] in {'queued','running','staging'} for job in listing['jobs'])
            if stage in {'upload_before_write','upload_partial'}:
                assert not recovered['retryable']
                assert not list((root/'store/uploads').rglob('.uploading-*.pdf'))
                status,value=second.request('/api/documents/upload','POST',raw=data)
                assert status==202
            else:
                assert recovered['retryable']
                status,value=second.request('/api/jobs/'+recovered['job_id']+'/retry','POST',{})
                assert status==200
            job=second.finish(value['job']['job_id'])
            assert job['state']=='succeeded' and job['ready']
        assert job['document_id']==digest
        assert second.get('/api/documents/'+digest+'/file')==(200,data)
        status,answer=second.request('/api/query','POST',{'question':'What approval is required for enrollment?',
            'doc_ids':[digest],'language':'en'})
        assert status==200 and not answer['answer']['abstained']
        assert answer['answer']['citations'][0]['doc_id']==digest
        assert answer['answer']['citations'][0]['quote']=='Enrollment requires approval from the academic advisor.'
        assert not list((root/'index/.jobs').glob('*')) if (root/'index/.jobs').exists() else True
        receipt.update(status='PASS',terminal_job=job,answer=answer)
        (tmp_path/'process-receipt.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    finally:second.kill()


def test_queued_jobs_are_interrupted_without_automatic_replay(tmp_path):
    root=tmp_path/'host';first=Host(root,'parsing')
    try:
        ids=[first.request('/api/documents/upload','POST',raw=pdf_bytes())[1]['job']['job_id']]
        first.wait_json('checkpoint.json',lambda value:value['pid']==first.pid)
        for label in ('second','third'):
            ids.append(first.request('/api/documents/upload','POST',raw=pdf_bytes(
                'Enrollment requires approval from the academic advisor. Record '+label))[1]['job']['job_id'])
        assert len(set(ids))==3
    finally:first.kill()
    second=Host(root)
    try:
        listing=second.get('/api/documents')[1]
        assert {job['job_id'] for job in listing['jobs']}==set(ids)
        assert all(job['state']=='failed' and job['retryable'] and not job['ready'] for job in listing['jobs'])
        for job_id in ids:
            status,value=second.request('/api/jobs/'+job_id+'/retry','POST',{})
            assert status==200 and second.finish(value['job']['job_id'])['ready']
        (tmp_path/'process-receipt.json').write_text(json.dumps({'status':'PASS',
            'stage':'one running and two queued','first_pid':first.pid,'second_pid':second.pid,
            'real_process_kill':True,'interrupted_job_ids':ids,'automatic_replays':0,
            'Gemini_calls':0,'cloud_or_ARM64_acceptance':False},indent=2)+'\n',encoding='utf-8')
    finally:second.kill()
