# 账号功能配置与验收

本更新以 `35caf1c330ed5668d576aec822854fb5e6a85e32`（Logo 已替换）为基础，将队友的独立 HTML 预览改为 Vue 组件，并添加真实后端账号功能。旧 HTML 不是可直接覆盖的项目首页，不随本包替换 `frontend/index.html`。

## 本地运行

在完整项目根目录运行：

```bash
python scripts/start.py
```

打开 `http://127.0.0.1:8000`，点击侧栏“登录 / 注册”；也可直接打开 `http://127.0.0.1:8000/login`。

账号为 6 至 20 位字母或数字，不区分大小写；密码为 8 至 128 个字符。注册成功后再登录。本功能不预置账号或通用演示密码。

本地默认自动创建 `database/careerlens_auth.sqlite3`。账号和会话保存在该文件中；重新启动程序后仍可登录。文件及其 SQLite 日志已由 `.gitignore` 排除。自定义位置可在本地环境变量中设置 `CAREERLENS_AUTH_DB_PATH`。

## Render 配置

Render 免费 Web Service 使用临时文件系统，本地文件会在重新部署、重启或休眠后丢失，因此本实现不会在 Render 上悄悄回退到 SQLite。没有配置数据库时，登录页明确显示账号服务暂不可用，并保留访客入口。

1. 在 Render Dashboard 选择 **New → Postgres**，为账号创建数据库。选择与当前 Web Service 相同的区域。
2. 创建前查看计划及实际价格。若选择 Free，注意其有 30 天有效期，且不提供备份；不能把它写成永久免费持久化。赛事之后若长期保留项目，需要另行迁移或升级，并安排备份。
3. 数据库就绪后，复制它的 **Internal Database URL**。在现有 CareerLens Web Service 的 **Environment** 中新增 `DATABASE_URL`，值为完整连接串。
4. 连接串按密钥保存，只填到服务端环境变量。保留原有 `DEEPSEEK_API_KEY` 等设置，选择 **Save and deploy**。
5. 使用新增账号代码完成部署后，访问 `/api/auth/status`。应返回 `available: true`，再测试 `/login` 的注册、登录、刷新、退出。

数据库表由程序在首次需要时创建，表名为 `careerlens_users`、`careerlens_sessions`。如果连接失败，浏览器只得到通用提示，不回显连接串或底层数据库报错。

参考 Render 官方说明（2026-10-27 核对）：

- https://render.com/docs/free
- https://render.com/docs/disks

## 已实现的边界

账号与会话由后端管理：

- `POST /api/auth/register`：校验格式并创建账号；重复账号返回 409。
- `POST /api/auth/login`：验证密码并创建随机服务端会话；错误账号和密码统一返回 401。
- `GET /api/auth/me`：由当前 Cookie 检查登录状态，不能通过本地存储伪造登录。
- `POST /api/auth/logout`：撤销当前会话并清除 Cookie。
- `GET /api/auth/status`：报告账号服务是否可用。

密码使用每次随机的 16 字节盐和 600,000 轮 PBKDF2-HMAC-SHA256。数据库保存密码哈希；会话使用 32 字节安全随机令牌，数据库仅保存令牌摘要和绝对失效时间，默认 7 天。Cookie 带 HttpOnly、SameSite=Lax，HTTPS 或 Render 环境使用 Secure。

账号写操作要求准确的 Origin 和 `X-CareerLens-Client: browser` 请求头。除相同来源外，本地默认允许 5173 的 Vite 来源；使用 5174 等其他端口时，需在本地环境变量 `AUTH_ALLOWED_ORIGINS` 中加入准确来源，例如 `http://127.0.0.1:5174`。同一个站点的一体化部署不需要此项。

进程内限制同时进行的密码运算最多 2 个；注册限制每个来源 IP 每小时 10 次；登录限制每 IP 每 5 分钟 30 次、每账号每 5 分钟 20 次。这些限制不是分布式限流，也没有替代压力测试或生产安全审计。

前端历史记录仍是浏览器本地数据，按账号 ID 或访客分开。原有访客记录保留在原键名下，不会自动合并到新账号。历史记录没有跨设备同步，也不是服务端私有数据接口。

六个就业分析页面支持访客浏览；登录不是这些公开功能的服务端访问门槛。未实现邮件验证、短信验证码、找回密码、个人资料页或跨端历史同步。

预览页中的“742 合作企业”“35 热门行业”已纠正为从 `/api/trends` 读取的技能标签数、覆盖城市数；不作企业合作或行业覆盖承诺。

## 本次验证

本地检查的实际结果记录在 `qa_auth_20261027.json`。自动检查与浏览器问答均使用规则模式，真实模型调用数为 0；本次没有重新测量或宣称模型效果提升。

`tests/test_auth.py` 覆盖密码哈希、重复账号、错误密码、会话恢复和撤销、过期或伪造令牌、来源检查、Cookie 属性、限流以及数据库故障的访客入口。

`frontend/tests/history.test.js` 覆盖访客与两个账号的记录区分、删除范围、原访客键兼容和 100 条上限。路由测试补充 `/login`。

CI 增加独立的 Postgres 17 测试容器，通过 `AUTH_TEST_DATABASE_URL` 运行真实 Postgres 的注册、重复账号、登录、会话查询和撤销检查。此变量只指向测试库；真实 `DATABASE_URL` 仅在服务端配置。本地没有独立 Postgres 时，该项明确标为跳过，不能算作通过。

本包交付时账号功能尚待用户本机复测、GitHub CI 和 Render 配置后验收；不能将已有的 RAG 线上验收直接当作账号上线验收。账号成功上线后，应同步更新技术文档与演示视频。
