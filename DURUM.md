# DURUM — devam eden işler

Son güncelleme: 2026-10-22 (WIP `c42a79e0` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir.

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| WP-E11 Gurobi lisans hatasında tekrar deneme (E14, en fazla 2) | `fix/wp-e11-gurobi-licence-retry` | Opus denetimi DUZELT tur 1: probe yalnızca lisans türünü yeniden denemeli; probe tekrarları manifestte (`run_history.probe_retries`) kayda geçmeli. Geliştiricide. |
| Gate C: birleşik (composite) ID'ler pilot listelerinde ve smoke dışa aktarımında + C-13 YAEM profili | `feat/gatec-c13-yaem` | Geliştiricide (TDD). Sonra Opus denetimi. |
| WP-E11 J12 kayıtlar | — | BİRLEŞTİ `c42a79e0` (karşılaştırma betiği, tasarım §6.1/§6.3, durum paragrafları). Açık: J11 README’den betiğe işaret. |

## Sıradaki

- Gate C kapanışı (C-15): yukarıdaki Gate C işi birleşince.
- WP-E11 makale ve yöntem metni: yazı hattından (yazar + olgu denetçisi).

## Sahibin kararını bekleyenler

- Yerel AMPL lisansı hâlâ 2026-11-05 bitişini gösteriyor; `ampl -vvq` ile kontrol.
- `max_no_improvement=75` varsayılanı, anahtar yazılmamış sabit bütçeli koşuları erken bitirebilir: sabit bütçede zorunlu mu olsun, yalnızca belgelensin mi?
- Birleştirilmiş worktree'lerin ve `C:\wt` geçici klasörlerinin silinmesi (bazılarında testlerin açtığı boş `tsplib.db` var).

## Ertelenen küçük işler

- Tamsayılık payı sınır testi (bound = raw + 5e-7).
- `Numba-Swap`, `Numba-Hybrid`, `SOTA-*` rota problemlerinde kendi adlarıyla açgözlü yönlendiriciyi kullanıyor; bunu sabitleyen test yok.
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
