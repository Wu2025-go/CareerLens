"""向本地服务提交一次问答，检查是否真正经过模型生成和引用校验。"""

import argparse
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000")
    parser.add_argument("--question", default="深圳 Java 后端开发岗位需要哪些技能？")
    parser.add_argument("--output", type=Path, help="可选：保存不含密钥的本次结果，便于补充技术文档")
    args = parser.parse_args()
    print("将向正在运行的后端发送1次问答；配置有效且检索有结果时会调用模型。")
    request = Request(args.url.rstrip("/") + "/api/ask", method="POST",
        headers={"Content-Type": "application/json"},
        data=json.dumps({"question": args.question}, ensure_ascii=False).encode("utf-8"))
    started = time.monotonic()
    try:
        with urlopen(request, timeout=55) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError):
        print("请求未成功。请先启动本地服务，并检查终端是否报错。")
        return 1
    record = {
        "question": args.question,
        "answer_mode": result.get("answer_mode"),
        "ai_status": result.get("ai_status"),
        "model": result.get("model"),
        "model_reported": result.get("model_reported"),
        "matched_count": result.get("matched_count"),
        "evidence_count": result.get("evidence_count"),
        "reference_integrity_checked": result.get("reference_integrity_checked"),
        "llm_usage": result.get("llm_usage", {}),
        "client_elapsed_ms": round((time.monotonic() - started) * 1000),
        "model_latency_ms": result.get("model_latency_ms"),
        "answer": result.get("answer"),
        "citations": result.get("citations", []),
    }
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print("本次结果已保存。")
    if result.get("answer_mode") == "rag" and result.get("reference_integrity_checked") is True and result.get("citations"):
        print("通过：本次为模型生成，引用编号与原文摘录校验通过。内容正确性仍需人工核对。")
        return 0
    hints = {
        "not_configured": "请运行 python scripts/configure_ai.py 配置密钥，然后重启服务。",
        "authentication_error": "平台未接受密钥，请重新复制有效密钥并检查API权限。",
        "balance_error": "请在模型平台检查账户余额或可用额度。",
        "config_error": "请检查.env中的模型名称、地址和参数。",
        "disabled": "当前设置为rules模式，请按配置说明启用auto模式。",
    }
    print("本次没有验证到模型生成。" + hints.get(result.get("ai_status"), "请查看ai_status与页面提示后重试。"))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
