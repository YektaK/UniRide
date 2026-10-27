# Yeniden üretim paketi (2026-10-17)

Hazırlayan: Claude Science. Bağlı belgeler: [../NIHAI_BIRLESIK_BULGULAR_VE_YOL_HARITASI_2026-10-17_ClaudeScience.md](../NIHAI_BIRLESIK_BULGULAR_VE_YOL_HARITASI_2026-10-17_ClaudeScience.md) ve kanıt arşivi [../nihai_kanit_arsivi_2026-10-17/](../nihai_kanit_arsivi_2026-10-17/README.md).

**Durum:** ana hatlar yeniden koşturuldu ve arşivle karşılaştırıldı (2026-10-17). Yeniden koşturulmayan hatlar "Kalan işler" bölümünde.

## Yapı

| Klasör | İçerik |
|---|---|
| `src/` | Arşivdeki betiklerin düz kopyası. Değişiklik yalnız `ROOT`: sabit yol yerine `UNIRIDE_ROOT` ortam değişkeni ya da paket konumundan 6 üst klasör. `analysis.py` (TSP) → `analysis_tsp.py`. `src/data/`: 15 TSPLIB dosyası |
| `surucu/` | Yeni betikler (aşağıda) |
| `ciktilar/` | Yeniden koşu çıktıları ve günlükler |
| `requirements.txt` | Sürümler |

| Betik | Görev |
|---|---|
| `calistir.py` | Tek giriş noktası: `python surucu/calistir.py <dogrula|dalga|cozum2|gun|gun_tablo|lodo|tsp_test|karsilastir|hepsi>` |
| `dogrula.py` | Nihai belgedeki 61 sayıyı arşiv dosyalarından yeniden hesaplar |
| `run_lodo.py` | Öğrenme tablolarının sürücüsü; 2026-10-15 çekirdek hücrelerinden birebir yeniden kuruldu (özgün sürücü yalnız çekirdekteydi) |
| `resolve_two_stage.py` | OPTIMAL olmayan dalga hücrelerini iki aşamalı HiGHS ile yeniden çözer |
| `gun_duzeyi.py` | Gün tablosu: GA filosu, sıralı kesin plan, LB0, ortak planın bağımsız doğrulaması (özgün kod yalnız çekirdekteydi; birebir aktarıldı) |
| `karsilastir.py` | Yeniden koşu çıktılarını arşivle karşılaştırır |
| `bellek_korumali.py`, `dalga_alt_kume.py` | Bellek yetmediğinde betiği çökertmeden sürdürmek için sarmalayıcılar (özgün kodu değiştirmez) |

## Ortam

`requirements.txt`. Python 3.11.17, Windows. Korumalı Windows ortamında joblib iş parçacığı havuzu açılamadığı için `run_lodo.py` HistGBM özellik kutulamasını tek işçiyle çalıştırır; her özelliğin eşikleri bağımsız hesaplandığından sonuç değişmez (aşağıdaki birebir eşleşme bunu doğruluyor).

## 2026-10-17 sonuçları

| Adım | Sonuç |
|---|---|
| `dogrula.py` | 61/61 kontrol geçti (nihai belge Sürüm 2'de O2 değeri 0,863 olarak düzeltildikten sonra) |
| TSPLIB dosyaları | 15/15 dosya depo kopyasıyla SHA-256 düzeyinde aynı |
| Dalga (WAVE-EXACT) | 228/228 hücre yeniden çözüldü; rota sayısı ve dakika 228/228 arşivle aynı; hepsi OPTIMAL (225 ağırlıklı HiGHS, 2 iki aşamalı HiGHS, 1 CP-SAT); sertifika ihlali 0 |
| İki aşamalı yeniden çözüm | 05.10 08:45 toplama R=50 ve R=70: ağırlıklı HiGHS 120 s'de kanıtlayamadı; iki aşamalı HiGHS 2,8 s ve 44,3 s'de OPTIMAL |
| En büyük dalga (R=90, 45 170 kolon) | HiGHS'e bellek yetmedi; özgün koddaki CP-SAT geri dönüşü OPTIMAL buldu (3 rota / 329 dk, arşivle aynı) |
| Gün (DAY-JOINT) | 19/20 hücrede K, rota, dakika ve aşama durumları arşivle aynı. Pazartesi R=90 çözülemedi (arşivde süre sınırı, burada bellek). Pazartesi R=70 ve 09.10 R=90 ancak tek başına çalıştırıldığında çözüldü |
| Gün tablosu (`gun_duzeyi.py`) | GA filosu, sıralı plan, LB0, ortak plan ve bağımsız denetim sütunları 20/20 hücrede aynı; haftalık filo tablosu birebir aynı |
| Öğrenme (`run_lodo.py`) | `lodo_metrics.csv` 42/42 satır, en büyük mutlak fark 0,0; `recall_at_k.csv` fark 0,0; yapıcı tablosu 1840/1840 satır aynı. `prune_in.pkl` yeniden üretildi |

Ayrıntı: `ciktilar/dogrulama_raporu.csv`, `ciktilar/karsilastirma_raporu.csv`, `ciktilar/gun/`, `ciktilar/lodo/`, `ciktilar/log/`.

## Kalan işler

1. Yeniden koşturulmayan hatlar: yay budama (`prune_exp.py`, saatler sürer), ESN-SP koşuları (duvar saatine bağlı), TSP kıyasları (`bench_runner.py`), arazi analizi, E2BSO/R2DMA/P-AOEA kıyası.
2. Sürücüsü yeniden kurulmayan tablolar: `lodo_auc_by_day.csv`, `forward_chaining_auc.csv`, `succ_feature_importance_fold1005.csv`.
3. Pazartesi R=90 gün hücresinin rota ve dakika aşamaları (her iki koşuda da kanıtsız).

## Bellek notu

Bu makinede (16 GiB; çalışma sırasında boş bellek 1–3 GiB) en zor HiGHS çözümleri `MemoryError` verebiliyor. Büyük hücreleri tek başına ve başka iş yokken çalıştırın.
