# PRAXIS-VirtualCell frontend

The React interface provides cell context selection, conversational task submission, data and Pack catalogs, and saved reports. It connects only to the standalone PRAXIS-VirtualCell API. Predictions, abstention, execution identity, and provenance come from the API. Language assistance only parses and explains text.

## Development

Install from the lockfile and start Vite in this directory:

```bash
npm ci
npm run dev
```

Start the local API separately using the instructions in the [repository README](../README.md). Vite serves the interface at `http://127.0.0.1:5173` and proxies relative `/api/*` requests to `http://127.0.0.1:8000`. Set `VITE_DEV_API` to change the development proxy target. `VITE_API_BASE` instead sets the browser API base at build time; leave it empty for same-origin production hosting.

## Build and checks

```bash
npm run typecheck
npm run lint
npm run build
CI=1 npm run e2e
```

Build before starting the production API so it can mount `dist/`. The build checks entry, lazy-chunk, and font size budgets.

Playwright starts a local API with temporary data and run directories. It uses the root `.venv/bin/python` by default; set `PRAXIS_VC_TEST_PYTHON` to an alternate Python interpreter with the API dependencies installed. Set `PRAXIS_VC_E2E_PORT` to use a port other than `8000`. Install the Playwright Chromium browser before running the suite.

The result view has seven tabs: Report, Predictions, Module routing, Data and execution identity, Evidence, Execution trace, and Provenance. The browser displays backend decisions and does not compute scientific predictions or store API credentials. Product version and build identity come from `/api/health`.
