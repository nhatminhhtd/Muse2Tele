# -*- coding: utf-8 -*-
"""Health server chi cho ban Render FREE dang Web Service.

Render Web Service bat buoc phai mo cong $PORT (mac dinh 10000) thi moi
duoc tinh la Live. Bot + FoxProfile goc chi nghe loopback 127.0.0.1:8000
nen khong duoc dung cho Web Service neu khong co server nay.

Chi chay khi bien PORT co gia tri (Render Web Service tu set). Tren
Background Worker tra phi, PORT khong co nen server nay khong chay,
khong anh huong gi.

GET / va /health -> 200 "ok" (de Render va dich vu ping giu song
kiem tra). Cac duong khac -> 404. Khong phuc vu file, khong mo
panel FoxProfile ra ngoai.
"""
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ("/", "/health"):
            body = b"ok"
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.send_header("Content-Length", "0")
            self.end_headers()

    def log_message(self, *args, **kwargs):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "10000"))
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
