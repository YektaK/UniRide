"""Yeniden üretim paketinin tek giriş noktası.

Kullanım (paket kökünden):  python surucu/calistir.py <adim> [--isci N] [--sure S]
Adımlar:
  dogrula     nihai belgedeki sayıları arşiv dosyalarından yeniden hesaplar (dakikalar içinde)
  dalga       228 dalga hücresini WAVE-EXACT ile yeniden çözer (N işçi; S = HiGHS süre sınırı)
  cozum2      OPTIMAL olmayan dalga hücrelerini iki aşamalı HiGHS ile yeniden çözer
  gun         ortak gün modelini (DAY-JOINT) 20 hücrede yeniden çözer (~25-40 dk; bellek korumalı)
  gun_tablo   gün tablosu: GA filosu, sıralı plan, LB0, ortak planın bağımsız denetimi
  lodo        öğrenme tablolarını (LODO) yeniden üretir
  tsp_test    hızlı yerel arama sözleşme testleri (test_contracts.py)
  karsilastir yeniden koşu çıktılarını arşivle karşılaştırır
  hepsi       dogrula, dalga, cozum2, gun, gun_tablo, lodo, karsilastir (sırayla)
Ortam değişkeni UNIRIDE_ROOT verilmezse depo kökü paket konumundan bulunur.
"""
import os, sys, glob, json, subprocess, argparse
HERE = os.path.dirname(os.path.abspath(__file__)); PKG = os.path.dirname(HERE); SRC = os.path.join(PKG, "src")
sys.path.insert(0, SRC)
import run_waves as RW
DATA = os.path.join(RW.ROOT, "docs", "paper", "results", "week-2026-10-05-4sw5so")
ARCH = os.path.join(os.path.dirname(PKG), "nihai_kanit_arsivi_2026-10-17")
CK = os.path.join(PKG, "ciktilar"); os.makedirs(CK, exist_ok=True)
PY = sys.executable


def run(args, log=None):
    print(">>", " ".join(args), flush=True)
    if log:
        with open(log, "w", encoding="utf-8") as fh: return subprocess.run([PY, "-u"] + args, cwd=PKG, stdout=fh, stderr=subprocess.STDOUT).returncode
    return subprocess.run([PY, "-u"] + args, cwd=PKG).returncode


def dalga(nw, tl):
    os.makedirs(os.path.join(CK, "log"), exist_ok=True)
    ps = [subprocess.Popen([PY, "-u", os.path.join(SRC, "run_waves.py"), DATA, os.path.join(CK, f"wave_exact_rerun_w{w}.jsonl"), str(w), str(nw), str(tl)],
                           cwd=PKG, stdout=open(os.path.join(CK, "log", f"dalga_w{w}.log"), "a", encoding="utf-8"), stderr=subprocess.STDOUT) for w in range(nw)]
    for p in ps: p.wait()
    recs = {}
    for f in sorted(glob.glob(os.path.join(CK, "wave_exact_rerun_w*.jsonl"))):
        for l in open(f, encoding="utf-8"): r = json.loads(l); recs[r["job_key"]] = r
    with open(os.path.join(CK, "wave_exact_rerun.jsonl"), "w", encoding="utf-8") as fh:
        for r in recs.values(): fh.write(json.dumps(r) + "\n")
    print(len(recs), "hücre birleştirildi")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("adim"); ap.add_argument("--isci", type=int, default=2); ap.add_argument("--sure", type=float, default=120.0)
    a = ap.parse_args(); steps = ["dogrula", "dalga", "cozum2", "gun", "gun_tablo", "lodo", "karsilastir"] if a.adim == "hepsi" else [a.adim]
    for s in steps:
        if s == "dogrula": run([os.path.join(HERE, "dogrula.py"), ARCH, DATA])
        elif s == "dalga": dalga(a.isci, a.sure)
        elif s == "cozum2": run([os.path.join(HERE, "resolve_two_stage.py"), DATA, os.path.join(CK, "wave_exact_rerun.jsonl"), os.path.join(CK, "wave_exact_rerun_resolved.jsonl")])
        elif s == "gun": run([os.path.join(HERE, "bellek_korumali.py"), os.path.join(SRC, "run_day_joint.py"), DATA, os.path.join(CK, "day_joint_rerun.jsonl")])
        elif s == "gun_tablo": run([os.path.join(HERE, "gun_duzeyi.py"), DATA, os.path.join(CK, "wave_exact_rerun_resolved.jsonl"), os.path.join(CK, "day_joint_rerun.jsonl"), os.path.join(CK, "gun")])
        elif s == "lodo": run([os.path.join(HERE, "run_lodo.py"), DATA, os.path.join(ARCH, "uretim_dalga_gun", "sonuc", "wave_exact_4sw5so.jsonl"), os.path.join(CK, "lodo")])
        elif s == "tsp_test": run([os.path.join(SRC, "test_contracts.py")], log=os.path.join(CK, "tsp_test.log"))
        elif s == "karsilastir": run([os.path.join(HERE, "karsilastir.py"), CK, ARCH])
        else: sys.exit("bilinmeyen adım: " + s)
