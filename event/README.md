# 制度智能审查系统

`event/` 是系统代码与官方技术资料目录。

## 目录

- `frontend/`：Vue 3 + TypeScript 前端。
- `backend/`：FastAPI + SQLAlchemy + Alembic 后端。
- `compose.yaml`：前端、API、PostgreSQL 18 + pgvector 的本地组合运行配置。
- `official-tech-docs/`：开发时使用的官方资料离线快照。
- `M2_DELIVERY.md`：M2 页面原型交付说明。
- `M3_DELIVERY.md`：M3 基础业务交付说明。
- `M4_DELIVERY.md`：M4 文件解析、候选召回与审查输入交付说明。
- `M5_DELIVERY.md`：M5 四维智能审查与报告交付说明。

## 推荐运行方式

需要先安装并启动 Docker Desktop，然后在本目录运行：

```bash
cp .env.example .env
# 打开 .env，只填写 LLM_API_KEY
docker compose up --build
```

首次运行需要能够访问 Docker Hub 以拉取 PostgreSQL/pgvector、Python、Node 和 Nginx 镜像。如果 `auth.docker.io:443` 超时，请先连接可访问 Docker Hub 的网络/VPN，或在 Docker Desktop 中配置可用代理，再重新执行同一命令。

完成后打开：

- 系统页面：<http://localhost:8080>
- 后端接口文档：<http://localhost:8000/docs>

演示账号统一初始密码为 `demo123`：

- `reviewer`：拥有上传、删除、关系管理权限。
- `reviewer_limited`：没有三项可配置权限。
- `admin`：系统管理员。

## 分开运行前后端

数据库仍建议通过 PostgreSQL 容器运行。后端：

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[test]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
pnpm install
pnpm dev
```

前端开发服务器会把 `/api` 请求转发到 `http://127.0.0.1:8000`。

## M5 已实现能力

- 上传并解析可选文字的 `.docx`、`.pdf` 制度文件，保存版本、解析状态和条款。
- 从制度库或临时文件选择待审条款，并选择一个或多个审查维度。
- 仅在当前制度关系覆盖的制度中，以关键词和 256 维本地向量混合召回候选条款。
- 用户确认候选条款后保存不可变审查输入，并按“制度名称-日期-序号”自动编号。
- 容器重启后保留原始文件、解析条款和审查记录。
- 使用“本地规则＋智谱 GLM‑4.7”执行语义分歧、规则匹配、制度冲突和一致性审查。
- 报告严格绑定本次审查记录，按维度展示真实问题和可信原文证据。
- 支持采纳修改建议、忽略和补充处理意见，并永久记录操作人、时间和内容。

当前不支持扫描 PDF 的 OCR、Word 表格解析和页码定位。规则审查只覆盖文本结构、条款编号和行文规范。

## 测试

```bash
cd backend
.venv/bin/pytest -q

cd ../frontend
pnpm test
pnpm exec vue-tsc --noEmit
pnpm build
```
