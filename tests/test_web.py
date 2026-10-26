import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.web import SPAStaticFiles


class StaticFrontendTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dist = Path(self.tmp.name)
        (self.dist / 'index.html').write_text('<html>CareerLens test page</html>')
        (self.dist / 'assets').mkdir()
        (self.dist / 'assets/app.js').write_text('window.careerlens = true;')
        app = FastAPI()
        app.add_api_route('/api/example', lambda: {'ok': True})
        app.mount('/', SPAStaticFiles(directory=self.dist, html=True, check_dir=False))
        self.client = TestClient(app)
        self.addCleanup(self.client.close)

    def test_direct_navigation_and_refresh_receive_the_app(self):
        for path in ['/', '/ask', '/recommend', '/trends', '/history', '/skills', '/ask/']:
            with self.subTest(path=path):
                response = self.client.get(path, headers={'Accept': 'text/html'})
                self.assertEqual(response.status_code, 200)
                self.assertIn('text/html', response.headers['content-type'])
                self.assertIn('CareerLens test page', response.text)

    def test_missing_api_and_assets_do_not_receive_html(self):
        for path in ['/api/missing', '/assets/missing.js', '/missing.css', '/docs/missing']:
            with self.subTest(path=path):
                response = self.client.get(path, headers={'Accept': 'text/html'})
                self.assertEqual(response.status_code, 404)
                self.assertNotIn('CareerLens test page', response.text)

    def test_non_navigation_requests_do_not_receive_the_app(self):
        self.assertEqual(self.client.get('/ask', headers={'Accept': 'application/json'}).status_code, 404)
        self.assertEqual(self.client.post('/ask', headers={'Accept': 'text/html'}).status_code, 405)

    def test_real_api_and_javascript_keep_their_content_types(self):
        self.assertEqual(self.client.get('/api/example').json(), {'ok': True})
        response = self.client.get('/assets/app.js')
        self.assertEqual(response.status_code, 200)
        self.assertIn('javascript', response.headers['content-type'])

    def test_head_navigation_has_no_body(self):
        response = self.client.head('/ask', headers={'Accept': 'text/html'})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b'')

    def test_unbuilt_frontend_gives_an_actionable_error(self):
        app = FastAPI()
        app.mount('/', SPAStaticFiles(directory=self.dist / 'not-built', html=True, check_dir=False))
        with TestClient(app) as client:
            response = client.get('/ask', headers={'Accept': 'text/html'})
        self.assertEqual(response.status_code, 503)
        self.assertIn('前端尚未构建', response.json()['detail'])
