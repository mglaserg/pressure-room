import io
import json
import zipfile
import time

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from app import db, drive_store
from app.main import app
from app.exporters import read_package, package_bytes


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(db, 'DB_PATH', tmp_path / 'test.db')
    db.bind_default_cache()
    db.init_db()
    yield
    db.bind_default_cache()


def test_default_backend_is_not_anonymous(isolated_db, monkeypatch):
    monkeypatch.delenv('PRESSURE_ROOM_ALLOW_LOCAL_API', raising=False)
    with TestClient(app) as client:
        assert client.get('/api/health').status_code == 200
        assert client.get('/api/projects').status_code == 403
        assert client.post('/api/projects', json={'data':{'title':'Private'}}).status_code == 403


def test_bad_import_rolls_back_original_story(isolated_db):
    pid = db.get_projects()[0]['id']
    original = db.project_payload(pid)
    broken = json.loads(json.dumps(original))
    broken['project']['title'] = 'Would destroy existing story'
    broken['scenes'][0]['unknown_column'] = 'bad'
    with pytest.raises(ValueError):
        db.import_payload(broken, mode='replace')
    restored = db.project_payload(pid)
    assert restored['project'] == original['project']
    assert restored['scenes'] == original['scenes']


def test_snapshot_restore_preserves_history(isolated_db):
    pid = db.get_projects()[0]['id']
    sid = db.create_snapshot(pid, 'Keep me')
    db.update('projects', pid, {'title':'Changed'})
    db.restore_snapshot(sid)
    assert db.project_payload(pid)['project']['title'] == 'The Last Favor'
    assert db.one('SELECT id FROM snapshots WHERE id=?', [sid])


def test_project_source_matches_schema(isolated_db):
    pid = db.get_projects()[0]['id']
    source = db.upsert_project_source(pid, source_kind='fountain', drive_file_id='valid-id', drive_file_name='test.fountain')
    assert source['drive_file_id'] == 'valid-id'


def test_package_limits_and_duplicate_json(monkeypatch):
    from app import exporters
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('project.json', 'x'*10000)
    monkeypatch.setattr(exporters, 'MAX_PROJECT_BYTES', 100)
    with pytest.raises(ValueError, match='oversized'):
        read_package(raw.getvalue())
    raw = io.BytesIO()
    with zipfile.ZipFile(raw, 'w') as z:
        z.writestr('project.json', '{}')
        with pytest.warns(UserWarning):
            z.writestr('project.json', '{}')
    with pytest.raises(ValueError, match='exactly one'):
        read_package(raw.getvalue())


def test_session_expiration_enforced(monkeypatch):
    key = Fernet.generate_key()
    monkeypatch.setattr(drive_store, 'GOOGLE_CLIENT_ID', 'test')
    monkeypatch.setattr(drive_store, 'GOOGLE_CLIENT_SECRET', 'test')
    monkeypatch.setattr(drive_store, 'SESSION_KEY', key.decode())
    monkeypatch.setattr(drive_store, 'PUBLIC_URL', 'https://example.com')
    f = Fernet(key)
    old = f.encrypt_at_time(b'{"sub":"user"}', int(time.time())-drive_store.SESSION_TTL-1)
    assert drive_store._open(old.decode()) is None
    assert drive_store._open(f.encrypt(b'{"sub":"user"}').decode())['sub'] == 'user'


def test_cross_origin_mutations_and_private_response_headers(isolated_db):
    with TestClient(app) as client:
        response = client.post('/api/projects', json={'data':{'title':'Attack'}}, headers={'Origin':'https://attacker.example'})
        assert response.status_code == 403
        assert client.get('/api/projects').headers['cache-control'] == 'no-store'
        assert client.get('/api/google/disconnect').status_code == 405


def test_unicode_export_title_is_safe(isolated_db):
    pid = db.get_projects()[0]['id']
    db.update('projects',pid,{'title':'物語 "\r\nInjected: yes'})
    with TestClient(app) as client:
        result = client.get(f'/api/projects/{pid}/export/package')
        assert result.status_code == 200
        assert "filename*=UTF-8''" in result.headers['content-disposition']
        assert '\n' not in result.headers['content-disposition']


def test_import_cannot_authorize_fountain_overwrite(isolated_db):
    pid = db.get_projects()[0]['id']
    payload = db.project_payload(pid)
    payload['project_source'] = {'source_kind':'fountain','drive_file_id':'victim','drive_file_name':'victim.fountain'}
    with TestClient(app) as client:
        result = client.post('/api/import?mode=replace',files={'file':('story.zip',package_bytes(payload))})
        assert result.status_code == 200
        assert db.get_project_source(pid) is None


def test_body_limit_before_parsing(isolated_db, monkeypatch):
    from app import request_limits
    monkeypatch.setattr(request_limits,'MAX_REQUEST_BYTES',20)
    with TestClient(app) as client:
        result=client.post('/api/projects',content=b'x'*21,headers={'Content-Type':'application/json'})
        assert result.status_code == 413


def test_drive_pull_is_atomic(isolated_db, monkeypatch):
    pid=db.get_projects()[0]['id']
    original=db.project_payload(pid)
    broken=json.loads(json.dumps(original));broken['scenes'][0]['bad_column']='bad'
    monkeypatch.setattr(drive_store,'_bind_user_cache',lambda session:'test')
    monkeypatch.setattr(drive_store,'_folder_id',lambda session:'folder')
    monkeypatch.setattr(drive_store,'_project_files',lambda *args:[{'id':'remote'}])
    monkeypatch.setattr(drive_store,'_download_project',lambda *args:broken)
    with pytest.raises(ValueError):drive_store.sync_all_from_drive({})
    assert db.project_payload(pid)['scenes']==original['scenes']


def test_patch_cannot_link_scenes_from_different_episodes(isolated_db):
    pid=db.get_projects()[0]['id']
    ws=db.workspace(pid)
    with TestClient(app) as client:
        ep=client.post(f'/api/projects/{pid}/episodes',json={'data':{'title':'Other','number':2}}).json()['id']
        scene=client.post(f'/api/episodes/{ep}/scenes',json={'data':{'slugline':'EXT. OTHER'}}).json()['id']
        result=client.patch(f"/api/causal_links/{ws['causal_links'][0]['id']}",json={'data':{'to_scene_id':scene}})
        assert result.status_code == 400


def test_cross_project_branch_rejected(isolated_db):
    ws=db.workspace(db.get_projects()[0]['id'])
    with TestClient(app) as client:
        pid=client.post('/api/projects',json={'data':{'title':'Other story'}}).json()['id']
        result=client.post(f'/api/projects/{pid}/episodes',json={'data':{'branch_id':ws['branches'][0]['id']}})
        assert result.status_code==400


def test_snapshot_content_cannot_retarget_story_or_drive_link(isolated_db):
    pid=db.get_projects()[0]['id']
    payload=db.project_payload(pid)
    payload['project_source']={'source_kind':'fountain','drive_file_id':'victim','drive_file_name':'victim.fountain'}
    sid=db.insert('snapshots',{'project_id':pid,'label':'Untrusted history','payload_json':json.dumps(payload),'created_at':db.now_iso()})
    db.restore_snapshot(sid)
    assert db.get_project_source(pid) is None
    payload['project']['id']='another-project'
    db.update('snapshots',sid,{'payload_json':json.dumps(payload)})
    with pytest.raises(ValueError,match='different story'):
        db.restore_snapshot(sid)
