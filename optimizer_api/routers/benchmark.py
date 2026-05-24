import os
import json
import logging
import threading
import glob as glob_mod
from typing import List, Dict, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query

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
        
        n_runs = settings.get("n_runs", 3)
        total_experiments = len(algorithms) * len(problems) * n_runs
        
        benchmark_problems: List[ProblemInstance] = []
        for problem_name in problems:
            info = get_problem_by_name(problem_name)
            if not info or not info.file_path:
                continue
            coords = load_problem_coordinates(problem_name)
            if not coords:
                continue
            bp = ProblemInstance(
                name=info.name, dimension=info.dimension, coordinates=coords,
                optimal=info.optimal, category=info.category, problem_type="tsp", depot_index=0,
            )
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
            "problem_type": "tsp", "problem_category": cli_record.get("category", "unknown"),
            "optimal_score": cli_record.get("optimal"), "n_runs": cli_record.get("n_runs", 3),
            "numba_optimized": cli_record.get("numba_optimized", True),
            "algorithm_type": cli_record.get("algorithm_type", "local_search"),
            "source": "cli_import", "execution_failed": False,
            "routes_count": 1, "vehicles_used": 1,
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
