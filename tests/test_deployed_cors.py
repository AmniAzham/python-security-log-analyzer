"""Exercise fresh startup configuration for the deployed Firebase origins."""
import os
import subprocess
import sys
import unittest


class DeployedCorsTests(unittest.TestCase):
    def test_firebase_posts_preflights_and_revision(self):
        # Import in a fresh process: Render injects settings before Uvicorn imports
        # backend.app. This does not change the development app used by other tests.
        code = '''
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app import app

origins = ['https://authwatch-85466.web.app', 'https://authwatch-85466.firebaseapp.com']
with TestClient(app) as client:
    assert client.get('/api/health').json() == {'status': 'ok'}
    assert client.get('/api/health?details=true').json() == {
        'status': 'ok', 'revision': 'test-deployment-revision', 'cors_origins': origins}
    for origin in origins:
        for path in ['/api/sample', '/api/analyze']:
            preflight = client.options(path, headers={
                'Origin': origin, 'Access-Control-Request-Method': 'POST',
                'Access-Control-Request-Headers': 'content-type'})
            assert preflight.status_code == 200
            assert preflight.headers['access-control-allow-origin'] == origin
            assert 'POST' in preflight.headers['access-control-allow-methods']
            assert 'access-control-allow-credentials' not in preflight.headers
            if path == '/api/sample':
                response = client.post(path, headers={'Origin': origin})
            else:
                response = client.post(path, content=Path('data/sample_auth_logs.csv').read_bytes(),
                    headers={'Origin': origin, 'Content-Type': 'text/csv'})
            assert response.status_code == 200
            assert response.headers['access-control-allow-origin'] == origin
            assert response.json()['events_analyzed'] == 19
            assert response.json()['total_alerts'] == 4
        invalid = client.post('/api/analyze', content=b'bad CSV',
            headers={'Origin': origin, 'Content-Type': 'text/csv'})
        assert invalid.status_code == 400
        assert invalid.headers['access-control-allow-origin'] == origin
    for origin in ['https://untrusted.example', 'https://authwatch-85466.web.app.evil.example', 'http://localhost:5173']:
        preflight = client.options('/api/analyze', headers={
            'Origin': origin, 'Access-Control-Request-Method': 'POST'})
        assert preflight.status_code == 400
        assert 'access-control-allow-origin' not in preflight.headers
    # The diagnostic endpoint must report middleware's startup snapshot.
    import os
    os.environ['FRONTEND_ORIGINS'] = 'https://different.example'
    assert client.get('/api/health?details=true').json()['cors_origins'] == origins
'''
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True,
            env={**os.environ,
                 'FRONTEND_ORIGINS': 'https://authwatch-85466.web.app,https://authwatch-85466.firebaseapp.com',
                 'RENDER_GIT_COMMIT': 'test-deployment-revision'})
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_missing_setting_reproduces_200_without_cors_permission(self):
        code = '''
from fastapi.testclient import TestClient
from backend.app import app
with TestClient(app) as client:
    response = client.post('/api/sample', headers={'Origin': 'https://authwatch-85466.web.app'})
    assert response.status_code == 200
    assert 'access-control-allow-origin' not in response.headers
    assert client.get('/api/health?details=true').json()['cors_origins'] == [
        'http://localhost:5173', 'http://127.0.0.1:5173']
'''
        environment = os.environ.copy()
        environment.pop('FRONTEND_ORIGINS', None)
        result = subprocess.run([sys.executable, '-c', code], capture_output=True, text=True, env=environment)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
