"""
TSPLIB Problem Parser and Registry — Canonical implementation.

Supports .tsp, .atsp, and .opt.tour file parsing, all TSPLIB distance types,
download from the official TSPLIB archive, and SQLite-free problem listing.

Usage:
    from uniride_core.algorithms.tsplib_parser import (
        parse_tsplib_file, parse_tsplib_text,
        tsplib_distance_by_type, get_available_problems,
        download_tsplib_problem,
    )

    data = parse_tsplib_file("path/to/berlin52.tsp")
    data = parse_tsplib_text(content_string)
    dist = tsplib_distance_by_type("EUC_2D", (0,0), (10,10))
"""

import os
import re
import math
import logging
import tarfile
import tempfile
import shutil
from typing import Dict, List, Optional, Tuple
from urllib.request import urlopen, Request
from urllib.error import HTTPError, URLError

from uniride_core.models import ProblemInstance


logger = logging.getLogger(__name__)

TSPLIB_DATA_DIR = os.path.join(os.path.dirname(__file__), '..', '..',
                                'optimizer_api', 'tests', 'tsplib_data')
TSPLIB_DOWNLOAD_URL = "http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/tsp/"
ATSP_DOWNLOAD_URL = "http://comopt.ifi.uni-heidelberg.de/software/TSPLIB95/atsp/"
_DOWNLOAD_TIMEOUT = 30
_DOWNLOAD_USER_AGENT = "UniRide-Optimizer/1.0 (+https://uniride.dev)"

# Known TSPLIB optimal solutions (source: TSPLIB95)
TSPLIB_OPTIMALS: Dict[str, int] = {
    "berlin52": 7542, "eil51": 426, "eil76": 538, "st70": 675,
    "kroa100": 21282, "krob100": 22141, "kroc100": 20749, "krod100": 21294,
    "kroe100": 22068, "rd100": 7910, "eil101": 629, "lin105": 14379,
    "pr107": 44303, "pr124": 59030, "pr136": 96772, "pr144": 58537,
    "pr152": 73682,
    "kroa150": 26524, "krob150": 26130, "kroa200": 29368, "krob200": 29437,
    "pr226": 80369, "pr264": 49135, "pr299": 48191, "ts225": 126843,
    "gil262": 2412, "pr439": 107217, "a280": 2579, "lin318": 42029,
    "rd400": 15281,
    "d493": 35002, "u724": 41910, "rat783": 8806, "pr1002": 259045,
    "u1060": 224094, "vm1084": 239297, "pcb1173": 56892, "nrw1379": 56638,
    "u1432": 152970, "d1655": 62128, "vm1748": 336556, "u1817": 57201,
    "d2103": 80450, "u2152": 64253, "u2319": 234256, "pr2392": 378032,
    # ATSP (Asymmetric TSP) optimal values
    "br17": 39, "ft53": 6905, "ft70": 38673, "ftv33": 1286,
    "ftv35": 1473, "ftv38": 1530, "ftv44": 1613, "ftv47": 1776,
    "ftv55": 1608, "ftv64": 1839, "ftv70": 1950, "ftv170": 2755,
    "kro124p": 36230, "p43": 28140, "rbg323": 1326,
    "rbg358": 1163, "rbg403": 2465, "rbg443": 2720,
}

_SUPPORTED_EWT = ("EUC_2D", "EUC_3D", "CEIL_2D", "ATT", "GEO", "GEOM", "NEU_2D")


def _normalize_name(raw: str, name_hint: str = "") -> str:
    name = raw.lower().strip()
    for sfx in (".opt.tour", ".opt", ".tsp", ".atsp"):
        if name.endswith(sfx):
            name = name[:-len(sfx)]
    name = name.split("/")[-1].split("\\")[-1]
    if not name:
        name = name_hint.lower().replace(".tsp", "").replace(".atsp", "")
        name = name.split("/")[-1].split("\\")[-1]
    return name


def parse_tsplib_text(content: str, name_hint: str = "") -> Optional[Dict]:
    """Parse TSPLIB text content and return problem data dict.
    
    Returns dict with keys: name, dimension, coordinates, type,
    edge_weight_type, problem_type.
    Returns None if the content is not parseable (EXPLICIT/ATSP types, etc.).
    """
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    coord_m = re.search(
        r"NODE_COORD_SECTION\s*\n(.*?)(?:\n(?:EOF|DISPLAY_DATA_SECTION)|\Z)",
        content, re.DOTALL | re.IGNORECASE
    )
    if not coord_m:
        return None
    header = content[:coord_m.start()]
    dim_m = re.search(r"DIMENSION\s*[:\s]\s*(\d+)", header, re.IGNORECASE)
    ewt_m = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    type_m = re.search(r"TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    name_matches = list(re.finditer(
        r"^NAME\s*[:\s]\s*(\S+)", header, re.IGNORECASE | re.MULTILINE
    ))
    if not dim_m:
        return None
    raw_name = name_matches[-1].group(1) if name_matches else name_hint
    name = _normalize_name(raw_name, name_hint)
    if not name:
        return None
    dimension = int(dim_m.group(1))
    ewt = ewt_m.group(1).upper() if ewt_m else "EUC_2D"
    if ewt not in _SUPPORTED_EWT:
        return None
    coords = []
    for line in coord_m.group(1).strip().splitlines():
        parts = line.strip().split()
        if len(parts) >= 3:
            try:
                coords.append((float(parts[1]), float(parts[2])))
            except ValueError:
                pass
    if not coords:
        return None
    return {
        "name": name,
        "dimension": dimension,
        "edge_weight_type": ewt,
        "problem_type": type_m.group(1).upper() if type_m else "TSP",
        "coordinates": coords,
    }


def parse_tsplib_file(filepath: str) -> Optional[Dict]:
    """Parse a TSPLIB .tsp file and extract problem data."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return parse_tsplib_text(f.read(), os.path.basename(filepath))
    except Exception as e:
        logger.error(f"Failed to parse TSPLIB file {filepath}: {e}")
        return None


def parse_opt_tour_text(content: str) -> Optional[List[int]]:
    """Parse TSPLIB .opt.tour file content to extract node list."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    m = re.search(
        r"TOUR_SECTION\s*\n(.*?)(?:\n-1|\nEOF|\Z)",
        content, re.DOTALL | re.IGNORECASE
    )
    if not m:
        return None
    nodes = []
    for tok in m.group(1).split():
        try:
            v = int(tok)
            if v == -1:
                break
            nodes.append(v)
        except ValueError:
            pass
    return nodes if nodes else None


def parse_atsp_text(content: str, name_hint: str = "") -> Optional[Dict]:
    """Parse ATSP file with EXPLICIT matrix. Returns dict or None."""
    content = content.replace("\r\n", "\n").replace("\r", "\n")
    header_end = re.search(r"EDGE_WEIGHT_SECTION\s*\n", content, re.IGNORECASE)
    if not header_end:
        return None
    header = content[:header_end.start()]
    dim_m = re.search(r"DIMENSION\s*[:\s]\s*(\d+)", header, re.IGNORECASE)
    if not dim_m:
        return None
    dimension = int(dim_m.group(1))
    name_matches = list(re.finditer(
        r"^NAME\s*[:\s]\s*(\S+)", header, re.IGNORECASE | re.MULTILINE
    ))
    ewt_m = re.search(r"EDGE_WEIGHT_TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    fmt_m = re.search(r"EDGE_WEIGHT_FORMAT\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    type_m = re.search(r"TYPE\s*[:\s]\s*(\S+)", header, re.IGNORECASE)
    ewt = ewt_m.group(1).upper() if ewt_m else "EXPLICIT"
    fmt = fmt_m.group(1).upper() if fmt_m else "FULL_MATRIX"
    raw_name = name_matches[-1].group(1) if name_matches else name_hint
    name = _normalize_name(raw_name, name_hint)
    if not name:
        return None
    matrix_section = content[header_end.end():]
    eof_m = re.search(r"\bEOF\b", matrix_section, re.IGNORECASE)
    if eof_m:
        matrix_section = matrix_section[:eof_m.start()]
    tokens = matrix_section.split()
    n_expected = dimension * dimension
    if fmt == "FULL_MATRIX":
        if len(tokens) < n_expected:
            return None
        vals = []
        for tok in tokens[:n_expected]:
            try:
                vals.append(int(tok))
            except ValueError:
                return None
        matrix = [vals[i * dimension:(i + 1) * dimension] for i in range(dimension)]
    else:
        return None
    return {
        "name": name, "dimension": dimension,
        "edge_weight_type": ewt, "problem_type": type_m.group(1).upper() if type_m else "ATSP",
        "explicit_matrix": matrix,
    }


def euclidean_distance_2d(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    return math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)


def tsplib_euc_2d_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    """NINT( sqrt( (xi-xj)² + (yi-yj)² ) )"""
    raw = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    return int(raw + 0.5)


def tsplib_ceil_2d_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    raw = math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
    return int(math.ceil(raw))


def tsplib_att_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    dx = p1[0] - p2[0]
    dy = p1[1] - p2[1]
    rij = math.sqrt((dx * dx + dy * dy) / 10.0)
    tij = int(rij + 0.5)
    return tij if tij >= rij else tij + 1


def tsplib_geo_distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> int:
    def _to_geo(x: float) -> float:
        deg = int(x)
        minute = x - deg
        return math.pi * (deg + 5.0 * minute / 3.0) / 180.0
    rrr = 6378.388
    lat1 = _to_geo(p1[0])
    lon1 = _to_geo(p1[1])
    lat2 = _to_geo(p2[0])
    lon2 = _to_geo(p2[1])
    q1 = math.cos(lon1 - lon2)
    q2 = math.cos(lat1 - lat2)
    q3 = math.cos(lat1 + lat2)
    return int(rrr * math.acos(0.5 * ((1.0 + q1) * q2 - (1.0 - q1) * q3)) + 1.0)


def tsplib_distance_by_type(
    edge_weight_type: str,
    p1: Tuple[float, float],
    p2: Tuple[float, float]
) -> int:
    et = (edge_weight_type or "EUC_2D").upper()
    if et == "EUC_2D":
        return tsplib_euc_2d_distance(p1, p2)
    if et == "CEIL_2D":
        return tsplib_ceil_2d_distance(p1, p2)
    if et == "ATT":
        return tsplib_att_distance(p1, p2)
    if et == "GEO":
        return tsplib_geo_distance(p1, p2)
    raise ValueError(f"Unsupported EDGE_WEIGHT_TYPE: {edge_weight_type}")


def tsplib_tour_distance(coords: List[Tuple[float, float]], tour: List[int]) -> float:
    if not tour or len(tour) < 2:
        return 0.0
    total = 0
    for i in range(len(tour)):
        p1 = coords[tour[i]]
        p2 = coords[tour[(i + 1) % len(tour)]]
        total += tsplib_euc_2d_distance(p1, p2)
    return float(total)


def _build_problem_info(data: Dict) -> Optional[ProblemInstance]:
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
    return ProblemInstance(
        name=name, dimension=dim,
        optimal=TSPLIB_OPTIMALS.get(name),
        category=category, problem_type=data['problem_type'],
        edge_weight_type=data['edge_weight_type'],
        file_path=None, source="tsplib",
    )


def get_available_problems() -> List[ProblemInstance]:
    problems: List[ProblemInstance] = []
    os.makedirs(TSPLIB_DATA_DIR, exist_ok=True)
    if not os.path.isdir(TSPLIB_DATA_DIR):
        return problems
    for filename in sorted(os.listdir(TSPLIB_DATA_DIR)):
        if filename.endswith('.tsp'):
            filepath = os.path.join(TSPLIB_DATA_DIR, filename)
            data = parse_tsplib_file(filepath)
            if not data:
                continue
            info = _build_problem_info(data)
            if info:
                info.file_path = filepath
                problems.append(info)
        elif filename.endswith('.atsp'):
            filepath = os.path.join(TSPLIB_DATA_DIR, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = parse_atsp_text(f.read(), os.path.basename(filepath))
                if data:
                    info = _build_problem_info(data)
                    if info:
                        info.file_path = filepath
                        info.dist_matrix = data['explicit_matrix']
                        problems.append(info)
            except Exception:
                continue
    return problems


def get_problem_by_name(name: str) -> Optional[ProblemInstance]:
    for p in get_available_problems():
        if p.name == name.lower():
            return p
    return None


def load_problem_coordinates(name: str) -> Optional[List[Tuple[float, float]]]:
    info = get_problem_by_name(name)
    if not info or not info.file_path:
        return None
    data = parse_tsplib_file(info.file_path)
    return data['coordinates'] if data else None


def _fetch_url(url: str, timeout: int = _DOWNLOAD_TIMEOUT) -> Optional[bytes]:
    try:
        req = Request(url, headers={"User-Agent": _DOWNLOAD_USER_AGENT})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except (HTTPError, URLError, Exception) as e:
        logger.debug(f"Download failed for {url}: {e}")
        return None


def _extract_tgz_to_dest(tgz_data: bytes, dest_dir: str, problem_name: str) -> Optional[str]:
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            tgz_path = os.path.join(tmpdir, f"{problem_name}.tgz")
            with open(tgz_path, 'wb') as f:
                f.write(tgz_data)
            try:
                with tarfile.open(tgz_path, 'r:gz') as tar:
                    real_tmpdir = os.path.realpath(tmpdir)
                    safe_members = []
                    for member in tar.getmembers():
                        member_path = os.path.realpath(os.path.join(tmpdir, member.name))
                        try:
                            if os.path.commonpath([real_tmpdir, member_path]) == real_tmpdir:
                                safe_members.append(member)
                        except ValueError:
                            pass
                    tar.extractall(path=tmpdir, members=safe_members)
            except tarfile.TarError:
                return None
            for root, _dirs, files in os.walk(tmpdir):
                for fname in files:
                    if fname.lower().endswith('.tsp'):
                        src = os.path.join(root, fname)
                        dst = os.path.join(dest_dir, f"{problem_name}.tsp")
                        shutil.copy2(src, dst)
                        return dst
            return None
    except Exception as e:
        logger.warning(f"Error extracting tgz for {problem_name}: {e}")
        return None


def download_tsplib_problem(name: str, dest_dir: Optional[str] = None) -> Optional[str]:
    name = name.lower().strip()
    if dest_dir is None:
        dest_dir = TSPLIB_DATA_DIR
    os.makedirs(dest_dir, exist_ok=True)
    target_path = os.path.join(dest_dir, f"{name}.tsp")
    if os.path.isfile(target_path):
        return target_path
    tgz_url = f"{TSPLIB_DOWNLOAD_URL}{name}.tsp.tgz"
    logger.info(f"[TSPLIB] Trying tgz: {tgz_url}")
    tgz_data = _fetch_url(tgz_url)
    if tgz_data is not None:
        result = _extract_tgz_to_dest(tgz_data, dest_dir, name)
        if result:
            return result
    direct_url = f"{TSPLIB_DOWNLOAD_URL}{name}/{name}.tsp"
    logger.info(f"[TSPLIB] Trying direct: {direct_url}")
    tsp_data = _fetch_url(direct_url)
    if tsp_data is not None:
        with open(target_path, 'wb') as f:
            f.write(tsp_data)
        return target_path
    return None


def ensure_tsplib_problems(problem_names: Optional[List[str]] = None) -> Dict[str, bool]:
    if problem_names is None:
        problem_names = list(TSPLIB_OPTIMALS.keys())
    results: Dict[str, bool] = {}
    for name in problem_names:
        name_lower = name.lower()
        expected_path = os.path.join(TSPLIB_DATA_DIR, f"{name_lower}.tsp")
        if os.path.isfile(expected_path):
            results[name_lower] = True
            continue
        downloaded = download_tsplib_problem(name_lower)
        results[name_lower] = downloaded is not None
    return results


# ── ATSP Download ──────────────────────────────────────────────────────────────

ATSP_PROBLEM_NAMES = [
    "br17", "ft53", "ft70", "ftv33", "ftv35", "ftv38", "ftv44",
    "ftv47", "ftv55", "ftv64", "ftv70", "ftv170",
    "kro124p", "p43", "rbg323", "rbg358", "rbg403", "rbg443",
]


def download_atsp_problem(name: str, dest_dir: Optional[str] = None) -> Optional[str]:
    name = name.lower().strip()
    if dest_dir is None:
        dest_dir = TSPLIB_DATA_DIR
    os.makedirs(dest_dir, exist_ok=True)
    target_path = os.path.join(dest_dir, f"{name}.atsp")
    if os.path.isfile(target_path):
        return target_path
    tgz_url = f"{ATSP_DOWNLOAD_URL}{name}.atsp.tgz"
    logger.info(f"[ATSP] Trying tgz: {tgz_url}")
    tgz_data = _fetch_url(tgz_url)
    if tgz_data is not None:
        content = _extract_tgz_to_dest(tgz_data, dest_dir, f"{name}_atsp")
        if content:
            return content
    direct_url = f"{ATSP_DOWNLOAD_URL}{name}.atsp"
    logger.info(f"[ATSP] Trying direct: {direct_url}")
    atsp_data = _fetch_url(direct_url)
    if atsp_data is not None:
        target_path = os.path.join(dest_dir, f"{name}.atsp")
        with open(target_path, 'wb') as f:
            f.write(atsp_data)
        return target_path
    return None


def ensure_atsp_problems(problem_names: Optional[List[str]] = None) -> Dict[str, bool]:
    if problem_names is None:
        problem_names = ATSP_PROBLEM_NAMES
    results: Dict[str, bool] = {}
    for name in problem_names:
        name_lower = name.lower()
        expected_path = os.path.join(TSPLIB_DATA_DIR, f"{name_lower}.atsp")
        if os.path.isfile(expected_path):
            results[name_lower] = True
            continue
        downloaded = download_atsp_problem(name_lower)
        results[name_lower] = downloaded is not None
    return results


__all__ = [
    'ProblemInstance', 'TSPLIB_OPTIMALS', 'TSPLIB_DATA_DIR', 'TSPLIB_DOWNLOAD_URL',
    'ATSP_DOWNLOAD_URL', 'ATSP_PROBLEM_NAMES',
    'parse_tsplib_file', 'parse_tsplib_text', 'parse_opt_tour_text', 'parse_atsp_text',
    'euclidean_distance_2d', 'tsplib_euc_2d_distance', 'tsplib_ceil_2d_distance',
    'tsplib_att_distance', 'tsplib_geo_distance', 'tsplib_distance_by_type',
    'tsplib_tour_distance', 'get_available_problems', 'get_problem_by_name',
    'load_problem_coordinates', 'download_tsplib_problem', 'ensure_tsplib_problems',
    'download_atsp_problem', 'ensure_atsp_problems',
]
