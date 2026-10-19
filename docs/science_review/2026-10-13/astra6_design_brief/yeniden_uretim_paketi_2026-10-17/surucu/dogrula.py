"""Nihai belgedeki (NIHAI_BIRLESIK_BULGULAR_VE_YOL_HARITASI_2026-10-17_ClaudeScience.md) sayıları arşivdeki ham dosyalardan
yeniden hesaplar ve belgede yazan değerle karşılaştırır.

Kullanım: python dogrula.py [arsiv_klasoru] [veri_klasoru] [cikti_csv]
Varsayılanlar: ../../nihai_kanit_arsivi_2026-10-17, depo kökü/docs/paper/results/week-2026-10-05-4sw5so, ../ciktilar/dogrulama_raporu.csv
"""
import os, sys, json, math
import numpy as np, pandas as pd
from scipy.stats import wilcoxon
HERE = os.path.dirname(os.path.abspath(__file__)); PKG = os.path.dirname(HERE); sys.path.insert(0, os.path.join(PKG, "src"))
import run_waves as RW

ARCH = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(PKG), "nihai_kanit_arsivi_2026-10-17")
DATA = sys.argv[2] if len(sys.argv) > 2 else os.path.join(RW.ROOT, "docs", "paper", "results", "week-2026-10-05-4sw5so")
OUTF = sys.argv[3] if len(sys.argv) > 3 else os.path.join(PKG, "ciktilar", "dogrulama_raporu.csv")
U, T_, O = (os.path.join(ARCH, g, "sonuc") for g in ("uretim_dalga_gun", "tsp_hizli_ls", "ogrenme_oruntu"))
Q = os.path.join(ARCH, "uclu_kiyas_e2bso_r2dma_paoea", "sonuc")
rows = []


def chk(cid, desc, value, expected, tol=0.0):
    if isinstance(expected, (list, tuple)):
        ok = len(value) == len(expected) and all(abs(float(a) - float(b)) <= tol for a, b in zip(value, expected))
    elif isinstance(expected, str):
        ok = str(value) == expected
    else:
        ok = abs(float(value) - float(expected)) <= tol
    rows.append(dict(id=cid, aciklama=desc, hesaplanan=str(value), belgede=str(expected), tolerans=tol, sonuc="GEÇTİ" if ok else "KALDI"))


def jl(p): return [json.loads(l) for l in open(p, encoding="utf-8")]
def wtl(a, b): a, b = [tuple(int(x) for x in s.split("/")) for s in (a, b)]; return "w" if a < b else ("t" if a == b else "l")

# --- §2 veri ---
waves = RW.load_waves(DATA)
by_job = {}
for w in waves: by_job.setdefault(w["job"], set()).add(tuple(sorted(w["occ"])))
chk("§2a", "temel dalga sayısı", len(by_job), 57)
chk("§2b", "4 R'de yolcu kümesi aynı olan temel dalga", sum(len(v) == 1 for v in by_job.values()), 57)
stops = {RW.loc_of(o) for w in waves for o in w["occ"]}
chk("§2c", "farklı durak sayısı", len(stops), 28)
mj = json.load(open(os.path.join(DATA, "2026-10-05_R60_repeat1.matrix.json"), encoding="utf-8"))
dm = [a["duration_minutes"] for a in mj["arcs"]]
chk("§2d", "örnek matris yay sayısı / tamsayı / en büyük", (len(dm), int(all(float(x).is_integer() for x in dm)), max(dm)), (756, 1, 57))

# --- §3 üretim ---
G = pd.read_csv(os.path.join(U, "wave_exact_vs_ga.csv")); raw = pd.DataFrame(jl(os.path.join(U, "wave_exact_4sw5so.jsonl")))
chk("U1a", "OPTIMAL hücre (birleşik kayıt)", int((G.status == "OPTIMAL").sum()), 228)
chk("U1b", "sertifika ihlali toplamı", int(G.cert_violations.sum()), 0)
chk("U1c", "en uzun sayım süresi (s)", round(G.t_enum.max(), 2), 8.64)
chk("U1d", "en büyük kolon sayısı", int(G.n_columns.max()), 45170)
chk("U1e", "ham kayıt: highs OPTIMAL / cpsat FEASIBLE", (int(((raw.solver == "highs") & (raw.status == "OPTIMAL")).sum()), int(((raw.solver == "cpsat") & (raw.status == "FEASIBLE")).sum())), (226, 2))
chk("U1f", "iki aşamalı yeniden çözülen hücre", int((G.solver == "highs-2stage").sum()), 2)
chk("§2e", "n>=6 hücre / temel dalga", (int((G.n >= 6).sum()), G[G.n >= 6].job.nunique()), (36, 9))
sub = (G.d_routes > 0) | (G.d_min > 0)
chk("U2a", "GA suboptimal hücre / temel dalga", (int(sub.sum()), G[sub].job.nunique()), (19, 7))
chk("U2b", "GA fazla rotalı hücre / temel dalga", (int((G.d_routes > 0).sum()), G[G.d_routes > 0].job.nunique()), (4, 2))
S = pd.read_csv(os.path.join(U, "wave_summary_by_R.csv")).set_index("R")
chk("U2c", "haftalık dakika farkı R=50/60/70/90", list(S.dk_farki), [19, 81, 25, 49])
chk("U2d", "haftalık fazla rota (her R)", list(S.ga_rota - S.kesin_rota), [1, 1, 1, 1])
E = pd.DataFrame(jl(os.path.join(U, "esn_real_v2.jsonl"))).merge(G[["job_key", "ex_routes", "ex_dur"]], left_on="key", right_on="job_key")
chk("U3", "ESN-SP v2 optimum hücre", int(((E.esn_routes == E.ex_routes) & (E.esn_dur == E.ex_dur)).sum()), 227)
SC = pd.read_csv(os.path.join(U, "scale_esn_vs_ga.csv")); EL = pd.read_csv(os.path.join(O, "esn_learned_vs_geo.csv"))
m = SC.merge(EL, left_on="ornek", right_on="örnek")
chk("U4a", "ESN-SP v3 iki koşuda aynı sonuç (15 örnek)", int((m.v3 == m.v3_geo).sum()), 12)
s2 = SC[SC.grup == "S2"]; s2b = m[m.grup_x == "S2"]
chk("U4b", "S2 koşu 1 kazanç/beraberlik/kayıp", tuple(sum(wtl(a, b) == k for a, b in zip(s2.v3, s2.ga_eq)) for k in "wtl"), (5, 0, 0))
chk("U4c", "S2 koşu 2 kazanç/beraberlik/kayıp", tuple(sum(wtl(a, b) == k for a, b in zip(s2b.v3_geo, s2b.ga_eq)) for k in "wtl"), (4, 0, 1))
DL = pd.read_csv(os.path.join(U, "day_level_4sw5so.csv")); WF = pd.read_csv(os.path.join(U, "weekly_fleet_4sw5so.csv")).set_index("R")
chk("U5", "sıralı kesin plan GA'dan az araç (hücre)", int((DL.ga_fleet > DL.seq_fleet).sum()), 2)
chk("U6a", "haftalık filo ortak R=50/60/70/90", list(WF.joint_fleet), [6, 5, 5, 4])
chk("U6b", "haftalık filo sıralı / GA", list(WF.seq_fleet) + list(WF.ga_fleet), [6, 6, 6, 4, 6, 6, 6, 4])
chk("U6c", "ortak < sıralı (hücre)", int((DL.joint_K < DL.seq_fleet).sum()), 9)
chk("U6d", "ortak < GA (hücre)", int((DL.ga_fleet > DL[["joint_K", "seq_fleet"]].min(axis=1)).sum()), 11)
DJ = pd.DataFrame(jl(os.path.join(U, "day_joint_4sw5so.jsonl")))
full = (DJ.s1 == 0) & (DJ.s2 == 0) & (DJ.s3 == 0)
chk("U6e", "üç aşaması OPTIMAL hücre", int(full.sum()), 19)
mon = DJ[(DJ.date == "2026-10-05") & (DJ.R == 90)].iloc[0]
chk("U6f", "Pazartesi R=90 s1 durumu / sıralı=LB0=3", (int(mon.s1), int(DL[(DL.date == "2026-10-05") & (DL.R == 90)].seq_fleet.iloc[0]), int(DL[(DL.date == "2026-10-05") & (DL.R == 90)].lb0.iloc[0])), (1, 3, 3))
mm = DL.dropna(subset=["joint_routes"]).assign(dr=lambda x: x.joint_routes - x.seq_routes, dmn=lambda x: x.joint_min - x.seq_min).groupby("R")
chk("U7a", "ortak - sıralı rota R=50/60/70/90", list(mm.dr.sum()), [3, 1, 4, 2])
chk("U7b", "ortak - sıralı dakika", list(mm.dmn.sum()), [47, 30, 86, 31])
chk("U7c", "haftalık dakika ortak (Pzt R90 sıralı)", list(DL.assign(j=DL.joint_min.fillna(DL.seq_min)).groupby("R").j.sum()), [6850, 6399, 6114, 5844])
chk("U7d", "haftalık dakika sıralı", list(DL.groupby("R").seq_min.sum()), [6803, 6369, 6028, 5813])
chk("U8", "LB0'a eşit: sıralı / ortak", (int((DL.seq_fleet == DL.lb0).sum()), int((DL.joint_K == DL.lb0).sum())), (4, 6))
TY = pd.read_csv(os.path.join(U, "weekly_typed_vs_campaign.csv")); t3 = TY[TY.L == 3]
chk("U9", "L=3 haftalık sedan kesin + kampanya", list(t3.kesin_haftalik_sedan) + list(t3.kampanya_haftalik_sedan), [3, 2, 2, 1, 4, 3, 3, 1])

# --- §4 TSP ---
BW = pd.read_csv(os.path.join(Q, "bench_wilcoxon.csv")).set_index(["a", "b"]); BS = pd.read_csv(os.path.join(Q, "bench_summary_overall.csv")).set_index("arm")
chk("T1a", "R2DMA ILS'ten kötü (çift) / Holm p", (int(BW.loc[("R2DMA", "ILS")].b_better), round(BW.loc[("R2DMA", "ILS")].holm_p, 6)), (27, 0.000156), 1e-6)
chk("T1b", "E2BSO-ILS kazanç/beraberlik/kayıp", tuple(int(BW.loc[("E2BSO", "ILS")][c]) for c in ("a_better", "ties", "b_better")), (8, 6, 16))
chk("T1c", "P-AOEA = P-AOEA-noevo (beraberlik)", int(BW.loc[("P-AOEA", "P-AOEA-noevo")].ties), 30)
chk("T1d", "LKH optimum", int(BS.loc["LKH"].opt_hits), 30)
MS = pd.read_csv(os.path.join(T_, "main_summary.csv")); al = MS[MS.inst == "ALL"].set_index("arm")
chk("T2a", "ILS-fast optimum / ortalama açık %", (int(al.loc["ils_fast"].n_opt), round(al.loc["ils_fast"].mean_gap, 3)), (36, 0.058), 1e-9)
chk("T2b", "repo ILS optimum (40) / ortalama açık %", (int(al.loc["repo_ils"].n_opt), round(al.loc["repo_ils"].mean_gap, 2)), (15, 2.02), 1e-9)
MW = pd.read_csv(os.path.join(T_, "main_wilcoxon.csv")).set_index("comparison")
r0 = MW.loc["ils_fast vs repo_ils"]
chk("T2c", "ILS-fast vs repo ILS koşu düzeyi k/b/k", (int(r0.wins_ref), int(r0.ties), int(r0.losses_ref)), (25, 15, 0))
chk("T2d", "Holm p (koşu düzeyi)", round(r0.p_holm, 6), 0.000024, 1e-6)
per = MW[MW.index.str.startswith("ils_fast vs repo_ils [")]
chk("T2e", "örnek düzeyi: daha iyi / eşit / kötü", (int((per.mean_diff_gap_pct < 0).sum()), int((per.mean_diff_gap_pct == 0).sum()), int((per.mean_diff_gap_pct > 0).sum())), (6, 2, 0))
pl = MW[MW.index.str.startswith("ils_fast vs lkh [")]
chk("T2f", "LKH'ye kayıp koşu (hepsi n>=318 örnekte)", (int(pl.losses_ref.sum()), int(pl[pl.losses_ref > 0].index.str.contains("lin318|pr439|rat783|pr1002").all())), (14, 1))
AS = pd.read_csv(os.path.join(T_, "atsp_summary.csv")).set_index("arm")
chk("T3", "ft53 ILS-fast optimum koşu", (int(AS.loc["ils_fast"].n_opt), int(AS.loc["ils_fast"].runs)), (10, 10))
GW = pd.read_csv(os.path.join(T_, "gpx_wilcoxon.csv")).set_index("comparison"); g0 = GW.loc["px_on vs px_off"]
chk("T5", "GPX açık-kapalı k/b/k ve p", (int(g0.wins_ref), int(g0.ties), int(g0.losses_ref), round(g0.p, 3)), (7, 5, 8, 0.776), 1e-9)
TC = pd.read_csv(os.path.join(O, "tsp_learned_cands.csv")); pg = TC.pivot_table(index=["inst", "seed"], columns="arm", values="gap")
d_ = pg["U+3NN"] - pg["K10"]; nz = d_[d_.abs() > 1e-12]
chk("T6a", "U+3NN vs K10 k/b/k", (int((d_ < 0).sum()), int((d_.abs() <= 1e-12).sum()), int((d_ > 0).sum())), (11, 1, 8))
chk("T6b", "U+3NN vs K10 Wilcoxon p (açık ölçeği)", round(wilcoxon(nz).pvalue, 2), 0.79, 1e-9)
d5 = pg["K5"] - pg["K10"]
chk("T6c", "K5 vs K10 k/b/k", (int((d5 < 0).sum()), int((d5.abs() <= 1e-12).sum()), int((d5 > 0).sum())), (4, 1, 15))
LS = json.load(open(os.path.join(O, "landscape.json"), encoding="utf-8"))
chk("T7", "tüm elitlerde ortak kenar = optimumdaki", [LS[k]["backbone_in_opt"] for k in ("rd100", "pr136", "a280", "lin318")], [44, 27, 42, 133])
chk("T7b", "ortak kenar sayısı", [LS[k]["backbone_n"] for k in ("rd100", "pr136", "a280", "lin318")], [44, 27, 42, 133])

# --- §5 öğrenme ---
LM = pd.read_csv(os.path.join(O, "lodo_metrics.csv")); a6 = LM[(LM.hedef == "ardil_yay") & (LM.n_min == 6)].set_index("model").AUC.round(3)
chk("O1a", "ardıl yay AUC: GBM-geo, LR-geo, MUTUAL, DETOUR, GEO, FREQ", [a6[k] for k in ("GBM-geo", "LR-geo", "MUTUAL-RANK", "DETOUR", "GEO", "FREQ")], [0.909, 0.893, 0.855, 0.807, 0.764, 0.714], 1e-9)
s6 = LM[(LM.hedef == "ayni_rota") & (LM.n_min == 6)].set_index("model").AUC.round(3)
chk("O1b", "aynı rota AUC: GBM-geo, GEO", [s6["GBM-geo"], s6["GEO"]], [0.812, 0.719], 1e-9)
RK = pd.read_csv(os.path.join(O, "recall_at_k.csv")).set_index("model")
chk("O1c", "Recall@5: MUTUAL, GBM-geo, GEO / ardıl sayısı", [RK.loc["MUTUAL-RANK", "recall@5"], RK.loc["GBM-geo", "recall@5"], RK.loc["GEO", "recall@5"], RK.n_ardil.iloc[0]], [0.956, 0.944, 0.896, 270], 1e-9)
FC_ = pd.read_csv(os.path.join(O, "forward_chaining_auc.csv")); fa = FC_[FC_.hedef == "ardil_yay"]
chk("O2", "ileri zincirleme GBM-geo min/max ve 4/4 gün üstün", [round(fa.GBM_geo.min(), 3), round(fa.GBM_geo.max(), 3), int(((fa.GBM_geo > fa.GEO) & (fa.GBM_geo > fa.MUTUAL_RANK)).sum())], [0.863, 0.921, 4], 1e-9)
p6 = LM[(LM.hedef == "oncelik") & (LM.n_min == 6)].set_index("model").dogruluk
chk("O3", "öncelik doğruluğu LR-geo/RADIAL/FREQ", [p6["LR-geo"], p6["RADIAL"], p6["FREQ"]], [0.779, 0.720, 0.620], 1e-9)
CW = pd.read_csv(os.path.join(O, "construct_learned_vs_cw.csv")); c6 = CW[(CW.n >= 6) & (CW.reseq)].groupby("method").d_routes.sum()
chk("O4", "fazla rota: öğrenilmiş GBM-geo / CW (yeniden sıralamalı)", [int(c6["learned-GBM-geo"]), int(c6["CW-savings"])], [9, 3])
PS = pd.read_csv(os.path.join(O, "prune_learned_arcs_summary.csv"))
gb = PS[(PS["mode"] == "arc") & (PS.method == "GBM-geo") & (PS.k == 4)].iloc[0]; ge = PS[(PS["mode"] == "arc") & (PS.method == "GEO") & (PS.k == 4)].iloc[0]
chk("O5a", "GBM-geo k=4: optimum/36, rota/36, kolon payı", [round(gb.opt_ok * 36), round(gb.route_ok * 36), round(gb.col_frac, 2)], [30, 36, 0.22], 1e-9)
chk("O5b", "GEO k=4: optimum/36, rota/36, kolon payı", [round(ge.opt_ok * 36), round(ge.route_ok * 36), round(ge.col_frac, 2)], [27, 34, 0.32], 1e-9)
PA = pd.read_csv(os.path.join(O, "prune_learned_arcs_all.csv")); s = PA[(PA["mode"] == "arc") & (PA.method == "GBM-geo") & (PA.k == 4)].copy()
s["job"] = s.key.str.split("|").str[0]; bw = s.groupby("job").opt_ok.agg(["sum", "count"])
chk("O5c", "temel dalga düzeyi tam optimum / toplam fark dk / en büyük fark", [int((bw["sum"] == bw["count"]).sum()), int(s.gap_min.sum()), int(s.gap_min.max())], [5, 13, 5])
chk("O6", "v3L vs v3 öğrenilmiş iyi / eşit / mesafe iyi", [int((EL.sonuç == "öğrenilmiş iyi").sum()), int((EL.sonuç == "eşit").sum()), int((EL.sonuç == "mesafe iyi").sum())], [5, 5, 5])

# --- §6 ---
chk("S1", "alt küme / sıralı dizi (n=20, en çok 9)", (sum(math.comb(20, k) for k in range(1, 10)), sum(math.perm(20, k) for k in range(1, 10))), (431909, 66449027200))
chk("S3", "n*T < W (dakika)", int(20 * 150 < 10000), 1)

R = pd.DataFrame(rows); os.makedirs(os.path.dirname(OUTF), exist_ok=True); R.to_csv(OUTF, index=False, encoding="utf-8")
print(R.sonuc.value_counts().to_dict())
for _, r in R[R.sonuc != "GEÇTİ"].iterrows(): print("KALDI", r.id, r.aciklama, r.hesaplanan, "belgede", r.belgede)
