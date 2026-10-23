# DURUM — devam eden işler

Son güncelleme: 2026-10-23 (WIP `c6e1d29e` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir.

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| WP-E11 Gurobi lisans hatasında tekrar deneme (E14, en fazla 2) | `fix/wp-e11-gurobi-licence-retry` | Opus DUZELT tur 1 (probe yalnızca lisans türünü yeniden denesin; probe tekrarları `run_history.probe_retries` ile kayda geçsin). Geliştiricide; rapor bekleniyor. |
| Sabit bütçede `max_no_improvement` zorunlu + YAEM tohumu 2027 (sahip kararları 2 ve 3) | `fix/fixed-budget-hygiene` | Geliştirici bitirdi; Opus denetiminde. |
| Gate D (Paket D) planı | `docs/gate-d-plan` | Opus denetimi 4 turda ONAY (`f3496883`). Sahibin 17 sorusu ve plan onayı bekleniyor. |

## Bu turda biten

- Gate C SAĞLANDI (`bc80645e`).
- Core-* ve Numba/SOTA ID'leri rota problemlerini reddediyor (`58f77d66`, `e9f11e72`).
- WP-E11 J12 kayıtları (`c42a79e0`); WP-E11 alt bölümü yöntem belgesi §7'de (`f422f67d`), eskimiş cümleler düzeltildi.
- Eski worktree'ler ve `C:\wt` geçici klasörleri Geri Dönüşüm Kutusu'na taşındı (sahip OK 2026-10-23).

## Sahibin kararını bekleyenler

- Gate D planının 17 sorusu (plan dosyası §5) ve planın onayı.
- `FCM-*-TSP` rota problemlerini reddetsin mi? `CVRP-/CVRPTW-Numba-Swap/-Hybrid` takma adları (eski 2-opt motoru) kalsın mı, yeniden adlandırılsın mı, kaldırılsın mı?
- Smart'ın "varsayılan" modu GWO/HHO'ya boş ayar gönderiyor; sabit bütçe kuralıyla artık reddediliyor. İstenen bu mu, yoksa o mod anahtarı açıkça mı yazsın? (fixed-budget-hygiene denetiminden sonra sorulacak)

## Ertelenen küçük işler

- `uniride_core/tests/test_exact_tsp_runner.py` boş tsplib.db taslağında atlanmak yerine hata veriyor (C-01 koruması eklenmeli).
- 42 AMPL testi (çekirdek): lisans işi bitince şef çalıştıracak, sonucu A17'ye eklenecek.
- J11 README'den `scripts/compare_exact_day_joint_runs.py` betiğine işaret (yazı hattı).
- Tamsayılık payı sınır testi (bound = raw + 5e-7).
- Gate C uygunluk testinin A17 penceresi `## ` başlığında da durmalı.
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
