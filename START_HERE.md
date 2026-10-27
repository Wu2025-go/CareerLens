# CareerLens 上线核验版 · 2026-10-26

本版在前后端整合版上新增DeepSeek调用与引用校验。本机和线上真实调用已通过，PR 4已合并，Render已部署应用提交6fb9c9c。后端73项、前端3项、本地浏览器24组和线上浏览器16组检查通过；模拟测试与真实链路记录分别保留。

## 先配置本机密钥

如果使用更新包，先在旧终端按Ctrl+C停止服务，将更新包里的文件和文件夹复制到当前项目根目录，合并文件夹并替换同名文件。更新包不包含真实.env、.venv或node_modules。

在能看到backend、frontend、scripts和requirements.txt的目录打开cmd，依次执行：

```bat
python scripts/configure_ai.py
python scripts/start.py
```

配置工具只在本机写入.env，不发送网络请求。粘贴密钥时不会显示字符，粘贴后按回车即可。启动后打开问答页面，发送示例问题；成功时必须看到“岗位检索 + 大模型生成”和非空引用，仅有岗位卡片不算真实模型成功。

可在另一个终端运行一次真实检查，结果不含密钥，可用于补充技术文档：

```bat
python scripts/check_ai.py --output docs/qa_live_result.json
```

这条命令提交1次问答，有证据且配置有效时会调用模型。详细配置见docs/RAG_SETUP.md，检查记录见docs/RAG_VERIFICATION.md。

本包包含完整项目，基于 GitHub `main` 的 `8fe4b4969d984eeacd2c252ddff897fac1b5c769`，合入队友提供的 `CareerLens-frontend-updated.zip` 前端源码。

## 先在本地运行

1. 把完整压缩包解压到一个新文件夹，保留原来的开发目录。
2. 安装 Python 3.10 及以上版本和 Node.js（本次前端验证使用 Node.js 24）。
3. 在包含 `requirements.txt`、`frontend`、`backend` 的目录打开终端，执行：

```bash
python scripts/start.py
```

脚本会创建项目 Python 环境、安装依赖、构建前端并启动服务。第一次运行需要网络。保持终端打开，看到服务启动完成后访问：

- 首页：<http://127.0.0.1:8000/>
- 就业问答：<http://127.0.0.1:8000/ask>
- 岗位推荐：<http://127.0.0.1:8000/recommend>
- 趋势分析：<http://127.0.0.1:8000/trends>
- 历史记录：<http://127.0.0.1:8000/history>

如果提示 8000 端口已占用，请在之前运行本项目的终端按 Ctrl+C，再执行启动命令。

## 本次已完成

- 保留最新后端静态托管和页面导航回退，合入队友新版界面。
- 前端支持按 URL 进入对应功能、刷新，以及浏览器前进/后退；未知页面显示返回首页入口。
- 问答结果新增岗位描述原文、岗位编号、数据集文件名、来源标记和发布日期。
- 问答历史使用全部匹配数，避免把展示的 Top 5 误写成全部匹配数量。
- 验证普通乱码和无匹配问题返回空结果，不返回全局技能统计；新增回归测试。
- 页面和历史记录区分模型生成与规则结果；历史记录明确标注本地保存的限制。
- ECharts 按需导入，功能页面分包，问答页面无需加载图表模块。

## 仍待完成

- 模型HTTP调用、引用校验和线上发布已验收；下一步应扩充独立标注问题集进行效果评测。本包使用关键词检索，没有embedding或向量库，不能宣称杜绝幻觉。
- 历史记录仍为当前浏览器的 LocalStorage，最多 100 条，没有账户同步或后端数据库保存。
- 数据集有来源平台名称，没有每条岗位的原始网页 URL；原文展示可追到本项目 CSV 记录，不能据此声称已完成外部网页真实性验证。

应用代码已同步GitHub并部署Render。Render继续使用下列构建和启动命令；DEEPSEEK_API_KEY由服务Environment配置，其余模型参数可沿用代码默认值。

```bash
# Build Command
pip install -r requirements.txt && npm --prefix frontend ci && npm --prefix frontend run build

# Start Command
python -m uvicorn backend.web:app --host 0.0.0.0 --port $PORT
```

部署静态资源的代码在 `backend/web.py`；`scripts/start.py` 负责本地安装、构建和启动。

## 技术文档交接

`docs/TECHNICAL_DRAFT.md` 是当前技术底稿。配套上线核验版Word和PDF已补充实际模型、真实调用记录及线上截图；比赛提交前仍需核对视频和最终材料，保留问答效果评测的覆盖边界。
