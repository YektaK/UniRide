import { createServer, IncomingMessage, ServerResponse } from 'http'
import { Server } from 'socket.io'

// ═══════════════════════════════════════════════════════════════════════════════
// PROBLEM DATABASE (TSPLIB reference data for realistic simulation)
// ═══════════════════════════════════════════════════════════════════════════════

interface ProblemData {
  name: string
  dimension: number
  optimal: number
  category: 'small' | 'medium' | 'large'
}

const PROBLEM_DB: Record<string, ProblemData> = {
  berlin52:  { name: 'berlin52',  dimension: 52,   optimal: 7542,   category: 'small' },
  eil51:    { name: 'eil51',    dimension: 51,   optimal: 426,    category: 'small' },
  eil76:    { name: 'eil76',    dimension: 76,   optimal: 538,    category: 'small' },
  st70:     { name: 'st70',     dimension: 70,   optimal: 675,    category: 'small' },
  kroA100:  { name: 'kroA100',  dimension: 100,  optimal: 21282,  category: 'small' },
  kroB100:  { name: 'kroB100',  dimension: 100,  optimal: 22141,  category: 'small' },
  kroC100:  { name: 'kroC100',  dimension: 100,  optimal: 20749,  category: 'small' },
  kroD100:  { name: 'kroD100',  dimension: 100,  optimal: 21294,  category: 'small' },
  kroE100:  { name: 'kroE100',  dimension: 100,  optimal: 22068,  category: 'small' },
  rd100:    { name: 'rd100',    dimension: 100,  optimal: 7910,   category: 'small' },
  eil101:   { name: 'eil101',   dimension: 101,  optimal: 629,    category: 'small' },
  lin105:   { name: 'lin105',   dimension: 105,  optimal: 14379,  category: 'small' },
  pr107:    { name: 'pr107',    dimension: 107,  optimal: 44303,  category: 'small' },
  pr124:    { name: 'pr124',    dimension: 124,  optimal: 59030,  category: 'small' },
  pr136:    { name: 'pr136',    dimension: 136,  optimal: 96772,  category: 'small' },
  pr144:    { name: 'pr144',    dimension: 144,  optimal: 58537,  category: 'small' },
  pr152:    { name: 'pr152',    dimension: 152,  optimal: 73682,  category: 'small' },
  kroA150:  { name: 'kroA150',  dimension: 150,  optimal: 26524,  category: 'medium' },
  kroB150:  { name: 'kroB150',  dimension: 150,  optimal: 26130,  category: 'medium' },
  kroA200:  { name: 'kroA200',  dimension: 200,  optimal: 29368,  category: 'medium' },
  kroB200:  { name: 'kroB200',  dimension: 200,  optimal: 29437,  category: 'medium' },
  pr226:    { name: 'pr226',    dimension: 226,  optimal: 80369,  category: 'medium' },
  pr264:    { name: 'pr264',    dimension: 264,  optimal: 49135,  category: 'medium' },
  pr299:    { name: 'pr299',    dimension: 299,  optimal: 48191,  category: 'medium' },
  ts225:    { name: 'ts225',    dimension: 225,  optimal: 126843, category: 'medium' },
  gil262:   { name: 'gil262',   dimension: 262,  optimal: 2412,   category: 'medium' },
  pr439:    { name: 'pr439',    dimension: 439,  optimal: 107217, category: 'medium' },
  a280:     { name: 'a280',     dimension: 280,  optimal: 2579,   category: 'medium' },
  lin318:   { name: 'lin318',   dimension: 318,  optimal: 42029,  category: 'medium' },
  rd400:    { name: 'rd400',    dimension: 400,  optimal: 15281,  category: 'medium' },
  d493:     { name: 'd493',     dimension: 493,  optimal: 35002,  category: 'large' },
  u724:     { name: 'u724',     dimension: 724,  optimal: 41910,  category: 'large' },
  rat783:   { name: 'rat783',   dimension: 783,  optimal: 8806,   category: 'large' },
  pr1002:   { name: 'pr1002',   dimension: 1002, optimal: 259045, category: 'large' },
  u1060:    { name: 'u1060',    dimension: 1060, optimal: 224094, category: 'large' },
  vm1084:   { name: 'vm1084',   dimension: 1084, optimal: 239297, category: 'large' },
  pcb1173:  { name: 'pcb1173',  dimension: 1173, optimal: 56892,  category: 'large' },
  nrw1379:  { name: 'nrw1379',  dimension: 1379, optimal: 56638,  category: 'large' },
  u1432:    { name: 'u1432',    dimension: 1432, optimal: 152970, category: 'large' },
  d1655:    { name: 'd1655',    dimension: 1655, optimal: 62128,  category: 'large' },
  vm1748:   { name: 'vm1748',    dimension: 1748, optimal: 336556, category: 'large' },
  u1817:    { name: 'u1817',    dimension: 1817, optimal: 57201,  category: 'large' },
  d2103:    { name: 'd2103',    dimension: 2103, optimal: 80450,  category: 'large' },
  u2152:    { name: 'u2152',    dimension: 2152, optimal: 64253,  category: 'large' },
  u2319:    { name: 'u2319',    dimension: 2319, optimal: 234256, category: 'large' },
  pr2392:   { name: 'pr2392',   dimension: 2392, optimal: 378032, category: 'large' },
}

// ═══════════════════════════════════════════════════════════════════════════════
// ALGORITHM CONFIGURATION (realistic GAP and time ranges)
// ═══════════════════════════════════════════════════════════════════════════════

interface AlgoConfig {
  shortName: string
  gapMin: number
  gapMax: number
  timeMin: number
  timeMax: number
}

const ALGO_CONFIG: Record<string, AlgoConfig> = {
  two_opt:   { shortName: '2-opt',   gapMin: 2.0,  gapMax: 5.5,  timeMin: 8,   timeMax: 45   },
  three_opt: { shortName: '3-opt',   gapMin: 0.3,  gapMax: 3.0,  timeMin: 40,  timeMax: 180  },
  or_opt:    { shortName: 'Or-opt',  gapMin: 1.5,  gapMax: 4.5,  timeMin: 6,   timeMax: 35   },
  swap:      { shortName: 'Swap',    gapMin: 4.0,  gapMax: 12.0, timeMin: 3,   timeMax: 18   },
  hybrid:    { shortName: 'Hybrid',  gapMin: 0.2,  gapMax: 2.5,  timeMin: 80,  timeMax: 400  },
  ga:        { shortName: 'GA',      gapMin: 1.0,  gapMax: 4.0,  timeMin: 200, timeMax: 1000 },
  pso:       { shortName: 'PSO',     gapMin: 1.5,  gapMax: 5.0,  timeMin: 150, timeMax: 800  },
  gwo:       { shortName: 'GWO',     gapMin: 2.0,  gapMax: 6.0,  timeMin: 120, timeMax: 600  },
  hho:       { shortName: 'HHO',     gapMin: 1.5,  gapMax: 5.0,  timeMin: 100, timeMax: 500  },
}

// ═══════════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════════

interface RunConfig {
  algorithms: { id: string; params: Record<string, number | string> }[]
  problems: string[]
  settings: {
    n_runs: number
    workers: number
    seed: number
    skip_cached: boolean
  }
}

interface ExperimentTask {
  problem: string
  algorithm: string
  run: number
}

interface RunResult {
  runId: string
  problem: string
  dimension: number
  optimal: number
  algorithm: string
  avg_gap: number
  best_gap: number
  avg_time_ms: number
  avg_length: number
  best_length: number
  n_runs: number
}

interface RunState {
  runId: string
  config: RunConfig
  status: 'idle' | 'running' | 'completed' | 'stopped' | 'error'
  startedAt: number | null
  completedAt: number | null
  totalExperiments: number
  completedExperiments: number
  results: RunResult[]
  currentTask: ExperimentTask | null
  abortController: AbortController | null
}

// ═══════════════════════════════════════════════════════════════════════════════
// SEEDED RANDOM
// ═══════════════════════════════════════════════════════════════════════════════

function createSeededRandom(seed: number) {
  let s = seed
  return () => {
    s = (s * 16807 + 0) % 2147483647
    return (s - 1) / 2147483646
  }
}

function hashSeed(problem: string, algorithm: string, baseSeed: number): number {
  let h = baseSeed
  for (let i = 0; i < problem.length; i++) {
    h = ((h << 5) - h + problem.charCodeAt(i)) | 0
  }
  for (let i = 0; i < algorithm.length; i++) {
    h = ((h << 7) - h + algorithm.charCodeAt(i)) | 0
  }
  return Math.abs(h) || 1
}

// ═══════════════════════════════════════════════════════════════════════════════
// RUN STATE
// ═══════════════════════════════════════════════════════════════════════════════

const state: RunState = {
  runId: '',
  config: { algorithms: [], problems: [], settings: { n_runs: 3, workers: 4, seed: 42, skip_cached: true } },
  status: 'idle',
  startedAt: null,
  completedAt: null,
  totalExperiments: 0,
  completedExperiments: 0,
  results: [],
  currentTask: null,
  abortController: null,
}

// ═══════════════════════════════════════════════════════════════════════════════
// HELPER: Parse JSON body from request
// ═══════════════════════════════════════════════════════════════════════════════

function readBody(req: IncomingMessage): Promise<string> {
  return new Promise((resolve, reject) => {
    let body = ''
    req.on('data', (chunk: Buffer) => { body += chunk.toString() })
    req.on('end', () => resolve(body))
    req.on('error', reject)
  })
}

function jsonRes(res: ServerResponse, status: number, data: unknown) {
  const body = JSON.stringify(data)
  res.writeHead(status, {
    'Content-Type': 'application/json',
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  })
  res.end(body)
}

// ═══════════════════════════════════════════════════════════════════════════════
// HTTP REQUEST HANDLER
// ═══════════════════════════════════════════════════════════════════════════════

function handleRequest(req: IncomingMessage, res: ServerResponse): boolean {
  // Parse URL (strip query string for path matching)
  const rawUrl = req.url || '/'
  const questionIdx = rawUrl.indexOf('?')
  const pathname = questionIdx >= 0 ? rawUrl.substring(0, questionIdx) : rawUrl

  // CORS preflight
  if (req.method === 'OPTIONS') {
    res.writeHead(204, {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
    })
    res.end()
    return true
  }

  // ─── POST /run ─────────────────────────────────────────────────────────
  if (req.method === 'POST' && pathname === '/run') {
    handleRun(req, res)
    return true
  }

  // ─── GET /status ───────────────────────────────────────────────────────
  if (req.method === 'GET' && pathname === '/status') {
    handleStatus(req, res)
    return true
  }

  // ─── POST /stop ────────────────────────────────────────────────────────
  if (req.method === 'POST' && pathname === '/stop') {
    handleStop(req, res)
    return true
  }

  // Not handled by our HTTP routes
  return false
}

async function handleRun(req: IncomingMessage, res: ServerResponse) {
  try {
    const body = await readBody(req)
    const config: RunConfig = JSON.parse(body)

    // Validate algorithms
    if (!config.algorithms || config.algorithms.length === 0) {
      jsonRes(res, 400, { error: 'No algorithms specified' })
      return
    }
    if (!config.problems || config.problems.length === 0) {
      jsonRes(res, 400, { error: 'No problems specified' })
      return
    }

    // Check if already running
    if (state.status === 'running') {
      jsonRes(res, 409, { error: 'Run already in progress', code: 'BUSY' })
      io.emit('benchmark', { type: 'error', data: { message: 'Run already in progress', code: 'BUSY' } })
      return
    }

    // Validate problems
    for (const p of config.problems) {
      if (!PROBLEM_DB[p]) {
        jsonRes(res, 400, { error: `Unknown problem: ${p}` })
        return
      }
    }

    // Validate algorithms
    for (const a of config.algorithms) {
      if (!ALGO_CONFIG[a.id]) {
        jsonRes(res, 400, { error: `Unknown algorithm: ${a.id}` })
        return
      }
    }

    // Generate run ID
    const runId = `run_${Date.now().toString(36)}_${Math.random().toString(36).slice(2, 8)}`
    const totalExperiments = config.algorithms.length * config.problems.length

    // Update state
    state.runId = runId
    state.config = config
    state.status = 'running'
    state.startedAt = Date.now()
    state.completedAt = null
    state.totalExperiments = totalExperiments
    state.completedExperiments = 0
    state.results = []
    state.currentTask = null
    state.abortController = new AbortController()

    console.log(`[RUN] Started ${runId}: ${config.algorithms.length} algos × ${config.problems.length} problems = ${totalExperiments} experiments (seed: ${config.settings.seed})`)

    jsonRes(res, 202, {
      runId,
      totalExperiments,
      status: 'running',
      message: `Benchmark run started with ${totalExperiments} experiments`,
    })

    // Start simulation
    startBenchmarkSimulation(state.abortController.signal)
  } catch (err) {
    console.error('[ERROR] /run parse error:', err)
    jsonRes(res, 400, { error: 'Invalid JSON body' })
  }
}

function handleStatus(_req: IncomingMessage, res: ServerResponse) {
  const elapsed = state.startedAt ? Date.now() - state.startedAt : 0
  const percentage = state.totalExperiments > 0
    ? +(state.completedExperiments / state.totalExperiments * 100).toFixed(1)
    : 0

  let etaMs = 0
  if (state.status === 'running' && state.completedExperiments > 0) {
    const avgPerExperiment = elapsed / state.completedExperiments
    etaMs = Math.round(avgPerExperiment * (state.totalExperiments - state.completedExperiments))
  }

  jsonRes(res, 200, {
    runId: state.runId || null,
    status: state.status,
    totalExperiments: state.totalExperiments,
    completedExperiments: state.completedExperiments,
    percentage,
    currentTask: state.currentTask,
    elapsed_ms: elapsed,
    eta_ms: etaMs,
    results: state.results.length,
  })
}

function handleStop(_req: IncomingMessage, res: ServerResponse) {
  if (state.status !== 'running') {
    jsonRes(res, 400, { error: 'No run in progress', code: 'NOT_RUNNING' })
    return
  }

  state.abortController?.abort()
  state.status = 'stopped'
  state.completedAt = Date.now()

  console.log(`[RUN] Stopped ${state.runId} after ${state.completedExperiments}/${state.totalExperiments} experiments`)

  io.emit('benchmark', {
    type: 'stopped',
    data: {
      runId: state.runId,
      completed: state.completedExperiments,
      total: state.totalExperiments,
      results: state.results,
    },
  })

  jsonRes(res, 200, {
    status: 'stopped',
    runId: state.runId,
    completedExperiments: state.completedExperiments,
    totalExperiments: state.totalExperiments,
    message: 'Run stopped',
  })
}

// ═══════════════════════════════════════════════════════════════════════════════
// HTTP SERVER + SOCKET.IO
// ═══════════════════════════════════════════════════════════════════════════════

const PORT = 3003

const httpServer = createServer()

// Attach our HTTP handler FIRST so it can respond before socket.io
httpServer.on('request', (req, res) => {
  const handled = handleRequest(req, res)
  if (handled) {
    // We handled it, socket.io will skip it since response is already sent
  }
  // If not handled, let it pass through to socket.io (which will 404 or handle as WS)
})

const io = new Server(httpServer, {
  // Use dedicated path so socket.io doesn't intercept HTTP API routes
  path: '/socket.io',
  cors: {
    origin: '*',
    methods: ['GET', 'POST'],
  },
  pingTimeout: 60000,
  pingInterval: 25000,
})

io.on('connection', (socket) => {
  console.log(`[WS] Client connected: ${socket.id}`)

  // Send current status on connect
  socket.emit('benchmark', {
    type: 'status',
    data: {
      runId: state.runId || null,
      status: state.status,
      totalExperiments: state.totalExperiments,
      completedExperiments: state.completedExperiments,
      currentTask: state.currentTask,
    },
  })

  socket.on('disconnect', () => {
    console.log(`[WS] Client disconnected: ${socket.id}`)
  })

  socket.on('error', (err) => {
    console.error(`[WS] Socket error (${socket.id}):`, err)
  })
})

// ═══════════════════════════════════════════════════════════════════════════════
// BENCHMARK SIMULATION
// ═══════════════════════════════════════════════════════════════════════════════

function simulateExperiment(
  problemName: string,
  algorithmId: string,
  nRuns: number,
  baseSeed: number,
): RunResult {
  const problem = PROBLEM_DB[problemName]
  if (!problem) throw new Error(`Unknown problem: ${problemName}`)

  const algo = ALGO_CONFIG[algorithmId]
  if (!algo) throw new Error(`Unknown algorithm: ${algorithmId}`)

  const rng = createSeededRandom(hashSeed(problemName, algorithmId, baseSeed))
  const dimFactor = problem.dimension / 100

  // Category factor: medium/large problems have slightly worse GAP
  const categoryFactor = problem.category === 'small' ? 1.0
    : problem.category === 'medium' ? 1.15 : 1.35

  // Simulate nRuns individual run gaps, then average
  const gaps: number[] = []
  const times: number[] = []
  for (let r = 0; r < nRuns; r++) {
    const runGap = (algo.gapMin + rng() * (algo.gapMax - algo.gapMin)) * categoryFactor * (0.85 + dimFactor * 0.25)
    const runTime = (algo.timeMin + rng() * (algo.timeMax - algo.timeMin)) * dimFactor
    gaps.push(runGap)
    times.push(runTime)
  }

  const avgGap = +(gaps.reduce((a, b) => a + b, 0) / nRuns).toFixed(2)
  const bestGap = +(Math.min(...gaps) * (0.6 + rng() * 0.35)).toFixed(2)
  const avgTimeMs = +(times.reduce((a, b) => a + b, 0) / nRuns).toFixed(1)
  const avgLength = Math.round(problem.optimal * (1 + avgGap / 100))
  const bestLength = Math.round(problem.optimal * (1 + bestGap / 100))

  return {
    runId: state.runId,
    problem: problem.name,
    dimension: problem.dimension,
    optimal: problem.optimal,
    algorithm: algo.shortName,
    avg_gap: avgGap,
    best_gap: bestGap,
    avg_time_ms: avgTimeMs,
    avg_length: avgLength,
    best_length: bestLength,
    n_runs: nRuns,
  }
}

function generateCSVData(results: RunResult[]): string {
  const header = 'problem,dimension,optimal,strategy,avg_gap,best_gap,avg_time_ms,avg_length,best_length,n_runs'
  const rows = results.map(r =>
    `${r.problem},${r.dimension},${r.optimal},${r.algorithm},${r.avg_gap},${r.best_gap},${r.avg_time_ms},${r.avg_length},${r.best_length},${r.n_runs}`
  )
  return [header, ...rows].join('\n')
}

async function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(new DOMException('Aborted', 'AbortError'))
      return
    }

    let onAbort: (() => void) | undefined

    const timer = setTimeout(() => {
      if (onAbort) signal?.removeEventListener('abort', onAbort)
      resolve()
    }, ms)

    if (signal) {
      onAbort = () => {
        clearTimeout(timer)
        reject(new DOMException('Aborted', 'AbortError'))
      }
      signal.addEventListener('abort', onAbort, { once: true })
    }
  })
}

async function startBenchmarkSimulation(signal: AbortSignal) {
  const { config } = state
  const nRuns = config.settings.n_runs || 3
  const seed = config.settings.seed || 42

  // Build experiment queue
  const queue: { problem: string; algorithm: string }[] = []
  for (const problem of config.problems) {
    for (const algo of config.algorithms) {
      queue.push({ problem, algorithm: algo.id })
    }
  }

  console.log(`[SIM] Starting simulation: ${queue.length} experiments (${nRuns} runs each)`)

  try {
    for (let i = 0; i < queue.length; i++) {
      if (signal.aborted) {
        console.log(`[SIM] Aborted at experiment ${i + 1}/${queue.length}`)
        return
      }

      const { problem, algorithm } = queue[i]
      const algoCfg = ALGO_CONFIG[algorithm]
      const problemData = PROBLEM_DB[problem]
      const dimFactor = (problemData?.dimension || 100) / 100

      // Update current task
      state.currentTask = { problem, algorithm: algoCfg?.shortName || algorithm, run: 0 }
      state.completedExperiments = i

      // Emit progress
      const elapsed = Date.now() - (state.startedAt || Date.now())
      const avgPerExperiment = i > 0 ? elapsed / i : 1000
      const etaMs = Math.round(avgPerExperiment * (queue.length - i))
      const percentage = +(i / queue.length * 100).toFixed(1)

      io.emit('benchmark', {
        type: 'progress',
        data: {
          runId: state.runId,
          completed: i,
          total: queue.length,
          percentage,
          current: { problem, algorithm: algoCfg?.shortName || algorithm, run: 0 },
          elapsed_ms: elapsed,
          eta_ms: etaMs,
        },
      })

      // Simulate computation time (scaled by problem size and algorithm)
      const baseSimTime = algoCfg ? (algoCfg.timeMin + algoCfg.timeMax) / 2 : 100
      const simDelay = Math.min(Math.round(baseSimTime * dimFactor * 0.8 + 200), 2000)

      // Sleep to simulate work; emit per-run progress for larger nRuns
      if (nRuns <= 3) {
        await sleep(simDelay, signal)
      } else {
        const chunkDelay = simDelay / nRuns
        for (let r = 0; r < nRuns; r++) {
          if (signal.aborted) break
          state.currentTask = { problem, algorithm: algoCfg?.shortName || algorithm, run: r + 1 }
          io.emit('benchmark', {
            type: 'progress',
            data: {
              runId: state.runId,
              completed: i,
              total: queue.length,
              percentage,
              current: { problem, algorithm: algoCfg?.shortName || algorithm, run: r + 1 },
              elapsed_ms: Date.now() - (state.startedAt || Date.now()),
              eta_ms: 0,
            },
          })
          await sleep(Math.round(chunkDelay), signal)
        }
      }

      // Generate result
      const result = simulateExperiment(problem, algorithm, nRuns, seed)
      state.results.push(result)
      state.completedExperiments = i + 1

      // Emit result
      io.emit('benchmark', {
        type: 'result',
        data: result,
      })

      console.log(`[SIM] (${i + 1}/${queue.length}) ${problem} × ${algoCfg?.shortName || algorithm}: avg_gap=${result.avg_gap}%, best_gap=${result.best_gap}%, time=${result.avg_time_ms}ms`)

      // Small inter-experiment delay
      if (i < queue.length - 1 && !signal.aborted) {
        await sleep(150, signal)
      }
    }

    // Completed normally
    if (!signal.aborted) {
      state.status = 'completed'
      state.completedAt = Date.now()
      state.currentTask = null

      const totalTime = state.completedAt - (state.startedAt || state.completedAt)
      const csvData = generateCSVData(state.results)

      io.emit('benchmark', {
        type: 'complete',
        data: {
          runId: state.runId,
          results: state.results,
          total_results: state.results.length,
          total_time_ms: totalTime,
          csv_data: csvData,
        },
      })

      console.log(`[SIM] Run ${state.runId} completed: ${state.results.length} results in ${totalTime}ms`)
    }
  } catch (err: unknown) {
    if (err instanceof DOMException && err.name === 'AbortError') {
      console.log(`[SIM] Run ${state.runId} was aborted`)
      return
    }
    console.error(`[SIM] Unexpected error:`, err)
    state.status = 'error'

    io.emit('benchmark', {
      type: 'error',
      data: {
        message: 'Simulation failed unexpectedly',
        code: 'SIMULATION_ERROR',
      },
    })
  }
}

// ═══════════════════════════════════════════════════════════════════════════════
// START SERVER
// ═══════════════════════════════════════════════════════════════════════════════

httpServer.listen(PORT, () => {
  console.log(`[SERVER] Benchmark Runner running on port ${PORT}`)
  console.log(`[SERVER] HTTP: POST /run, GET /status, POST /stop`)
  console.log(`[SERVER] WebSocket (socket.io): path=/socket.io`)
  console.log(`[SERVER] Client connect: io('/socket.io/?XTransformPort=${PORT}')`)
})

// Graceful shutdown
function shutdown() {
  console.log('[SERVER] Shutting down...')
  state.abortController?.abort()
  io.close()
  httpServer.close(() => {
    console.log('[SERVER] Shutdown complete')
    process.exit(0)
  })
}

process.on('SIGTERM', shutdown)
process.on('SIGINT', shutdown)
