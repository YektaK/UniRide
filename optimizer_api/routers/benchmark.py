import os
import json
import logging
import threading
import glob as glob_mod
from typing import Any, List, Dict, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query
from fastapi.params import Query as QueryParam

from models.schemas import BenchmarkRunRequest, BenchmarkImportRequest
from benchmark_runner import BenchmarkRunner, ProblemInstance, AlgorithmConfig
from benchmark_state import benchmark_state_manager, BenchmarkStatus, MAX_CONCURRENT_BENCHMARKS
from strategies import STRATEGY_REGISTRY
from utils.tsplib_parser import (
    get_available_problems as get_tsplib_problems,
    get_problem_by_name,
    load_problem_coordinates,
    download_tsplib_problem,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/benchmark", tags=["Benchmark"])

CLI_RESULTS_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "benchmark_results")
CLI_RESULTS_NUMBA_DIR = os.path.join(os.path.dirname(__file__), "..", "tests", "benchmark_results_numba")


def _infer_param_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int) and not isinstance(value, bool):
        return "int"
    if isinstance(value, float):
        return "float"
    return "string"


def _space_from_config(config: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    return {
        key: {"type": _infer_param_type(value), "default": value, "source": "production"}
        for key, value in sorted(config.items())
        if isinstance(value, (bool, int, float, str))
    }


def _query_value(value: Any) -> Any:
    """Resolve FastAPI Query defaults when router functions are called directly."""
    return value.default if isinstance(value, QueryParam) else value


def _academic_param_spaces() -> Dict[str, Dict[str, Dict[str, Any]]]:
    try:
        from academic_benchmark.param_spaces import NUMBA_PARAM_SPACES, SOTA_PARAM_SPACES
    except Exception:
        logger.exception("Academic parameter spaces could not be loaded")
        return {}

    spaces: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for source, raw_spaces in (("numba", NUMBA_PARAM_SPACES), ("sota", SOTA_PARAM_SPACES)):
        for algo_name, raw_space in raw_spaces.items():
            spaces[algo_name] = {
                key: {**spec, "source": source}
                for key, spec in raw_space.items()
            }
    _add_param_space_aliases(spaces, {
        "e2bso": "E2BSO-TSP",
        "entropy_bso": "E2BSO-TSP",
        "e2b": "E2BSO-TSP",
        "r2dma": "R2DMA-TSP",
        "rdma": "R2DMA-TSP",
        "paoea": "P-AOEA-TSP",
        "aoea": "P-AOEA-TSP",
    })
    return spaces


def _add_param_space_aliases(
    spaces: Dict[str, Dict[str, Dict[str, Any]]],
    aliases: Dict[str, str],
) -> None:
    for alias, canonical in aliases.items():
        if alias not in spaces and canonical in spaces:
            spaces[alias] = {
                key: {**spec, "alias_of": canonical}
                for key, spec in spaces[canonical].items()
            }


def _strategy_param_spaces() -> Dict[str, Dict[str, Dict[str, Any]]]:
    spaces: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for key, strategy in STRATEGY_REGISTRY.items():
        config = getattr(strategy, "config", None)
        if isinstance(config, dict) and config:
            spaces[key] = _space_from_config(config)
    return spaces


@router.get("/param-spaces")
def list_benchmark_param_spaces() -> Dict:
    """Expose editable benchmark parameters without making web the source of truth."""
    production_spaces = _strategy_param_spaces()
    academic_spaces = _academic_param_spaces()
    return {
        "spaces": {**academic_spaces, **production_spaces},
        "production_spaces": production_spaces,
        "academic_spaces": academic_spaces,
    }


@router.get("/academic/leaderboard")
def get_academic_leaderboard(
    algorithm: Optional[str] = Query(None, description="Filter by algorithm"),
    category: Optional[str] = Query(None, description="Filter by problem category"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return"),
) -> Dict:
    """Read-only leaderboard backed by the academic benchmark database."""
    try:
        from academic_benchmark.results_reader import get_leaderboard

        return get_leaderboard(
            algorithm=_query_value(algorithm),
            category=_query_value(category),
            limit=_query_value(limit),
        )
    except Exception as exc:
        logger.exception("Academic leaderboard query failed")
        raise HTTPException(status_code=503, detail=f"Academic DB unavailable: {exc}")


@router.get("/academic/best")
def get_academic_best_result(
    problem: str = Query(..., description="Problem name"),
    algorithm: str = Query(..., description="Algorithm name"),
) -> Dict:
    """Read-only best result lookup backed by the academic benchmark database."""
    try:
        from academic_benchmark.results_reader import get_best_result

        result = get_best_result(problem=problem, algorithm=algorithm)
        if result.get("result") is None:
            raise HTTPException(status_code=404, detail="No academic result found")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Academic best-result query failed")
        raise HTTPException(status_code=503, detail=f"Academic DB unavailable: {exc}")


@router.get("/academic/benchmark-results")
def get_academic_benchmark_results(
    limit: int = Query(100, ge=1, le=1000, description="Maximum rows to return"),
    feasible_only: bool = Query(False, description="Return only successful, constraint-feasible rows"),
) -> Dict:
    """Read-only benchmark CSV rows, including CVRP/CVRPTW routing fields."""
    try:
        from academic_benchmark.results_reader import get_benchmark_rows

        return get_benchmark_rows(
            limit=_query_value(limit),
            feasible_only=bool(_query_value(feasible_only)),
        )
    except Exception as exc:
        logger.exception("Academic benchmark-results query failed")
        raise HTTPException(status_code=503, detail=f"Academic benchmark results unavailable: {exc}")


@router.get("/academic/problems")
def get_academic_problems(
    problem_type: Optional[str] = Query(None, description="Filter by problem type"),
    category: Optional[str] = Query(None, description="Filter by problem category"),
    max_dim: int = Query(0, ge=0, description="Maximum dimension; 0 means no limit"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum rows to return"),
) -> Dict:
    """Read-only academic problem inventory backed by SQLite."""
    try:
        from academic_benchmark.results_reader import get_academic_problems as _get_problems

        return _get_problems(
            problem_type=_query_value(problem_type),
            category=_query_value(category),
            max_dim=_query_value(max_dim),
            limit=_query_value(limit),
        )
    except Exception as exc:
        logger.exception("Academic problems query failed")
        raise HTTPException(status_code=503, detail=f"Academic problems unavailable: {exc}")


@router.get("/problems")
def list_benchmark_problems(category: Optional[str] = Query(None, description="Filter by category")) -> List[Dict]:
    problems = get_tsplib_problems()
    if category:
        problems = [p for p in problems if p.category == category]
    return [
        {
            "name": p.name, "dimension": p.dimension, "optimal": p.optimal,
            "category": p.category, "problem_type": p.problem_type,
            "edge_weight_type": p.edge_weight_type, "available": p.file_path is not None,
        }
        for p in problems
    ]

@router.get("/problems/{problem_name}")
def get_benchmark_problem_detail(problem_name: str) -> Dict:
    info = get_problem_by_name(problem_name)
    if not info:
        raise HTTPException(status_code=404, detail=f"Problem '{problem_name}' not found")
    result = {
        "name": info.name, "dimension": info.dimension, "optimal": info.optimal,
        "category": info.category, "problem_type": info.problem_type,
        "edge_weight_type": info.edge_weight_type, "available": info.file_path is not None,
        "coordinates": None,
    }
    if info.file_path:
        coords = load_problem_coordinates(problem_name)
        if coords:
            result["coordinates"] = coords
    return result

@router.get("/results/{run_id}")
def get_benchmark_results(run_id: str) -> Dict:
    state = benchmark_state_manager.get_run(run_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    if state.status != BenchmarkStatus.COMPLETED:
        return {
            "run_id": run_id, "status": state.status.value, "results": [],
            "message": f"Benchmark is still {state.status.value}.",
            "parameters": state.parameters,
        }
    return {
        "run_id": run_id, "status": state.status.value, "results_count": state.results_count,
        "total_experiments": state.total_experiments, "message": state.message,
        "parameters": state.parameters, "results": state.results,
    }

@router.post("/run")
def start_benchmark(body: BenchmarkRunRequest) -> Dict:
    return _start_benchmark_impl(body.run_id, body.algorithms, body.problems, body.settings)

def _start_benchmark_impl(run_id: str, algorithms: List[Dict], problems: List[str], settings: Dict) -> Dict:
    try:
        if not benchmark_state_manager.can_start_run():
            raise HTTPException(
                status_code=429,
                detail={"error": "Maximum concurrent benchmarks reached", "max_concurrent": MAX_CONCURRENT_BENCHMARKS}
            )

        if settings.get("execution_mode") in {"matrix_native", "academic_matrix"}:
            return _start_matrix_native_benchmark_impl(run_id, algorithms, problems, settings)
        
        n_runs = settings.get("n_runs", 3)
        total_experiments = len(algorithms) * len(problems) * n_runs
        
        benchmark_problems: List[ProblemInstance] = []
        for problem_name in problems:
            bp = _load_benchmark_problem(problem_name)
            if bp is None:
                continue
            benchmark_problems.append(bp)
        
        if not benchmark_problems:
            raise HTTPException(status_code=400, detail={"error": "No valid benchmark problems found"})

        state = benchmark_state_manager.create_run(
            run_id=run_id, total_experiments=total_experiments,
            parameters={"algorithms": algorithms, "problems": problems, "settings": settings}
        )
        
        def run_benchmark_task():
            try:
                algo_configs: List[AlgorithmConfig] = []
                for algo_dict in algorithms:
                    algo_configs.append(AlgorithmConfig(
                        name=algo_dict.get("id", algo_dict.get("name", "unknown")),
                        algorithm_id=algo_dict.get("id", algo_dict.get("name", "unknown")),
                        params=algo_dict.get("params", {}),
                    ))
                runner = BenchmarkRunner(strategies_registry=STRATEGY_REGISTRY, state_manager=benchmark_state_manager, run_id=run_id)
                runner.run(problems=benchmark_problems, algorithms=algo_configs, n_runs=n_runs, seed=settings.get("seed", 42), skip_cached=settings.get("skip_cached", False))
            except Exception as e:
                benchmark_state_manager.fail_run(run_id, f"Error: {str(e)}")
        
        executor_thread = threading.Thread(target=run_benchmark_task, daemon=True, name=f"benchmark-executor-{run_id}")
        executor_thread.start()
        
        return {
            "run_id": run_id, "status": "running", "total_experiments": total_experiments,
            "problems_count": len(problems), "algorithms_count": len(algorithms),
            "message": f"Benchmark run {run_id} started in background",
            "start_time": state.start_time
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Benchmark run failed for run_id=%s", run_id)
        raise HTTPException(status_code=500, detail="Internal benchmark error")


def _start_matrix_native_benchmark_impl(run_id: str, algorithms: List[Dict], problems: List[str], settings: Dict) -> Dict:
    from dataclasses import asdict

    from academic_benchmark.tsplib_manager import load_routing_problem, save_benchmark_result, save_benchmark_run
    from uniride_core.algorithms.engine_factory import canonical_matrix_engine_name, create_matrix_engine
    from uniride_core.benchmark_runner import MatrixAlgorithmConfig, MatrixBenchmarkRunner

    n_runs = int(settings.get("n_runs", 1))
    routing_problems = []
    for problem_name in problems:
        loaded = load_routing_problem(problem_name)
        if loaded is not None:
            routing_problems.append(loaded)

    if not routing_problems:
        raise HTTPException(status_code=400, detail={"error": "No matrix-native academic problems found"})

    matrix_algorithms: List[MatrixAlgorithmConfig] = []
    for algo_dict in algorithms:
        algo_id = algo_dict.get("id", algo_dict.get("name", "Core-Greedy-Routing"))
        params = algo_dict.get("params", {})
        try:
            canonical_algo_id = canonical_matrix_engine_name(algo_id)
            engine = create_matrix_engine(algo_id)
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail={"error": f"Matrix-native algorithm not available yet: {algo_id}"},
            )
        matrix_algorithms.append(MatrixAlgorithmConfig(
            name=canonical_algo_id,
            engine=engine,
            params=params,
        ))

    total_experiments = len(routing_problems) * len(matrix_algorithms) * n_runs
    state = benchmark_state_manager.create_run(
        run_id=run_id,
        total_experiments=total_experiments,
        parameters={
            "algorithms": algorithms,
            "problems": problems,
            "settings": {**settings, "execution_mode": "matrix_native"},
        },
    )
    save_benchmark_run(
        run_id,
        source="web_matrix_native",
        status="running",
        settings=state.parameters,
    )

    def run_matrix_task():
        try:
            runner = MatrixBenchmarkRunner(matrix_algorithms)
            completed = 0
            collected = []
            for problem in routing_problems:
                for algorithm in matrix_algorithms:
                    for run_number in range(1, n_runs + 1):
                        result = runner.run_one(
                            problem,
                            algorithm,
                            run_number=run_number,
                            seed=int(settings.get("seed", 42)) + run_number - 1,
                        )
                        result_dict = asdict(result)
                        collected.append(result_dict)
                        save_benchmark_result(run_id, result_dict)
                        completed += 1
                        benchmark_state_manager.add_result(run_id, result_dict)
                        benchmark_state_manager.update_progress(
                            run_id,
                            completed,
                            f"Completed matrix-native: {algorithm.name} on {problem.name} ({completed}/{total_experiments})",
                        )
            save_benchmark_run(
                run_id,
                source="web_matrix_native",
                status="completed",
                settings=state.parameters,
                metadata={"results": len(collected)},
            )
            benchmark_state_manager.complete_run(
                run_id,
                len(collected),
                f"Matrix-native benchmark completed: {len(collected)} results",
            )
        except Exception as exc:
            save_benchmark_run(
                run_id,
                source="web_matrix_native",
                status="failed",
                settings=state.parameters,
                metadata={"error": str(exc)},
            )
            benchmark_state_manager.fail_run(run_id, f"Error: {str(exc)}")

    executor_thread = threading.Thread(target=run_matrix_task, daemon=True, name=f"matrix-benchmark-executor-{run_id}")
    executor_thread.start()
    return {
        "run_id": run_id,
        "status": "running",
        "execution_mode": "matrix_native",
        "total_experiments": total_experiments,
        "problems_count": len(routing_problems),
        "algorithms_count": len(matrix_algorithms),
        "message": f"Matrix-native benchmark run {run_id} started in background",
        "start_time": state.start_time,
    }


def _load_benchmark_problem(problem_name: str) -> Optional[ProblemInstance]:
    """Load an academic benchmark problem without flattening its metadata to TSP."""
    info = get_problem_by_name(problem_name)
    if not info or not info.file_path:
        return None

    problem_type = str(getattr(info, "problem_type", "tsp") or "tsp").lower()
    coords = load_problem_coordinates(problem_name) or list(getattr(info, "coordinates", []) or [])
    dist_matrix = getattr(info, "dist_matrix", None)
    time_matrix = getattr(info, "time_matrix", None)

    # The current web quick-runner still dispatches through production
    # OptimizationRequest objects, which need coordinates for response mapping.
    # Matrix-native academic runs are owned by uniride_core/academic_benchmark.
    if not coords:
        return None

    return ProblemInstance(
        name=info.name,
        dimension=info.dimension,
        coordinates=coords,
        optimal=info.optimal,
        category=info.category,
        source=getattr(info, "source", "tsplib"),
        problem_type=problem_type,
        is_time_matrix=bool(getattr(info, "is_time_matrix", False) or time_matrix is not None),
        time_matrix=time_matrix,
        dist_matrix=dist_matrix,
        edge_weight_type=getattr(info, "edge_weight_type", "EUC_2D"),
        capacity=getattr(info, "capacity", None),
        capacities=getattr(info, "capacities", None),
        demands=getattr(info, "demands", None),
        service_times=getattr(info, "service_times", None),
        num_vehicles=getattr(info, "num_vehicles", None),
        max_route_duration=getattr(info, "max_route_duration", None),
        matrix_kind=getattr(info, "matrix_kind", "distance"),
        direction=getattr(info, "direction", "pickup"),
        time_windows=getattr(info, "time_windows", None),
        depot_index=getattr(info, "depot_index", 0),
        file_path=info.file_path,
    )

@router.post("/import")
def import_benchmark(body: BenchmarkImportRequest) -> Dict:
    try:
        data = body.model_dump()
        state = benchmark_state_manager.import_run(body.run_id, data)
        return {
            "run_id": state.run_id, "status": state.status.value,
            "results_imported": state.results_count, "message": f"Data imported ({state.results_count})"
        }
    except Exception as e:
        logger.exception("Benchmark import failed")
        raise HTTPException(status_code=500, detail="Import failed")

@router.get("/status")
def get_benchmark_status(run_id: str) -> Dict:
    state = benchmark_state_manager.get_run(run_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    
    progress_percent = 0.0
    if state.total_experiments > 0:
        progress_percent = (state.completed_experiments / state.total_experiments) * 100
    
    return {
        "run_id": run_id, "status": state.status.value, "total_experiments": state.total_experiments,
        "completed_experiments": state.completed_experiments, "results_count": state.results_count,
        "message": state.message, "progress_percent": min(100.0, progress_percent),
        "start_time": state.start_time, "end_time": state.end_time
    }

@router.post("/stop")
def stop_benchmark(run_id: str) -> Dict:
    state = benchmark_state_manager.get_run(run_id)
    if not state:
        raise HTTPException(status_code=404, detail=f"Benchmark run {run_id} not found")
    benchmark_state_manager.stop_run(run_id, "User requested stop")
    return {
        "run_id": run_id, "status": "stopped", "results_collected": state.results_count,
        "message": f"Benchmark {run_id} stopped"
    }

@router.post("/download/{problem_name}")
def download_benchmark_problem(problem_name: str) -> Dict:
    name_lower = problem_name.lower().strip()
    info = get_problem_by_name(name_lower)
    if info and info.file_path:
        return {
            "problem_name": name_lower, "status": "already_existed",
            "file_path": info.file_path, "message": f"Problem already available at {info.file_path}"
        }
    result_path = download_tsplib_problem(name_lower)
    if result_path:
        return {
            "problem_name": name_lower, "status": "downloaded",
            "file_path": result_path, "message": f"Successfully downloaded to {result_path}"
        }
    return {
        "problem_name": name_lower, "status": "failed", "file_path": None,
        "message": "Could not download from TSPLIB archive"
    }

def _convert_cli_record_to_web(cli_record: Dict, run_number: int = 1) -> Dict:
    is_best_run = (run_number == 1)
    problem_type = cli_record.get("problem_type", "tsp")
    matrix_kind = cli_record.get("matrix_kind", "distance")
    num_vehicles = cli_record.get("num_vehicles")
    routes = cli_record.get("routes")
    if routes is None and cli_record.get("routes_json"):
        try:
            routes = json.loads(cli_record.get("routes_json") or "null")
        except (TypeError, json.JSONDecodeError):
            routes = None
    routes_count = len(routes) if isinstance(routes, list) else (num_vehicles or 1)
    return {
        "algorithm": cli_record.get("strategy", "unknown"),
        "problem": cli_record.get("problem", "unknown"),
        "run_number": run_number,
        "tour_length": float(cli_record.get("best_length", cli_record.get("avg_length", 0))) if is_best_run else float(cli_record.get("avg_length", 0)),
        "elapsed_ms": float(cli_record.get("avg_time_ms", 0)),
        "gap_percent": float(cli_record.get("best_gap", cli_record.get("avg_gap", 0))) if is_best_run else float(cli_record.get("avg_gap", 0)),
        "timestamp": cli_record.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "metadata": {
            "problem_dimension": cli_record.get("dimension", 0),
            "problem_type": problem_type,
            "matrix_kind": matrix_kind,
            "problem_category": cli_record.get("category", "unknown"),
            "optimal_score": cli_record.get("optimal"), "n_runs": cli_record.get("n_runs", 3),
            "numba_optimized": cli_record.get("numba_optimized", True),
            "algorithm_type": cli_record.get("algorithm_type", "local_search"),
            "source": "cli_import", "execution_failed": False,
            "routes_count": routes_count,
            "vehicles_used": num_vehicles or routes_count,
            "routes": routes,
            "route_loads": cli_record.get("route_loads"),
            "route_costs": cli_record.get("route_costs"),
            "objective_cost": cli_record.get("objective_cost"),
            "capacity_violations": cli_record.get("capacity_violations", 0),
            "tw_violations": cli_record.get("tw_violations", 0),
            "cli_avg_length": cli_record.get("avg_length"), "cli_best_length": cli_record.get("best_length"),
            "cli_avg_gap": cli_record.get("avg_gap"), "cli_best_gap": cli_record.get("best_gap"),
            "cli_avg_time_ms": cli_record.get("avg_time_ms"),
        },
    }

def _find_cli_json_files() -> List[Dict]:
    files = []
    for search_dir in [CLI_RESULTS_DIR, CLI_RESULTS_NUMBA_DIR]:
        if not os.path.isdir(search_dir): continue
        for filepath in sorted(glob_mod.glob(os.path.join(search_dir, "*.json"))):
            try:
                stat = os.stat(filepath)
                files.append({
                    "filename": os.path.basename(filepath), "filepath": filepath, "size_bytes": stat.st_size,
                    "modified_time": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
                    "source_dir": os.path.basename(search_dir),
                })
            except OSError: continue
    return files

def _load_and_validate_cli_json(filepath: str) -> List[Dict]:
    if not os.path.isfile(filepath): raise HTTPException(status_code=404, detail=f"File not found: {filepath}")
    try:
        with open(filepath, "r", encoding="utf-8") as f: data = json.load(f)
    except json.JSONDecodeError as e: raise HTTPException(status_code=400, detail=f"JSON error: {e}")
    if not isinstance(data, list) or not data: raise HTTPException(status_code=400, detail="Invalid JSON array")
    missing = [f for f in ["problem", "strategy", "dimension"] if f not in data[0]]
    if missing: raise HTTPException(status_code=400, detail=f"Missing fields: {missing}")
    return data

@router.get("/cli/files")
def list_cli_benchmark_files() -> Dict:
    files = _find_cli_json_files()
    return {
        "total_files": len(files),
        "scan_directories": [d for d in [CLI_RESULTS_DIR, CLI_RESULTS_NUMBA_DIR] if os.path.isdir(d)],
        "files": files,
    }

@router.post("/cli/import")
def import_cli_benchmark_results(filepath: str = "", filename: str = "", run_id: Optional[str] = None, label: Optional[str] = None) -> Dict:
    if not filepath and not filename: raise HTTPException(status_code=400, detail="Required filepath or filename")
    if filename and not filepath:
        for search_dir in [CLI_RESULTS_DIR, CLI_RESULTS_NUMBA_DIR]:
            if os.path.isfile(os.path.join(search_dir, filename)): filepath = os.path.join(search_dir, filename); break
        if not filepath: raise HTTPException(status_code=404, detail="File not found")
    filepath = os.path.abspath(filepath)
    cli_records = _load_and_validate_cli_json(filepath)
    if not run_id: run_id = f"cli-import-{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    if benchmark_state_manager.get_run(run_id): raise HTTPException(status_code=409, detail="run_id already exists")
    
    web_results = []
    for record in cli_records:
        for run_num in range(1, record.get("n_runs", 3) + 1):
            web_results.append(_convert_cli_record_to_web(record, run_number=run_num))
            
    unique_problems = list(set(r["problem"] for r in cli_records))
    unique_strategies = list(set(r["strategy"] for r in cli_records))
    
    state = benchmark_state_manager.create_run(
        run_id=run_id, total_experiments=len(web_results),
        parameters={"source": "cli_import", "source_file": os.path.basename(filepath), "problems": unique_problems}
    )
    for result in web_results: benchmark_state_manager.add_result(run_id, result)
    benchmark_state_manager.complete_run(run_id=run_id, results_count=len(web_results), message="CLI Imported")
    
    return {
        "run_id": run_id, "status": "completed", "results_count": len(web_results),
        "source_file": os.path.basename(filepath), "summary": {"unique_problems": len(unique_problems)}
    }

@router.get("/cli/preview")
def preview_cli_import(filepath: str = "", filename: str = "") -> Dict:
    if not filepath and filename:
        for search_dir in [CLI_RESULTS_DIR, CLI_RESULTS_NUMBA_DIR]:
            if os.path.isfile(os.path.join(search_dir, filename)): filepath = os.path.join(search_dir, filename); break
    if not filepath: raise HTTPException(status_code=400, detail="Required")
    filepath = os.path.abspath(filepath)
    cli_records = _load_and_validate_cli_json(filepath)
    preview = [{"original": r, "converted_web": _convert_cli_record_to_web(r, 1)} for r in cli_records[:3]]
    return {"file": {"name": os.path.basename(filepath)}, "total_records": len(cli_records), "preview": preview}
