# 通用客户信息管理系统（CIMS）

基于 **FastAPI + SQLAlchemy 2.0 + SQLite** 的通用客户信息采集与管理平台。项目、表单字段全部动态配置（不写死），前端按后端返回的字段配置自动生成表单；支持本地开发 → GitHub 代码管理 → GitHub Actions 自动构建 Docker 镜像 → 推送到 GHCR → 任意服务器 Docker 拉取运行的完整链路。

---

## 目录

- [功能特性](#功能特性)
- [技术栈与架构](#技术栈与架构)
- [快速开始（本地开发）](#快速开始本地开发)
- [环境变量配置](#环境变量配置)
- [后台使用指南](#后台使用指南)
- [客户填报说明](#客户填报说明)
- [邮件提醒](#邮件提醒)
- [数据备份与恢复](#数据备份与恢复)
- [接口契约与二次开发](#接口契约与二次开发)
- [GitHub → GHCR 自动构建](#github--ghcr-自动构建)
- [推送后自动部署到服务器（GitHub Secrets）](#推送后自动部署到服务器github-secrets)
- [服务器 Docker 部署](#服务器-docker-部署)
- [API 速查表](#api-速查表)
- [项目目录结构](#项目目录结构)
- [常见问题](#常见问题)

---

## 功能特性

- **动态项目管理**：项目支持名称、slug（英文短链）、描述、启停，随时增删改查
- **动态表单设计器**：每个项目可独立配置字段，支持 11 种字段类型：
  - `text` 单行文本、`textarea` 多行文本、`number` 数字、`email` 邮箱、`phone` 电话
  - `date` 日期、`datetime` 日期时间
  - `select` 下拉单选、`radio` 单选、`multiselect` 多选、`boolean` 是/否
  - 支持必填、占位提示、字段说明、排序、选项列表、最小/最大值、最小/最大长度、正则表达式
- **客户信息管理**：客户提交的数据按字段配置动态校验入库，支持分页、关键字搜索、查看、编辑、删除
- **客户填报表单**：公开链接免登录，前端根据字段配置自动渲染表单，后端二次校验，错误逐字段提示
- **邮件提醒（可选）**：按项目独立开关，客户每次提交后异步发送邮件给指定收件人，SMTP 故障不影响提交
- **账号密码登录**：后台使用 JWT 鉴权，密码 PBKDF2 哈希存储
- **API Token 集成**：独立/替换前端使用 `X-API-Token` 请求头，Token 仅由环境变量配置，改完重启即生效，无 UI
- **OpenAPI 契约**：FastAPI 自动生成，内置 Swagger UI / Redoc，可下载 `openapi.json`
- **数据库备份/恢复**：后台一键下载 SQLite 一致性快照到本地；可上传本地备份在线热恢复（自动校验文件合法性）
- **前后端解耦**：内置纯静态 UI 仅通过 REST API 交互，可随时整体替换为 Vue/React/小程序等任意前端

## 技术栈与架构

```
┌─────────────────────┐   JWT Bearer    ┌─────────────────────────────┐
│ 内置后台管理 UI      │ ──────────────▶ │ /api/admin/*   管理接口      │
│ (HTML/CSS/JS 静态页) │                 │                             │
├─────────────────────┤   免登录         │ 项目 / 字段 / 客户 CRUD      │
│ 客户公开填报表单     │ ──────────────▶ │ 邮件设置 / 备份恢复          │
│ /#/form/{id或slug}  │                 ├─────────────────────────────┤
├─────────────────────┤                 │ /api/public/*  公开填报接口  │
│ 任意替换的独立前端    │  X-API-Token    ├─────────────────────────────┤
│ (Vue/React/小程序…)  │ ──────────────▶ │ /api/v1/*      集成接口      │
└─────────────────────┘                 ├─────────────────────────────┤
                                        │ /docs /redoc /openapi.json   │
                                        └──────────────┬──────────────┘
                                                       │ SQLAlchemy 2.0
                                                       ▼
                                              SQLite 数据库文件
```

- 后端：Python 3.12、FastAPI、SQLAlchemy 2.0、Pydantic v2、PyJWT
- 前端：原生 HTML + CSS + JavaScript（无构建步骤，静态文件由 FastAPI 直接托管）
- 数据库：SQLite（单文件，零运维，挂载到 Docker 卷持久化）
- 交付：Docker 多架构镜像（linux/amd64 + linux/arm64）、GitHub Container Registry

## 快速开始（本地开发）

要求：Python 3.11+

```powershell
# 1. 创建虚拟环境并安装依赖
python -m venv .venv
.\.venv\Scripts\Activate.ps1        # Windows PowerShell
# source .venv/bin/activate         # macOS / Linux
pip install -r requirements.txt

# 2. 准备环境变量
copy .env.example .env              # Windows
# cp .env.example .env              # macOS / Linux
# 按需编辑 .env（不配 SMTP 也能正常使用，邮件功能仅不启用）

# 3. 启动开发服务器
uvicorn app.main:app --reload
```

打开浏览器访问：

| 地址 | 说明 |
| --- | --- |
| http://127.0.0.1:8000 | 后台登录页（默认账号 `admin` / `admin123456`） |
| http://127.0.0.1:8000/docs | Swagger UI（在线调试接口） |
| http://127.0.0.1:8000/redoc | Redoc 文档 |
| http://127.0.0.1:8000/openapi.json | OpenAPI 契约文件 |
| http://127.0.0.1:8000/#/forms | 客户填报入口（项目列表） |

> 首次启动会自动创建 `data/cims.db` 并按 `ADMIN_USERNAME / ADMIN_PASSWORD` 初始化管理员（仅当用户表为空时）。

## 环境变量配置

所有配置通过环境变量（本地开发读取项目根目录 `.env`，Docker 部署在 compose 的 `.env` 中配置）：

| 变量 | 必填 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `DATABASE_URL` | 否 | `sqlite:///./data/cims.db` | SQLite 连接串；**容器内固定为** `sqlite:////data/cims.db` |
| `SECRET_KEY` | 是（生产） | `change-me-in-production` | JWT 签名密钥，生产务必改为随机长串（如 `openssl rand -hex 32`） |
| `ADMIN_USERNAME` | 否 | `admin` | 初始管理员账号（仅首次初始化） |
| `ADMIN_PASSWORD` | 是（生产） | `admin123456` | 初始管理员密码（仅首次初始化） |
| `API_TOKEN` | 是（生产） | `change-me-api-token` | 集成接口 Token，**修改后重启即完成更换** |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | 否 | `720` | 后台登录 JWT 有效期（分钟） |
| `CORS_ORIGINS` | 否 | `*` | 跨域允许来源，多个用逗号分隔 |
| `SMTP_HOST` | 否 | 空 | SMTP 服务器地址，留空表示不启用邮件 |
| `SMTP_PORT` | 否 | `465` | SMTP 端口 |
| `SMTP_USER` | 否 | 空 | SMTP 登录账号/发件邮箱 |
| `SMTP_PASSWORD` | 否 | 空 | SMTP 密码或**授权码** |
| `SMTP_FROM` | 否 | 同 `SMTP_USER` | 发件人地址 |
| `SMTP_SECURITY` | 否 | `ssl` | 加密方式：`ssl`（465）/ `starttls`（587）/ `none` |
| `SMTP_TIMEOUT` | 否 | `15` | 发信超时秒数 |
| `IMAGE_URL` | 部署用 | — | 仅 `docker compose` 使用：GHCR 镜像地址 |
| `APP_PORT` | 否 | `8000` | 仅 `docker compose` 使用：宿主机对外端口（容器内固定 8000）；自动部署时由同名 Secret 注入 |

## 后台使用指南

### 1. 登录

访问根路径，使用管理员账号密码登录。登录后获得 JWT，保存在浏览器 localStorage，过期需重新登录。

### 2. 项目管理

「项目管理」页面：

- **新建项目**：填写项目名称、slug（可选，用于公开链接，只允许小写字母、数字、连字符）、描述
- **编辑/删除**：删除项目会级联删除其全部字段与客户数据，操作不可恢复
- 项目停用后，客户将无法访问其公开表单（返回 404）

### 3. 设计表单字段

进入项目详情 →「表单字段」标签页 →「新增字段」：

- **字段名称**：客户看到的标签，如"姓名"
- **键名 key**：提交数据 JSON 中的键，只允许字母、数字、下划线，且项目内唯一，如 `name`
- **字段类型**：11 种可选；选择 `select / radio / multiselect` 时必须逐行配置选项
- **校验规则**：数字可配最小/最大值；文本类可配最小/最大长度与正则（如手机号 `^1[3-9]\d{9}$`）
- 可设置必填、占位提示、说明、排序值、启停

修改即时生效，客户表单页下次打开即按最新配置渲染。

### 4. 管理客户信息

项目详情 →「客户信息」标签页：

- 表格按当前启用字段动态生成列，支持在提交内容中做关键字搜索与分页
- 可**手动新增**、**编辑**（按当前字段配置重新校验）、**删除**客户信息

### 5. 查看接口契约

「接口契约」页面提供 Swagger UI / Redoc 入口、`openapi.json` 下载、鉴权说明与调用示例。

## 客户填报说明

- 方式一：将公开链接发给客户：
  `http://你的域名或IP:8000/#/form/{项目slug}`，未设置 slug 时用 `/#/form/{项目ID}`
- 方式二：打开 `http://你的域名或IP:8000/#/forms` 查看全部启用中的项目
- 客户填写提交后，后端按字段配置二次校验，错误会逐字段标红提示；提交成功显示确认页

## 邮件提醒

按"**SMTP 服务能力 + 按项目开关**"两层配置：

1. **配置 SMTP（服务器侧）**：在 `.env` 中设置 SMTP 变量并重启。常见服务商：

   | 服务商 | SMTP_HOST | 端口 | SMTP_SECURITY | 密码 |
   | --- | --- | --- | --- | --- |
   | QQ 邮箱 | `smtp.qq.com` | 465 | `ssl` | 授权码 |
   | 163 邮箱 | `smtp.163.com` | 465 | `ssl` | 授权码 |
   | 阿里企业邮箱 | `smtp.qiye.aliyun.com` | 465 | `ssl` | 邮箱密码 |
   | Gmail | `smtp.gmail.com` | 587 | `starttls` | 应用专用密码 |

2. **开启项目提醒**：项目管理 → 编辑项目 → 勾选"收到客户表单提交时发送邮件提醒" → 填写收件人（多个用逗号或换行分隔）
3. **验证连通性**：后台「邮件提醒」页面查看 SMTP 状态，并可发送测试邮件

机制说明：

- 客户填报、后台手动新增、API Token 提交三个入口均会触发
- 邮件在数据**成功入库之后**通过后台线程异步发送，页面提交不会因邮件服务器慢/故障而失败
- 邮件内容包含项目名、提交时间、全部字段标签与客户填写值（HTML + 纯文本双格式）
- SMTP 凭据仅存在于环境变量，不会在界面回显或写入数据库

## 数据备份与恢复

SQLite 数据库运行在服务器容器的 `/data/cims.db`（Docker 卷持久化）。

- **备份到本地**：后台「备份与恢复」→「下载数据库备份」，系统使用 sqlite3 在线 backup API 生成一致性快照 `cims-backup-时间戳.db` 并通过浏览器下载
- **从本地恢复**：选择本地 `.db` 文件上传，系统依次校验：文件头（SQLite 魔数）→ `PRAGMA integrity_check` 完整性 → 必备系统表；通过后在线热替换数据库，无需停机
- 恢复会用备份文件覆盖当前全部数据，操作前请先备份现有数据
- 备份文件就是标准 SQLite 文件，也可用 DB Browser for SQLite 等工具直接打开

## 接口契约与二次开发

### 鉴权方式

| 接口前缀 | 鉴权 | 用途 |
| --- | --- | --- |
| `/api/admin/*` | `Authorization: Bearer <JWT>`（账号密码登录换取） | 后台 UI |
| `/api/public/*` | 无 | 客户填报 |
| `/api/v1/*` | `X-API-Token: <API_TOKEN>` | 独立部署/替换的前端、系统集成 |

### 典型调用示例

```bash
# 后台登录获取 JWT
curl -X POST http://服务器:8000/api/auth/login \
  -d "username=admin&password=你的密码"

# 集成接口：获取项目 1 的字段配置（Token 来自环境变量 API_TOKEN）
curl -H "X-API-Token: 你的Token" \
  http://服务器:8000/api/v1/projects/1/fields

# 集成接口：提交一条客户信息（后端按字段配置校验）
curl -X POST http://服务器:8000/api/v1/projects/1/customers \
  -H "X-API-Token: 你的Token" \
  -H "Content-Type: application/json" \
  -d '{"data":{"name":"张三","phone":"13800000000"}}'

# 客户公开提交（无需鉴权）
curl -X POST http://服务器:8000/api/public/projects/expo-2026/submissions \
  -H "Content-Type: application/json" \
  -d '{"data":{"name":"李四"}}'
```

替换前端时，让新前端只对接 `/api/v1/*`（或公开接口），契约以 `/openapi.json` 为准，可用 openapi-generator 自动生成客户端 SDK；内置静态 UI 可直接删除，后端无需改动。

## GitHub → GHCR 自动构建

仓库已配置工作流 [.github/workflows/docker-publish.yml](.github/workflows/docker-publish.yml)：

- 推送到 `main`/`master`：自动构建并推送 `ghcr.io/<所有者>/<仓库名>:latest` 及 `sha-xxxx` 标签
- 推送 `v*` 标签（如 `v1.0.0`）：额外生成 `1.0.0`、`1.0` 语义化版本标签
- 镜像同时支持 `linux/amd64` 与 `linux/arm64`；Pull Request 只构建不推送
- 鉴权使用 Actions 内置的 `GITHUB_TOKEN`，无需额外配置 Secret

查看构建过程：GitHub 仓库 → **Actions** 标签页。
镜像地址：仓库首页右侧 → **Packages**，或 `ghcr.io/<你的用户名>/<仓库名>`。

首次推送或日常更新：

```bash
git add .
git commit -m "feat: 你的变更说明"
git push origin main
```

发布版本标签：

```bash
git tag v1.0.0
git push origin v1.0.0
```

## 推送后自动部署到服务器（GitHub Secrets）

工作流在镜像构建任务后追加了 **deploy 任务**（仅推送 `main` 分支触发；PR、tag 不会触发；同一时间只允许一个部署任务）：

```text
git push origin main
   └─▶ ① docker 任务：buildx 构建 amd64/arm64 → 推送 GHCR
          └─▶ ② deploy 任务：SCP 同步 compose 文件 → SSH 执行
                 .env 注入 →（私有包可选登录 GHCR）→ docker compose pull/up → 健康检查
```

### 第一步：生成一对专用部署密钥

在你本地电脑（不是服务器）执行，回车两次不设密码：

```bash
ssh-keygen -t ed25519 -f cims_deploy -C "github-actions-deploy"
```

生成 `cims_deploy`（私钥）和 `cims_deploy.pub`（公钥）。把**公钥**安装到服务器：

```bash
# 自行 SSH 登录服务器后执行（如使用非 root 用户，将该用户加入 docker 组：sudo usermod -aG docker 用户名）
mkdir -p ~/.ssh && chmod 700 ~/.ssh
echo "这里粘贴 cims_deploy.pub 的全部内容" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

> 私钥只放进 GitHub Secret，不要提交到仓库，对话中也不要粘贴完整私钥。

### 第二步：在仓库中配置 Secrets

进入 GitHub 仓库 → **Settings → Secrets and variables → Actions → New repository secret**，逐个添加：

| Secret 名称 | 必填 | 说明 |
| --- | --- | --- |
| `SSH_HOST` | 是 | 服务器公网 IP 或域名 |
| `SSH_USERNAME` | 是 | SSH 登录用户（如 `root`、`ubuntu`；非 root 需在 docker 组） |
| `SSH_KEY` | 是 | `cims_deploy` 私钥文件的**完整内容**（含 `-----BEGIN/END...-----` 两行） |
| `SSH_PORT` | 否 | SSH 端口，默认 22 |
| `DEPLOY_DIR` | 否 | 服务器部署目录，默认 `/opt/cims` |
| `DEPLOY_ENV` | 否 | 完整 `.env` 内容（多行直接整段粘贴）；**配置后每次部署都会覆盖服务器 .env** |
| `APP_PORT` | 否 | 宿主机对外访问端口，默认 `8000`（容器内固定 8000）。改端口后下次部署自动重建端口映射，记得同步放行安全组 |
| `GHCR_PAT` | 视情况 | 镜像包为**私有**时必填：勾选了 `read:packages` 权限的 GitHub PAT；包改公开则无需配置 |

> 端口取值优先级：`APP_PORT` Secret ＞ 服务器 `.env` 中的 `APP_PORT` ＞ 默认 `8000`。

`DEPLOY_ENV` 的内容就是部署环境变量（参考 [.env.example](.env.example)），例如：

```env
IMAGE_URL=ghcr.io/oceandriel/webbake:latest
SECRET_KEY=随机长字符串
ADMIN_USERNAME=admin
ADMIN_PASSWORD=强密码
API_TOKEN=随机长Token
APP_PORT=8000
SMTP_HOST=smtp.qq.com
SMTP_PORT=465
SMTP_USER=你的邮箱@qq.com
SMTP_PASSWORD=授权码
SMTP_SECURITY=ssl
```

- 不配置 `DEPLOY_ENV` 时，工作流沿用服务器上手动维护的 `$DEPLOY_DIR/.env`，但首次部署前该文件必须已存在
- 修改 Secret 后**下一次推 main 即生效**，无需登录服务器
- 安全组/防火墙需放行 SSH 端口（默认 22）与服务端口（`APP_PORT`，默认 8000）；修改 `APP_PORT` 后旧端口自动释放，需放行新端口才能访问

### 第三步：服务器一次性准备（仅首次）

服务器需已安装 Docker Engine 与 Docker Compose 插件：

```bash
docker --version && docker compose version    # 验证
mkdir -p /opt/cims                            # 与 DEPLOY_DIR 保持一致；不配置 DEPLOY_ENV 时在此目录放好 .env
```

### 第四步：触发与验证

推送到 `main` 后，在仓库 **Actions** 页面可看到 `docker` → `deploy` 两个任务依次执行。部署脚本最后会请求 `http://127.0.0.1:8000/health` 做健康检查，失败则本次部署标记为失败（旧容器仍在运行，可在日志中排查）。

**回滚**：SSH 登录服务器，把 `.env` 中的 `IMAGE_URL` 改为上一个可用的 `sha-xxxxxxxx`（镜像标签见 Actions 构建日志或 Packages），执行 `docker compose up -d`。

## 服务器 Docker 部署（手动方式）

适用于任意安装了 Docker / Docker Compose 的 Linux 服务器（x86 或 ARM 均可）。

1. 将本仓库中的 [docker-compose.yml](docker-compose.yml) 与 [.env.example](.env.example) 放到服务器同一目录（可只下载这两个文件）

2. 创建 `.env` 并修改：

   ```env
   IMAGE_URL=ghcr.io/oceandriel/webbake:latest
   SECRET_KEY=用openssl生成的随机长字符串
   ADMIN_USERNAME=admin
   ADMIN_PASSWORD=请改成强密码
   API_TOKEN=请改成随机长Token
   # 需要邮件提醒时再补充 SMTP_* 变量
   ```

3. 如果镜像是**私有包**，先登录 GHCR（公开包可跳过）：

   ```bash
   echo "你的GitHub_PAT(需read:packages权限)" | docker login ghcr.io -u 你的GitHub用户名 --password-stdin
   ```

4. 启动：

   ```bash
   docker compose up -d
   docker compose logs -f      # 查看日志
   ```

5. 访问 `http://服务器IP:8000`，建议前面再挂 Nginx/Caddy 配置 HTTPS 域名

更新到最新镜像：

```bash
docker compose pull
docker compose up -d        # 数据在 cims-data 卷中，升级不丢数据
```

备份数据库卷（除后台下载外的可选方式）：

```bash
docker run --rm -v webback_cims-data:/data -v "$PWD":/backup alpine \
  tar czf /backup/cims-data.tar.gz -C /data .
```

## API 速查表

| 方法 | 路径 | 鉴权 | 说明 |
| --- | --- | --- | --- |
| POST | `/api/auth/login` | — | 账号密码登录（form 表单），返回 JWT |
| GET | `/api/auth/me` | JWT | 当前登录用户 |
| GET/POST | `/api/admin/projects` | JWT | 项目列表（分页/搜索）/ 新建 |
| GET/PUT/DELETE | `/api/admin/projects/{id}` | JWT | 项目详情/更新/删除 |
| GET/POST | `/api/admin/projects/{id}/fields` | JWT | 字段列表/新增字段 |
| GET/PUT/DELETE | `/api/admin/fields/{id}` | JWT | 字段详情/更新/删除 |
| GET/POST | `/api/admin/projects/{id}/customers` | JWT | 客户列表（分页/搜索）/手动新增 |
| GET/PUT/DELETE | `/api/admin/customers/{id}` | JWT | 客户详情/编辑/删除 |
| GET | `/api/admin/database/backup` | JWT | 下载数据库备份 |
| POST | `/api/admin/database/restore` | JWT | 上传备份恢复（multipart） |
| GET | `/api/admin/settings/email` | JWT | SMTP 配置状态（脱敏） |
| POST | `/api/admin/settings/email/test` | JWT | 发送测试邮件 |
| GET | `/api/public/projects` | — | 启用中的项目列表 |
| GET | `/api/public/projects/{id或slug}/form` | — | 动态表单字段配置 |
| POST | `/api/public/projects/{id或slug}/submissions` | — | 客户提交表单 |
| GET | `/api/v1/projects` | Token | 项目列表 |
| GET | `/api/v1/projects/{id}/fields` | Token | 字段配置 |
| GET/POST | `/api/v1/projects/{id}/customers` | Token | 客户列表/新增 |
| GET/PUT/DELETE | `/api/v1/customers/{id}` | Token | 客户详情/编辑/删除 |
| GET | `/health` | — | 健康检查 |

列表类接口统一使用 `page`（从 1 开始）、`page_size`（默认 20，最大 200）分页参数，返回结构：

```json
{ "items": [], "total": 0, "page": 1, "page_size": 20 }
```

## 项目目录结构

```
webback/
├── app/
│   ├── main.py                # FastAPI 入口：中间件、路由、静态 UI 挂载
│   ├── config.py              # 环境变量配置（含 SMTP）
│   ├── database.py            # 引擎/会话工厂/建表/轻量迁移/引擎重绑
│   ├── services.py            # 业务服务层（含提交后邮件通知）
│   ├── api/
│   │   ├── auth.py            # 登录 / JWT
│   │   ├── deps.py            # 公共依赖（JWT、API Token、分页）
│   │   ├── admin_projects.py  # 项目 CRUD
│   │   ├── admin_fields.py    # 字段 CRUD
│   │   ├── admin_customers.py # 客户 CRUD
│   │   ├── admin_backup.py    # 备份下载 / 恢复上传
│   │   ├── admin_settings.py  # 邮件状态 / 测试发送
│   │   ├── public.py          # 客户公开填报
│   │   └── v1.py              # API Token 集成接口
│   ├── core/
│   │   ├── security.py        # 密码哈希与 JWT
│   │   ├── validation.py      # 按字段配置动态校验提交数据
│   │   └── email_utils.py     # SMTP 发送与异步提醒
│   ├── models/                # SQLAlchemy 模型
│   ├── schemas/               # Pydantic 模型
│   └── static/                # 内置后台 UI 与填报表单（可整体替换）
│       ├── index.html
│       ├── css/app.css
│       └── js/ (api.js / forms.js / app.js)
├── .github/workflows/docker-publish.yml
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```

## 常见问题

**Q：忘记管理员密码怎么办？**
A：管理员密码只在用户表为空时自动初始化。可在服务器上用 `docker exec -it cims python` 进入容器执行 Python，调用 `app.core.security.hash_password` 更新 users 表；或通过备份恢复机制处理。注意改环境变量中的 `ADMIN_PASSWORD` 不会重置已有密码。

**Q：修改 API Token / SMTP 配置后不生效？**
A：这些配置只在启动时读取，需要重启服务（`docker compose restart` 或本地重启 uvicorn）。

**Q：客户提交后没收到提醒邮件？**
A：依次检查：①「邮件提醒」页 SMTP 状态是否"已配置"并用测试邮件验证；②项目编辑弹窗中提醒是否勾选、收件人是否正确；③ `docker compose logs cims` 中是否有发送失败异常。即使发信失败，客户数据也已正常保存，重发即可。

**Q：客户能看到/提交其他项目的数据吗？**
A：不能。公开接口只能读取启用项目的字段配置和提交自己的数据，没有任何查询/列举客户数据的能力；客户数据仅后台 JWT 与 API Token 可访问。

**Q：如何只做后端，前端完全自研？**
A：新前端对接 `/api/v1/*`（`X-API-Token` 鉴权）与 `/api/public/*`（填报），从 `/openapi.json` 生成客户端即可。部署时可用 Nginx 单独托管前端并通过 `CORS_ORIGINS` 放行其域名。

**Q：升级版本会影响已有数据吗？**
A：不会。数据在 Docker 卷中；新版本启动时会自动执行向后兼容的轻量表结构迁移（如补列），仍建议升级前先在后台下载一次备份。
