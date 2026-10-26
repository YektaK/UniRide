# DURUM — devam eden işler

Son güncelleme: 2026-10-26 gece (WIP `56b1a35a` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir. Sahip dışarıdayken şefin aldığı kararlar: DECISION_LOG **A20** (L1–L10; her biri seçenekler, artı/eksi, seçim, geri alma yolu ile).

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| Gate D (Paket D) | — | BİRLEŞTİ: D-01..D-11, D-14, redline, run index v2, makale raporu hazırlığı 1 ve 2 (`2c169b26`, `8bfeaeca`), kapanış öncesi cila (`03baaaf8`). D-13 kontrolü `eeeb727b` üzerinde bir GERÇEK HATA buldu: smoke raporu `tsp`/`TSP` büyük-küçük harf farkıyla reddediliyor (A20 L10). Düzeltme çalışıyor: `fix/gated-problem-type-canonical`. Ardından D-13 + MT6-07 kontrolü yeni commit'te yeniden. D-12 yalnız sahip izniyle; D-04b2 güçlü bilgisayarda. |
| MT6 | — | MT6-01..05 + iki cila turu BİRLEŞTİ; MT6-06 ölçümü bitti. MT6 kabul maddeleri 1–6 `eeeb727b` üzerinde sağlandı; MT6-07 kaydı D-13 ile birlikte yazılacak. |
| Üretim çözücü kaydı (A20 L2 + L3) | — | BİRLEŞTİ `37963463` (SOTA üretim varsayılan 60 s, `termination_reason`, `solver_code_version`); A16 go-live maddeleri eklendi. |

## Bu turda biten

- Run index v2, MT6-01..05, native kabul testi, MT6-06 yeniden ölçüm (Bildiri 45,1 → 16,7 sa, YAEM 31,0 → 11,5 sa; bu bilgisayar, yük altında; kesin sayı D-04b2), makale raporu hazırlığı 1–2, üretim çözücü kaydı, kapanış öncesi cila.
- OQ-4 yanıtlandı: her algoritma native'de, global 1000 yineleme, yerel arama/cila kendiliğinden durur (güvenlik sınırı 1000); profillere onay öncesi commit'te girecek.
- Birleşmiş 19 worktree ve 31 geçici klasör Geri Dönüşüm Kutusu'na taşındı (sahip OK); ölçüm klasörleri (`C:\wt\d04b1*`, `C:\wt\mt6-06*`) duruyor.

## Makale ölçeğinde koşudan önce zorunlu

- L10 düzeltmesi, sonra MT6-07 ve D-13 kapanışı.
- Paper raporunun paper koşu servisine bağlanması; o dalda `analyse_family(index_sha256=...)` zorunlu olsun (A20 L7).
- D-04b2 güçlü bilgisayarda; onay öncesi commit'te OQ-1/3/4/16 değerlerinin profillere yazılması (D-10 kuralı) ve `.gitattributes` ile JSON satır sonlarının sabitlenmesi (A20 L6 d).

## Sahibin kararını bekleyenler

- D-12 yayın (WIP → main, taslak PR) yalnız sahibin açık izniyle.
- A20 kararlarının (L1–L10) sahip tarafından gözden geçirilmesi.

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
