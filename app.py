from __future__ import annotations

import cgi
import html
import imghdr
import os
import shutil
import urllib.parse
import uuid
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
STATIC_DIR = BASE_DIR / "static"
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

UPLOAD_DIR.mkdir(exist_ok=True)
STATIC_DIR.mkdir(exist_ok=True)


class ImageShareHandler(SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/":
            self.serve_index(parsed)
            return
        if parsed.path.startswith("/uploads/"):
            filename = parsed.path.removeprefix("/uploads/")
            self.serve_upload(filename)
            return
        if parsed.path.startswith("/static/"):
            self.serve_static(parsed.path.removeprefix("/static/"))
            return
        self.send_error(HTTPStatus.NOT_FOUND, "页面不存在")

    def do_POST(self):
        if self.path != "/upload":
            self.send_error(HTTPStatus.NOT_FOUND, "页面不存在")
            return
        self.handle_upload()

    def serve_index(self, parsed):
        params = urllib.parse.parse_qs(parsed.query)
        message = params.get("msg", [""])[0]
        escaped_msg = html.escape(message)

        images = sorted(
            [f for f in UPLOAD_DIR.iterdir() if f.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        cards = "".join(
            f'''<figure class="card"><img src="/uploads/{urllib.parse.quote(img.name)}" alt="用户上传图片" loading="lazy" /><figcaption>{html.escape(img.name)}</figcaption></figure>'''
            for img in images
        )
        if not cards:
            cards = '<p class="empty">还没有图片，快上传第一张吧！</p>'

        message_block = (
            f'<div class="messages"><p>{escaped_msg}</p></div>' if escaped_msg else ""
        )

        page = f"""<!doctype html>
<html lang='zh-CN'>
<head>
  <meta charset='UTF-8' />
  <meta name='viewport' content='width=device-width, initial-scale=1.0' />
  <title>图片共享墙</title>
  <link rel='stylesheet' href='/static/styles.css' />
</head>
<body>
  <main class='container'>
    <h1>图片共享墙</h1>
    <p class='subtitle'>上传本地图片后，所有访问这个网页的人都能看到。</p>
    {message_block}
    <form class='upload-form' action='/upload' method='post' enctype='multipart/form-data'>
      <input type='file' name='image' accept='image/*' required />
      <button type='submit'>上传图片</button>
    </form>
    <section class='gallery'>{cards}</section>
  </main>
</body>
</html>
"""
        content = page.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_upload(self, filename: str):
        safe_name = os.path.basename(filename)
        target = UPLOAD_DIR / safe_name
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "图片不存在")
            return

        ctype = self.guess_type(str(target))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()
        with target.open("rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def serve_static(self, filename: str):
        safe_name = os.path.basename(filename)
        target = STATIC_DIR / safe_name
        if not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "静态文件不存在")
            return
        ctype = self.guess_type(str(target))
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(target.stat().st_size))
        self.end_headers()
        with target.open("rb") as f:
            shutil.copyfileobj(f, self.wfile)

    def handle_upload(self):
        content_length = int(self.headers.get("Content-Length", "0"))
        if content_length > MAX_FILE_SIZE + 2048:
            self.redirect_with_message("文件过大，最大支持 10MB")
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={"REQUEST_METHOD": "POST", "CONTENT_TYPE": self.headers.get("Content-Type", "")},
        )
        if "image" not in form:
            self.redirect_with_message("没有选择文件")
            return

        file_item = form["image"]
        if not file_item.filename:
            self.redirect_with_message("请选择要上传的图片")
            return

        original_name = os.path.basename(file_item.filename)
        ext = original_name.rsplit(".", 1)[-1].lower() if "." in original_name else ""
        if ext not in ALLOWED_EXTENSIONS:
            self.redirect_with_message("仅支持 png/jpg/jpeg/gif/webp 格式")
            return

        raw = file_item.file.read(MAX_FILE_SIZE + 1)
        if len(raw) > MAX_FILE_SIZE:
            self.redirect_with_message("文件过大，最大支持 10MB")
            return

        filename = f"{uuid.uuid4().hex}.{ext}"
        target = UPLOAD_DIR / filename
        target.write_bytes(raw)

        detected = imghdr.what(target)
        if detected is None:
            target.unlink(missing_ok=True)
            self.redirect_with_message("上传失败：文件不是有效图片")
            return

        self.redirect_with_message("上传成功，所有人都可以浏览这张图片")

    def redirect_with_message(self, message: str):
        encoded = urllib.parse.urlencode({"msg": message})
        self.send_response(HTTPStatus.SEE_OTHER)
        self.send_header("Location", f"/?{encoded}")
        self.end_headers()


def run(host: str = "0.0.0.0", port: int = 8000):
    server = ThreadingHTTPServer((host, port), ImageShareHandler)
    print(f"Server running at http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
