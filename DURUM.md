# DURUM — devam eden işler

Son güncelleme: 2026-10-26 (WIP `a08920e1` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir.

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| Sabit bütçede `max_no_improvement` zorunlu + YAEM tohumu 2027 | — | BİRLEŞTİ `e24a5cd1` (Opus ONAY). |
| Gate D (Paket D) | — | BİRLEŞTİ: D-01, D-02, D-03, D-04a, D-04b1 (araç + ölçüm), D-05, D-06, D-07, D-08a, D-08b, D-09, D-10, D-14. BİRLEŞTİ ayrıca: tasarım redline (`ae118736`), D-11 (`69bd7168`), run index tamlığı (`0e3d0ee8`, uniride-run-index/v2, Opus ONAY). OQ-4 yanıtlandı (A18). Çalışıyor: makale raporu hazırlığı (`fix/gated-paper-report-readiness`: run index v2 cilası, D-07 cilası, FamilyAnalysis kampanya kimliği) ve tüm çalışma kimliklerinin native kabulü (`fix/native-admission-all-study-ids`). Sahip dışarıdayken şef kararları A20. |
| MT6 (tek kanonik 3-opt, deterministik SOTA durdurma) | — | Plan BİRLEŞTİ `e3be3873`; sahip OQ-MT6-1..7 hepsi öneri (A19). MT6-01 + MT6-02 BİRLEŞTİ (`d0c73a8b`). Sıra: MT6-01 hız (sonuç değişmez) → MT6-02 (H10) → MT6-03 (H11); MT6-04 (M14, Dudullu tekrar oynatma sahibe) MT6-01'den sonra; MT6-05; MT6-06 şef ölçümü; MT6-07 kapanış. Sıradaki: D-13, D-12 (sahip izniyle); D-04b2 güçlü bilgisayarda. Çalışıyor: MT6-03 (`fix/mt6-03-sota-deterministic-stop`), MT6-04 (`fix/mt6-04-path-three-opt`), MT6-05 + MT6-01 cilası (`fix/mt6-05-budgeted-tolerance`). MT6-06 ölçümü bitti (A19). MT6-03/04/05 denetimde. |

## Bu turda biten

- Gate C SAĞLANDI (`bc80645e`).
- Core-* ve Numba/SOTA ID'leri rota problemlerini reddediyor (`58f77d66`, `e9f11e72`).
- WP-E11 J12 kayıtları (`c42a79e0`); WP-E11 alt bölümü yöntem belgesi §7'de (`f422f67d`), eskimiş cümleler düzeltildi.
- Eski worktree'ler ve `C:\wt` geçici klasörleri Geri Dönüşüm Kutusu'na taşındı (sahip OK 2026-10-23).

## Makale ölçeğinde koşudan önce zorunlu

- MT6 planı (H10 + M25 birlikte, H11, M14): Gate C planı Q4 gereği Gate C sonrası, her makale ölçeğindeki koşudan önce; MT6-01 (`7c41237b`) ve MT6-02 (`d0c73a8b`) BİRLEŞTİ; kalan MT6-03, MT6-04, MT6-05, MT6-06 şef ölçümü, MT6-07.
- Run index v2 cilası (A18 notu `0e3d0ee8`): plan özeti ifadesi ("çözülmedi" yerine dosya yokluğu), rapor yolunda doğrulayıcı notlarının ve plan dosyası özetinin kontrolü, başka düzeydeki hataların istenmesi uç durumu, hayatta kalan 5 mutasyon için test.

- Paper raporunun paper koşu servisine bağlanması (D-07 izleme): önce `FamilyAnalysis` kampanya kimliğini (indeks sha256 + commit) taşısın, rapor bunu banner ile karşılaştırsın.

## Sahibin kararını bekleyenler

- OQ-4 2026-10-26'da yanıtlandı (A18: her algoritma native'de, global 1000 yineleme, yerel arama/cila kendi durur, güvenlik sınırı 1000). Profillere onay öncesi commit'te girecek; önce native koşu servisinin bileşik aşamalara sınırı nasıl uyguladığı kontrol edilmeli. OQ-1, OQ-3, OQ-16 de onaylı.
- S08 sağlayıcı kaydına kod commit'i alanı eklensin mi (MT6-02 bulgusu).
- D-04b2 güçlü bilgisayara ertelenirken D-13 ile Gate D kapatılsın mı.


## Ertelenen küçük işler

- `uniride_core/tests/test_exact_tsp_runner.py` boş tsplib.db taslağında atlanmak yerine hata veriyor (C-01 koruması eklenmeli).
- J11 README'den `scripts/compare_exact_day_joint_runs.py` betiğine işaret (yazı hattı).
- Tamsayılık payı sınır testi (bound = raw + 5e-7).
- Gate C uygunluk testinin A17 penceresi `## ` başlığında da durmalı.
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
- ALNS birleşik cila dalı için iki yardımcı test (mutant kaldı); Smart/CLI parametre bloklarının ön kontrolü (isteğe bağlı).
- D-03 cila: smoke varsayılanı 3 tekrar için test; yarım kalan checkpoint silmesinin elle temizlenmesi docstring'e.
- D-05 cila: başarısız satır aile kontrolü `tsplib-<ad>` veri kümesi kimliğini varsayıyor; plana örnek başına uygulanabilirlik beyanı yok (karma aile reddedilir).
- D-07 cila: `ReferenceCrossCheckError` bütünlük reddi sayılsın (yeniden kurma çıkış 2); 3 mutasyon için test; yeniden kurma planı kampanya commit'inden okusun.
- D-04b1 cila: `objective_count < 0` koruması ve nedensiz prob yedeği için test.
- MT6-01 cila: tamsayı olmayan pencere (12.0) artık TypeError veriyor, açık doğrulama; yakınsamaya kadar window None tam koşu eşlik testi; tasarım :57 ifadesi.
- MT6-02 cila: yok sayılan `window`/`max_iterations` argümanını yakalayan test; `ls_engine.py:10` başlık cümlesi.
- Lisans tekrar denemesi: `real_deps` üzerinden Gurobi probe sayısının manifeste ulaştığını sınayan test (mutant kaldı).
