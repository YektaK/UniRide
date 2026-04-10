---
Task ID: 4-a
Agent: Benchmark Runner Service Agent
Task: Create benchmark runner mini-service

Work Log:
- Created `mini-services/benchmark-runner/package.json` with socket.io dependency
- Installed dependencies via `bun install` (socket.io@4.8.3)
- Created `mini-services/benchmark-runner/index.ts` — a comprehensive HTTP + WebSocket (socket.io) server on port 3003
- Implemented three HTTP endpoints:
  - `POST /run` — Accepts experiment config (algorithms, problems, settings), validates input, starts simulation, returns 202 with run ID
  - `GET /status` — Returns current run state: status, progress, percentage, current task, elapsed time, ETA
  - `POST /stop` — Aborts the current run via AbortController, returns stopped status
- Implemented WebSocket via socket.io (`path: '/socket.io'`) for real-time updates:
  - `benchmark` event with types: `progress`, `result`, `complete`, `stopped`, `error`, `status`
  - Sends current status on client connect
- Implemented benchmark simulation engine:
  - Seeded random number generator for reproducible results
  - Hash-based seed from (problem + algorithm + base seed) for deterministic per-experiment values
  - Realistic GAP simulation per algorithm: two_opt (2-5.5%), three_opt (0.3-3%), or_opt (1.5-4.5%), swap (4-12%), hybrid (0.2-2.5%), ga (1-4%), pso (1.5-5%), gwo (2-6%), hho (1.5-5%)
  - Time scaling by dimension: `baseTime * (dimension / 100)`
  - Category factor: medium (+15%), large (+35%) for worse GAP
  - Per-run progress emission for nRuns > 3
  - CSV data generation in complete message
- Full problem database (44 TSPLIB problems) with dimensions, optimal values, and categories
- CORS headers on all responses
- Validation: unknown problems, unknown algorithms, empty algorithm/problem lists, invalid JSON
- Only one run at a time (BUSY error on concurrent run attempts)
- Graceful shutdown via SIGTERM/SIGINT
- Fixed `sleep()` AbortSignal scoping bug
- Tested all endpoints successfully: status, run, stop, BUSY, validation errors, CORS preflight

Stage Summary:
- Mini-service at `mini-services/benchmark-runner/` with `package.json` and `index.ts`
- Port 3003, HTTP + WebSocket (socket.io with path `/socket.io`)
- Client connect URL: `io('/socket.io/?XTransformPort=3003')`
- 3 HTTP endpoints fully tested: POST /run, GET /status, POST /stop
- 5 WebSocket message types: progress, result, complete, stopped, error
- Realistic simulation with seeded random, dimension scaling, category factors
- Service running in background (PID 8990)
