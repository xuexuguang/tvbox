"""Serve the local management page and test sources from the local configuration."""

import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit

import requests

from update import CONFIG_FILE, ROOT, fetch_config, load_source_config


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        if self.headers.get('Host') != '127.0.0.1:8765':
            self.send_error(403)
            return
        target = urlsplit(self.path)
        if target.path == '/manage/probe':
            self.send_error(405)
        else:
            super().do_GET()

    def do_POST(self):
        target = urlsplit(self.path)
        if target.path != '/manage/probe':
            self.send_error(404)
            return
        if (self.headers.get('Host') != '127.0.0.1:8765'
                or self.headers.get('Origin') != 'http://127.0.0.1:8765'):
            self.send_error(403)
            return
        source_id = parse_qs(target.query).get('id', [''])[0]
        sources = load_source_config(CONFIG_FILE)['sources']
        source = next((item for item in sources if item['id'] == source_id), None)
        if source is None:
            self.reply({'error': '本地清单没有这条源'}, 404)
            return
        errors = []
        cms = source if source.get('type') == 'cms' else None
        for url in source['urls']:
            try:
                data, used_url, elapsed = fetch_config(url, cms)
            except (OSError, ValueError, requests.RequestException) as error:
                errors.append(str(error))
                continue
            entries = data.get('sites') or data.get('urls') or []
            self.reply({'url': used_url, 'ms': elapsed, 'count': None if cms else len(entries)})
            return
        self.reply({'error': '；'.join(errors) or '无地址可测'})

    def reply(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(body)


if __name__ == '__main__':
    with ThreadingHTTPServer(('127.0.0.1', 8765), Handler) as server:
        server.serve_forever()
