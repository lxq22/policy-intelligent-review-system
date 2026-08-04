# 制度智能审查系统

`event/` 是系统代码与官方技术资料目录。

## 目录

- `frontend/`：Vue 3 + TypeScript 前端。
- `backend/`：FastAPI + SQLAlchemy + Alembic 后端。
- `compose.yaml`：前端、API、PostgreSQL 18 + pgvector 的本地组合运行配置。
- `official-tech-docs/`：开发时使用的官方资料离线快照。
- `M2_DELIVERY.md`：M2 页面原型交付说明。
- `M3_DELIVERY.md`：M3 基础业务交付说明。

## 推荐运行方式

需要先安装并启动 Docker Desktop，然后在本目录运行：

```bash
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
