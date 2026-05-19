"""
Benchmark Utils — Ortak araçlar modülü (Konsolidasyon FAZ 0)

Tüm master engine'ler tarafından paylaşılan yardımcı fonksiyonlar.
DRY prensibiyle 6 farklı benchmark dosyasından çıkarılmıştır.
"""

import csv
import hashlib
import io
import itertools
import json
import math
import os
import platform
import random
import signal
import statistics
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from multiprocessing import cpu_count
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple


# ── TSPLIB Bilinen Optimal Değerler ──────────────────────────────────────────

TSPLIB_OPTIMALS: Dict[str, int] = {
    # ── Symmetric TSP (STSP) — from Heidelberg TSPLIB95 / mastqe/tsplib ──
    "berlin52": 7542, "eil51": 426, "eil76": 538, "st70": 675,
    "kroa100": 21282, "krob100": 22141, "kroc100": 20749, "krod100": 21294,
    "kroe100": 22068, "eil101": 629, "pr76": 108159, "pr107": 44303, "pr124": 59030,
    "bier127": 118282, "ch130": 6110, "ch150": 6528, "kroa150": 26524,
    "krob150": 26130, "pr152": 73682, "u159": 42080, "rat195": 2323,
    "d198": 15780, "kroa200": 29368, "krob200": 29437, "ts225": 126643,
    "tsp225": 3916, "pr226": 80369, "gil262": 2378, "pr264": 49135,
    "a280": 2579, "pr299": 48191, "lin318": 42029, "rd400": 15281,
    "fl417": 11861, "pr439": 107217, "pcb442": 50778, "d493": 35002,
    "u574": 36905, "rat575": 6773, "p654": 34643, "d657": 48912,
    "u724": 41910, "rat783": 8806, "pr1002": 259045, "u1060": 224094,
    "vm1084": 239297, "pcb1173": 56892, "d1291": 50801, "rl1304": 252948,
    "rl1323": 270199, "nrw1379": 56638, "fl1400": 20127, "u1432": 152970,
    "fl1577": 22249, "d1655": 62128, "vm1748": 336556, "u1817": 57201,
    "rl1889": 316536, "d2103": 80450, "u2152": 64253, "u2319": 234256,
    "pr2392": 378032, "pcb3038": 137694, "fl3795": 28772, "fnl4461": 182566,
    "lin105": 14379, "rd100": 7910, "pr136": 96772, "pr144": 58537,
    "att48": 10628, "att532": 27686, "burma14": 3323, "bayg29": 1610,
    "bays29": 2020, "brazil58": 25395, "dantzig42": 699, "gr17": 2085,
    "gr21": 2707, "gr24": 1272, "gr48": 5046, "gr96": 55209,
    "gr120": 6942, "gr137": 69853, "gr202": 40160, "gr229": 134602,
    "gr431": 171414, "gr666": 294358, "hk48": 11461, "swiss42": 1273,
    "ulysses16": 6859, "ulysses22": 7013,
    # Additional STSP from mastqe/tsplib solutions
    "ali535": 202339, "brd14051": 469385, "brg180": 1950,
    "d15112": 1573084, "d18512": 645238, "dsj1000": 18660188,
    "fri26": 937, "linhp318": 41345, "pa561": 2763,
    "pla7397": 23260728, "pla33810": 66048945, "pla85900": 142382641,
    "rat99": 1211, "rl5915": 565530, "rl5934": 556045,
    "rl11849": 923288, "si175": 21407, "si535": 48450, "si1032": 92650,
    "usa13509": 19982859,
    # ── Asymmetric TSP (ATSP) — proven optimal ──
    "br17": 39, "ft53": 6905, "ft70": 38673, "ftv33": 1286,
    "ftv35": 1473, "ftv38": 1530, "ftv44": 1613, "ftv47": 1776,
    "ftv55": 1608, "ftv64": 1839, "ftv70": 1950, "ftv170": 2755,
    "kro124p": 36230, "p43": 28140, "rbg323": 1326,
    "rbg358": 1163, "rbg403": 2465, "rbg443": 2720,
}


# ── Best-So-Far (BSF) Tracker for Unknown-Optimal Problems ───────────────────

class BSFTracker:
    """Thread-safe tracker for best-so-far tour cost per problem.
    Used when optimal value is unknown — gap is computed relative to BSF.
    """
    def __init__(self):
        self._best: Dict[str, float] = {}

    def update(self, problem: str, cost: float) -> float:
        """Update BSF for a problem. Returns the current BSF."""
        prev = self._best.get(problem)
        if prev is None or cost < prev:
            self._best[problem] = cost
        return self._best[problem]

    def get(self, problem: str) -> Optional[float]:
        """Get current BSF for a problem. None if not yet recorded."""
        return self._best.get(problem)

    def compute_gap(self, problem: str, cost: float) -> Tuple[float, str]:
        """Compute gap. Returns (gap_pct, gap_type).
        If optimal known: gap vs optimal, type='optimal'
        If optimal unknown: gap vs BSF, type='bsf'
        """
        optimal = TSPLIB_OPTIMALS.get(problem.lower())
        if optimal and optimal > 0:
            gap = (cost - optimal) / optimal * 100.0
            return gap, "optimal"
        bsf = self._best.get(problem)
        if bsf and bsf > 0:
            gap = (cost - bsf) / bsf * 100.0
            return gap, "bsf"
        return float("nan"), "unknown"


# Global BSF tracker instance (shared across engine runs)
_bsf_tracker = BSFTracker()


def get_bsf_tracker() -> BSFTracker:
    """Get the global BSF tracker instance."""
    return _bsf_tracker


def compute_gap(problem: str, cost: float, optimal: Optional[int] = None) -> Tuple[float, str]:
    """Compute gap percentage. Returns (gap_pct, gap_type).
    gap_type: 'optimal' | 'bsf' | 'unknown'
    """
    opt = optimal if optimal is not None else TSPLIB_OPTIMALS.get(problem.lower())
    if opt and opt > 0:
        gap = (cost - opt) / opt * 100.0
        return gap, "optimal"
    # Fallback to BSF
    bsf = _bsf_tracker.get(problem)
    if bsf and bsf > 0:
        gap = (cost - bsf) / bsf * 100.0
        return gap, "bsf"
    return float("nan"), "unknown"


_MAX_RECOMMENDED_WORKERS = 16


# ── Dosya Hash ───────────────────────────────────────────────────────────────

def get_file_hash(filepath: str) -> str:
    """SHA-256 hash hesaplar. Dosya yoksa boş string döner."""
    if not os.path.exists(filepath):
        return ""
    h = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            h.update(chunk)
    return h.hexdigest()


# ── Metadata Yönetimi ────────────────────────────────────────────────────────

def _sync_hash_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    fh = data.get("file_hashes", {})
    ah = data.get("algorithm_hashes", {})
    if fh and ah and fh != ah:
        common_keys = set(fh) & set(ah)
        divergent = [k for k in common_keys if fh.get(k) != ah.get(k)]
        if divergent:
            print(f"[UYARI] Hash uyumsuzlugu tespit edildi: {divergent}. algorithm_hashes oncelikli.")
    merged = {**fh, **ah}
    return {**data, "file_hashes": merged, "algorithm_hashes": merged}


def load_metadata(path: str) -> Dict[str, Any]:
    """JSON metadata dosyasını okur."""
    default = {
        "file_hashes": {}, "algorithm_hashes": {},
        "results": {}, "best_params": {}, "last_updated": "",
    }
    if not os.path.exists(path):
        return default.copy()
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return default.copy()
        synced = _sync_hash_fields(data)
        return {
            "file_hashes": synced.get("file_hashes", {}),
            "algorithm_hashes": synced.get("algorithm_hashes", {}),
            "results": synced.get("results", {}),
            "best_params": synced.get("best_params", {}),
            "last_updated": synced.get("last_updated", ""),
        }
    except Exception:
        return default.copy()


def save_metadata(path: str, data: Dict[str, Any]) -> None:
    """Metadata'yı JSON dosyasına kaydeder."""
    data_to_save = _sync_hash_fields(data)
    data_to_save["last_updated"] = datetime.now().isoformat()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data_to_save, f, indent=2, ensure_ascii=False)


def check_algorithms_status(
    metadata: Dict[str, Any],
    algorithms_to_check: Dict[str, str],
) -> Dict[str, str]:
    """Algoritma dosyalarının hash durumunu kontrol eder."""
    saved = metadata.get("algorithm_hashes") or metadata.get("file_hashes", {})
    status: Dict[str, str] = {}
    for name, filepath in algorithms_to_check.items():
        if not os.path.exists(filepath):
            status[name] = "FILE_MISSING"
        else:
            cur = get_file_hash(filepath)
            if name not in saved:
                status[name] = "NEW"
            elif saved[name] != cur:
                status[name] = "CHANGED"
            else:
                status[name] = "CURRENT"
    return status


def update_algorithm_hashes(
    metadata: Dict[str, Any],
    algorithms_to_check: Dict[str, str],
) -> None:
    """Metadata'daki hash değerlerini günceller."""
    hashes = {k: get_file_hash(v) for k, v in algorithms_to_check.items()}
    metadata["algorithm_hashes"] = hashes
    metadata["file_hashes"] = hashes


# ── Zaman ve UI Araçları ─────────────────────────────────────────────────────

def format_time(seconds: float) -> str:
    """Saniyeyi okunabilir formata çevirir."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    if seconds < 3600:
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m}m {s:02d}s"
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    return f"{h}h {m:02d}m"


def clear_screen() -> None:
    """Terminal ekranını temizler."""
    if sys.stdin.isatty():
        os.system("cls" if os.name == "nt" else "clear")
    else:
        print("\n" * 3)


def gap_str(gap) -> str:
    """Gap değerini formatlar."""
    if gap is None or (isinstance(gap, float) and math.isnan(gap)):
        return "  N/A "
    return f"{gap:.2f}%"


def make_bar(done: int, total: int, width: int = 12) -> str:
    if total <= 0:
        return "." * width
    filled = int(done / total * width)
    return "#" * filled + "." * (width - filled)


def log_environment_info() -> None:
    """Ortam bilgilerini yazdırır."""
    print(f"[ENV] OS: {platform.system()} {platform.release()}")
    print(f"[ENV] Python: {sys.version.split()[0]}")
    try:
        import numpy
        print(f"[ENV] NumPy: {numpy.__version__}")
    except ImportError:
        print("[ENV] NumPy: N/A")
    try:
        import numba
        print(f"[ENV] Numba: {numba.__version__}")
    except ImportError:
        print("[ENV] Numba: N/A")
    print(f"[ENV] CPU: {cpu_count()} cores")


# ── ETA Tracker ──────────────────────────────────────────────────────────────

class ETATracker:
    """Tamamlanan görevlere göre ETA tahmin eder."""

    def __init__(self):
        self._times: List[float] = []
        self._by_algo: Dict[str, List[float]] = {}
        self._by_cat: Dict[str, List[float]] = {}

    def record(self, elapsed: float, algo: str = "", cat: str = "") -> None:
        self._times.append(elapsed)
        if algo:
            self._by_algo.setdefault(algo, []).append(elapsed)
        if cat:
            self._by_cat.setdefault(cat, []).append(elapsed)

    def estimate_remaining(self, tasks_left: int) -> Optional[float]:
        if not self._times:
            return None
        avg = sum(self._times) / len(self._times)
        return avg * tasks_left

    def estimate_for(self, algo: str, cat: str) -> Optional[float]:
        if algo in self._by_algo:
            vals = self._by_algo[algo]
            return sum(vals) / len(vals)
        if cat in self._by_cat:
            vals = self._by_cat[cat]
            return sum(vals) / len(vals)
        if self._times:
            return sum(self._times) / len(self._times)
        return None


# ── CPU & Worker Seçimi ──────────────────────────────────────────────────────

def get_cpu_info() -> Dict[str, Any]:
    """CPU bilgilerini toplar ve optimal worker sayısı önerir."""
    try:
        import psutil
        physical = psutil.cpu_count(logical=False) or cpu_count()
        logical = psutil.cpu_count(logical=True) or cpu_count()
    except ImportError:
        physical = cpu_count()
        logical = cpu_count()
    smt = logical > physical
    recommended = physical if smt else max(1, physical - 1)
    recommended = min(recommended, _MAX_RECOMMENDED_WORKERS)
    return {
        "physical": physical, "logical": logical, "smt": smt,
        "recommended": recommended,
        "platform": platform.processor() or platform.machine(),
    }


def select_worker_count() -> int:
    """Kullanıcıdan worker sayısı seçimi alır."""
    info = get_cpu_info()
    rec = info["recommended"]
    print("\n" + "=" * 60)
    print("[CPU] ISLEMCI BILGILERI")
    print("=" * 60)
    print(f"   Platform      : {info['platform']}")
    print(f"   Fiziksel Cekirdek : {info['physical']}")
    print(f"   Mantiksal Cekirdek: {info['logical']}")
    print(f"\n[ONERI] Optimal worker sayisi: {rec}")
    print("\n[SECIM] Worker sayisi belirleyin:")
    print(f"   [A] {rec} (Onerilen)")
    print(f"   [B] {min(info['logical'], 8)} (Standart)")
    print(f"   [C] {min(info['logical'], _MAX_RECOMMENDED_WORKERS)} (Yuksek)")
    print(f"   [D] {info['logical']} (Maksimum)")
    print("   [Sayi] Dogrudan sayi girin (1-{})".format(info['logical']))
    print(f"   [Enter] Varsayilan: {rec}")
    choice = input("\nSeciminiz: ").strip().upper()
    if choice == "":
        return rec
    if choice == "A":
        return rec
    if choice == "B":
        return min(info["logical"], 8)
    if choice == "C":
        return min(info["logical"], _MAX_RECOMMENDED_WORKERS)
    if choice == "D":
        return info["logical"]
    try:
        v = int(choice)
        return max(1, min(v, info["logical"]))
    except ValueError:
        return rec


def select_run_count(label: str, default: int, allow_zero: bool = False) -> int:
    """Kullanıcıdan çalıştırma sayısı seçimi alır."""
    print(f"\n[RUNS] {label} CALISTIRMA SAYISI SECIN:")
    print(f"   Varsayilan: {default}")
    if allow_zero:
        print("   [0] 0 run (atla)")
    print("   [3] 3 run (hizli)")
    print("   [5] 5 run (standart)")
    print("   [10] 10 run (detayli)")
    print("   [Enter] Varsayilan kullan")
    raw = input("\nSeciminiz: ").strip()
    if not raw:
        return default
    if raw.isdigit():
        val = int(raw)
        if val == 0 and allow_zero:
            return 0
        if val >= 1:
            return val
    return default


def select_mode() -> bool:
    """Sequential vs Parallel seçimi. True = sequential."""
    print("\n[MODE] CALISTIRMA MODU SECIN:")
    print("   [S] Sirali (Sequential) - Anlik progress (onerilen)")
    print("   [P] Paralel - Daha hizli")
    choice = input("\nSeciminiz [S/P]: ").strip().upper()
    return choice != "P"


# ── Problem Selection (Universal Selector) ───────────────────────────────────

def _prob_name(p: Any) -> str:
    """Problem adini dict veya dataclass nesnesinden okur."""
    if isinstance(p, dict):
        return str(p.get("name", ""))
    return str(getattr(p, "name", p))


def _prob_dim(p: Any) -> int:
    """Problem boyutunu dict veya dataclass nesnesinden okur."""
    if isinstance(p, dict):
        try:
            return int(p.get("dimension", 0) or 0)
        except (TypeError, ValueError):
            return 0
    try:
        return int(getattr(p, "dimension", 0) or 0)
    except (TypeError, ValueError):
        return 0


def _prob_optimal(p: Any) -> Optional[int]:
    """Problem optimal degerini okur; gerekirse TSPLIB_OPTIMALS'a bakar."""
    if isinstance(p, dict):
        raw = p.get("optimal")
        if raw is not None:
            try:
                return int(raw)
            except (TypeError, ValueError):
                pass
        return TSPLIB_OPTIMALS.get(_prob_name(p).lower())

    raw = getattr(p, "optimal", None)
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass

    raw = getattr(p, "optimal_score", None)
    if raw is not None:
        try:
            return int(raw)
        except (TypeError, ValueError):
            pass

    return TSPLIB_OPTIMALS.get(_prob_name(p).lower())


def _prob_category(p: Any, dim: Optional[int] = None) -> str:
    """Boyuta gore small/medium/large kategorisini döner."""
    d = _prob_dim(p) if dim is None else dim
    return categorize_dimension(d)


class ProblemSelector:
    """SOTA ve Numba icin ortak problem secim motoru."""

    def __init__(self, problems: Sequence[Any], title: str = "PROBLEM SEÇİMİ"):
        self.title = title
        self.all_problems = list(problems)
        self._build_index()

    def _build_index(self) -> None:
        self.sorted = sorted(self.all_problems, key=lambda p: _prob_dim(p))
        self.name_map: Dict[str, int] = {}
        self.cat_indices: Dict[str, List[int]] = {"small": [], "medium": [], "large": []}

        for idx, problem in enumerate(self.sorted):
            name = _prob_name(problem).lower()
            self.name_map[name] = idx
            category = _prob_category(problem, _prob_dim(problem))
            if category in self.cat_indices:
                self.cat_indices[category].append(idx)

    def display_table(self, selected: Optional[Set[int]] = None) -> None:
        total = len(self.sorted)
        selected_count = len(selected) if selected else 0
        print(f"\n{'═' * 72}")
        print(f"  {self.title:<42} Toplam: {total} | Seçili: {selected_count}")
        print(f"{'═' * 72}")
        print("  Kategoriler:  small (n≤100) | medium (101-500) | large (500+)")
        print(f"  {'─' * 64}")
        print(f"  {'#':>3}  {'Name':<20} {'n':>5}  {'Optimal':>10}  {'Kat':<8}")
        print(f"  {'─' * 64}")
        for idx, problem in enumerate(self.sorted, 1):
            name = _prob_name(problem)
            dim = _prob_dim(problem)
            optimal = _prob_optimal(problem)
            category = _prob_category(problem, dim)
            marker = "▸" if selected is not None and (idx - 1) in selected else " "
            optimal_text = f"{optimal:>10}" if optimal is not None else "       N/A"
            print(f"  {marker}[{idx:>2}] {name:<20} n={dim:>5}  {optimal_text}  [{category:<6}]")
        print(f"  {'─' * 64}")
        print("  Syntax:  1,3,5 | 1-7 | berlin52 | small | medium | large | all")
        print("           !token = exclude")
        print(f"  {'─' * 64}")

    def _resolve_token(self, token: str, current: Set[int]) -> Tuple[Set[int], List[str]]:
        warnings: List[str] = []
        lower = token.strip().lower()

        if not lower:
            return current, warnings

        if lower.startswith("!"):
            resolved, child_warnings = self._resolve_token(lower[1:], set())
            warnings.extend(child_warnings)
            return current - resolved, warnings

        if lower == "all":
            return current | set(range(len(self.sorted))), warnings

        if lower in self.cat_indices:
            return current | set(self.cat_indices[lower]), warnings

        if "-" in lower and not lower.startswith("-"):
            left, right = lower.split("-", 1)
            try:
                start = int(left)
                end = int(right)
                if start > end:
                    start, end = end, start
                start_idx = max(0, start - 1)
                end_idx = min(len(self.sorted), end)
                return current | set(range(start_idx, end_idx)), warnings
            except ValueError:
                pass

        if lower.isdigit():
            idx = int(lower) - 1
            if 0 <= idx < len(self.sorted):
                return current | {idx}, warnings
            warnings.append(f"[UYARI] İndeks geçersiz: {token} (1-{len(self.sorted)})")
            return current, warnings

        if lower in self.name_map:
            return current | {self.name_map[lower]}, warnings

        warnings.append(f"[UYARI] Bilinmeyen token: {token}")
        return current, warnings

    def resolve_tokens(self, raw: str, current: Optional[Set[int]] = None) -> Tuple[Set[int], List[str]]:
        selected = set() if current is None else set(current)
        warnings: List[str] = []
        for token in (part.strip() for part in raw.split(",")):
            if not token:
                continue
            selected, token_warnings = self._resolve_token(token, selected)
            warnings.extend(token_warnings)
        return selected, warnings

    def quick_select(self, token_str: str) -> List[Any]:
        raw = (token_str or "").strip()
        if not raw or raw.lower() == "all":
            return list(self.sorted)
        selected, _ = self.resolve_tokens(raw)
        return [self.sorted[idx] for idx in sorted(selected)]

    def interactive_select(self) -> List[Any]:
        current: Set[int] = set()
        first_prompt = True

        while True:
            self.display_table(current)
            raw = input("\n  Seçim [Enter=tümü, done=bitir, ?=yardım, list=tablo]: ").strip()

            if not raw:
                if first_prompt:
                    current = set(range(len(self.sorted)))
                    break
                print("  [UYARI] Boş giriş yoksayıldı; mevcut seçim korunuyor.")
                continue

            first_prompt = False
            lowered = raw.lower()

            if lowered == "?":
                self._show_help()
                continue

            if lowered == "list":
                continue

            if lowered == "done":
                if not current:
                    confirm = input("  Hiç seçim yok. Boş seçimle çıkılsın mı? [e/H]: ").strip().lower()
                    if confirm not in {"e", "evet", "y", "yes"}:
                        continue
                break

            current, warnings = self.resolve_tokens(raw, current)
            for warning in warnings:
                print(f"  {warning}")

            if not current:
                print("  [UYARI] Seçim boş! Tekrar deneyin veya 'done' ile çıkın.")
                continue

            print(f"  → {len(current)} problem seçildi.")

        return [self.sorted[idx] for idx in sorted(current)]

    @staticmethod
    def _show_help() -> None:
        print(
            """
  ── SEÇİM YARDIMI ──────────────────────────────────
  all           → Tüm problemler
  small/medium/large → Kategori filtresi
  1,3,5         → 1., 3. ve 5. problem
  1-7           → 1-7 arası (ters yazılırsa düzeltilir)
  berlin52      → İsimle eşleşme (büyük/küçük harf duyarsız)
  !berlin52     → Hariç tut
  Karma: small,!eil51,10-15
  ───────────────────────────────────────────────────
            """
        )


# ── Parametre Araçları ───────────────────────────────────────────────────────

def validate_param_value(key: str, raw: str, expected_type: type,
                         validators: Optional[Dict] = None) -> Optional[Any]:
    """Parametre değerini doğrular ve çevirir."""
    try:
        if expected_type == bool:
            val = raw.lower() in ("true", "1", "t", "evet", "e")
        elif expected_type == float:
            val = float(raw)
        elif expected_type == int:
            val = int(raw)
        else:
            val = raw
        if validators and key in validators:
            vmin, vmax, _ = validators[key]
            if val < vmin or val > vmax:
                print(f"    [!] {key} aralik disi [{vmin}, {vmax}]: {val}")
                return None
        return val
    except ValueError:
        print(f"    [!] {key} icin gecersiz deger: {raw}")
        return None


def edit_param_space(space: Dict[str, List[Any]], algo_name: str,
                     validators: Optional[Dict] = None) -> Dict[str, List[Any]]:
    """Parametre uzayını kullanıcı ile düzenler."""
    print(f"\n[PARAM] {algo_name} parametre uzayini duzenleyin (Enter = kabul):")
    result: Dict[str, List[Any]] = {}
    for key, vals in space.items():
        print(f"  {key} = {vals}")
        raw = input(f"    Yeni degerler (virgul) [{vals}]: ").strip()
        if not raw:
            result[key] = vals
            continue
        parts = [x.strip() for x in raw.split(",")]
        new_vals: List[Any] = []
        sample_type = type(vals[0]) if vals else str
        valid = True
        for p in parts:
            if not p:
                continue
            v = validate_param_value(key, p, sample_type, validators)
            if v is None:
                valid = False
                break
            new_vals.append(v)
        if valid and new_vals:
            result[key] = new_vals
        else:
            print(f"    [!] Gecersiz, mevcut korunuyor: {vals}")
            result[key] = vals
    return result


# ── DoE Araçları ─────────────────────────────────────────────────────────────

def generate_combinations(space: Dict[str, List[Any]], max_combos: int,
                          strategy: str = "sequential",
                          random_seed: int = 42) -> List[Dict[str, Any]]:
    """Parametre uzayından kombinasyonlar üretir."""
    keys = list(space.keys())
    combos = [dict(zip(keys, v)) for v in itertools.product(*(space[k] for k in keys))]
    if len(combos) > max_combos and strategy == "fractional_fallback":
        random.seed(random_seed)
        combos = random.sample(combos, max_combos)
    else:
        combos = combos[:max_combos]
    return combos


def param_signature(params: Dict[str, Any]) -> str:
    """Parametre setinin benzersiz imzasını döner."""
    return json.dumps(params, sort_keys=True, ensure_ascii=False)


def make_deterministic_seed(problem_name: str, algo_name: str,
                            run_idx: int, algo_idx: int,
                            seed_base: int) -> int:
    """Hashlib tabanlı deterministik seed üretir."""
    raw = f"{problem_name}|{algo_name}|{run_idx}|{algo_idx}|{seed_base}".encode("utf-8")
    digest = hashlib.sha256(raw).hexdigest()
    return int(digest[:8], 16) & 0x7FFFFFFF


# ── Seçim Araçları ───────────────────────────────────────────────────────────

def parse_index_or_all(raw: str, item_count: int) -> Optional[List[int]]:
    """Kullanıcı girdisinden indeks listesi parse eder."""
    raw = raw.strip().lower()
    if raw == "all":
        return list(range(item_count))
    indices: List[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                lo, hi = part.split("-", 1)
                for i in range(int(lo) - 1, int(hi)):
                    if 0 <= i < item_count:
                        indices.append(i)
            except ValueError:
                print(f"  [HATA] Gecersiz aralik: '{part}'")
                return None
        elif part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < item_count:
                indices.append(idx)
            else:
                print(f"  [HATA] {part} aralik disi (1-{item_count})")
                return None
        else:
            print(f"  [HATA] Gecersiz giris: '{part}'")
            return None
    if not indices:
        return None
    seen: set = set()
    return [i for i in indices if not (i in seen or seen.add(i))]


def multi_select(items: Sequence[str], title: str) -> List[str]:
    """Listeden çoklu seçim yapar."""
    print(f"\n[{title}]")
    for idx, item in enumerate(items, 1):
        print(f"   [{idx}] {item}")
    raw = input("Secimler (virgul) / Enter=all: ").strip()
    if not raw:
        return list(items)
    selected: List[str] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(items):
                selected.append(items[idx])
                continue
        matches = [item for item in items if part.lower() in item.lower()]
        selected.extend(matches)
    seen: set = set()
    return [item for item in selected if not (item in seen or seen.add(item))]


# ── CSV Araçları ─────────────────────────────────────────────────────────────

def append_csv_row(path: str, fieldnames: Sequence[str],
                   row: Dict[str, Any]) -> None:
    """CSV dosyasına tek satır ekler. Dosya yoksa header yazar."""
    exists = os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(fieldnames))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


# ── Config Yönetimi ──────────────────────────────────────────────────────────

def list_configs(configs_dir: str) -> List[str]:
    """Kayıtlı config dosyalarını listeler."""
    if not os.path.exists(configs_dir):
        return []
    return sorted([f for f in os.listdir(configs_dir) if f.endswith(".json")])


def save_config(problems_names: List[str], algo_names: List[str],
                settings: Dict[str, Any], configs_dir: str,
                param_overrides: Optional[Dict] = None) -> str:
    """Seçimleri JSON config olarak kaydeder."""
    os.makedirs(configs_dir, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    scope = "_".join(problems_names[:3])
    if len(problems_names) > 3:
        scope += f"_and{len(problems_names) - 3}more"
    filename = f"{ts}_{scope}.json"
    filepath = os.path.join(configs_dir, filename)
    config = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "problems": problems_names,
        "algorithms": algo_names,
        "settings": settings,
    }
    if param_overrides:
        config["param_overrides"] = param_overrides
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    return filepath


def load_config(filepath: str) -> Optional[Dict[str, Any]]:
    """Config dosyasını yükler ve doğrular."""
    if not os.path.exists(filepath):
        print(f"[HATA] Config bulunamadi: {filepath}")
        return None
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            config = json.load(f)
    except json.JSONDecodeError as e:
        print(f"[HATA] JSON hatasi: {e}")
        return None
    if not isinstance(config, dict) or "version" not in config:
        print("[HATA] Gecersiz config formati")
        return None
    return config


def save_convergence_history(best_params: Dict[str, Dict[str, Any]],
                             histories_dir: str) -> None:
    """Yakınsama profillerini kaydeder."""
    histories: Dict[str, Any] = {}
    for key, entry in best_params.items():
        profile = entry.get("per_run_lengths") or entry.get("convergence_profile")
        if profile:
            histories[key] = {
                "problem": entry.get("problem"),
                "strategy": entry.get("strategy"),
                "avg_length": entry.get("avg_length"),
                "avg_gap": entry.get("avg_gap"),
                "convergence_profile": profile,
            }
    if histories:
        os.makedirs(histories_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join(histories_dir, f"convergence_{ts}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(histories, f, indent=2, ensure_ascii=False)
        print(f"[SAVED] Yakinsama gecmisi: {path}")


# ── Çeşitlilik Ölçümü ───────────────────────────────────────────────────────

def compute_population_diversity(
    population: list,
    n_cities: int,
    sample_size: int = 0,
) -> float:
    """
    Popülasyondaki bireylerin ortalama çeşitliliğini ölçer.
    B3 (Dinamik √n örnekleme) ve B10 (DRY) gereği merkezi fonksiyon.
    """
    pop_size = len(population)
    if pop_size < 2 or n_cities < 2:
        return 1.0
    if sample_size <= 0:
        sample_size = min(pop_size, int(math.sqrt(pop_size)) + 1)
    sample_size = min(sample_size, pop_size)

    total_dist = 0.0
    pair_count = 0
    for i in range(sample_size):
        for j in range(i + 1, sample_size):
            shared = sum(
                1 for k in range(n_cities)
                if population[i][(k + 1) % n_cities] == population[j][(k + 1) % n_cities]
            )
            total_dist += 1.0 - shared / n_cities
            pair_count += 1
    return total_dist / pair_count if pair_count > 0 else 1.0


# ── Kategori Sınıflandırma ───────────────────────────────────────────────────

def categorize_dimension(n: int) -> str:
    """Problem boyutuna göre kategori belirler."""
    if n <= 100:
        return "small"
    if n <= 500:
        return "medium"
    return "large"


def stdev_safe(vals: List[float]) -> float:
    """Güvenli standart sapma (n<2 için 0.0)."""
    return statistics.stdev(vals) if len(vals) >= 2 else 0.0


# ── Shared Infrastructure (consumed by all engines) ──────────────────────────

def resolve_dist_matrix(
    problem_name: str,
    db_path: str,
    dimension: Optional[int] = None,
) -> Optional[object]:
    """Load correct distance matrix from TSPLib DB cache.
    Handles all edge weight types (EUC_2D, GEO, ATT, CEIL_2D, EXPLICIT/ATSP).

    Args:
        problem_name: TSPLIB problem name (e.g. burma14, eil51)
        db_path: Path to tsplib.db
        dimension: If provided, validates matrix dimension matches

    Returns:
        numpy int32 array (n, n) on cache hit, None on miss
    """
    try:
        from academic_benchmark.tsplib_manager import get_distance_matrix as _dm
        matrix = _dm(problem_name, db_path)
        if matrix is not None and dimension is not None and len(matrix) != dimension:
            return None
        return matrix
    except Exception:
        return None


def validate_param_value(key: str, value_str: str, sample_type: type) -> Optional[object]:
    """Validate and convert a single parameter value string.
    Returns converted value or None on error.
    """
    try:
        if sample_type == bool:
            return value_str.lower() in ("true", "t", "1", "yes", "e", "evet")
        if sample_type == int:
            return int(value_str)
        if sample_type == float:
            return float(value_str)
        return value_str
    except (ValueError, TypeError):
        return None


def parse_param_list(val_str: str, current_list: List) -> List:
    """Parse a comma-separated parameter value string into a typed list.
    Like bildiri2026 Stage 1: user enters '10,20,50' → [10, 20, 50].
    Returns current_list if val_str is empty.
    """
    if not val_str.strip():
        return current_list
    parts = [x.strip() for x in val_str.split(",")]
    sample_type = type(current_list[0]) if current_list else str
    result = []
    for p in parts:
        v = validate_param_value("", p, sample_type)
        if v is not None:
            result.append(v)
    return result if result else current_list


def save_tuning_params_and_solution(
    problem_name: str,
    algorithm: str,
    params: Dict[str, Any],
    tour: List[int],
    tour_length: float,
    gap: float,
    db_path: str,
) -> int:
    """Save tuning params + best solution to the best_solutions table.
    Returns entry id.
    """
    try:
        from academic_benchmark.tsplib_manager import save_best_solution as _save
        return _save(problem_name, algorithm, params, tour, tour_length, gap, db_path)
    except Exception:
        return -1


def load_best_params(
    problem_name: str,
    algorithm: str,
    db_path: str,
) -> Optional[Dict[str, Any]]:
    """Load best known params for (problem, algorithm) from best_solutions table.
    Returns params dict or None.
    """
    try:
        from academic_benchmark.tsplib_manager import get_best_solution as _load
        entry = _load(problem_name, algorithm, db_path)
        return entry["params"] if entry else None
    except Exception:
        return None
