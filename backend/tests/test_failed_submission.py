"""Focused submission regressions. Uses a fresh SQLite DB and Demo/mocks only."""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

os.environ.setdefault("SECRET_KEY", "test-only-secret-key-at-least-32-characters")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.config import settings
from app.database import Base, get_db
from app.models import Application, Job, PreferenceSignal, SubmissionLog
from app.services import apply_service


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "apply_mode", "demo")
    monkeypatch.setattr(settings, "job_source", "seed")
    monkeypatch.setattr(settings, "ai_provider", "local")
    monkeypatch.setattr(settings, "schedule_enabled", False)
    engine = create_engine(f"sqlite:///{tmp_path / 'submissions.db'}",
                           connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    def database():
        with sessions() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    client = TestClient(app, raise_server_exceptions=False)
    def account(name):
        response = client.post('/api/auth/register', json={
            'username': name, 'password': 'secret123',
            'security_question': 'Pet?', 'security_answer': 'Rex'})
        assert response.status_code == 200
        headers = {'Authorization': 'Bearer ' + response.json()['access_token']}
        client.put('/api/profile', headers=headers, json={
            'full_name': name, 'email': name+'@example.test', 'skills': ['Python'],
            'onboarded': True})
        return headers
    first = account('first_user')
    second = account('second_user')
    jobs = client.get('/api/jobs/matches', headers=first).json()
    yield client, sessions, first, second, jobs
    client.close()
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)
    engine.dispose()


def failure(mode='demo'):
    return {'ok': False, 'mode': mode, 'message': 'Mock submission failure',
            'confirmation_ref': '', 'submitted_at': '', 'proof_path': ''}


def test_demo_success_duplicate_and_user_isolation(sandbox):
    client, sessions, first, second, jobs = sandbox
    data = {'job_id': jobs[0]['id']}
    response = client.post('/api/applications', headers=first, json=data)
    assert response.status_code == 200
    application = response.json()
    assert application['status'] == 'applied'
    assert application['submission_status'] == 'submitted'
    assert application['confirmation_ref'].startswith('JQ-DEMO-')
    assert not application['can_retry']
    assert client.post('/api/applications', headers=first, json=data).status_code == 409
    assert client.get('/api/applications', headers=second).json() == []
    assert client.get('/api/autopilot/logs', headers=second).json() == []
    assert client.get(f"/api/applications/{application['id']}", headers=second).status_code == 404
    assert client.post('/api/applications', headers=second, json=data).status_code == 200
    with sessions() as db:
        assert db.query(Application).count() == db.query(SubmissionLog).count() == 2


def test_failed_demo_retry_preserves_history_and_statistics(sandbox, monkeypatch):
    client, sessions, first, second, jobs = sandbox
    data = {'job_id': jobs[0]['id']}
    original = apply_service.submit_application
    monkeypatch.setattr(apply_service, 'submit_application', lambda *args: failure())
    failed = client.post('/api/applications', headers=first, json=data).json()
    assert failed['status'] == failed['submission_status'] == 'failed'
    assert failed['can_retry'] and not failed['confirmation_ref']
    assert client.get('/api/applications', headers=first).json()[0]['status'] == 'failed'
    assert client.get('/api/autopilot/logs', headers=first).json()[0]['status'] == 'failed'
    dash = client.get('/api/dashboard', headers=first).json()
    assert dash['total_applications'] == dash['status_counts']['applied'] == 0
    assert dash['failed_applications'] == 1
    assert dash['response_rate'] == dash['interview_rate'] == 0
    job = next(j for j in client.get('/api/jobs/matches', headers=first).json() if j['id'] == data['job_id'])
    assert job['can_retry'] and not job['already_applied'] and job['application_status'] == 'failed'
    assert client.get('/api/applications', headers=second).json() == []
    monkeypatch.setattr(apply_service, 'submit_application', original)
    retried = client.post('/api/applications', headers=first, json=data).json()
    assert retried['id'] == failed['id']
    assert retried['status'] == 'applied' and retried['submission_status'] == 'submitted'
    assert not retried['can_retry']
    assert client.post('/api/applications', headers=first, json=data).status_code == 409
    with sessions() as db:
        assert db.query(Application).count() == 1
        logs = db.query(SubmissionLog).order_by(SubmissionLog.id).all()
        assert [log.status for log in logs] == ['failed', 'submitted']
        assert all(log.application_id == failed['id'] for log in logs)
    assert client.get('/api/dashboard', headers=first).json()['status_counts']['applied'] == 1


def test_legacy_failed_record_is_read_correctly_without_rewriting(sandbox, monkeypatch):
    client, sessions, first, _, jobs = sandbox
    original = apply_service.submit_application
    monkeypatch.setattr(apply_service, 'submit_application', lambda *args: failure())
    failed = client.post('/api/applications', headers=first, json={'job_id': jobs[0]['id']}).json()
    with sessions() as db:
        db.get(Application, failed['id']).status = 'applied'
        db.commit()
    view = client.get('/api/applications', headers=first).json()[0]
    assert view['status'] == 'failed' and view['can_retry']
    assert client.get('/api/dashboard', headers=first).json()['total_applications'] == 0
    with sessions() as db:
        assert db.get(Application, failed['id']).status == 'applied'
    monkeypatch.setattr(apply_service, 'submit_application', original)
    assert client.post('/api/applications', headers=first, json={'job_id': jobs[0]['id']}).json()['id'] == failed['id']


@pytest.mark.parametrize('mode', ['live', '', 'unknown', None])
def test_non_demo_failure_never_retries(sandbox, monkeypatch, mode):
    client, _, first, _, jobs = sandbox
    calls = []
    def submit(*args):
        calls.append(True)
        result = failure(mode)
        if mode is None:
            del result["mode"]
        return result
    monkeypatch.setattr(apply_service, 'submit_application', submit)
    data = {'job_id': jobs[0]['id']}
    failed = client.post('/api/applications', headers=first, json=data).json()
    assert failed['status'] == 'failed' and not failed['can_retry']
    assert client.post('/api/applications', headers=first, json=data).status_code == 409
    assert len(calls) == 1  # no real Live function is ever called


def test_historical_success_prevents_retry_even_after_failed_log(sandbox):
    client, sessions, first, _, jobs = sandbox
    data = {'job_id': jobs[0]['id']}
    success = client.post('/api/applications', headers=first, json=data).json()
    with sessions() as db:
        stored = db.get(Application, success['id'])
        db.add(SubmissionLog(user_id=stored.user_id, job_id=stored.job_id,
            application_id=stored.id, mode='demo', status='failed'))
        db.commit()
    assert not client.get('/api/applications', headers=first).json()[0]['can_retry']
    assert client.post('/api/applications', headers=first, json=data).status_code == 409


def test_failed_status_cannot_be_manually_forged(sandbox, monkeypatch):
    client, sessions, first, _, jobs = sandbox
    monkeypatch.setattr(apply_service, 'submit_application', lambda *args: failure())
    failed = client.post('/api/applications', headers=first, json={'job_id': jobs[0]['id']}).json()
    for status in ['applied', 'interview', 'offer']:
        assert client.patch(f"/api/applications/{failed['id']}/status", headers=first,
                            json={'status': status}).status_code == 409
    assert client.patch(f"/api/applications/{failed['id']}/status", headers=first,
                        json={'status': 'failed'}).status_code == 400
    with sessions() as db:
        assert db.query(PreferenceSignal).count() == 0


def test_application_and_log_rollback_together(sandbox, monkeypatch):
    client, sessions, first, _, jobs = sandbox
    original = apply_service._log
    def broken_log(*args):
        original(*args)
        raise RuntimeError('Mock persistence failure')
    monkeypatch.setattr(apply_service, '_log', broken_log)
    assert client.post('/api/applications', headers=first,
                       json={'job_id': jobs[0]['id']}).status_code == 500
    with sessions() as db:
        assert db.query(Application).count() == db.query(SubmissionLog).count() == 0


@pytest.mark.parametrize('path', ['/api/applications/auto', '/api/autopilot/run-now'])
def test_automatic_failure_uses_shared_status_without_automatic_retry(sandbox, monkeypatch, path):
    client, sessions, first, _, _ = sandbox
    monkeypatch.setattr(apply_service, 'submit_application', lambda *args: failure())
    client.put('/api/autopilot', headers=first, json={'enabled': False, 'min_score': 0, 'daily_limit': 1})
    response = client.post(path, headers=first, json={'min_score': 0, 'limit': 1})
    assert response.status_code == 200 and len(response.json()) == 1
    failed = response.json()[0]
    assert failed['status'] == 'failed' and failed['can_retry']
    assert client.get('/api/autopilot/logs', headers=first).json()[0]['status'] == 'failed'
    assert client.get('/api/dashboard', headers=first).json()['auto_applied'] == 0
    if path.endswith('run-now'):
        assert client.get('/api/autopilot', headers=first).json()['settings']['last_run_count'] == 0
    # A subsequent automatic run may select a different job, but cannot retry this one.
    client.post(path, headers=first, json={'min_score': 0, 'limit': 1})
    with sessions() as db:
        assert db.query(SubmissionLog).filter(SubmissionLog.application_id == failed['id']).count() == 1


def test_simultaneous_requests_submit_only_once(sandbox, monkeypatch):
    client, sessions, first, _, jobs = sandbox
    original = apply_service.submit_application
    calls = []
    count_lock = Lock()
    def submit(*args):
        with count_lock:
            calls.append(True)
        return original(*args)
    monkeypatch.setattr(apply_service, 'submit_application', submit)
    def request(_):
        return client.post('/api/applications', headers=first, json={'job_id': jobs[0]['id']}).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(request, range(2))) == [200, 409]
    assert len(calls) == 1
    with sessions() as db:
        assert db.query(Application).count() == db.query(SubmissionLog).count() == 1


def test_demo_failure_cannot_be_retried_after_switching_to_live(sandbox, monkeypatch):
    client, _, first, _, jobs = sandbox
    calls = []
    def submit(*args):
        calls.append(True)
        return failure()
    monkeypatch.setattr(apply_service, 'submit_application', submit)
    data = {'job_id': jobs[0]['id']}
    assert client.post('/api/applications', headers=first, json=data).json()['can_retry']
    monkeypatch.setattr(settings, 'apply_mode', 'live')
    assert not client.get('/api/applications', headers=first).json()[0]['can_retry']
    assert client.post('/api/applications', headers=first, json=data).status_code == 409
    assert len(calls) == 1


def test_scheduled_failures_are_not_counted_as_submitted(sandbox, monkeypatch):
    client, sessions, first, _, _ = sandbox
    monkeypatch.setattr(apply_service, 'submit_application', lambda *args: failure())
    client.put('/api/autopilot', headers=first,
               json={'enabled': True, 'min_score': 0, 'daily_limit': 1})
    with sessions() as db:
        summary = apply_service.run_all_scheduled(db)
        assert summary['users'] == 1 and summary['applications'] == 0
        assert db.query(SubmissionLog).one().run_type == 'scheduled'
        assert db.query(SubmissionLog).one().status == 'failed'
