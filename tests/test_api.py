import os
import time

import pytest
from app import main, engine

def test_health_does_not_reveal_key(client,monkeypatch):
    monkeypatch.setenv('NEBIUS_API_KEY','secret-dont-reveal')
    r=client.get('/api/health')
    assert r.status_code==200
    assert r.json()['nebius_configured'] is True
    assert 'secret-dont-reveal' not in r.text

def test_landing(client):
    r=client.get('/')
    assert r.status_code==200
    assert 'See what matters' in r.text

def test_create_and_retrieve(client,make_case):
    sid=make_case['id']
    assert len(sid)==24
    assert len(make_case['photos'])==1
    assert client.get(f'/api/sessions/{sid}').json()['id']==sid
    img=client.get(f'/api/sessions/{sid}/photos/P-01')
    assert img.status_code==200
    assert img.headers['content-type'].startswith('image/jpeg')

def test_path_traversal_rejected(client,make_case):
    assert client.get('/api/sessions/not-an-id').status_code==404
    sid=make_case['id']
    assert client.get(f'/api/sessions/{sid}/photos/P-99').status_code==404

def test_no_key_no_fake_analysis(client,make_case,monkeypatch):
    monkeypatch.delenv('NEBIUS_API_KEY',raising=False)
    r=client.post(f"/api/sessions/{make_case['id']}/analyze")
    assert r.status_code==503
    assert client.get(f"/api/sessions/{make_case['id']}").json()['result'] is None

def test_image_validation(client):
    r=client.post('/api/sessions',files=[('files',('s.txt',b'abc','text/plain'))])
    assert r.status_code==400
    r=client.post('/api/sessions',files=[('files',('a.jpg',b'bad','image/jpeg'))])
    assert r.status_code==400

def test_demo_fixture_is_clearly_labeled(client):
    sample=client.get('/api/demo').json()
    assert sample['result']['mode']=='sample_fixture'
    assert not sample['result']['trace']
    assert 'No inference performed' in sample['result']['model']

def test_unauthorized_review_without_inference(client,make_case):
    assert client.post(f"/api/sessions/{make_case['id']}/review",json={'finding_id':'F-01','status':'confirmed'}).status_code==409

def test_live_flow_mock_calls_and_review(client,make_case,monkeypatch):
    monkeypatch.setenv('NEBIUS_API_KEY','testing-only')
    calls=[]
    async def mocked(messages,*,max_tokens):
        calls.append(messages)
        if len(calls)==1:
            return ({'summary':'Visible surface condition','findings':[{'title':'Surface mark','observation':'A line is visible','interpretation':'May be cosmetic','priority':'unknown','evidence_ids':['P-01']},{'title':'Bad citation','observation':'Undocumented','evidence_ids':['P-02']}],'uncertainties':['Need close-up']},{'model':engine.DEFAULT_MODEL,'seconds':1.2,'tokens':{},'response_id':'mock1'})
        return ({'next_shot_title':'Take close-up','instruction':'Aim at the surface','reason':'To see the mark','question':'Is it raised?'},{'model':engine.DEFAULT_MODEL,'seconds':0.3,'tokens':{},'response_id':'mock2'})
    monkeypatch.setattr(engine,'_call_nebius',mocked)
    sid=make_case['id']
    res=client.post(f'/api/sessions/{sid}/analyze')
    assert res.status_code==200,res.text
    result=res.json()['result']
    assert result['mode']=='live'
    assert len(result['trace'])==2
    assert len(result['findings'])==1
    assert result['rejected_claims']==1
    review=client.post(f'/api/sessions/{sid}/review',json={'finding_id':'F-01','status':'needs_more_evidence','note':'Second view required'})
    assert review.status_code==200
    assert review.json()['result']['findings'][0]['review_note']=='Second view required'
    assert client.get(f'/api/sessions/{sid}/export').status_code==200


def test_followup_photo_archives_old_run(client,make_case,photo,monkeypatch):
    sid=make_case['id']
    current=main._read(sid)
    current['result']={'summary':'Earlier findings','findings':[], 'uncertainties':[]}
    main._write(sid,current)
    res=client.post(f'/api/sessions/{sid}/photos',files=[('files',('second.jpg',photo,'image/jpeg'))])
    assert res.status_code==200,res.text
    result=res.json()
    assert result['photos'][1]['id']=='P-02'
    assert result['result'] is None
    assert result['analysis_history'][0]['result']['summary']=='Earlier findings'
    assert result['status']=='awaiting_reanalysis'
    assert client.get(f'/api/sessions/{sid}/photos/P-02').status_code==200

def test_followup_validation_does_not_corrupt_case(client,make_case):
    sid=make_case['id']
    r=client.post(f'/api/sessions/{sid}/photos',files=[('files',('invalid.jpg',b'bad','image/jpeg'))])
    assert r.status_code==400
    assert len(client.get(f'/api/sessions/{sid}').json()['photos'])==1


def test_public_demo_caps_paid_analysis(client,make_case,monkeypatch):
    monkeypatch.setenv('NEBIUS_API_KEY','testing-only')
    monkeypatch.setattr(main,'_events',{})
    calls=[]
    async def mocked(record, folder):
        calls.append(record['id'])
        return {'model':engine.DEFAULT_MODEL,'findings':[],'uncertainties':[],
                'trace':[{},{}], 'mode':'live'}
    monkeypatch.setattr(main,'inspect_with_nebius',mocked)
    sid=make_case['id']
    for _ in range(12):
        assert client.post(f'/api/sessions/{sid}/analyze').status_code==200
    denied=client.post(f'/api/sessions/{sid}/analyze')
    assert denied.status_code==429
    assert 'Retry-After' in denied.headers
    assert len(calls)==12


def test_expired_case_photos_are_purged(client,make_case,monkeypatch):
    sid=make_case['id']
    folder=main.SESSIONS / sid
    old=time.time()-main.SESSION_TTL_SECONDS-5
    os.utime(folder,(old,old))
    monkeypatch.setattr(main,'_last_cleanup',0)
    assert client.get('/api/health').status_code==200
    assert not folder.exists()
    assert client.get(f'/api/sessions/{sid}').status_code==404
