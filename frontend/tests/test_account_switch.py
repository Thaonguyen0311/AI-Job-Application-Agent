"""Browser regressions for Yan's two bugs; no server or external requests.

Run from the repo root with: python -m pytest frontend/tests/test_account_switch.py
Requires the existing backend dependencies plus Playwright and installed Chrome.
"""
import json
import mimetypes
import os
import sys
from pathlib import Path
from urllib.parse import urlsplit

import pytest
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
os.environ.setdefault('SECRET_KEY', 'test-only-secret-key-at-least-32-characters')

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.config import settings
from app.database import Base, get_db
from app.services import apply_service


@pytest.fixture
def ui(tmp_path, monkeypatch):
    for key, value in [('apply_mode', 'demo'), ('job_source', 'seed'),
                       ('ai_provider', 'local'), ('schedule_enabled', False)]:
        monkeypatch.setattr(settings, key, value)
    engine = create_engine(f"sqlite:///{tmp_path / 'ui.db'}", connect_args={'check_same_thread': False})
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)
    def database():
        with sessions() as db:
            yield db
    previous = dict(app.dependency_overrides)
    app.dependency_overrides[get_db] = database
    client = TestClient(app, raise_server_exceptions=False)
    errors, calls, held = [], [], []
    control = {'hold_profile': False, 'fail_profile': False}
    def route_request(route):
        url = urlsplit(route.request.url)
        if url.netloc != 'jobquest-test.invalid':
            route.fulfill(status=200, content_type='text/css' if 'fonts' in url.netloc else 'application/javascript', body='')
        elif url.path.startswith('/api/'):
            if url.path == '/api/profile' and route.request.method == 'PUT':
                if control['hold_profile']:
                    held.append(route)
                    return
                if control['fail_profile']:
                    route.fulfill(status=500, content_type='application/json', body=json.dumps({'detail': 'Mock save failure'}))
                    return
            headers = {k: v for k, v in route.request.headers.items() if k in ('authorization', 'content-type')}
            response = client.request(route.request.method, url.path + ('?' + url.query if url.query else ''),
                                      headers=headers, content=route.request.post_data)
            calls.append((route.request.method, url.path, response.status_code))
            route.fulfill(status=response.status_code, content_type=response.headers.get('content-type', 'application/json'), body=response.content)
        else:
            path = ROOT / 'frontend' / ('index.html' if url.path == '/' else url.path.lstrip('/'))
            route.fulfill(status=200, content_type=mimetypes.guess_type(str(path))[0] or 'text/plain', body=path.read_bytes())
    with sync_playwright() as pw:
        browser = pw.chromium.launch(channel=os.environ.get('JOBQUEST_TEST_BROWSER_CHANNEL', 'chrome'), headless=True)
        context = browser.new_context(viewport={'width': 1365, 'height': 900})
        context.route('**/*', route_request)
        page = context.new_page()
        page.set_default_timeout(10000)
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.add_init_script("""if (window === window.top) {
          localStorage.setItem('jq_tour_done_account_a','1');
          localStorage.setItem('jq_tour_done_account_b','1');
        } window.Chart = class { destroy() {} };""")
        page.goto('http://jobquest-test.invalid/', wait_until='domcontentloaded')
        yield page, client, calls, control, held
        assert errors == []
        browser.close()
    client.close()
    app.dependency_overrides.clear()
    app.dependency_overrides.update(previous)
    engine.dispose()


def register(page, name):
    if not page.locator('#view-register').is_visible():
        page.locator('[data-go="register"]').click()
    for field, value in [('reg-username', name), ('reg-password', 'secret123'),
                         ('reg-question', 'Pet?'), ('reg-answer', 'Rex')]:
        page.locator('#' + field).fill(value)
    page.locator('#btn-register').click()
    expect(page.locator('#onboarding')).to_be_visible()


def fill_onboarding(page, name, skill):
    page.locator('#onb-full_name').fill(name)
    page.locator('#onb-email').fill(name.replace(' ', '')+'@example.test')
    page.locator('[data-next="1"]').click()
    page.locator('#onb-skills input').fill(skill)
    page.locator('#onb-skills input').press('Enter')
    page.locator('[data-next="2"]').click()


def finish(page):
    page.locator('#onb-finish').click()
    expect(page.locator('#app')).to_be_visible()
    expect(page.locator('#onb-finish')).to_be_enabled()


def test_a_logout_b_register_without_reload_then_login_a(ui):
    page, client, calls, _, _ = ui
    register(page, 'account_a')
    fill_onboarding(page, 'Person A', 'Python')
    finish(page)
    page.locator('#btn-logout').click()
    register(page, 'account_b')
    expect(page.locator('#onb-full_name')).to_have_value('')
    expect(page.locator('#onb-email')).to_have_value('')
    expect(page.locator('#onb-skills .tag')).to_have_count(0)
    expect(page.locator('#onb-finish')).to_be_enabled()
    expect(page.locator('#onb-finish')).to_have_text('Finish & explore jobs →')
    assert page.evaluate('state.profile.full_name') == ''
    fill_onboarding(page, 'Person B', 'SQL')
    finish(page)
    assert page.evaluate('state.profile.skills') == ['SQL']
    page.locator('#btn-logout').click()
    if not page.locator('#view-login').is_visible():
        page.locator('[data-go="login"]:visible').click()
    page.locator('#login-username').fill('account_a')
    page.locator('#login-password').fill('secret123')
    page.locator('#btn-login').click()
    expect(page.locator('#app')).to_be_visible()
    assert page.evaluate('state.profile.full_name') == 'Person A'
    assert page.evaluate('state.profile.skills') == ['Python']
    assert [status for method, path, status in calls if path == '/api/auth/register'] == [200, 200]


def test_current_account_draft_is_loaded_and_save_failure_restores_button(ui):
    page, client, _, control, _ = ui
    register(page, 'account_b')
    token = page.evaluate('state.token')
    client.put('/api/profile', headers={'Authorization': 'Bearer '+token}, json={
        'full_name': 'Draft B', 'email': 'b@example.test', 'skills': ['SQL'],
        'languages': ['Finnish'], 'onboarded': False})
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#onboarding')).to_be_visible()
    expect(page.locator('#onb-full_name')).to_have_value('Draft B')
    expect(page.locator('#onb-skills .tag')).to_have_count(1)
    assert page.locator('#onb-skills .tag').get_attribute('data-val') == 'SQL'
    page.locator('[data-next="1"]').click()
    page.locator('[data-next="2"]').click()
    control['fail_profile'] = True
    page.locator('#onb-finish').click()
    expect(page.locator('#onb-msg')).to_have_text('Mock save failure')
    expect(page.locator('#onb-finish')).to_be_enabled()
    control['fail_profile'] = False
    finish(page)


def test_old_onboarding_response_cannot_change_new_account(ui):
    page, client, _, control, held = ui
    register(page, 'account_a')
    fill_onboarding(page, 'Person A', 'Python')
    control['hold_profile'] = True
    page.locator('#onb-finish').click()
    expect(page.locator('#onb-finish')).to_be_disabled()
    # Exercise a session change while the old save is still in flight.
    page.evaluate('logout()')
    register(page, 'account_b')
    assert held
    held[0].fulfill(status=401, content_type='application/json', body='{"detail":"Old session expired"}')
    expect(page.locator('#onb-finish')).to_be_enabled()
    expect(page.locator('#onb-full_name')).to_have_value('')
    page.wait_for_function("state.username === 'account_b' && document.querySelector('#onboarding').classList.contains('show')")
    assert page.evaluate('state.profile.full_name') == ''
    expect(page.locator('#onb-msg')).to_have_text('')
    control['hold_profile'] = False
    fill_onboarding(page, 'Person B', 'SQL')
    finish(page)


def test_failed_submission_ui_retry_and_success(ui, monkeypatch, tmp_path):
    page, client, _, _, _ = ui
    register(page, 'account_a')
    fill_onboarding(page, 'Person A', 'Python')
    finish(page)
    original = apply_service.submit_application
    monkeypatch.setattr(apply_service, 'submit_application', lambda *args: {
        'ok': False, 'mode': 'demo', 'message': 'Mock failure', 'confirmation_ref': ''})
    page.locator('[data-nav="jobs"]').click()
    expect(page.locator('[data-review]').first).to_be_visible()
    job_id = page.locator('[data-review]').first.get_attribute('data-review')
    page.locator('[data-review]').first.click()
    expect(page.locator('#do-apply')).to_be_enabled()
    page.locator('#do-apply').click()
    expect(page.locator('#apply-msg')).to_contain_text('Submission failed.')
    expect(page.locator('#do-apply')).to_be_enabled()
    page.locator('#modal-x').click()
    page.locator('[data-nav="applications"]').click()
    expect(page.locator('[data-retry]')).to_have_count(1)
    expect(page.locator('.status-select')).to_be_disabled()
    expect(page.locator('.status-select option:checked')).to_have_text('Failed')
    expect(page.locator('.submitted-tag')).to_have_count(0)
    application_id = page.locator('[data-retry]').get_attribute('data-retry')
    artifact_dir = Path(os.environ.get('JOBQUEST_TEST_ARTIFACTS', str(tmp_path)))
    page.screenshot(path=str(artifact_dir / 'failed-application-fixed.png'), full_page=True)
    monkeypatch.setattr(apply_service, 'submit_application', original)
    page.locator('[data-retry]').click()
    expect(page.locator('#do-apply')).to_be_enabled()
    page.locator('#do-apply').click()
    expect(page.locator('#modal-back')).not_to_be_visible()
    expect(page.locator('.status-select')).to_be_enabled()
    expect(page.locator('.submitted-tag')).to_have_count(1)
    expect(page.locator('[data-retry]')).to_have_count(0)
    token = page.evaluate('state.token')
    headers = {'Authorization': 'Bearer '+token}
    applications = client.get('/api/applications', headers=headers).json()
    assert len(applications) == 1 and str(applications[0]['id']) == application_id
    assert sorted(log['status'] for log in client.get('/api/autopilot/logs', headers=headers).json()) == ['failed', 'submitted']
    assert client.post('/api/applications', headers=headers, json={'job_id': int(job_id)}).status_code == 409
