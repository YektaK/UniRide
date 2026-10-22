# DURUM — devam eden işler

Son güncelleme: 2026-10-22 (WIP `30646ecd` sonrası). Kararlar `docs/DECISION_LOG.md` içinde; bu dosya yalnızca işin nerede olduğunu gösterir.

## Çalışan işler

| İş | Dal | Durum |
|---|---|---|
| WP-E11 Gurobi lisans hatasında tekrar deneme (E14, en fazla 2) | `fix/wp-e11-gurobi-licence-retry` | Opus denetimi DUZELT tur 1: probe yalnızca lisans türünü yeniden denemeli; probe tekrarları manifestte (`run_history.probe_retries`) kayda geçmeli. Geliştiricide. |
| Gate C: birleşik ID'ler smoke + pilotlarda, C-13 YAEM profili | — | BİRLEŞTİ `30646ecd` (Opus ONAY). Cila: v1 reddi testi, uçtan uca pilot testi. |
| WP-E11 J12 kayıtlar | — | BİRLEŞTİ `c42a79e0` (karşılaştırma betiği, tasarım §6.1/§6.3, durum paragrafları). Açık: J11 README’den betiğe işaret. |

## Sıradaki

- Gate C kapanışı (C-15): bütün önkoşullar birleşti; sıradaki iş.
- WP-E11 makale ve yöntem metni: yazı hattından (yazar + olgu denetçisi).

## Sahibin kararını bekleyenler

- YAEM profilindeki taslak değerler (seviyeler 50x/250x, 3 koşu, tohum 2026 = Bildiri ile aynı, global pay 0,80, birleşik algoritma ayarları): makale planından önce onay.
- AMPL lisansı: AMPL kısmı 2026-11-05 gösteriyor, ama bu büyük olasılıkla internet üzerinden kendiliğinden yenilenen kısa kiralama (sahibin bulduğu AMPL açıklaması). 2026-11-01 civarı tarihi yeniden kontrol; ileri kaydıysa sorun yok. Koşularda bilgisayar çevrimiçi olmalı.
- `max_no_improvement=75` varsayılanı, anahtar yazılmamış sabit bütçeli koşuları erken bitirebilir: sabit bütçede zorunlu mu olsun, yalnızca belgelensin mi?
- Birleştirilmiş worktree'lerin ve `C:\wt` geçici klasörlerinin silinmesi (bazılarında testlerin açtığı boş `tsplib.db` var).

## Ertelenen küçük işler

- Tamsayılık payı sınır testi (bound = raw + 5e-7).
- `Numba-Swap`, `Numba-Hybrid`, `SOTA-*` rota problemlerinde kendi adlarıyla açgözlü yönlendiriciyi kullanıyor; bunu sabitleyen test yok.
- `scratch/test_hho.py`; eski cila listesi (C-12/C-16b/J3/ayrıştırıcı).
