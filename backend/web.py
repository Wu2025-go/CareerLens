"""CareerLens 前后端一体化入口：API、静态资源及浏览器导航回退。"""
import mimetypes
from pathlib import Path

from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.datastructures import Headers
from starlette.exceptions import HTTPException

from backend.main import app, root


FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend" / "dist"
BUILD_MESSAGE = (
    "前端尚未构建。请在项目根目录依次运行："
    "npm --prefix frontend ci；npm --prefix frontend run build。"
)

# Windows 注册表可能将 .js 错误识别为其他类型，统一使用浏览器认可的 MIME。
mimetypes.add_type("text/javascript", ".js")
mimetypes.add_type("text/css", ".css")


def is_frontend_navigation(path: str, scope: dict) -> bool:
    """仅为浏览器访问页面提供回退，API 与缺失资源保留 404。"""
    if scope.get("method") not in {"GET", "HEAD"}:
        return False
    accept = Headers(scope=scope).get("accept", "")
    media_types = {part.split(";", 1)[0].strip().lower() for part in accept.split(",")}
    if not media_types.intersection({"text/html", "application/xhtml+xml"}):
        return False
    relative = path.strip("/")
    reserved = {"api", "health", "docs", "redoc", "openapi.json", "assets"}
    if relative.split("/", 1)[0] in reserved:
        return False
    return ".." not in relative.split("/") and not Path(relative).suffix


class SPAStaticFiles(StaticFiles):
    """使用标准静态托管，仅对 HTML 页面导航补充 index.html 回退。"""

    async def check_config(self) -> None:
        if not (Path(self.directory) / "index.html").is_file():
            raise HTTPException(status_code=503, detail=BUILD_MESSAGE)
        await super().check_config()

    async def get_response(self, path: str, scope: dict):
        try:
            response = await super().get_response(path, scope)
        except HTTPException as exc:
            if exc.status_code != 404:
                raise
        else:
            if response.status_code != 404:
                return response

        if is_frontend_navigation(path, scope):
            return await super().get_response("index.html", scope)
        raise HTTPException(status_code=404, detail="Not Found")


app.add_api_route("/health", root, methods=["GET"], include_in_schema=False)


@app.middleware("http")
async def serve_homepage(request: Request, call_next):
    # backend.main 的 / 仍用于独立启动 API；一体化入口在此返回网页。
    if request.url.path == "/" and request.method in {"GET", "HEAD"}:
        index_file = FRONTEND_DIR / "index.html"
        if not index_file.is_file():
            return JSONResponse(status_code=503, content={"detail": BUILD_MESSAGE})
        return FileResponse(index_file)
    return await call_next(request)


# API、/docs 和 /health 已在挂载之前注册，因此优先匹配。
# 允许源码包在尚未构建时导入；访问前端时会返回明确的 503 提示。
app.mount(
    "/",
    SPAStaticFiles(directory=FRONTEND_DIR, html=True, check_dir=False),
    name="frontend",
)
