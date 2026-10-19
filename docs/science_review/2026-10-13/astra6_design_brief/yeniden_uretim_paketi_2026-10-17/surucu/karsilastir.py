"""Yeniden koşu çıktılarını arşivdeki sonuçlarla karşılaştırır.

Kullanım: python karsilastir.py [ciktilar_klasoru] [arsiv_klasoru]
Bulunan çıktıları karşılaştırır (olmayan bölüm atlanır):
  ciktilar/wave_exact_rerun_resolved.jsonl  <->  arşiv wave_exact_vs_ga.csv (rota sayısı, dakika, durum)
  ciktilar/day_joint_rerun.jsonl             <->  arşiv day_joint_4sw5so.jsonl (K, rota, dakika, aşama durumları)
  ciktilar/lodo/*.csv                        <->  arşiv lodo_metrics.csv, recall_at_k.csv, construct_learned_vs_cw.csv
"""
import os, sys, json, glob
import numpy as np, pandas as pd
HERE = os.path.dirname(os.path.abspath(__file__)); PKG = os.path.dirname(HERE)
CK = sys.argv[1] if len(sys.argv) > 1 else os.path.join(PKG, "ciktilar")
ARCH = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(PKG), "nihai_kanit_arsivi_2026-10-17")
U, O = os.path.join(ARCH, "uretim_dalga_gun", "sonuc"), os.path.join(ARCH, "ogrenme_oruntu", "sonuc")
rows = []
def add(bolum, olcu, deger, not_=""): rows.append(dict(bolum=bolum, olcu=olcu, deger=deger, not_=not_)); print(bolum, "|", olcu, "|", deger, "|", not_)
def jl(p): return [json.loads(l) for l in open(p, encoding="utf-8")]

wp = os.path.join(CK, "wave_exact_rerun_resolved.jsonl")
if os.path.exists(wp):
    new = pd.DataFrame(jl(wp)).drop_duplicates("job_key", keep="last"); old = pd.read_csv(os.path.join(U, "wave_exact_vs_ga.csv"))
    m = old.merge(new, on="job_key", suffixes=("_a", "_y"))
    same = (m.ex_routes_a == m.ex_routes_y) & (m.ex_dur_a == m.ex_dur_y)
    add("dalga", "karşılaştırılan hücre", len(m), f"arşivde {len(old)}")
    add("dalga", "rota ve dakika aynı", int(same.sum()))
    add("dalga", "yeni koşuda OPTIMAL", int((m.status_y == "OPTIMAL").sum()), str(m.solver_y.value_counts().to_dict()))
    add("dalga", "sertifika ihlali (yeni)", int(m.cert_violations_y.sum()))
    for _, r in m[~same].iterrows(): add("dalga", "FARK " + r.job_key, f"arşiv {r.ex_routes_a}/{r.ex_dur_a} yeni {r.ex_routes_y}/{r.ex_dur_y}", r.status_y)

dp = os.path.join(CK, "day_joint_rerun.jsonl")
if os.path.exists(dp):
    new = pd.DataFrame(jl(dp)); old = pd.DataFrame(jl(os.path.join(U, "day_joint_4sw5so.jsonl")))
    m = old.merge(new, on=["date", "R"], suffixes=("_a", "_y"))
    cols = ["K", "routes", "minutes", "s1", "s2", "s3"]
    eq = np.ones(len(m), bool)
    for c in cols: eq &= (m[c + "_a"].fillna(-1).values == m[c + "_y"].fillna(-1).values)
    add("gün", "karşılaştırılan hücre", len(m), f"arşivde {len(old)}")
    add("gün", "K, rota, dakika ve aşama durumları aynı", int(eq.sum()))
    for _, r in m[~eq].iterrows():
        add("gün", f"FARK {r.date} R{r.R}", "arşiv " + str({c: r[c + '_a'] for c in cols}) + " yeni " + str({c: r[c + '_y'] for c in cols}))

lp = os.path.join(CK, "lodo", "lodo_metrics.csv")
if os.path.exists(lp):
    a = pd.read_csv(os.path.join(O, "lodo_metrics.csv")); b = pd.read_csv(lp)
    m = a.merge(b, on=["hedef", "n_min", "model"], suffixes=("_a", "_y"), how="outer", indicator=True)
    add("öğrenme", "lodo_metrics satır (ortak / yalnız arşiv / yalnız yeni)", str(m._merge.value_counts().to_dict()))
    for c in ["AUC", "AP", "taban_orani", "dogruluk", "n_cift"]:
        d = (m[c + "_a"] - m[c + "_y"]).abs(); add("öğrenme", f"lodo_metrics en büyük |fark| {c}", float(d.max()) if d.notna().any() else "yok")
    a = pd.read_csv(os.path.join(O, "recall_at_k.csv")); b = pd.read_csv(os.path.join(CK, "lodo", "recall_at_k.csv"))
    m = a.merge(b, on="model", suffixes=("_a", "_y"))
    add("öğrenme", "recall@k en büyük |fark|", float(max((m[f"recall@{k}_a"] - m[f"recall@{k}_y"]).abs().max() for k in range(1, 6))), f"{len(m)} model")
    a = pd.read_csv(os.path.join(O, "construct_learned_vs_cw.csv")); b = pd.read_csv(os.path.join(CK, "lodo", "construct_learned_vs_cw.csv"))
    m = a.merge(b, on=["key", "method", "reseq"], suffixes=("_a", "_y"))
    add("öğrenme", "yapıcı: aynı rota ve dakika", f"{int(((m.routes_a == m.routes_y) & (m.dur_a == m.dur_y)).sum())}/{len(m)}", f"arşivde {len(a)}")

out = os.path.join(CK, "karsilastirma_raporu.csv"); pd.DataFrame(rows).to_csv(out, index=False, encoding="utf-8"); print("yazıldı:", out)
