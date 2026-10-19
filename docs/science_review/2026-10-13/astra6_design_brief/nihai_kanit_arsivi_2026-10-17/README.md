# Nihai kanıt arşivi (2026-10-17)

Hazırlayan: Claude Science. Bağlı belge: [../NIHAI_BIRLESIK_BULGULAR_VE_YOL_HARITASI_2026-10-17_ClaudeScience.md](../NIHAI_BIRLESIK_BULGULAR_VE_YOL_HARITASI_2026-10-17_ClaudeScience.md).

## Bu arşiv nedir, ne değildir

- **Nedir:** Nihai belgedeki her sayının dayandığı kod ve ham sonuç dosyaları. Dosyalar Claude Science çalışma alanındaki kayıtlardan birebir kopyalandı. Her dosyanın SHA-256 özeti ve kaynak kayıt kimliği `MANIFEST_sha256.csv` içinde.
- **Ne değildir:** Tek komutla çalışan bir yeniden üretim paketi değildir. Temiz bir ortamda yeniden çalıştırma testi **yapılmadı**. Codex'in M2 kararının tam karşılığı için bu arşiv çalıştırılabilir hale getirilmelidir (aşağıda "Bilinen engeller").

## Klasörler

| Klasör | İçerik |
|---|---|
| `uretim_dalga_gun/` | P5 dalga kesin çözücüsü (WAVE-EXACT), gün düzeyi ortak model (DAY-JOINT), tipli filo (DAY-TYPED), ESN-SP v2/v3 ve eşit süreli GA kıyasları |
| `tsp_hizli_ls/` | ILS-fast (Numba), PX-ILS/GPX ablasyonu, ATSP ft53, D1 yerel arama kalite ölçümü, sözleşme testleri |
| `uclu_kiyas_e2bso_r2dma_paoea/` | E2BSO, R2DMA, P-AOEA ile ILS/GLS/LKH kıyası (6 örnek × 5 tohum) |
| `ogrenme_oruntu/` | LODO öğrenme deneyleri, yay budama, öğrenilmiş yapıcı, ESN-SP v3L, TSP aday listesi, arazi analizi |
| `raporlar_ilk_surum/` | Depoda bulunmayan ilk raporlar: CS1 (`ALGORITHM_DEVELOPMENT_RESULTS_2026-10-14.md`) ve CS2 (`TSP_FAST_LS_REPORT.md`). İçlerindeki `{{artifact:…}}` bağlantıları Claude Science kayıt deposunu gösterir; aynı adlı dosyalar bu arşivin ilgili klasörlerindedir. Bu raporlardaki ifadelerin geçerli hali nihai belgededir (§7). |

## Ortam

Çalışmanın yapıldığı ortamdaki sürümler (ortam yalnız ekleme yapılarak değişti; koşu anındaki sürümlerin bunlarla aynı olduğu varsayılıyor, ayrıca kaydedilmedi):

Python 3.11.17 · numpy 2.4.6 · scipy 1.17.1 (HiGHS, `scipy.optimize.milp`) · pandas 2.3.3 · numba 0.68.0 · ortools 9.15.6755 (CP-SAT) · scikit-learn 1.9.1 · elkai 2.0.1 · matplotlib 3.11.2. İşletim sistemi: Windows; 12 çekirdek, 16 GiB bellek.

**Lisans notu:** elkai (LKH) yalnız akademik ve ticari olmayan kullanım için serbesttir. Üretim yolunda kullanılamaz; yalnız referans koludur.

## Girdi verisi

`docs/paper/results/week-2026-10-05-4sw5so/` altındaki 48 girdi dosyasının SHA-256 özetleri de `MANIFEST_sha256.csv` sonundadır (`kaynak_artifact = depo girdisi`). Sonuç kayıtlarındaki `matrix_sha` alanı (bfb2dd85…dd31e5) dosya özeti değil, matris yaylarının içerik özetidir.

## Kayıt düzeyinde bilinmesi gerekenler

1. **İki dalga hücresinin ilk kaydı.** `wave_exact_4sw5so.jsonl` içinde `2026-10-05:pickup:525` dalgasının R=50 ve R=70 hücreleri CP-SAT ile `FEASIBLE` olarak kayıtlı. Bu iki hücre sonradan iki aşamalı HiGHS ile yeniden çözüldü ve `OPTIMAL` sonuç aynı rota sayısı ve dakikayı verdi. Geçerli birleşik kayıt `wave_exact_vs_ga.csv` dosyasıdır (228/228 `OPTIMAL`). Yeniden çözüm koşusunun ayrı ham kaydı arşivde yok.
2. **Gün modeli, Pazartesi R=90.** `day_joint_4sw5so.jsonl` içinde bu hücrede 1. aşama süre sınırına takıldı (`s1=1`, `K=11` yalnız eldeki uygun çözüm). Filo 3, sıralı kesin planın LB0 alt sınırına eşit olmasıyla kanıtlı; rota ve dakika aşamaları koşmadı.
3. **ESN-SP duvar saati bütçelidir.** Aynı yapılandırmanın iki koşusunda (`scale_esn_vs_ga.csv` ve `esn_learned_vs_geo.csv` içindeki `v3_geo`) 15 örneğin 3'ünde sonuç farklı. Tek koşu kıyasları gösterge niteliğindedir.
4. **TSP p-değerleri koşu (tohum) çiftleri üzerinedir.** Örnek sayısı küçüktür (4–10). Nihai belgede örnek düzeyi sayımlar ayrıca verildi.
5. **LKH kıyası eşit süreli değil.** elkai tohum almaz; 5 "tohum" aynı koşudur. n≥439 örneklerde LKH 30 s'yi aşar (43,8–65,3 s).

## Bilinen engeller (çalıştırılabilir paket için yapılacaklar)

- Betiklerin bir kısmı depo kökünü sabit yol olarak içerir (`ROOT = C:\Users\…\UniRide`); `run_waves.py`, `run_esn.py`, `bench_common.py` gibi betikler `uniride_core` paketini içe aktarır.
- Betikler tek klasörde birlikte duracak biçimde yazıldı. Bu arşivde klasörler arası içe aktarmalar var: `prune_exp.py` → `wave_exact`; `run_esn_learned.py`, `esn_sp_v3L.py` → `esn_sp`, `esn_sp_v3`, `run_esn`, `run_waves`; `landscape_demo.py`, `tsp_learned_cands.py` → `fast_ls`, `ils_fast` (`ls/` alt klasörü bekler); `bench_runner.py`, `d1_experiment.py` → `bench_common`.
- Bir sonraki adım: tek `requirements`/ortam dosyası, göreli yollar, her tablo için tek komut ve sonuçların bu arşivdeki dosyalarla özet karşılaştırması.
