"""Lightweight TSPLIB loaders (read-only access to the repo data; no repo imports)."""
import os, sqlite3
import numpy as np

ROOT = r"C:\Users\yektakayman\Desktop\AiCode\FirebaseUniRide\UniRide"
TD_REPO = os.path.join(ROOT, "academic_benchmark", "tsplib_data")
# NOTE: after a session restart the host grant for academic_benchmark/ became unusable
# (PermissionError).  Canonical TSPLIB95 files were downloaded from
# comopt.ifi.uni-heidelberg.de into ./data (ft53.atsp sha256 == repo checksum).
TD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
# optima as read from academic_benchmark/tsplib_data/tsplib.db earlier in this session
OPT = {"rd100": 7910, "eil101": 629, "lin105": 14379, "pr136": 96772, "pr152": 73682,
       "a280": 2579, "lin318": 42029, "pr439": 107217, "rat783": 8806, "pr1002": 259045,
       "pcb1173": 56892, "pr299": 48191, "d493": 35002, "u724": 41910}


def load_tsp(name):
    """Same construction as bench_common.load_instance: EUC_2D, nint rounding."""
    coords, ewt, sec = [], None, False
    for line in open(os.path.join(TD, name + ".tsp"), encoding="utf-8", errors="ignore"):
        s = line.strip()
        if s.startswith("EDGE_WEIGHT_TYPE"):
            ewt = s.split(":")[-1].strip()
        if s.startswith("NODE_COORD_SECTION"):
            sec = True
            continue
        if s.startswith("EOF"):
            break
        if sec and s:
            p = s.split()
            coords.append((float(p[1]), float(p[2])))
    assert ewt == "EUC_2D", (name, ewt)
    xy = np.array(coords)
    d = np.sqrt(((xy[:, None, :] - xy[None, :, :]) ** 2).sum(-1))
    dm = np.floor(d + 0.5)
    np.fill_diagonal(dm, 0.0)
    return dm, float(OPT[name])


def load_atsp(name="ft53"):
    """TSPLIB ATSP FULL_MATRIX.  Diagonal sentinel replaced by 0 (never used by a tour)."""
    vals, n, sec = [], None, False
    for line in open(os.path.join(TD, name + ".atsp"), encoding="utf-8", errors="ignore"):
        s = line.strip()
        if s.startswith("DIMENSION"):
            n = int(s.split(":")[-1])
        elif s.startswith("EDGE_WEIGHT_FORMAT"):
            assert "FULL_MATRIX" in s
        elif s.startswith("EDGE_WEIGHT_SECTION"):
            sec = True
        elif s.startswith("EOF"):
            break
        elif sec and s:
            vals.extend(float(v) for v in s.split())
    dm = np.array(vals[: n * n]).reshape(n, n)
    np.fill_diagonal(dm, 0.0)
    return dm, 6905.0 if name == "ft53" else None
