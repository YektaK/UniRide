# DURUM — devam eden işler

Son güncelleme: 2026-10-26 akşam (WIP `985c6509` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir. Sahip dışarıdayken şefin aldığı kararlar: DECISION_LOG **A20** (L1–L5; her biri seçenekler, artı/eksi, seçim, geri alma yolu ile).

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| Gate D (Paket D) | — | BİRLEŞTİ: D-01..D-11, D-14, tasarım redline, run index v2 (`0e3d0ee8`). OQ-1/3/4/16 yanıtlandı (A18). Kalan: D-13 kapanış (A20 L1: MT6-07'den hemen sonra, D-04b2 makale koşusunun ön koşulu olarak açık kalır), D-12 yayın (yalnız sahip izniyle), D-04b2 güçlü bilgisayarda. |
| Makale raporu hazırlığı | `fix/gated-paper-report-readiness` | Geliştirici bitti (run index v2 cilası 1–4, D-07 cilası, `FamilyAnalysis` kampanya kimliği); Opus denetimi sürüyor. |
| MT6 (tek kanonik 3-opt, deterministik SOTA durdurma) | — | BİRLEŞTİ: MT6-01 `7c41237b`, MT6-02 `d0c73a8b`, MT6-03 `693d8fd2`, MT6-04 `dfaadc2d`, MT6-05 `9bd31aea`; MT6-06 ölçümü bitti (A19). Kalan: denetim cilası (`fix/mt6-review-polish`, geliştirici çalışıyor), MT6-07 kapanış. |
| Üretim çözücü kaydı (A20 L2 + L3) | `feat/production-solver-provenance` | Geliştirici bitti (SOTA üretim varsayılan süre sınırı 60 s, yanıtta `termination_reason`, `solver_code_version` = `UNIRIDE_BUILD_COMMIT`, S08 anahtarları, EN/TR not cümlesi); Opus denetimi sürüyor. |

## Bu turda biten

- Run index v2, MT6-01..05, native kabul testi (her iki profilin her kimliği native protokolde geçiyor), MT6-06 yeniden ölçüm: Bildiri 45,1 → 16,7 sa, YAEM 31,0 → 11,5 sa (bu bilgisayar, yük altında; kesin sayı D-04b2).
- OQ-4 yanıtlandı: her algoritma native'de, global 1000 yineleme, yerel arama/cila kendiliğinden durur (güvenlik sınırı 1000); profillere onay öncesi commit'te girecek.

## Makale ölçeğinde koşudan önce zorunlu

- MT6-07 kapanış ve D-13.
- Makale raporu hazırlığı dalının birleşmesi; ardından paper raporunun paper koşu servisine bağlanması (`FamilyAnalysis` kimliği hazır olunca).
- D-04b2 güçlü bilgisayarda; onay öncesi commit'te OQ-1/3/4/16 değerlerinin profillere yazılması (D-10 kuralı).
- A16 go-live listesine: derlemede `UNIRIDE_BUILD_COMMIT` ayarlanması (provenance dalı birleşince).

## Sahibin kararını bekleyenler

- D-12 yayın (WIP → main, taslak PR) yalnız sahibin açık izniyle.
- A20 kararlarının (L1–L5) sahip tarafından gözden geçirilmesi.

## Ertelenen küçük işler

- MT6-05 cila: 1'in altındaki maliyetlerle test (`max(1, …)` tabanı korumasız); altın vakaların bütçe tükenmesiyle bittiğini söyleyen docstring; `registry_setup.py` pencere doğrulaması erken ve tutarlı (`:298` sabit bütçe, `:383` native `int(12.5)`).
- Or-opt native kabulünün `native_protocol.py` kuyruk yamasından ana kümelere taşınması (A20 L5: makale koşusundan sonra).
- Run index v2 küçükleri: `failed_run_entries` eksik `evaluation_budget`'ı null yapıyor, `replicate` alt sınırı yok, `output_location.path` Windows kullanıcı adını içeriyor (D-12 öncesi).
- `/compare` yolu `termination_reason`/`solver_code_version` taşımıyor (kaydedilmiyor; denetim kararı bekleniyor).
- J11 README'den `scripts/compare_exact_day_joint_runs.py` betiğine işaret (yazı hattı).
- Tamsayılık payı sınır testi (bound = raw + 5e-7).
- Gate C uygunluk testinin A17 penceresi `## ` başlığında da durmalı.
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
- ALNS birleşik cila dalı için iki yardımcı test (mutant kaldı); Smart/CLI parametre bloklarının ön kontrolü (isteğe bağlı).
- D-03 cila: smoke varsayılanı 3 tekrar için test; yarım kalan checkpoint silmesinin elle temizlenmesi docstring'e.
- D-05 cila: başarısız satır aile kontrolü `tsplib-<ad>` veri kümesi kimliğini varsayıyor; plana örnek başına uygulanabilirlik beyanı yok (karma aile reddedilir).
- D-04b1 cila: `objective_count < 0` koruması ve nedensiz prob yedeği için test.
- Lisans tekrar denemesi: `real_deps` üzerinden Gurobi probe sayısının manifeste ulaştığını sınayan test (mutant kaldı).
- Birleşmiş worktree'lerin ve `C:\wt` geçici klasörlerinin temizliği (sahip OK birleşmişler için var; Geri Dönüşüm Kutusu + `git worktree prune`).
