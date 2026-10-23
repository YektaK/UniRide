# DURUM — devam eden işler

Son güncelleme: 2026-10-23 (WIP `e24a5cd1` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir.

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| WP-E11 Gurobi lisans hatasında tekrar deneme (E14, en fazla 2) | `fix/wp-e11-gurobi-licence-retry` | Opus DUZELT tur 1 (probe yalnızca lisans türünü yeniden denesin; probe tekrarları `run_history.probe_retries` ile kayda geçsin). Geliştiricide; rapor bekleniyor. |
| Sabit bütçede `max_no_improvement` zorunlu + YAEM tohumu 2027 | — | BİRLEŞTİ `e24a5cd1` (Opus ONAY). |
| Gate D (Paket D) | — | Plan BİRLEŞTİ `944c2b4a`; 17 soru = öneriler (A18). İlk dalga: D-01, D-08a, D-09 + FCM reddi / max_iterations zorunlu. |

## Bu turda biten

- Gate C SAĞLANDI (`bc80645e`).
- Core-* ve Numba/SOTA ID'leri rota problemlerini reddediyor (`58f77d66`, `e9f11e72`).
- WP-E11 J12 kayıtları (`c42a79e0`); WP-E11 alt bölümü yöntem belgesi §7'de (`f422f67d`), eskimiş cümleler düzeltildi.
- Eski worktree'ler ve `C:\wt` geçici klasörleri Geri Dönüşüm Kutusu'na taşındı (sahip OK 2026-10-23).

## Sahibin kararını bekleyenler

- D-04b1 zaman ölçümünden sonra: OQ-1 (30 koşu), OQ-3 (YAEM), OQ-4 (native sınırlar), OQ-16 (Bildiri ayarları) kesinleşecek.


## Ertelenen küçük işler

- `uniride_core/tests/test_exact_tsp_runner.py` boş tsplib.db taslağında atlanmak yerine hata veriyor (C-01 koruması eklenmeli).
- 42 AMPL testi (çekirdek): lisans işi bitince şef çalıştıracak, sonucu A17'ye eklenecek.
- J11 README'den `scripts/compare_exact_day_joint_runs.py` betiğine işaret (yazı hattı).
- Tamsayılık payı sınır testi (bound = raw + 5e-7).
- Gate C uygunluk testinin A17 penceresi `## ` başlığında da durmalı.
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
- ALNS birleşik cila dalı için iki yardımcı test (mutant kaldı); Smart/CLI parametre bloklarının ön kontrolü (isteğe bağlı).
