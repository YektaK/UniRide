# DURUM — devam eden işler

Son güncelleme: 2026-10-24 (WIP `25333088` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir.

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| Sabit bütçede `max_no_improvement` zorunlu + YAEM tohumu 2027 | — | BİRLEŞTİ `e24a5cd1` (Opus ONAY). |
| Gate D (Paket D) | — | BİRLEŞTİ: D-01, D-02, D-03, D-04a, D-04b1 (araç + ölçüm), D-05, D-06, D-07, D-08a, D-08b, D-09, D-10, D-14. BİRLEŞTİ ayrıca: tasarım redline (`ae118736`), D-11 (`69bd7168`). Çalışıyor: OQ-4 için ikinci native ölçüm (kroA100). Sıradaki: D-13, D-12 (sahip izniyle); D-04b2 güçlü bilgisayarda. |

## Bu turda biten

- Gate C SAĞLANDI (`bc80645e`).
- Core-* ve Numba/SOTA ID'leri rota problemlerini reddediyor (`58f77d66`, `e9f11e72`).
- WP-E11 J12 kayıtları (`c42a79e0`); WP-E11 alt bölümü yöntem belgesi §7'de (`f422f67d`), eskimiş cümleler düzeltildi.
- Eski worktree'ler ve `C:\wt` geçici klasörleri Geri Dönüşüm Kutusu'na taşındı (sahip OK 2026-10-23).

## Makale ölçeğinde koşudan önce zorunlu

- MT6 planı (H10 + M25 birlikte, H11, M14): Gate C planı Q4 gereği Gate C sonrası, her makale ölçeğindeki koşudan önce; henüz başlamadı.
- Run index tamlığı (D-02/D-03 izleme): profil özeti, analiz planı özeti ve kimliği, planlanan koşu sayısı, çıktı yeri ve başarısız koşular run index'e yazılsın (D-10 boşlukları G1, G2, G3, G6, G7).

- Paper raporunun paper koşu servisine bağlanması (D-07 izleme): önce `FamilyAnalysis` kampanya kimliğini (indeks sha256 + commit) taşısın, rapor bunu banner ile karşılaştırsın.

## Sahibin kararını bekleyenler

- OQ-4 (native sınırlar): kroA100 üzerinde ikinci geçici ölçümden sonra (3-opt aileleri en çok ~1 saat). OQ-1 (30 koşu), OQ-3 (YAEM) ve OQ-16 (Bildiri) 2026-10-26'da onaylandı.


## Ertelenen küçük işler

- `uniride_core/tests/test_exact_tsp_runner.py` boş tsplib.db taslağında atlanmak yerine hata veriyor (C-01 koruması eklenmeli).
- J11 README'den `scripts/compare_exact_day_joint_runs.py` betiğine işaret (yazı hattı).
- Tamsayılık payı sınır testi (bound = raw + 5e-7).
- Gate C uygunluk testinin A17 penceresi `## ` başlığında da durmalı.
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
- ALNS birleşik cila dalı için iki yardımcı test (mutant kaldı); Smart/CLI parametre bloklarının ön kontrolü (isteğe bağlı).
- D-03 cila: smoke varsayılanı 3 tekrar için test; yarım kalan checkpoint silmesinin elle temizlenmesi docstring'e.
- D-05 cila: başarısız satır aile kontrolü `tsplib-<ad>` veri kümesi kimliğini varsayıyor; plana örnek başına uygulanabilirlik beyanı yok (karma aile reddedilir).
- D-02/D-03 izleme: başarısız koşular run index'e yazılsın (OQ-9 a doğrulanabilir olsun).
- D-07 cila: `ReferenceCrossCheckError` bütünlük reddi sayılsın (yeniden kurma çıkış 2); 3 mutasyon için test; yeniden kurma planı kampanya commit'inden okusun.
- D-04b1 cila: `objective_count < 0` koruması ve nedensiz prob yedeği için test.
- Lisans tekrar denemesi: `real_deps` üzerinden Gurobi probe sayısının manifeste ulaştığını sınayan test (mutant kaldı).
