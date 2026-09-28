"""Coordinate one story mutation across the working cache and durable stores.

SQLite provides request-local rollback. When Supabase is configured, the durable
Postgres snapshot is compare-and-swapped before that transaction commits. Drive
is drained afterward as a portable mirror and uses remote ETags for conflicts.
"""
from contextvars import ContextVar
from functools import wraps
from fastapi import HTTPException
from . import db, drive_store, supabase_store

_ACTIVE = ContextVar('workspace_session', default=False)
_CHANGED = ContextVar('workspace_changed', default=None)
_BASE_REVISIONS = ContextVar('workspace_base_revisions', default=None)


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
            bases = {}
            changed_token = _CHANGED.set(affected)
            base_token = _BASE_REVISIONS.set(bases)
            try:
                with db.transaction():
                    result = fn(*args, **kwargs)
                    if session and supabase_store.enabled():
                        for pid in affected:
                            supabase_store.save_project(session, pid, expected_revision=bases.get(pid))
                if session:
                    for pid in affected:
                        drive_store.drain_project(session, pid)
                        if supabase_store.enabled():
                            try:
                                supabase_store.save_sync_state(session, pid, story_revision=db.project_revision(pid))
                            except HTTPException:
                                # Story content is already durable. A later retry can recover
                                # Drive identity from appProperties without duplicating files.
                                pass
                if isinstance(result, dict) and affected:
                    pid = next(iter(affected))
                    result.update(revision=db.project_revision(pid), sync=db.sync_status(pid), project_id=pid)
                return result
            finally:
                _ACTIVE.reset(token)
                _CHANGED.reset(changed_token)
                _BASE_REVISIONS.reset(base_token)
    return wrapped


def check_revision(request, project_id):
    if not project_id:
        return
    expected = request.headers.get('x-project-revision')
    if drive_store.enabled() and not expected:
        raise HTTPException(428, 'Reload this story before changing it.')
    current = db.project_revision(project_id)
    if expected and expected != current:
        raise HTTPException(409, {'code':'stale_story','message':'This story changed in another tab or device. Your draft is kept here. Download it before loading the latest story.'})
    bases = _BASE_REVISIONS.get()
    if bases is not None:
        bases.setdefault(project_id, current)
