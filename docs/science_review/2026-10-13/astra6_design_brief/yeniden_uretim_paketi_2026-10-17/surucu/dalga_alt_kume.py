"""run_waves.main'i belirli hücreleri atlayarak çalıştırır (bellek yetmeyen hücreler için). milp bellek korumalıdır.
Kullanım: python dalga_alt_kume.py <veri> <cikti_jsonl> <isci> <isci_sayisi> <sure> [atlanacak_anahtar1,anahtar2,...]
"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))
import scipy.optimize as so
from scipy.optimize import OptimizeResult
_orig = so.milp
def milp_korumali(*a, **k):
    try: return _orig(*a, **k)
    except MemoryError:
        print("[bellek_korumali] HiGHS MemoryError -> status=-9", flush=True)
        return OptimizeResult(x=None, fun=None, status=-9, success=False, message="MemoryError")
so.milp = milp_korumali
import run_waves
atla = set(sys.argv[6].split(",")) if len(sys.argv) > 6 and sys.argv[6] else set()
_lw = run_waves.load_waves
run_waves.load_waves = lambda D: [w for w in _lw(D) if f'{w["job"]}|R{w["R"]}' not in atla]
run_waves.main(sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), float(sys.argv[5]))
