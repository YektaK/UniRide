"""Bellek korumalı çalıştırıcı: bir betiği değiştirmeden çalıştırır; scipy.optimize.milp içinde MemoryError olursa
çözümü durum kodu -9 ile "çözülemedi" olarak döndürür. Böylece betik çökmez, sonraki hücreye geçer.
run_waves.py'de bu durum özgün koddaki CP-SAT geri dönüşünü tetikler; run_day_joint.py'de hücre s1=-9 ile kaydedilir.
Kullanım: python bellek_korumali.py <betik.py> [betik argümanları...]
"""
import sys, runpy
import scipy.optimize as so
from scipy.optimize import OptimizeResult
_orig = so.milp

def milp_korumali(*a, **k):
    try:
        return _orig(*a, **k)
    except MemoryError:
        print("[bellek_korumali] HiGHS MemoryError -> status=-9", flush=True)
        return OptimizeResult(x=None, fun=None, status=-9, success=False, message="MemoryError", mip_gap=None, mip_node_count=None, mip_dual_bound=None)

so.milp = milp_korumali
script = sys.argv[1]; sys.argv = sys.argv[1:]
runpy.run_path(script, run_name="__main__")
