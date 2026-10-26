# DURUM — devam eden işler

Son güncelleme: 2026-10-27 (Gate D ve MT6 kapanış birleşmesi). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir. Sahip dışarıdayken şefin aldığı kararlar: DECISION_LOG **A20** (L1–L11; her biri seçenekler, artı/eksi, seçim, geri alma yolu ile).

## Durum

| İş | Durum |
|---|---|
| Gate D (Paket D) | **KAPANDI** (D-13, kontrol edilen commit `04612880`; kanıt `docs/superpowers/plans/2026-10-26-gate-d-mt6-close-evidence.md`; A18). Ölçüt 6'nın değer eşleşmesi ön-onay commit'ine ertelendi (A20 L11). Açık: D-04b2 (güçlü bilgisayar, makale koşusunun ön koşulu, A20 L1); D-12 yayın yalnız sahip izniyle. |
| MT6 | **KAPANDI** (MT6-07, aynı kanıt; A19). H10, H11, M14, M25, N-1 giderildi. MT6 altında SOTA ve üretim hibrit sonuçları değişti (eski satırlarla birleştirilmez); Bildiri/YAEM sonuçları değişmedi. |
| Üretim çözücü kaydı (A20 L2 + L3) | BİRLEŞTİ `37963463`; A16 go-live maddeleri eklendi. |

## Bu turda biten

- Run index v2, MT6-01..07, native kabul testi, MT6-06 yeniden ölçüm (Bildiri 45,1 → 16,7 sa, YAEM 31,0 → 11,5 sa; bu bilgisayar, yük altında; kesin sayı D-04b2), makale raporu hazırlığı 1–2, üretim çözücü kaydı, kapanış öncesi cila, problem türü düzeltmesi (A20 L10; kapanış kontrolünün bulduğu gerçek hata), Gate D kapanışı.
- OQ-4 yanıtlandı: her algoritma native'de, global 1000 yineleme, yerel arama/cila kendiliğinden durur (güvenlik sınırı 1000).
- Birleşmiş worktree'ler ve geçici klasörler Geri Dönüşüm Kutusu'na taşındı (sahip OK); ölçüm klasörleri (`C:\wt\d04b1*`, `C:\wt\mt6-06*`) duruyor.

## Makale ölçeğinde koşudan önce zorunlu

- Paper raporunun paper koşu servisine bağlanması; o dalda `analyse_family(index_sha256=...)` zorunlu olsun (A20 L7).
- D-04b2 güçlü bilgisayarda (tam test koşusu dahil).
- Şefin ön-onay commit'i: OQ-1/3/4/16 değerlerinin profillere yazılması (30 koşu, native 1000; A20 L11), `.gitattributes` ile JSON satır sonlarının sabitlenmesi (A20 L6 d), D-10 şablonuyla doldurulmuş ve sahibin onayladığı koşu planı.

## Sahibin kararını bekleyenler

- D-12 yayın (WIP → main, taslak PR) yalnız sahibin açık izniyle.
- A20 kararlarının (L1–L11) sahip tarafından gözden geçirilmesi.

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
