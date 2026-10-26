"""本机交互配置DeepSeek。只使用Python标准库，不发送网络请求。"""

import getpass
import os
from pathlib import Path
import re
import sys
import tempfile


PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULTS = {
    "CAREERLENS_ANSWER_MODE": "auto",
    "LLM_BASE_URL": "https://api.deepseek.com",
    "LLM_MODEL": "deepseek-flash",
}


def save_configuration(path, key):
    key = key.strip()
    if not re.fullmatch(r"sk-[A-Za-z0-9_-]{8,250}", key):
        raise ValueError("密钥格式不正确，请复制平台生成的完整密钥。")
    values = {"DEEPSEEK_API_KEY": key, **DEFAULTS}
    original = path.read_text(encoding="utf-8-sig") if path.exists() else ""
    # 保留数据库等其他配置，删除这次配置项的所有旧定义，避免重复值。
    lines = []
    for line in original.splitlines():
        match = re.match(r"\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=", line)
        if match and match[1] in values:
            continue
        lines.append(line)
    if lines and lines[-1].strip():
        lines.append("")
    lines.extend(name + "=" + value for name, value in values.items())
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=".env-", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write("\n".join(lines) + "\n")
        if os.name != "nt":
            os.chmod(temporary, 0o600)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def main():
    print("配置CareerLens模型接口。此步骤不会调用模型或产生API请求。")
    print("粘贴密钥后按回车；输入内容不会显示，这是正常的。")
    if not sys.stdin.isatty():
        print("请在交互式cmd或PowerShell终端中运行，不能通过管道传入密钥。")
        return 1
    key = getpass.getpass("DeepSeek API密钥：")
    try:
        save_configuration(PROJECT_ROOT / ".env", key)
    except ValueError as error:
        print(str(error))
        return 1
    except (OSError, UnicodeError):
        print("配置文件保存失败，请检查项目文件夹的写入权限。")
        return 1
    print("已保存到项目根目录的.env。密钥没有显示，也没有发送到网络。")
    print("下一步运行：python scripts/start.py")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyboardInterrupt, EOFError):
        print("\n已取消，配置没有更新。")
        raise SystemExit(1)
