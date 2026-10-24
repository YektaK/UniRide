# DURUM — devam eden işler

Son güncelleme: 2026-10-24 (WIP `d8259753` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir.

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| Sabit bütçede `max_no_improvement` zorunlu + YAEM tohumu 2027 | — | BİRLEŞTİ `e24a5cd1` (Opus ONAY). |
| Gate D (Paket D) | — | BİRLEŞTİ: D-01, D-02, D-03, D-04a, D-05, D-06, D-08a, D-09, D-14. Sıradaki: D-07 (betimsel raporlar), D-04b1 ölçümü, D-08b, D-10. |

## Bu turda biten

- Gate C SAĞLANDI (`bc80645e`).
- Core-* ve Numba/SOTA ID'leri rota problemlerini reddediyor (`58f77d66`, `e9f11e72`).
- WP-E11 J12 kayıtları (`c42a79e0`); WP-E11 alt bölümü yöntem belgesi §7'de (`f422f67d`), eskimiş cümleler düzeltildi.
- Eski worktree'ler ve `C:\wt` geçici klasörleri Geri Dönüşüm Kutusu'na taşındı (sahip OK 2026-10-23).

## Sahibin kararını bekleyenler

- D-04b1 zaman ölçümünden sonra: OQ-1 (30 koşu), OQ-3 (YAEM), OQ-4 (native sınırlar), OQ-16 (Bildiri ayarları) kesinleşecek.


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
- Lisans tekrar denemesi: `real_deps` üzerinden Gurobi probe sayısının manifeste ulaştığını sınayan test (mutant kaldı).
