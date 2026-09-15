"""One request = atomic local mutation + persistent upload intent.

Network writes happen only after commit. Keep one worker per cache volume;
remote ETag preconditions remain authoritative across independent servers.
"""
from contextvars import ContextVar
from functools import wraps
from fastapi import HTTPException
from . import db, drive_store

_ACTIVE = ContextVar('workspace_session', default=False)
_CHANGED = ContextVar('workspace_changed', default=None)


def changed(project_id):
    ids = _CHANGED.get()
    if ids is not None:
        ids.add(project_id)


def workspace_request(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        from .main import _prepare
        request = kwargs.get('request')
        if request is None:
            import inspect
            request=inspect.signature(fn).bind(*args,**kwargs).arguments['request']
        with drive_store.SYNC_LOCK:
            session = _prepare(request)
            token = _ACTIVE.set(session)
            affected = set()
            changed_token = _CHANGED.set(affected)
            try:
                with db.transaction():
                    result = fn(*args, **kwargs)
                if session:
                    for pid in affected:
                        drive_store.drain_project(session, pid)
                if isinstance(result, dict) and affected:
                    pid = next(iter(affected))
                    result.update(revision=db.project_revision(pid), sync=db.sync_status(pid), project_id=pid)
                return result
            finally:
                _ACTIVE.reset(token)
                _CHANGED.reset(changed_token)
    return wrapped


def check_revision(request, project_id):
    if not project_id:
        return
    expected = request.headers.get('x-project-revision')
    if drive_store.enabled() and not expected:
        raise HTTPException(428, 'Reload this story before changing it.')
    if expected and expected != db.project_revision(project_id):
        raise HTTPException(409, {'code':'stale_story','message':'This story changed in another tab or device. Your draft is kept here. Download it before loading the latest story.'})
