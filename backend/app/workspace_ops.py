"""Coordinate one story mutation across the working cache and durable stores.

SQLite provides request-local rollback. When Supabase is configured, the durable
Postgres snapshot is compare-and-swapped before that transaction commits. Drive
is drained afterward as an optional portable mirror for the project owner.
"""
from contextvars import ContextVar
from functools import wraps
from fastapi import HTTPException
from . import auth_store, db, drive_store, supabase_store

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
                    drive = session.get('drive') if isinstance(session, dict) else None
                    for pid in affected:
                        if drive:
                            # A collaborator's personal Drive must never become the
                            # shared story mirror. Only the owner drains Drive.
                            if supabase_store.can_manage_drive(session, pid):
                                drive_store.drain_project(drive, pid)
                                if supabase_store.enabled():
                                    try:
                                        supabase_store.save_sync_state(session, pid, story_revision=db.project_revision(pid))
                                    except HTTPException:
                                        pass
                        if auth_store.enabled() and supabase_store.enabled():
                            try:
                                supabase_store.record_event(
                                    session,
                                    pid,
                                    'story.updated',
                                    {'revision': db.project_revision(pid)},
                                )
                            except HTTPException:
                                # Story persistence already succeeded. Activity
                                # history is useful metadata, not commit authority.
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
    session = _ACTIVE.get()
    if auth_store.enabled() and isinstance(session, dict):
        supabase_store.require_role(session, project_id, 'editor')
    expected = request.headers.get('x-project-revision')
    if (drive_store.enabled() or auth_store.enabled() or supabase_store.enabled()) and not expected:
        raise HTTPException(428, 'Reload this story before changing it.')
    current = db.project_revision(project_id)
    if expected and expected != current:
        raise HTTPException(409, {'code':'stale_story','message':'This story changed in another tab or device. Your draft is kept here. Download it before loading the latest story.'})
    bases = _BASE_REVISIONS.get()
    if bases is not None:
        bases.setdefault(project_id, current)
