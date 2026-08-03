# 制度智能审查系统官方技术资料索引

## 1. 说明

| 项目 | 内容 |
|---|---|
| 下载日期 | 2026-07-30 |
| 资料范围 | `TECHNICAL_SOLUTION.md` 1.0.0 中已采用的技术，以及用户指定的国产模型候选 |
| 来源要求 | 只保存技术官网、标准组织或官方 GitHub 仓库提供的资料 |
| 使用目的 | 供后续 AI 编码、接口核对、故障排查和离线检索 |
| 模型候选 | DeepSeek、智谱 BigModel；最终供应商和模型尚未确定 |

资料内容属于各自项目或组织，其许可证和使用条款仍然有效。本目录是下载时点的离线快照；正式开发前应结合在线官方文档检查重大版本变化。

## 2. 前端

### Vue 3

- 本地目录：`frontend/vue-3/`
- AI 友好手册：`frontend/vue-3-official-manual.txt`
- 官方来源：
  - https://vuejs.org/
  - https://github.com/vuejs/docs
- 用途：组合式 API、组件、响应式、TypeScript、表单与应用结构。

### TypeScript

- 本地目录：`frontend/typescript-handbook/`
- 官方来源：https://github.com/microsoft/TypeScript-Website
- 用途：类型系统、对象、函数、泛型、类型收窄、模块和声明。

### Vite

- AI 友好手册：`frontend/vite-official-manual.txt`
- 官方来源：https://vite.dev/
- 用途：Vue 项目创建、开发服务器、环境变量、资源处理和生产构建。

### Element Plus

- AI 友好手册：`frontend/element-plus-official-manual.txt`
- 官方来源：https://element-plus.org/
- 用途：后台表单、表格、筛选、分页、弹窗、标签页和反馈组件。

### Vue Router

- AI 友好手册：`frontend/vue-router-official-manual.txt`
- 官方来源：https://router.vuejs.org/
- 用途：审查人员区、管理员区、路由守卫和页面参数。

### Pinia

- 本地目录：`frontend/pinia/`
- 官方来源：
  - https://pinia.vuejs.org/
  - https://github.com/vuejs/pinia
- 用途：当前用户、权限和跨页面临时数据。

## 3. 后端

### Python 3.12

- 本地目录：`backend/python-3.12-text/`
- 官方来源：https://docs.python.org/3.12/
- 用途：语言标准库、异步、类型、文件、异常和测试基础。
- 说明：采用官方纯文本完整手册，便于 AI 全文检索。

### FastAPI

- 本地目录：`backend/fastapi/`
- 官方来源：
  - https://fastapi.tiangolo.com/
  - https://github.com/fastapi/fastapi
- 用途：REST API、请求校验、文件上传、Cookie、鉴权、依赖注入、SSE/流式响应、错误处理和 OpenAPI。

### Pydantic

- AI 友好手册：`backend/pydantic-official-manual.txt`
- 官方来源：https://docs.pydantic.dev/
- 用途：请求响应模型、四维审查结果模型、结构化模型输出校验。

### SQLAlchemy 2

- 本地目录：`backend/sqlalchemy-2/`
- 官方来源：
  - https://docs.sqlalchemy.org/en/20/
  - https://github.com/sqlalchemy/sqlalchemy
- 用途：ORM 模型、关系、会话、事务、查询和 PostgreSQL 方言。

### Alembic

- 本地目录：`backend/alembic/`
- 官方来源：
  - https://alembic.sqlalchemy.org/
  - https://github.com/sqlalchemy/alembic
- 用途：数据库迁移、自动生成迁移和版本管理。

### pytest

- 本地目录：`backend/pytest/`
- 官方来源：
  - https://docs.pytest.org/
  - https://github.com/pytest-dev/pytest
- 用途：单元测试、接口测试、fixture 和参数化测试。

## 4. 数据库与检索

### PostgreSQL 18

- 官方 PDF：`database-and-retrieval/postgresql-18/postgresql-18.pdf`
- 官方来源：https://www.postgresql.org/docs/18/
- 验证结果：PostgreSQL 18.4 Documentation，3130 页，PDF 可正常读取。
- 用途：关系建模、事务、约束、索引、全文检索、GIN 和运维基础。

### pgvector

- 官方说明：`database-and-retrieval/pgvector/README.md`
- Python 接口说明：`database-and-retrieval/pgvector-python/README.md`
- 官方来源：
  - https://github.com/pgvector/pgvector
  - https://github.com/pgvector/pgvector-python
- 用途：向量列、距离函数、HNSW/IVFFlat 索引和 SQLAlchemy 集成。

### jieba

- 官方说明：`database-and-retrieval/jieba/README.md`
- 官方来源：https://github.com/fxsjy/jieba
- 用途：第一版中文分词、搜索模式和自定义词典。
- 注意：真实制度数据到位后仍需验证专业术语切分效果。

## 5. 文档解析

### python-docx

- 本地目录：`document-parsing/python-docx/`
- 官方来源：
  - https://python-docx.readthedocs.io/
  - https://github.com/python-openxml/python-docx
- 用途：读取 `.docx` 段落、样式和标题；本项目不解析表格。

### PyMuPDF

- 官方 PDF：`document-parsing/pymupdf/pymupdf-official-manual.pdf`
- 官方来源：https://pymupdf.readthedocs.io/
- 验证结果：PyMuPDF Documentation，622 页，PDF 可正常读取。
- 用途：普通文字 PDF 的打开、文本提取、阅读顺序和异常处理；本项目不使用 OCR。

## 6. 部署与接口规范

### Docker 与 Docker Compose

- 官方索引：`deployment-and-standards/docker/docker-official-manual.txt`
- 已成功下载的相关章节：`deployment-and-standards/docker/pages/`
- Compose 完整规范：`deployment-and-standards/compose-spec/`
- 官方来源：
  - https://docs.docker.com/
  - https://github.com/compose-spec/compose-spec
- 用途：镜像、容器、卷、网络、环境变量、服务依赖和 `compose.yaml`。
- 下载说明：Docker 官网对连续页面请求进行了连接重置。官方完整章节索引、46 个项目相关页面和 Compose 完整规范已保存，可覆盖第一版开发；其余页面可按索引在需要时单独补充。

### Nginx

- 入门指南：`deployment-and-standards/nginx/nginx-beginners.html`
- 反向代理模块：`deployment-and-standards/nginx/nginx-proxy.html`
- 官方来源：https://nginx.org/en/docs/
- 用途：提供 Vue 静态资源并反向代理 FastAPI。

### Server-Sent Events

- 标准章节：`deployment-and-standards/sse/server-sent-events.html`
- 官方来源：https://html.spec.whatwg.org/dev/server-sent-events.html
- 用途：当次审查的临时运行反馈，不建立持久化任务状态。

### OpenAPI

- 本地目录：`deployment-and-standards/openapi/`
- 官方来源：https://github.com/OAI/OpenAPI-Specification
- 用途：FastAPI 接口定义、前后端联调和接口文档。

## 7. 国产模型候选

### DeepSeek

- 官方 API 首页快照：`model-providers/deepseek-api-official-home.html`
- 中文核心 API 页面：`model-providers/deepseek-api-pages/`
- 官方来源：https://api-docs.deepseek.com/
- 用途：对话生成、结构化输出、流式输出、错误处理和 API 调用。
- 状态：候选，尚未确认具体模型。

### 智谱 BigModel

- 官方 API 手册：`model-providers/zhipu-bigmodel-official-manual.txt`
- 官方 Python SDK：`model-providers/zhipu-python-sdk/`
- 中文 SDK 说明：`model-providers/zhipu-python-sdk/README_CN.md`
- 官方来源：
  - https://docs.bigmodel.cn/
  - https://github.com/zai-org/z-ai-sdk-python
- 用途：对话生成、嵌入、流式输出、结构化结果和 Python SDK 调用。
- 状态：候选，尚未确认具体模型。

## 8. 明确未下载的资料

1. 未下载 OpenAI API 或模型资料。
2. 未下载 Redis、消息队列、Elasticsearch、独立向量数据库或 LangChain 资料，因为第一版技术方案不采用这些技术。
3. 未下载 OCR、制度表格解析和视觉排版审查资料，因为这些能力不在第一版范围内。
4. 未下载 DeepSeek 或智谱以外的模型厂商资料。
