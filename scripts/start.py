"""本地启动：python scripts/start.py。首次运行会安装依赖并构建前端。"""

from pathlib import Path
import shutil
import subprocess
import sys
import venv


PROJECT_ROOT = Path(__file__).resolve().parent.parent


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=PROJECT_ROOT, check=True)


def main() -> int:
    if sys.version_info < (3, 10):
        print("请先安装 Python 3.10 或更高版本。", flush=True)
        return 1

    npm = shutil.which("npm.cmd" if sys.platform == "win32" else "npm")
    if npm is None:
        print("找不到 npm。请安装 Node.js LTS，然后重新打开终端。", flush=True)
        return 1

    required = ["requirements.txt", "frontend/package-lock.json", "data/sample/jobs_sample.csv"]
    missing = [name for name in required if not (PROJECT_ROOT / name).is_file()]
    if missing:
        print("项目文件不完整，请先解压完整源码：" + "、".join(missing), flush=True)
        return 1

    env_dir = PROJECT_ROOT / ".venv"
    python = env_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    if not python.is_file():
        print("正在创建项目 Python 环境……", flush=True)
        venv.EnvBuilder(with_pip=True).create(env_dir)

    print("1/3 安装后端依赖……", flush=True)
    run([str(python), "-m", "pip", "install", "-r", "requirements.txt"])
    print("2/3 安装依赖并构建前端……", flush=True)
    run([npm, "--prefix", "frontend", "ci"])
    run([npm, "--prefix", "frontend", "run", "build"])
    print("3/3 启动 CareerLens：请在浏览器打开 http://127.0.0.1:8000", flush=True)
    print("此终端需要保持打开；按 Ctrl+C 停止本地服务。", flush=True)
    run([str(python), "-m", "uvicorn", "backend.web:app", "--host", "127.0.0.1", "--port", "8000"])
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except subprocess.CalledProcessError as exc:
        print("上一步执行失败，已停止启动。请查看上方具体报错。", flush=True)
        raise SystemExit(exc.returncode)
    except KeyboardInterrupt:
        print("\n本地服务已停止。", flush=True)
        raise SystemExit(130)
