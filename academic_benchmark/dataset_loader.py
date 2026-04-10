import os
import sys
import math
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass

# Klasik test arraylerini alarak devasa koordinat çöplüğünden kaçınıyoruz
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Önce v2'yi dene (gerçek TSPLIB koordinatları), yoksa v1 veya fallback
try:
    from optimizer_api.tests.run_interactive_benchmark_v2 import (
        TSPLIBProblem, TSPLIB_PROBLEMS, load_tsplib_problem
    )
    USE_V2 = True
except ImportError:
    try:
        from optimizer_api.tests.run_interactive_benchmark import (
            TSPLIBProblem, ALL_PROBLEMS
        )
        USE_V2 = False
        TSPLIB_PROBLEMS = None
        load_tsplib_problem = None
    except ImportError:
        @dataclass
        class TSPLIBProblem:
            name: str
            dimension: int
            optimal: int
            coordinates: List[Tuple[float, float]]
            category: str
        ALL_PROBLEMS = []
        USE_V2 = False
        TSPLIB_PROBLEMS = None
        load_tsplib_problem = None

def parse_tsp_file(filepath: str, optimal_score: int = 0) -> TSPLIBProblem:
    """Belirtilen .tsp dosyasını parse edip TSPLIBProblem objesine çevirir."""
    name = os.path.basename(filepath).replace(".tsp", "")
    dimension = 0
    coordinates = []
    
    with open(filepath, 'r', encoding='utf-8') as f:
        in_node_section = False
        for line in f:
            line = line.strip()
            if not line or line == "EOF":
                continue
                
            if line.startswith("NAME"):
                name = line.split(":")[-1].strip()
            elif line.startswith("DIMENSION"):
                dimension = int(line.split(":")[-1].strip())
            elif line.startswith("NODE_COORD_SECTION"):
                in_node_section = True
                continue
                
            if in_node_section:
                parts = line.split()
                if len(parts) >= 3:
                    try:
                        x = float(parts[1])
                        y = float(parts[2])
                        coordinates.append((x, y))
                    except ValueError:
                        pass
                        
    # Dinamik Kategori Belirlemesi
    if dimension <= 100:
        category = "small"
    elif dimension <= 500:
        category = "medium"
    else:
        category = "large"
        
    return TSPLIBProblem(
        name=name,
        dimension=dimension,
        optimal=optimal_score, 
        coordinates=coordinates,
        category=category
    )

def parse_opt_tour_file(filepath: str) -> List[int]:
    """ .opt.tour dosyasını okur ve sırayla ziyaret edilen tam sayı düğüm indekslerini döner. """
    tour = []
    with open(filepath, 'r', encoding='utf-8') as f:
        in_tour_section = False
        for line in f:
            line = line.strip()
            if not line or line == "EOF":
                continue
            if line.startswith("TOUR_SECTION"):
                in_tour_section = True
                continue
            if in_tour_section:
                try:
                    node_idx = int(line)
                    if node_idx == -1: # TSPLib standardında dosya sonu belirteci
                        break
                    tour.append(node_idx)
                except ValueError:
                    pass
    return tour

def compute_tour_length(tour: List[int], coordinates: List[Tuple[float, float]]) -> int:
    """ 
    Rota sırasını ve koordinatları alıp TSPLib EUC_2D mesafesini hesaplar.
    
    Args:
        tour: 1-based düğüm indeksleri listesi (TSPLIB standardı)
        coordinates: 0-based koordinat listesi
    
    Returns:
        Toplam tur uzunluğu (EUC_2D)
    """
    if not tour or not coordinates:
        return 0
    
    n_coords = len(coordinates)
    
    def dist(p1, p2):  # EUC 2D TSPLib standard mesafe formülü
        return int(math.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2) + 0.5)
    
    def safe_get_coord(idx: int) -> Optional[Tuple[float, float]]:
        """Güvenli koordinat erişimi - bounds checking"""
        # TSPLIB'de indeksler 1-based, Python'da 0-based
        real_idx = idx - 1 if idx > 0 else idx
        if 0 <= real_idx < n_coords:
            return coordinates[real_idx]
        return None
    
    total = 0
    
    for i in range(len(tour) - 1):
        p1 = safe_get_coord(tour[i])
        p2 = safe_get_coord(tour[i + 1])
        
        if p1 is None or p2 is None:
            print(f"[WARNING] Geçersiz indeks: tour[{i}]={tour[i]}, tour[{i+1}]={tour[i+1]} (coords: {n_coords})")
            continue
            
        total += dist(p1, p2)
    
    # Kapanış döngüsü (Son şehirden başa dönüş)
    p1 = safe_get_coord(tour[-1])
    p2 = safe_get_coord(tour[0])
    
    if p1 is not None and p2 is not None:
        total += dist(p1, p2)
    
    return total

class BenchmarkDatasetLoader:
    def __init__(self, tsplib_folder: Optional[str] = None):
        self.tsplib_folder = tsplib_folder
        
        # Eğer opt.tour dosyası bulunamazsa, buradan yedek senaryo eşleştirmesi yaparız 
        self.known_optimals = {
            "berlin52": 7542,
            "eil51": 426,
            "eil76": 538,
            "st70": 675,
            "kroA100": 21282,
            "kroC100": 20749,
            "eil101": 629,
            "lin105": 14379,
            "pr1002": 259045
        }
        
    def load_all_datasets(self) -> List[TSPLIBProblem]:
        """Sistemdeki problemleri ve klasördeki dinamik veri setlerini okur."""
        problems = {}
        
        # v2 modunda TSPLIB_PROBLEMS'den yükle
        if USE_V2 and TSPLIB_PROBLEMS:
            print("[INFO] TSPLIB problemleri v2'den yükleniyor...")
            for category, prob_list in TSPLIB_PROBLEMS.items():
                for problem_name, optimal in prob_list:
                    prob = load_tsplib_problem(problem_name, optimal, category)
                    if prob:
                        problems[prob.name] = prob
        # v1 modunda ALL_PROBLEMS'den yükle
        elif 'ALL_PROBLEMS' in dir() and ALL_PROBLEMS:
            problems = {p.name: p for p in ALL_PROBLEMS}
        
        # Klasördeki ek dosyaları da tara
        if self.tsplib_folder and os.path.exists(self.tsplib_folder):
            for filename in os.listdir(self.tsplib_folder):
                if filename.endswith(".tsp"):
                    filepath = os.path.join(self.tsplib_folder, filename)
                    name_key = filename.replace(".tsp", "")
                    
                    # 1. Yedek (Kayıtlı Optimals)
                    opt_score = self.known_optimals.get(name_key, 0)
                    if name_key in problems and problems[name_key].optimal > 0:
                        opt_score = problems[name_key].optimal
                        
                    parsed_problem = parse_tsp_file(filepath, optimal_score=opt_score)
                    
                    # 2. Asıl Hedef (opt.tour Dinamik Hesaplama Sistemi)
                    opt_tour_path = filepath.replace(".tsp", ".opt.tour")
                    if os.path.exists(opt_tour_path):
                        tour = parse_opt_tour_file(opt_tour_path)
                        dynamic_opt = compute_tour_length(tour, parsed_problem.coordinates)
                        if dynamic_opt > 0:
                            parsed_problem.optimal = dynamic_opt
                    
                    problems[parsed_problem.name] = parsed_problem
                        
        return list(problems.values())
        
    def get_by_category(self, category_list: List[str]) -> List[TSPLIBProblem]:
        """İstenen kategorideki probelemleri döner (Örn: ['small', 'medium'])"""
        all_probs = self.load_all_datasets()
        return [p for p in all_probs if p.category in category_list]
