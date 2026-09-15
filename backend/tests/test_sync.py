import json
import pytest
import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from app import db, drive_store, fountain_link
from app.main import app

@pytest.fixture
def story(tmp_path,monkeypatch):
    monkeypatch.setattr(db,'DB_PATH',tmp_path/'app.db')
    db.bind_default_cache();db.init_db()
    yield db.get_projects()[0]['id']
    db.bind_default_cache()


def test_replace_keeps_ids_and_revision(story):
    payload=db.project_payload(story,include_snapshots=True);revision=db.project_revision(story)
    db.import_payload(payload,mode='replace')
    assert db.project_revision(story)==revision
    assert db.project_payload(story)['scenes'][0]['id']==payload['scenes'][0]['id']


def test_pending_intent_survives_reopen_and_failed_upload(story,monkeypatch):
    drive_store.save_project({},story)
    monkeypatch.setattr(drive_store,'_write_sidecar',lambda *a: (_ for _ in ()).throw(httpx.ConnectError('offline')))
    assert drive_store.drain_project({},story)['status']=='pending'
    assert json.loads(db.sync_job(story)['payload_json'])['project']['id']==story
    db.init_db(seed=False)
    assert db.sync_job(story)['stage']=='sidecar'


def test_retry_acknowledges_lost_success_without_second_upload(story,monkeypatch):
    drive_store.save_project({},story);db.set_sync(story,file_id='remote',etag='old')
    payload=json.loads(db.sync_job(story)['payload_json'])
    monkeypatch.setattr(drive_store,'_read_consistent',lambda *a:(payload,'new'))
    monkeypatch.setattr(drive_store,'_request',lambda *a,**k: pytest.fail('must not upload again'))
    assert drive_store.drain_project({},story)['status']=='synced'
    assert db.sync_job(story)['etag']=='new'


def test_remote_change_keeps_local_copy_and_never_uploads(story,monkeypatch):
    drive_store.save_project({},story);db.set_sync(story,file_id='remote',etag='old')
    remote=db.project_payload(story);remote['project']['title']='Their change'
    monkeypatch.setattr(drive_store,'_read_consistent',lambda *a:(remote,'changed'))
    monkeypatch.setattr(drive_store,'_request',lambda *a,**k:pytest.fail('must not overwrite'))
    assert drive_store.drain_project({},story)['status']=='conflict'
    assert db.project_payload(story)['project']['title']=='The Last Favor'
    assert db.sync_job(story)['payload_json']


def test_conditional_sidecar_write_carries_exact_etag(story,monkeypatch):
    drive_store.save_project({},story);db.set_sync(story,file_id='remote',etag='"base"')
    remote=db.project_payload(story)
    monkeypatch.setattr(drive_store,'_read_consistent',lambda *a:(remote,'"base"'))
    monkeypatch.setattr(drive_store,'verify_conditional_writes',lambda s:None)
    calls=[]
    def request(*args,**kwargs):
        calls.append((args,kwargs));return httpx.Response(200,json={'etag':'"next"'})
    monkeypatch.setattr(drive_store,'_request',request)
    assert drive_store.drain_project({},story)['status']=='synced'
    assert calls[0][0][1]=='PUT'
    assert calls[0][1]['headers']['If-Match']=='"base"'


def test_google_412_is_a_conflict(monkeypatch):
    monkeypatch.setattr(drive_store,'access_token',lambda s:'test')
    monkeypatch.setattr(httpx,'request',lambda *a,**k:httpx.Response(412))
    with pytest.raises(HTTPException) as exc:drive_store._request({},'PUT','https://www.googleapis.com/example')
    assert exc.value.status_code==409


def test_pending_project_is_never_replaced_by_refresh(story,monkeypatch):
    drive_store.save_project({},story)
    monkeypatch.setattr(drive_store,'_bind_user_cache',lambda s:'u')
    monkeypatch.setattr(drive_store,'_project_files',lambda *a:[{'id':'r','appProperties':{'pressure_room_project_id':story}}])
    monkeypatch.setattr(drive_store,'_read_consistent',lambda *a:pytest.fail('must not replace pending edits'))
    assert drive_store.sync_all_from_drive({})['pending']==1
    assert db.project_payload(story)['project']['title']=='The Last Favor'


def test_missing_reserved_file_retries_same_create_id(story,monkeypatch):
    drive_store.save_project({},story);db.set_sync(story,file_id='reserved')
    monkeypatch.setattr(drive_store,'_read_consistent',lambda *a:(_ for _ in ()).throw(HTTPException(404)))
    ids=[]
    monkeypatch.setattr(drive_store,'_create_sidecar',lambda s,p,j,f:(ids.append(f) or (f,'etag')))
    drive_store.drain_project({},story)
    assert ids==['reserved']


def test_fountain_renders_only_selected_branch(story):
    ws=db.workspace(story);main=ws['branches'][0]['id']
    alt=db.clone_branch(story,main,'Alternative')
    db.upsert_project_source(story,source_kind='fountain',drive_file_id='file',drive_file_name='story.fountain',branch_id=main,source_etag='base')
    alt_ep=next(e for e in db.get_episodes(story) if e['branch_id']==alt)
    db.update('scenes',db.get_scenes(alt_ep['id'])[0]['id'],{'screenplay_text':'ALTERNATE ONLY'})
    assert 'ALTERNATE ONLY' not in fountain_link._render_linked_fountain(story,'')
    db.upsert_project_source(story,branch_id=alt)
    assert 'ALTERNATE ONLY' in fountain_link._render_linked_fountain(story,'')


def test_external_fountain_edit_never_overwritten(story,monkeypatch):
    db.upsert_project_source(story,source_kind='fountain',drive_file_id='f',drive_file_name='s.fountain',source_etag='old',screenplay_hash='old-hash')
    monkeypatch.setattr(drive_store,'file_revision',lambda *a:'new')
    monkeypatch.setattr(drive_store,'download_text',lambda *a:'Other editor changed this')
    monkeypatch.setattr(drive_store,'upload_text',lambda *a:pytest.fail('no overwrite'))
    with pytest.raises(HTTPException) as exc:fountain_link.sync_to_fountain({},story)
    assert exc.value.status_code==409


def test_stale_browser_revision_rejected_atomically(story):
    with TestClient(app) as client:
        old=client.get(f'/api/projects/{story}').json()['revision']
        first=client.patch(f'/api/projects/{story}',headers={'X-Project-Revision':old},json={'data':{'title':'First writer'}})
        assert first.status_code==200
        second=client.patch(f'/api/projects/{story}',headers={'X-Project-Revision':old},json={'data':{'title':'Stale writer'}})
        assert second.status_code==409
        assert db.project_payload(story)['project']['title']=='First writer'


def test_load_drive_preserves_recovery_story(story,monkeypatch):
    db.set_sync(story,file_id='remote',etag='old',status='conflict',stage='sidecar')
    remote=db.project_payload(story);remote['project']['title']='Remote title'
    monkeypatch.setattr(drive_store,'_read_consistent',lambda *a:(remote,'new'))
    result=drive_store.resolve_project({},story,'load-drive')
    assert db.project_payload(result['recovery_project_id'])['project']['title'].startswith('The Last Favor')
    assert db.project_payload(story)['project']['title']=='Remote title'


@pytest.mark.parametrize('honors_header',[True,False])
def test_conditional_capability_probe_fails_closed_and_cleans_up(monkeypatch,honors_header):
    monkeypatch.setattr(drive_store,'CONDITIONAL_WRITE_CHECKS',{})
    calls=[]
    def request(session,method,url,**kwargs):
        calls.append(method)
        if method=='POST':return httpx.Response(200,json={'id':'probe'})
        if method=='PUT':
            assert kwargs['headers']['If-Match'].startswith('"pressure-room-impossible-')
            if honors_header:raise HTTPException(409)
        return httpx.Response(204)
    monkeypatch.setattr(drive_store,'_request',request)
    if honors_header:
        drive_store.verify_conditional_writes({'sub':'probe-account'})
        drive_store.verify_conditional_writes({'sub':'probe-account'})
    else:
        with pytest.raises(HTTPException):drive_store.verify_conditional_writes({'sub':'probe-account'})
    assert calls==['POST','PUT','DELETE']


def test_external_edit_retaining_operation_marker_is_not_acknowledged(story,monkeypatch):
    drive_store.save_project({},story);db.set_sync(story,file_id='remote',etag='old')
    remote=json.loads(db.sync_job(story)['payload_json']);remote['project']['title']='External edit'
    monkeypatch.setattr(drive_store,'_read_consistent',lambda *a:(remote,'new'))
    assert drive_store.drain_project({},story)['status']=='conflict'


def test_recovery_copy_keeps_restorable_snapshot_history(story):
    db.create_snapshot(story,'Before')
    payload=db.project_payload(story,include_snapshots=True)
    copy=db.import_payload(payload,mode='copy')
    history=db.rows('SELECT * FROM snapshots WHERE project_id=?',[copy])
    assert len(history)==1
    assert json.loads(history[0]['payload_json'])['project']['id']==copy
    assert db.restore_snapshot(history[0]['id'])==copy
    assert db.project_payload(story)['project']['id']==story


def test_cached_story_access_survives_drive_outage(story,monkeypatch):
    monkeypatch.setattr(drive_store,'_bind_user_cache',lambda s:'offline-user')
    monkeypatch.setattr(drive_store,'LAST_SYNC_AT',{})
    monkeypatch.setattr(drive_store,'sync_all_from_drive',lambda s:(_ for _ in ()).throw(httpx.ConnectError('offline')))
    drive_store.ensure_local({})
    assert db.project_payload(story)['project']['id']==story


def test_disconnect_revokes_copied_cookie(story,monkeypatch):
    from starlette.requests import Request
    monkeypatch.setattr(drive_store,'enabled',lambda:True)
    monkeypatch.setattr(drive_store,'configuration_error',lambda:None)
    monkeypatch.setattr(drive_store,'_open',lambda t:{'sid':'session-id','sub':'account'})
    request=Request({'type':'http','headers':[(b'cookie',f'{drive_store.COOKIE_NAME}=copied'.encode())]})
    assert drive_store.session_from_request(request)
    drive_store.disconnect_response(request)
    assert drive_store.session_from_request(request) is None


def test_reload_external_fountain_keeps_other_path(story,monkeypatch):
    main=db.get_branches(story)[0]['id'];alt=db.clone_branch(story,main,'Alternative')
    alt_ids=[e['id'] for e in db.get_episodes(story) if e['branch_id']==alt]
    db.upsert_project_source(story,source_kind='fountain',drive_file_id='f',drive_file_name='s.fountain',branch_id=main)
    monkeypatch.setattr(drive_store,'file_revision',lambda *a:'new')
    monkeypatch.setattr(drive_store,'download_text',lambda *a:'INT. EXTERNAL - DAY\n\nAn external change.\n')
    fountain_link.reload_linked_fountain({},story)
    assert [e['id'] for e in db.get_episodes(story) if e['branch_id']==alt]==alt_ids
    assert 'An external change.' in fountain_link._render_linked_fountain(story,'')
    assert db.get_project_source(story)['source_etag']=='new'
