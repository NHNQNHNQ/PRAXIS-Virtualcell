# PRAXIS-VirtualCell React 前端

这是 PRAXIS-VirtualCell 的薄交互与展示层。前端负责五阶段任务流程、历史 job、报告、预测视图、模块路由、证据、运行轨迹和溯源展示；它会向后端提交任务，但不执行预测、不产生治理 verdict，也不保存 API key。

## 环境与安装

CI 使用 Node 24 LTS。依赖必须从 lockfile 安装：

```bash
cd praxis_vc_react
npm ci
```

`package.json` 的版本只是后端产品版本的生成镜像。界面显示的产品版本和 build SHA 来自 `/api/health`，不能从前端常量推断发布状态。

## 开发模式

先在仓库根目录启动 API：

```bash
.venv/bin/praxis-vc serve --host 127.0.0.1 --port 8000
```

再在另一个终端启动 Vite：

```bash
cd praxis_vc_react
npm run dev
```

默认访问 `http://127.0.0.1:5173`。开发时浏览器仍请求相对 `/api/*`，Vite 将它代理到 `http://127.0.0.1:8000`；用 `VITE_DEV_API` 可以覆盖代理目标。`VITE_API_BASE` 在 Vite 构建时注入客户端 bundle，用于覆盖浏览器请求的 API base；默认空字符串以保持生产同源，二者用途不同。

## 同源构建

```bash
cd praxis_vc_react
npm ci
npm run build
cd ..
.venv/bin/praxis-vc serve
```

FastAPI 只有在启动时发现 `praxis_vc_react/dist` 才会把 React 挂载到 `/`，所以必须先 build、后启动服务。E2E 的 webServer 也遵循这个顺序，并把运行输出写到临时目录。

## 界面结构

主流程固定为：提问 → 核对 → 路由 → 运行 → 结果。结果页包含六个 tab：报告、预测、模块路由、证据、运行轨迹、溯源。

Stage 3 只展示运行前的路由预期；真正的模块路由结果来自运行后的 `/api/reports/{job_id}/module-plan`。所有数值、可靠性裁决和 provenance 都以 API 返回为准。

## 质量门

```bash
npm ci
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

当前 Playwright 套件覆盖五阶段 happy path、六个结果 tab、首屏结构和后端版本真值。它尚不代表 CSS/像素视觉验收、深层 abstain/failed 值、真实 LLM 或远端模型已经通过；这些范围必须分别报告。

Playwright 会在仓库根目录使用 `.venv/bin/python` 启动 Uvicorn，因此运行 E2E 前需要安装 `.[api]`，并保证 8000 端口没有属于其他进程的服务。不要通过杀死未知进程来“腾端口”。
