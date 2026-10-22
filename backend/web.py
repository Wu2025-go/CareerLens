"""CareerLens 前后端一体化启动入口。"""

import mimetypes
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse

from backend.main import app, root


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# 确保 Windows 正确标记 JavaScript 文件，否则浏览器会出现白屏。
mimetypes.add_type("text/javascript", ".js")

app.add_api_route("/health", root, methods=["GET"], include_in_schema=False)


@app.middleware("http")
async def serve_homepage(request: Request, call_next):
    if request.url.path == "/" and request.method in {"GET", "HEAD"}:
        return FileResponse(FRONTEND_DIR / "index.html")
    return await call_next(request)


app.frontend("/", directory=FRONTEND_DIR, fallback=None)