# M10 — agents/profile + 文件管理 设计稿

> 起草:2026-05-25
> 来源:`PRAXIS-2-计划-v2-完整重写-路线图.md` §6,经 2026-05-25 brainstorming 11 个决策点收紧后定稿。
> 上游约束:
> - [v0.10.0 已 ship](../../../VERSION-STATUS-v0.10.0.md) — `praxis2/core / agents / brains / tools / scheduler / runtime` 全程不动
> - [M13 推迟](/Users/mzy/.claude/projects/-Volumes-T7-clade-learn/memory/project_m13_deferred.md) — v1 链路冻结
> - 部署形态:`.40:8080` v2 入口 / `.53:8001` backend(gunicorn + conda env `praxis2`)/ PG docker / Redis docker

---

## §0 决策摘要(11 项已锁,brainstorming 输出)

| # | 决策 | 取值 |
|---|------|------|
| 1 | 文件存储后端 | 本地 fs `.53:/home/zkyd/data1/praxis2-files/<user_id>/<file_id>`(env `PRAXIS_FILES_ROOT`);v3 上云预留 `files/store_s3.py` 接口 |
| 2 | 单文件上限 | **20 GB**(env `PRAXIS_FILES_MAX_PER_FILE_BYTES` 默认 `21474836480`)— 必须流式 multipart |
| 3 | 用户总配额 | **100 GB**(env `PRAXIS_FILES_QUOTA_BYTES` 默认 `107374182400`)— 单 plan 不分,M12 用 admin/adjust 给个别用户调 |
| 4 | multipart 库 | `python-multipart>=0.0.9`(加依赖) |
| 5 | `purpose` | 枚举 `pdb / config / report / md_input / other`,DB CHECK 约束;非法 → 400 |
| 6 | brain profile 缓存 | Process-lifetime:启动 lazy walk 13 brain + module-level dict;改 brain → 重启 backend |
| 7 | 文件下载 | M10 做 `GET /api/files/{id}/content`,支持 `Range: bytes=N-M` → 206 |
| 8 | 文件名 sanitization | 自写正则 `[A-Za-z0-9._一-鿿-]+`(保留中文),200 字符截断;真存储路径用 UUID,filename 仅 DB display |
| 9 | mime 检测 | `python-magic>=0.4.27` + `libmagic1` 系统库(`.53` `sudo apt install libmagic1` 一次性);上传后服务端检,不信任 client `Content-Type` |
| 10 | `sample_cases` + 4 文本字段 | `sample_cases` 取 `brains/<slug>/memory/cases/` 前 5(mtime DESC,取 `title` from frontmatter / 文件名);`short_prompt`/`methods`/`helps_with`/`delivers` 从 `brains/<slug>/metadata.yaml`(若缺 → 返空,后续 brain 作者补)|
| 11 | 配额 / 超限错码 | `413 Payload Too Large` + `{error:"file_too_large", limit_bytes}` 或 `{error:"quota_exceeded", used_bytes, quota_bytes}` |

---

## §1 范围(P0 / Carry)

### P0 — M10 必做(~6.5d)

- **DB**:`003_files.py` migration(`files` 表 + 2 索引)
- **新模块** `praxis2/files/`:
  - `repo.py` — `FilesRepo` CRUD(asyncpg)
  - `store_fs.py` — `FsStore.write_stream / read_stream / delete / exists`
  - `mime.py` — `detect(path) -> str`(magic + octet-stream 兜底)
  - `multipart_stream.py` — `parse_upload(receive)` 真流式 parser(20GB safe)
  - `security.py` — `sanitize_filename(name) -> str`
- **brain profile**:`praxis2/brains/profile.py`(`load_all_profiles()` + `load_metadata_yaml(slug)`,启动一次 walk)
- **6 个 endpoint** + ROUTES 注册:
  - `GET /api/agents/profile`
  - `GET /api/files` (`?purpose=`)
  - `POST /api/files` (`?purpose=` + multipart)
  - `DELETE /api/files/{id}`
  - `GET /api/files/usage`(真接 + **顺便 fix M9.1 stub 字段名 `files_count` → `count`**)
  - `GET /api/files/{id}/content`(含 Range)
- **Config 3 个 env**:`PRAXIS_FILES_ROOT` / `PRAXIS_FILES_QUOTA_BYTES` / `PRAXIS_FILES_MAX_PER_FILE_BYTES`
- **依赖**:`python-multipart>=0.0.9` + `python-magic>=0.4.27` + `PyYAML>=6.0`(metadata.yaml 解析)
- **.53 ops**:`sudo apt install libmagic1`(staging 一次性,失败 → fallback by checking magic bytes 表)
- **gunicorn timeout**:`120s → 1800s`(20GB upload 慢路径,在 `deploy/gunicorn.conf.py`)
- **deploy/push_backend.sh**:pip install 加新 deps

### Carry(M10 不做)

| Carry | 推到 |
|---|---|
| 异步 GC 真删 fs 文件(M10 软删 DB,fs 留) | M11 后台清理任务 |
| 单 plan 配额差异化(free 100GB vs pro 500GB) | M12 admin/adjust_quota |
| `store_s3.py` 真接腾讯云 COS | v3 上云 |
| 真 virus scan / antivirus | 永远(staging 私网信任) |
| 多文件 multipart(同 POST 多 file field) | M10.5(单文件够 staging) |
| 断点续传(`Tus / RFC 7233 Range upload`) | M10.5 |
| brain `metadata.yaml` 批量自写(13 学科文案) | brain 作者后续提交 |
| `/api/admin/files/*`(全用户文件审查) | M12 admin v2 |

---

## §2 DB schema(`003_files.py`)

```sql
-- migrations/versions/003_files.py
revision = "003_files"
down_revision = "002_user_profile_billing"

def upgrade() -> None:
    op.execute("""
        CREATE TABLE files (
            id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            filename    TEXT NOT NULL,
            size_bytes  BIGINT NOT NULL CHECK (size_bytes >= 0),
            mime        TEXT,
            purpose     TEXT NOT NULL
                         CHECK (purpose IN ('pdb','config','report','md_input','other')),
            storage_key TEXT NOT NULL,
            created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
            deleted_at  TIMESTAMPTZ
        );
    """)
    op.execute(
        "CREATE INDEX ix_files_user_purpose ON files(user_id, purpose) "
        "WHERE deleted_at IS NULL;"
    )
    op.execute(
        "CREATE INDEX ix_files_user_created ON files(user_id, created_at DESC) "
        "WHERE deleted_at IS NULL;"
    )

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_files_user_created;")
    op.execute("DROP INDEX IF EXISTS ix_files_user_purpose;")
    op.execute("DROP TABLE IF EXISTS files;")
```

**`storage_key` 格式**:
- 本地 fs:`fs:<user_id>/<file_id>` — read path = `<PRAXIS_FILES_ROOT>/<user_id>/<file_id>`
- v3 S3:`s3://<bucket>/<user_id>/<file_id>` — `store_s3.py` 解析

---

## §3 模块清单

### 3.1 新增文件

| 路径 | 责任 | 估行 |
|------|------|---|
| `migrations/versions/003_files.py` | DDL upgrade/downgrade | 35 |
| `praxis2/files/__init__.py` | 包 | 0 |
| `praxis2/files/repo.py` | `FilesRepo`:`list_files / create_file / get_file / soft_delete / usage` | 120 |
| `praxis2/files/store_fs.py` | `FsStore`:`write_stream(uid, fid, async_iter) / read_stream(uid, fid, start=0, end=None) / delete / exists / get_size` | 100 |
| `praxis2/files/mime.py` | `detect(path) -> str`(`python-magic` + fallback octet-stream) | 30 |
| `praxis2/files/multipart_stream.py` | `parse_upload(receive) -> AsyncIterator[bytes] + filename + content_type`(包装 `python-multipart` Streaming parser) | 100 |
| `praxis2/files/security.py` | `sanitize_filename(name) -> str` | 25 |
| `praxis2/brains/profile.py` | `load_all_profiles() -> dict[slug, AgentProfile]`(module-level cache);`_walk_brain(slug)` 数 cases/rules/workflows;`_load_metadata_yaml(slug)` | 120 |
| `tests/test_files_repo.py` | repo CRUD(integration) | ~150 |
| `tests/test_files_store_fs.py` | streaming write/read + Range + 异常 cleanup | ~140 |
| `tests/test_files_routes.py` | 6 endpoint × happy + 错误 + Range | ~220 |
| `tests/test_files_security.py` | filename sanitize / path traversal / mime spoofing | ~80 |
| `tests/test_brains_profile.py` | 13 brain load / metadata 缺缺补缺 / sample_cases mtime DESC | ~100 |

### 3.2 改文件

| 路径 | 改动 |
|---|---|
| `praxis2/auth/routes.py` | **删** `handle_files_usage_stub`(M9.1 stub,字段名错位 `files_count`)+ `ROUTES` 里那一行;**不删** 其他 M9.1 admin stubs(M12 才接) |
| `praxis2/server/routes/__init__.py` | 包(已有) |
| `praxis2/server/routes/files.py` | **新**:6 个 handler + 模块级 `ROUTES dict[tuple,str]` (跟 `auth/routes.py:ROUTES` 同模式);`load_all_profiles` 也在此模块 boot 时调 |
| `praxis2/server/app.py` | `_App.__init__` 构造 `FilesRepo` + `FsStore` + boot 时 `load_all_profiles()`;merge `files_routes.ROUTES.items()` 进 `self._routes`(跟现有 auth_routes.ROUTES merge 同模式);构造 `files_deps = {repo, fs_store, settings}` dict 注入每个 handler |
| `praxis2/config.py` | 加 3 个 env 字段 |
| `pyproject.toml` | + `python-multipart>=0.0.9` + `python-magic>=0.4.27` + `PyYAML>=6.0` |
| `deploy/gunicorn.conf.py` | `timeout = 1800` |
| `deploy/push_backend.sh` | pip install 末尾加 3 个新 deps |
| `frontend/src/lib/extras.ts` | 0 改(shape 已对齐) |

### 3.3 brain metadata 模板(后续 brain 作者补)

`brains/<slug>/metadata.yaml`(可选,缺 → 4 字段返空):

```yaml
# brains/synth/metadata.yaml
short_prompt: "Synth 合成生物学智能体:异源表达通路 / antiSMASH BGC / Golden-Gate / Cell-free / FBA。"
methods:
  - antiSMASH
  - cobra (FBA)
  - cell-free 转录翻译
  - Golden-Gate cloning
helps_with:
  - 异源表达通路设计
  - BGC 挖掘 + 优先级
  - FBA 稳态多目标分析
delivers:
  - 5-Phase 选题 playbook
  - cobra FBA JSON + 通量图
  - 实验执行 pipeline 清单
```

13 学科都需要,可由 brain 作者按这个模板填。**M10 代码只 load 不写**。

---

## §4 Endpoint 合约(精确)

### 4.1 `GET /api/agents/profile` → 200

```json
{ "profiles": [
  {
    "slug": "synth",
    "name": "Synth 合成",
    "desc": "合成生物学 / 异源表达 / BGC 挖掘 / Cell-free / FBA",
    "emoji": "⚗️",
    "examples": ["把这条 pathway 转到 E.coli 怎么走?", ...],
    "short_prompt": "Synth 合成生物学智能体:...",
    "methods": ["antiSMASH", "cobra (FBA)", ...],
    "case_count": 22,
    "rule_count": 44,
    "skill_workflows": ["fba_steady_state", "antismash_bgc", ...],
    "sample_cases": [
      {"case_id":"01-bgc-prioritize", "title":"BGC 挖掘 + 优先级", "file":"brains/synth/memory/cases/01-bgc-prioritize.md"},
      // ... up to 5
    ],
    "helps_with": ["异源表达通路设计", ...],
    "delivers": ["5-Phase 课题方案", ...]
  }
  // ... 13 学科
]}
```

- 不需要登录(public,FE splash 阶段即调)
- module-level 缓存,boot 时 walk;后续请求 O(1)
- 缺 `metadata.yaml` 的 brain:4 个文本字段返 `[]` / `""`,FE 已有兜底
- `slug / name / desc / emoji / examples` 5 个字段从 `_AGENT_META`(`praxis2/server/app.py`)取,跟 `/api/agents` 一致

### 4.2 `GET /api/files?purpose=pdb` → 200

```json
{ "files": [
  {"id":"<uuid>", "filename":"1abc.pdb", "size_bytes":12345, "mime":"chemical/x-pdb", "purpose":"pdb", "created_at":"2026-05-25T..."}
]}
```

- `purpose` 缺失 → 返该用户所有文件
- `purpose` 不在 5 枚举 → 400 `{error:"invalid_purpose"}`
- 未登录 → 401
- DESC by created_at,默认全返(不分页;**M11 carry 分页,FE 期望简单数组**)

### 4.3 `POST /api/files?purpose=pdb` → 200

**Request**: multipart/form-data,`file` field

**Streaming pipeline**(实现关键):

```
multipart_stream.parse_upload(receive) 异步生成 chunks
  │
  ├─ 解析 filename + content_type (from form)
  ├─ for each chunk (8-64 KB):
  │    accumulate size_bytes
  │    if size_bytes > MAX_PER_FILE → abort + 413 + delete .part
  │    if usage(user) + size_bytes > QUOTA → abort + 413 + delete .part
  │    fs.write_stream(.part, chunk)
  │
  ├─ on EOF:
  │    detect mime via python-magic(read first 4KB of .part)
  │    sanitize_filename(form.filename)
  │    INSERT files row + COMMIT
  │    mv .part → final path
  │    return {id, filename, size_bytes, mime, purpose, created_at}
  │
  └─ on any exception (network drop / parse error / DB error):
       unlink .part
       return 500 {error:"upload_failed", reason}
```

**Response 200**:
```json
{"id":"<uuid>", "filename":"1abc.pdb", "size_bytes":12345, "mime":"chemical/x-pdb", "purpose":"pdb", "created_at":"..."}
```

**Error responses**:
- 401 未登录 `{error:"unauthorized"}`
- 400 purpose 不合法 `{error:"invalid_purpose"}`
- 400 form 解析失败(无 file field 等) `{error:"bad_multipart"}`
- 413 单文件超 `{error:"file_too_large", limit_bytes:21474836480}`
- 413 总配额超 `{error:"quota_exceeded", used_bytes:..., quota_bytes:107374182400}`
- 500 内部 `{error:"upload_failed", reason}`

### 4.4 `DELETE /api/files/{id}` → 200

```sql
UPDATE files SET deleted_at=now()
 WHERE id=$1 AND user_id=$2 AND deleted_at IS NULL
RETURNING id;
```

- 返 `{ok:true}` 或 404 `{error:"not_found"}`(不归属当前用户 / 已删 / 不存在 都 404)
- **fs 文件不删**(碰撞防止 + 误操作恢复;M11 异步 GC carry)

### 4.5 `GET /api/files/usage` → 200

```json
{"used_bytes":1234567, "quota_bytes":107374182400, "count":5, "max_per_file_bytes":21474836480}
```

- **字段名 `count` 不 `files_count`**(顺手 fix M9.1 stub 笔误)
- 30s in-memory cache(避免每次请求 SUM 全表)
- `used_bytes = SELECT SUM(size_bytes) FROM files WHERE user_id=$1 AND deleted_at IS NULL`
- `count = SELECT COUNT(*) FROM files WHERE user_id=$1 AND deleted_at IS NULL`

### 4.6 `GET /api/files/{id}/content` → 200 / 206

- 鉴权:`SELECT * FROM files WHERE id=$1 AND user_id=$2 AND deleted_at IS NULL`
- 不存在 / 不归属 / fs 文件丢失 → 404
- 无 Range header → 200,流式整文件:
  - Headers: `Content-Type: <mime>`, `Content-Length: <size>`, `Content-Disposition: attachment; filename="<sanitized>"`, `Accept-Ranges: bytes`
  - Body: `fs.read_stream(uid, fid, 0, size)` 8KB 块异步
- 有 `Range: bytes=N-M` header:
  - 解析 N / M(M 缺 → size-1)
  - N > M 或 M >= size → 416 `Range Not Satisfiable`
  - 206 + `Content-Range: bytes N-M/size` + `Content-Length: M-N+1`
  - Body: `fs.read_stream(uid, fid, N, M)`
- **不**支持多 Range(`bytes=0-99,200-299` 类),返 416

---

## §5 一致性 / 安全

### 5.1 流式 multipart 路径

```python
# praxis2/files/multipart_stream.py
from python_multipart import multipart   # parser

async def parse_upload(receive) -> AsyncIterator[bytes]:
    """yield chunks of file body. Side-output filename + content_type via attrs.

    parser 用 PUSH 模式,接到 ASGI receive 的 chunk → 推进 parser →
    parser 调 on_field / on_file / on_chunk callback。我们把 on_chunk
    转 async queue 推 yield。
    """
    # 略 (~100 行,RFC 7578 边界 + boundary 检测 + ASGI receive 适配)
```

**关键不变量**:
- **不读全 body 到内存** — 任何时刻 buffer ≤ 1MB
- **半文件清理** — `try/finally` ensure `.part` unlink on exception
- **single tx for DB** — INSERT files 用单 fetchrow,fs `.part → final` mv 在 DB commit 后
- **race condition** — 同用户并发上传:每 chunk 检 quota 用最新 SUM(`SELECT FOR UPDATE` files 表行不可行,锁不住聚合查询;改用 advisory lock per user_id:`SELECT pg_advisory_xact_lock(hashtext('upload:'||user_id))`)

### 5.2 安全

| 风险 | 措施 |
|---|---|
| Path traversal(`filename = "../etc/passwd"`)| 真存储路径用 `<root>/<user_id>/<file_id>` UUID,filename 仅 DB display 字段;sanitize 去 `../` / 绝对路径 |
| mime spoofing(声明 image/png 实际 .exe) | 服务端 `magic.from_file(.part)` 重检;client 上送 mime 仅作 fallback |
| 大 filename 攻击 | 200 字符截断 |
| 任意用户读他人文件 | `WHERE user_id=$2` 强检 + 404(不暴露存在) |
| 配额绕过(并发 upload) | advisory lock per user_id |
| 磁盘满 | quota 总额 ≤ 100GB × 用户数;`.53` 7TB 限 ≤ 70 用户(staging 充裕);M12 admin/stats 加 disk_usage 字段告警 |

### 5.3 错误码统一

| 状态 | body 模板 |
|---|---|
| 401 | `{error:"unauthorized", reason:"未登录"}` |
| 400 invalid_purpose | `{error:"invalid_purpose", allowed:["pdb","config","report","md_input","other"]}` |
| 400 bad_multipart | `{error:"bad_multipart", reason:"<detail>"}` |
| 404 | `{error:"not_found"}` |
| 413 file_too_large | `{error:"file_too_large", limit_bytes:21474836480}` |
| 413 quota_exceeded | `{error:"quota_exceeded", used_bytes:N, quota_bytes:107374182400}` |
| 416 | `{error:"range_not_satisfiable", size_bytes:N}` |
| 500 upload_failed | `{error:"upload_failed", reason:"<sanitized>"}` |

### 5.4 brain profile boot

```python
# praxis2/brains/profile.py
_PROFILES: dict[str, dict] | None = None   # module-level cache

def load_all_profiles() -> dict[str, dict]:
    global _PROFILES
    if _PROFILES is not None:
        return _PROFILES
    _PROFILES = {}
    for slug in DISCIPLINE_SLUGS:           # praxis2/brains/migrate.py
        _PROFILES[slug] = _walk_brain(slug)
    return _PROFILES
```

`_walk_brain(slug)`:
- `case_count = len(list(brain/slug/memory/cases/*.md))`
- `rule_count = sum lines in rules/*.md`(粗略)
- `skill_workflows = sorted(d.name for d in brain/slug/skills/workflows/*.exists())`
- `sample_cases`:scandir + sort by mtime DESC + take 5,parse `title:` frontmatter or filename stem
- `metadata.yaml`:`yaml.safe_load`,取 4 个文本字段;缺 → 全空

**`/api/agents/profile`** handler:
```python
async def handle_agents_profile(scope, receive, send, deps):
    profiles_dict = load_all_profiles()
    out = []
    for slug in DISCIPLINE_SLUGS:
        base = _agent_meta(slug)                  # 5 字段从 _AGENT_META
        prof = profiles_dict.get(slug, {})
        out.append({**base, **prof})
    await _json(send, 200, {"profiles": out})
```

---

## §6 测试覆盖(目标新增 ~36 测试,pytest ≥ 1606)

### 6.1 `tests/test_files_repo.py`(~10 integration)
- create_file_returns_uuid_and_persists
- list_files_filters_by_purpose
- list_files_excludes_soft_deleted
- soft_delete_marks_deleted_at_only
- soft_delete_other_user_returns_none
- usage_sums_only_active
- usage_zero_for_new_user
- get_file_404_when_deleted
- get_file_404_other_user
- create_file_with_invalid_purpose_raises

### 6.2 `tests/test_files_store_fs.py`(~8)
- write_stream_creates_part_then_final
- read_stream_full
- read_stream_range_partial
- read_stream_range_invalid_returns_416
- write_stream_aborts_on_exception_cleans_part
- delete_removes_file
- exists_returns_false_for_missing
- get_size_returns_bytes

### 6.3 `tests/test_files_routes.py`(~12)
- upload_pdb_happy_path
- upload_returns_size_mime_purpose
- upload_size_too_large_413
- upload_quota_exceeded_413
- upload_invalid_purpose_400
- upload_no_auth_401
- list_files_no_filter
- list_files_filter_pdb
- delete_404_not_owned
- usage_includes_count_field(不是 files_count!)
- download_full_200
- download_range_partial_206

### 6.4 `tests/test_files_security.py`(~4)
- sanitize_filename_keeps_chinese
- sanitize_filename_strips_path_traversal
- sanitize_filename_caps_200_chars
- mime_detect_overrides_client_content_type

### 6.5 `tests/test_brains_profile.py`(~6)
- load_all_profiles_13_slugs
- profile_case_count_matches_filesystem
- profile_metadata_yaml_loaded_when_present
- profile_metadata_yaml_returns_empty_when_missing
- profile_sample_cases_5_mtime_desc
- profile_skill_workflows_sorted

---

## §7 Ship / 回滚

### 7.1 Ship 流程

```bash
# 1. 全测过
cd /Volumes/T7/clade-learn/PRAXIS-2
pytest -q tests/ -k "not integration" --ignore=tests/test_skills | tail -5  # ≥ 1606
ruff check praxis2/ tests/
cd frontend && npm run typecheck

# 2. .53 装 libmagic1(若没装)
ssh zkyd@10.102.106.53 'dpkg -l | grep libmagic || sudo apt install -y libmagic1'

# 3. push backend
SERVICE_NAME=skip BACKEND_HOST=10.102.106.53 BACKEND_USER=zkyd \
  BACKEND_PATH=/home/zkyd/data1/mzy/PRAXIS-2 \
  bash deploy/push_backend.sh

# 4. .53 装 Python deps(若没装)
ssh zkyd@10.102.106.53 \
  '/home/zkyd/software/miniconda3/envs/praxis2/bin/pip install \
     python-multipart>=0.0.9 python-magic>=0.4.27 pyyaml>=6.0'

# 5. alembic upgrade
ssh zkyd@10.102.106.53 \
  'cd /home/zkyd/data1/mzy/PRAXIS-2 && source /home/zkyd/praxis2.env && \
   /home/zkyd/software/miniconda3/envs/praxis2/bin/alembic upgrade head'
# → 003_files

# 6. backend restart (tmux 10:praxis2-be)
ssh zkyd@10.102.106.53 'tmux send-keys -t 10:praxis2-be C-c' && sleep 2
ssh zkyd@10.102.106.53 'tmux send-keys -t 10:praxis2-be \
    "cd /home/zkyd/data1/mzy/PRAXIS-2 && source /home/zkyd/praxis2.env && \
     /home/zkyd/software/miniconda3/envs/praxis2/bin/gunicorn \
     -c deploy/gunicorn.conf.py praxis2.server.app:make_app_default" Enter'
sleep 5

# 7. smoke
curl -m 5 -s http://10.102.106.53:8001/api/info  # version v0.11.0
curl -m 5 -s -b /tmp/m9cj -X POST \
    "http://10.102.106.53:8001/api/files?purpose=other" \
    -F file=@/tmp/100kb.pdb \
    | python3 -m json.tool
curl -m 5 -s -b /tmp/m9cj http://10.102.106.53:8001/api/files/usage
curl -m 5 -s -b /tmp/m9cj http://10.102.106.53:8001/api/agents/profile \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(len(d['profiles']))"
# → 13

# 8. tag v0.11.0 + push
git tag v0.11.0 && git push origin v0.11.0
```

### 7.2 回滚

```bash
# A. 数据库
ssh zkyd@10.102.106.53 'cd /home/zkyd/data1/mzy/PRAXIS-2 && \
    source /home/zkyd/praxis2.env && \
    /home/zkyd/software/miniconda3/envs/praxis2/bin/alembic downgrade -1'
# → 撤 003,丢 files 表(任何已上传文件元数据);fs 实物在 data1 不动

# B. 代码:revert merge commit
git checkout main && git revert -m 1 <m10_merge_sha>

# C. backend restart 同 §7 step 6

# D. libmagic1 + python-multipart + python-magic + pyyaml:留着不卸,无副作用
```

**v1 链路全程不受影响**。

### 7.3 估时

| 子任务 | 估时 |
|---|---|
| 003 migration + FilesRepo + 测试 | 1 d |
| store_fs streaming + Range download + 测试 | 1 d |
| multipart_stream(python-multipart 包装,真 20GB streaming)+ advisory lock | 1.5 d |
| mime / sanitize / security + 测试 | 0.5 d |
| brain profile loader + metadata.yaml 解析 + 13 brain 测 | 1 d |
| 6 handler + ROUTES + app.py 注入 + frontend smoke | 1 d |
| staging ship(libmagic / pip / alembic / restart / smoke)+ tag | 0.5 d |
| **合计** | **6.5 d** |

---

## §8 不在 M10 做的事(避免范围蔓延)

- 不动 `praxis2/core / agents / brains / tools / scheduler / runtime / llm`
- 不接 `/api/admin/files/*`(M12 admin v2 真做时再加)
- 不删 M9 任何 endpoint
- 不动 v1(`.40:8088` + `.53:7788` 全冻结)
- 不写 brain `metadata.yaml` 13 学科内容(M10 只 loader,内容 brain 作者补)
- 不接 S3(`store_s3.py` 接口位预留为空 stub)
- 不接 virus scan
- 不做断点续传 / 多文件 multipart

---

## §9 关联文档

- 上游路线图:[`PRAXIS-2-计划-v2-完整重写-路线图.md`](../../../PRAXIS-2-计划-v2-完整重写-路线图.md) §6
- M9 spec 体例参考:[`2026-05-24-m9-user-center-design.md`](./2026-05-24-m9-user-center-design.md)
- M13 推迟约束:`project_m13_deferred.md`(memory)
- v0.10.0 现状:[`VERSION-STATUS-v0.10.0.md`](../../../VERSION-STATUS-v0.10.0.md) — M10 全程**不动** §2.2 列出的 9 个智能体内核目录
- 后续 milestone:M11 spawn + md + HPC、M12 admin v2 + proposals
