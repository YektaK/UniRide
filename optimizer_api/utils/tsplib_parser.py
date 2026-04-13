"""
TSPLIB Problem Parser and Registry

Parses .tsp files from the TSPLIB library and provides problem metadata
for benchmark selection. Supports EUC_2D edge weight type.

Known optimal solutions sourced from:
http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/STSP.html
"""

import os
import re
import math
import logging
import tarfile
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

logger = logging.getLogger(__name__)

# Directory where TSPLIB .tsp files are stored
TSPLIB_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'tests', 'tsplib_data')

# Official TSPLIB download base URL
TSPLIB_DOWNLOAD_URL = "http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/"

# Request timeout for downloads (seconds)
_DOWNLOAD_TIMEOUT = 30

# User-Agent for requests (some servers block default Python UA)
_DOWNLOAD_USER_AGENT = "UniRide-Optimizer/1.0 (+https://uniride.dev)"


@dataclass
class TSPLIBProblemInfo:
    """Metadata for a TSPLIB benchmark problem"""
    name: str
    dimension: int
    optimal: Optional[int]  # Known optimal tour length (None if unknown)
    category: str  # "small" (≤100), "medium" (101-500), "large" (501+)
    problem_type: str  # "TSP", "ATSP", etc.
    edge_weight_type: str  # "EUC_2D", "CEIL_2D", etc.
    file_path: Optional[str] = None  # Path to .tsp file if downloaded


# Known TSPLIB optimal solutions (source: TSPLIB95)
TSPLIB_OPTIMALS: Dict[str, int] = {
    # Small (n ≤ 100)
    "berlin52": 7542, "eil51": 426, "eil76": 538, "st70": 675,
    "kroA100": 21282, "kroB100": 22141, "kroC100": 20749, "kroD100": 21294,
    "kroE100": 22068, "rd100": 7910, "eil101": 629, "lin105": 14379,
    "pr107": 44303, "pr124": 59030, "pr136": 96772, "pr144": 58537,
    "pr152": 73682,
    # Medium (101-500)
    "kroA150": 26524, "kroB150": 26130, "kroA200": 29368, "kroB200": 29437,
    "pr226": 80369, "pr264": 49135, "pr299": 48191, "ts225": 126843,
    "gil262": 2412, "pr439": 107217, "a280": 2579, "lin318": 42029,
    "rd400": 15281,
    # Large (501+)
    "d493": 35002, "u724": 41910, "rat783": 8806, "pr1002": 259045,
    "u1060": 224094, "vm1084": 239297, "pcb1173": 56892, "nrw1379": 56638,
    "u1432": 152970, "d1655": 62128, "vm1748": 336556, "u1817": 57201,
    "d2103": 80450, "u2152": 64253, "u2319": 234256, "pr2392": 378032,
}


def parse_tsplib_file(filepath: str) -> Optional[Dict]:
    """
    Parse a TSPLIB .tsp file and extract problem data.
    
    Returns dict with: name, dimension, coordinates, type, edge_weight_type
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        name_match = re.search(r'NAME\s*:\s*(\S+)', content, re.IGNORECASE)
        dim_match = re.search(r'DIMENSION\s*:\s*(\d+)', content, re.IGNORECASE)
        type_match = re.search(r'TYPE\s*:\s*(\S+)', content, re.IGNORECASE)
        ewt_match = re.search(r'EDGE_WEIGHT_TYPE\s*:\s*(\S+)', content, re.IGNORECASE)
        
        if not dim_match:
            return None
        
        name = name_match.group(1).lower() if name_match else os.path.basename(filepath).replace('.tsp', '')
        dimension = int(dim_match.group(1))
        problem_type = type_match.group(1) if type_match else "TSP"
        edge_weight_type = ewt_match.group(1) if ewt_match else "EUC_2D"
        
        # Extract coordinates from NODE_COORD_SECTION
        coordinates: List[Tuple[float, float]] = []
        coord_section = re.search(
            r'NODE_COORD_SECTION\s*\n(.*?)\n?(?:EOF|DISPLAY_DATA_SECTION)',
            content, re.DOTALL | re.IGNORECASE
        )
        
        if coord_section:
            for line in coord_section.group(1).strip().split('\n'):
                line = line.strip()
                if not line or line.upper().startswith('EOF'):
                    continue
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        coordinates.append((float(parts[1]), float(parts[2])))
                    except ValueError:
                        continue
        
        if not coordinates:
            return None
        
        return {
            'name': name,
            'dimension': dimension,
            'coordinates': coordinates,
            'type': problem_type,
            'edge_weight_type': edge_weight_type,
        }
    except Exception as e:
        logger.error(f"Failed to parse TSPLIB file {filepath}: {e}")
        return None


def euclidean_distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate raw Euclidean distance (used by EUC_2D problems, no rounding)."""
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def tsplib_euc_2d_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """TSPLIB EUC_2D distance: nearest integer rounding per edge (NINT).

    TSPLIB standard: d(i,j) = NINT( sqrt( (xi-xj)² + (yi-yj)² ) )
    Returns an integer as specified in the TSPLIB format.
    """
    raw = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    return int(raw + 0.5)


def tsplib_tour_distance(coords: List[Tuple[float, float]], tour: List[int]) -> float:
    """
    Calculate total tour distance using EUC_2D NINT rounding (TSPLIB standard).
    Each edge distance is rounded to nearest integer before summing.
    tour: 0-based list of node indices.
    """
    if not tour or len(tour) < 2:
        return 0.0

    total = 0
    for i in range(len(tour)):
        p1 = coords[tour[i]]
        p2 = coords[tour[(i + 1) % len(tour)]]
        total += tsplib_euc_2d_distance(p1, p2)

    return float(total)


def _build_problem_info(data: Dict) -> Optional[TSPLIBProblemInfo]:
    """Helper: build a TSPLIBProblemInfo from parsed file data. Returns None on failure."""
    if not data:
        return None

    name = data['name']
    dim = data['dimension']

    if dim <= 100:
        category = "small"
    elif dim <= 500:
        category = "medium"
    else:
        category = "large"

    return TSPLIBProblemInfo(
        name=name,
        dimension=dim,
        optimal=TSPLIB_OPTIMALS.get(name),
        category=category,
        problem_type=data['type'],
        edge_weight_type=data['edge_weight_type'],
        file_path=None,  # caller must set if known
    )


def get_available_problems() -> List[TSPLIBProblemInfo]:
    """
    List all available TSPLIB problems from the data directory.

    For known problems in TSPLIB_OPTIMALS that are not present locally,
    an automatic download from the official TSPLIB archive is attempted.
    Returns problem metadata for benchmark selection.
    """
    problems: List[TSPLIBProblemInfo] = []

    # Ensure the data directory exists (create if missing so downloads work)
    os.makedirs(TSPLIB_DATA_DIR, exist_ok=True)

    if not os.path.isdir(TSPLIB_DATA_DIR):
        logger.warning(f"TSPLIB data directory not found: {TSPLIB_DATA_DIR}")
        return problems

    # ── Step 1: scan local .tsp files (existing behaviour) ──────────
    local_names: set = set()

    for filename in sorted(os.listdir(TSPLIB_DATA_DIR)):
        if not filename.endswith('.tsp'):
            continue

        filepath = os.path.join(TSPLIB_DATA_DIR, filename)
        data = parse_tsplib_file(filepath)

        if not data:
            continue

        name = data['name']
        local_names.add(name)

        info = _build_problem_info(data)
        if info:
            info.file_path = filepath
            problems.append(info)

    # ── Step 2: Skip auto-download on startup (network may be unavailable) ──
    # The download endpoint handles on-demand downloads.
    # Auto-download on startup caused 30s+ blocking timeouts in sandboxed environments.
    # Missing problems can be downloaded via POST /api/v1/benchmark/download/{name}.

    return problems


def get_problem_by_name(name: str) -> Optional[TSPLIBProblemInfo]:
    """Get a single problem by name."""
    for p in get_available_problems():
        if p.name == name.lower():
            return p
    return None


def load_problem_coordinates(name: str) -> Optional[List[Tuple[float, float]]]:
    """Load full coordinates for a problem by name."""
    info = get_problem_by_name(name)
    if not info or not info.file_path:
        return None
    
    data = parse_tsplib_file(info.file_path)
    if data:
        return data['coordinates']
    return None


def _fetch_url(url: str, timeout: int = _DOWNLOAD_TIMEOUT) -> Optional[bytes]:
    """Fetch URL content with error handling and timeout. Returns bytes or None."""
    try:
        req = Request(url, headers={"User-Agent": _DOWNLOAD_USER_AGENT})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except HTTPError as e:
        logger.debug(f"HTTP {e.code} for {url}: {e.reason}")
        return None
    except URLError as e:
        logger.debug(f"URL error for {url}: {e.reason}")
        return None
    except Exception as e:
        logger.debug(f"Download failed for {url}: {e}")
        return None


def _extract_tgz_to_dest(tgz_data: bytes, dest_dir: str, problem_name: str) -> Optional[str]:
    """
    Extract a .tgz archive into dest_dir and return the path to the .tsp file
    if one is found inside.
    """
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tgz_path = os.path.join(tmpdir, f"{problem_name}.tgz")
            with open(tgz_path, 'wb') as f:
                f.write(tgz_data)

            try:
                with tarfile.open(tgz_path, 'r:gz') as tar:
                    # Guard against path traversal: only extract members whose
                    # resolved path stays inside tmpdir.
                    safe_members = []
                    for member in tar.getmembers():
                        member_path = os.path.realpath(os.path.join(tmpdir, member.name))
                        if member_path.startswith(os.path.realpath(tmpdir) + os.sep) or \
                                member_path == os.path.realpath(tmpdir):
                            safe_members.append(member)
                        else:
                            logger.warning(
                                f"Skipping unsafe tar member: {member.name}"
                            )
                    tar.extractall(path=tmpdir, members=safe_members)
            except tarfile.TarError:
                logger.debug(f"Not a valid tar.gz archive for {problem_name}")
                return None

            # Look for the .tsp file in extracted contents
            for root, _dirs, files in os.walk(tmpdir):
                for fname in files:
                    if fname.lower().endswith('.tsp'):
                        src = os.path.join(root, fname)
                        dst = os.path.join(dest_dir, f"{problem_name}.tsp")
                        shutil.copy2(src, dst)
                        return dst

            logger.debug(f"No .tsp file found inside archive for {problem_name}")
            return None
    except Exception as e:
        logger.warning(f"Error extracting tgz for {problem_name}: {e}")
        return None


def download_tsplib_problem(name: str, dest_dir: Optional[str] = None) -> Optional[str]:
    """
    Download a TSPLIB problem file from the official TSPLIB archive.

    Tries two URL patterns:
    1. {NAME}.tsp.tgz  (compressed archive)
    2. {NAME}/{NAME}.tsp  (direct file in subdirectory)

    Args:
        name: Problem name (e.g., "eil51")
        dest_dir: Target directory (defaults to TSPLIB_DATA_DIR)

    Returns:
        Path to downloaded file, or None if failed
    """
    name = name.lower().strip()
    if dest_dir is None:
        dest_dir = TSPLIB_DATA_DIR

    # Ensure destination directory exists
    os.makedirs(dest_dir, exist_ok=True)

    target_path = os.path.join(dest_dir, f"{name}.tsp")

    # Already exists?
    if os.path.isfile(target_path):
        logger.debug(f"Problem '{name}' already exists at {target_path}")
        return target_path

    # ── Strategy 1: .tgz archive ──
    tgz_url = f"{TSPLIB_DOWNLOAD_URL}{name}.tsp.tgz"
    logger.info(f"[TSPLIB Download] Trying tgz: {tgz_url}")
    tgz_data = _fetch_url(tgz_url)
    if tgz_data is not None:
        result = _extract_tgz_to_dest(tgz_data, dest_dir, name)
        if result:
            logger.info(f"[TSPLIB Download] Downloaded '{name}' via .tgz → {result}")
            return result

    # ── Strategy 2: direct .tsp in subdirectory ──
    direct_url = f"{TSPLIB_DOWNLOAD_URL}{name}/{name}.tsp"
    logger.info(f"[TSPLIB Download] Trying direct: {direct_url}")
    tsp_data = _fetch_url(direct_url)
    if tsp_data is not None:
        try:
            with open(target_path, 'wb') as f:
                f.write(tsp_data)
            logger.info(f"[TSPLIB Download] Downloaded '{name}' via direct URL → {target_path}")
            return target_path
        except OSError as e:
            logger.warning(f"[TSPLIB Download] Failed to write '{name}': {e}")
            return None

    logger.warning(f"[TSPLIB Download] Could not download '{name}' from TSPLIB archive")
    return None


def ensure_tsplib_problems(problem_names: Optional[List[str]] = None) -> Dict[str, bool]:
    """
    Ensure specified problems are available locally. Downloads missing ones.

    Args:
        problem_names: List of problem names to ensure.
                      If None, checks all known optimals.

    Returns:
        Dict mapping problem_name -> bool (True if available, False if download failed)
    """
    if problem_names is None:
        problem_names = list(TSPLIB_OPTIMALS.keys())

    results: Dict[str, bool] = {}
    for name in problem_names:
        name_lower = name.lower()
        expected_path = os.path.join(TSPLIB_DATA_DIR, f"{name_lower}.tsp")

        if os.path.isfile(expected_path):
            results[name_lower] = True
            continue

        # Try downloading
        downloaded = download_tsplib_problem(name_lower)
        results[name_lower] = downloaded is not None

    return results


__all__ = [
    'TSPLIBProblemInfo',
    'TSPLIB_OPTIMALS',
    'TSPLIB_DATA_DIR',
    'TSPLIB_DOWNLOAD_URL',
    'parse_tsplib_file',
    'euclidean_distance_2d',
    'tsplib_tour_distance',
    'get_available_problems',
    'get_problem_by_name',
    'load_problem_coordinates',
    'download_tsplib_problem',
    'ensure_tsplib_problems',
]
