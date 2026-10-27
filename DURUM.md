# DURUM — devam eden işler

Son güncelleme: 2026-10-27 (MT1 planı onaylandı). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir. Sahip dışarıdayken şefin aldığı kararlar: DECISION_LOG **A20** (L1–L13) ve **A21** (MT6 takip planı, OQ-F1..F8); her biri seçenekler, artı/eksi, seçim, geri alma yolu ile.

## Durum

| İş | Durum |
|---|---|
| Gate D (Paket D) | **KAPANDI** (D-13, `04612880`; kanıt `docs/superpowers/plans/2026-10-26-gate-d-mt6-close-evidence.md`; A18). Ölçüt 6'nın değer eşleşmesi ön-onay commit'ine ertelendi (A20 L11). Açık: D-04b2 (güçlü bilgisayar); D-12 yayın yalnız sahip izniyle. |
| MT6 | **KAPANDI** (MT6-07; A19). |
| MT6 takip planı (sota_common arşivi, shim'ler, denetim L3 ve L10, RUN 3-opt hamlesi) | **KAPANDI** (MT6F-09, `e8851f34`; kanıt `docs/superpowers/plans/2026-10-27-mt6-followup-close-evidence.md`; A21). Yalnız `SOTA-RUN-TSP` sonuçları değişti; Bildiri/YAEM değişmedi. |
| Makale raporu komutu, üretim çözücü kaydı, analiz cilası 1–2, birikmiş işler 1 | BİRLEŞTİ (A20 L2, L3, L7, L10, L12, L13). |
| CI: analiz testleri akademik ek paket olmadan toplanıyor | BİRLEŞTİ `13819af5` (D-04a eki; PR #27 kapatıldı). Gece işindeki `UNIRIDE_REQUIRE_ANALYSIS_EXTRA=1` ilk gece koşusunda kontrol edilecek. |
| MT1 (zaman pencereleri, okula dönüş, dürüst araç sayısı) | PLAN ONAYLANDI 2026-10-27 (O09; plan `docs/superpowers/plans/2026-10-27-mt1-time-window-unification.md`). Şimdi: MT1-01 → 02 → 03 → 04 (sıralı) ve 07, 08, 10 (paralel) + H16 pano notu. Kampanyadan sonra: 05, 06, 09, 11, 12 (çalışma yolunun içe aktardığı modüller). |

## Makale ölçeğinde koşudan önce zorunlu

- Yazılım ön koşulları TAMAM. Kalanlar donanım ve sahip işleri:
- D-04b2 TAMAM (2026-10-28, A18; kayıt `docs/superpowers/plans/2026-10-27-d04b2-strong-pc-measurement.md`): güçlü PC'de seri tahmin Bildiri 14,02 sa, YAEM 9,56 sa sabit bütçe + YAEM native 5,85 sa (toplam ~29,4 sa).
- Kampanyadan önce güçlü PC'de: dizüstündeki güncel `tsplib.db` oraya kopyalanacak ve iki örnek-kümesi testi orada geçmeli (A18 D-04b2 karar a); `pyvrp<0.14` sınırı (karar b, ayrı küçük iş).
- Şefin ön-onay commit'i: OQ-1/3/4/16 değerlerinin profillere yazılması (30 koşu, native 1000; A20 L11), `.gitattributes` ile JSON satır sonlarının sabitlenmesi (A20 L6 d), D-10 şablonuyla doldurulmuş ve sahibin onayladığı koşu planı.
- Kural (A21 OQ-F7): onay commit'i ile kampanya arasında birleştirme yok.

## Sahibin kararını bekleyenler

- D-12 yayın (WIP → main, taslak PR) yalnız sahibin açık izniyle.
- A20 (L1–L13) ve A21 (OQ-F1..F8) şef kararlarının sahip tarafından gözden geçirilmesi.

## Ertelenen işler

- Makale koşusundan sonra: `tsp_matrix_metaheuristics/*` seed varsayılanları (A21 OQ-F4 a); Or-opt native kabulünün kuyruk yamasından ana kümelere taşınması (A20 L5).
- Ayrı plan: `ls_engine` 2-opt/Or-opt/swap katmanlarının arka uca bağlı davranışı (A21 OQ-F8 a).
- MT7 ile: `run/status`, `run/stop` BFF rotaları (H14 ile birlikte).
- Cila: `uniride.egg-info/SOURCES.txt` silinmiş yolları listeliyor; shim koruma testi `scripts/` taramıyor; sabit-matris eşitlik testinde kullanılmayan `symmetric` parametresi; RUN'un 3-opt dışı hamleleri ATSP'de ters çeviriyor; canlı yönetici araç planlama sayfasında matris-hata bildirimi testi yok; `test_mutation_proof_tsp.py:109` sahte fonksiyonu kaldırılan anahtar sözcüğü kabul ediyor; `/compare` ve rota-test sayfası `termination_reason`/`solver_code_version` taşımıyor (plan kaydetmiyorlar).
- D-05 cila: plana örnek başına uygulanabilirlik beyanı yok (karma aile reddedilir).
- J11 README'den `scripts/compare_exact_day_joint_runs.py` betiğine işaret (yazı hattı).
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
