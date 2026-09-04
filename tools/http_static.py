"""静态文件服务器：为 /workspace/web 提供服务，强制 no-store 防止浏览器缓存旧版 index.html。

用法：python3 http_static.py [port]
"""
import os, sys, functools
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

ROOT = '/workspace/web'
PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8080


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def end_headers(self):
        
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write('[web %s] %s\n' % (self.log_date_time_string(), fmt % args))


if __name__ == '__main__':
    os.chdir(ROOT)
    srv = ThreadingHTTPServer(('127.0.0.1', PORT), Handler)
    print('serving %s on 127.0.0.1:%d (no-cache, threaded)' % (ROOT, PORT), flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
