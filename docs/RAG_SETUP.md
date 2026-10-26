# 模型接口配置和验收

## 当前链路

`POST /api/ask`先运行原有岗位检索和统计，获得全部命中数与最多5条展示记录，再将其中可引用的岗位字段交给DeepSeek Chat Completions接口。JSON回答由后端解析和校验，前端显示结论、引用链接、摘录和岗位原文。

检索器为关键词排序，不包含embedding或向量数据库。仅当本次模型请求成功且编号、摘录校验通过时返回`answer_mode=rag`。结构校验与引用定位不能保证结论的事实正确性。

## 本机配置

在包含requirements.txt的目录运行：

```bat
python scripts/configure_ai.py
```

按照提示在本机终端粘贴完整密钥。输入不回显是正常行为；工具不会发送网络请求，不会打印密钥，也不通过命令参数接收密钥。配置写入项目根目录`.env`，原来的其他配置会保留。

随后执行`python scripts/start.py`安装依赖并构建。默认值：

| 变量 | 默认值 | 含义 |
| --- | --- | --- |
| DEEPSEEK_API_KEY | 空 | 只在自己电脑或部署平台填写 |
| CAREERLENS_ANSWER_MODE | auto | 有可用密钥则尝试模型；rules强制规则模式 |
| LLM_BASE_URL | https://api.deepseek.com | 官方模型接口根地址 |
| LLM_MODEL | deepseek-flash | 请求使用的模型标识 |
| LLM_TIMEOUT_SECONDS | 35 | 整个模型请求的等待上限，允许5至45秒 |
| LLM_MAX_OUTPUT_TOKENS | 1200 | 输出Token上限，允许200至2000 |
| RAG_TOP_K | 5 | 最多发送5条展示岗位证据 |

部署环境变量优先于`.env`；修改后建议重启服务。HTTP客户端直接连接配置地址，不继承代理环境变量，不自动跟随重定向。若服务网络必须使用代理，应在服务端明确配置并测试。

## 真实验收

在网页中发送示例问题，或在另一个终端运行：

```bat
python scripts/check_ai.py --output docs/qa_live_result.json
```

本命令发送1次问答；检索命中且启用模型时会使用账户额度。检查输出中的`answer_mode=rag`、`ai_status=generated`、`reference_integrity_checked=true`和非空`citations`。同时人工检查结论是否符合原文，不能只凭模式标记判断答案质量。

脚本记录请求模型、提供方报告的模型名、Token用量、客户端耗时、模型请求耗时、答案和引用。一次成功只证明该次链路可运行；比赛文档仍需补充多个正常和异常问题的实测结果，不应把模拟接口测试写成真实模型效果评测。

## 状态与处理

| ai_status | 行为 | 排查方向 |
| --- | --- | --- |
| generated | 显示模型结论与引用 | 人工核对结论和原文 |
| no_matches / no_evidence | 未调用模型 | 补充城市或技能；检查样本字段 |
| not_configured / disabled | 规则结果 | 检查密钥配置与回答模式 |
| authentication_error | 规则结果 | 检查密钥有效性和平台权限 |
| balance_error | 规则结果 | 检查平台余额或可用额度 |
| timeout / provider_error | 规则结果 | 检查服务可用性及网络后重试 |
| invalid_response | 模型内容被舍弃 | 引用或JSON未通过校验，保留案例复核 |
| insufficient_evidence | 不展示模型结论 | 当前证据不足，调整问题或补充数据 |
| busy / rate_limited | 规则结果 | 稍后重试 |

每个Uvicorn进程最多2个并发模型请求、每分钟20次调用尝试，不自动重试。如果使用多个进程或多个实例，这些计数不共享，不能将其表述为全局计费上限。

## 验证逻辑

模型返回`evidence_insufficient`和`claims`；每个结论包含`text`及引用数组。引用仅允许使用本次发送的岗位编号；摘录必须是同一条已发送岗位描述或技能字段中的连续片段。被上下文预算截掉的内容也不能被引用。输出截断、未知编号、改写摘录、空内容或错误结构均明确回退为规则结果。

前端通过Vue普通文本插值展示模型输出，不将其作为HTML执行。历史记录保留回答方式、使用模型与引用摘录，避免回看时丢失生成方式。

## 发布到Render

Build和Start保持原命令。在Environment中填写`DEEPSEEK_API_KEY`，设置`CAREERLENS_ANSWER_MODE=auto`、`LLM_MODEL=deepseek-flash`、`LLM_BASE_URL=https://api.deepseek.com`。真实`.env`不提交到GitHub。发布后确认提交编号，分别检查问答、引用、失败回退和页面刷新，再录制视频。

## 官方接口参考

- [Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/)
- [JSON Output](https://api-docs.deepseek.com/guides/json_mode/)
- [Thinking Mode](https://api-docs.deepseek.com/guides/thinking_mode/)

上述接口及默认模型标识按2026-10-26官方文档核对；实际调用结果以`check_ai.py`保存的记录为准。
