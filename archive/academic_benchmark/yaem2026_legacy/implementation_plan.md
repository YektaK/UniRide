# YAEM 2026 Optuna-TPE & Evrensel Optimizasyon Planı

Kullanıcının yönlendirmesiyle UniRide içindeki `core/doe.py` modülü incelenmiş ve Taguchi (veya rastgele Fractional) yerine çok daha modern ve güçlü olan **Optuna (Tree-structured Parzen Estimator - TPE)** Bayesian Optimizasyon yönteminin varlığı doğrulanmıştır.

Taguchi Kesirli Faktöriyel iyi bir klasik tasarım olsa da, özellikle HHO-ALNS gibi 10 parametreli devasa arama uzaylarında Optuna'nın Bayesian öğrenme yeteneği (iyi sonuç veren parametrelere doğru yoğunlaşması) çok daha üstün ve hızlı sonuç verir.

## User Review Required

> [!IMPORTANT]
> 1. **Optuna TPE Entegrasyonu:** `2_run_tuning.py` dosyasındaki "Fractional Factorial / Random" algoritmasını tamamen kaldırıp yerine Optuna'yı entegre edeceğim. Her algoritma için körlemesine 27 kombinasyon denemek yerine, Optuna ile akıllıca **30 Trial (Deneme)** yapacağız.
> 2. **Ölçek Tabanlı Evrensel Set Çıkarımı:** Daha önce anlaştığımız gibi; Optuna ile `eil51`, `berlin52`, `st70`, `kroA100` problemleri üzerinde ayrı ayrı optimizasyon yapılacak.
> 3. **Universal Extraction:** Yeni yazılacak `extract_universal_params.py` betiği, bu 4 problemin Optuna sonuçlarını alıp her algoritma için en baskın/ortak hiper-parametre setini (Evrensel Set) sentezleyecek.
> 4. **Benchmark:** `3_run_benchmark.py` bu Evrensel seti okuyarak `student_matrix` dahil tüm problemlerde kapıştırma yapacak.

## Open Questions

> [!WARNING]
> Optuna kullanırken `1_generate_config.py` içerisindeki mevcut liste sınırlarını (örn. `popülasyon: [40, 80, 120]`) kullanacağım. Optuna bu üçlü seçeneklerden en iyisini `suggest_categorical` ile arayacak (Tıpkı Taguchi'deki Seviye-1, Seviye-2, Seviye-3 mantığı gibi). Optuna TPE kullanılarak yapılacak bu devrimsel altyapı değişikliğini onaylıyor musunuz?

## Proposed Changes

### 1. Optuna'nın `2_run_tuning.py`'ye Entegre Edilmesi
#### [MODIFY] [2_run_tuning.py](file:///C:/Users/yekta/Masa%C3%BCst%C3%BC/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/2_run_tuning.py)
- `generate_combinations` ve `fractional_fallback` mantığı silinecek.
- Optuna modülü import edilip `optuna.create_study(sampler=TPESampler)` altyapısı kurulacak.
- Hedeflenen her problem/algoritma ikilisi için Bayesian Optimizasyon koşturularak sonuçlar DB'ye eklenecek.

### 2. Evrensel Parametre Betiği
#### [NEW] [extract_universal_params.py](file:///C:/Users/yekta/Masa%C3%BCst%C3%BC/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/extract_universal_params.py)
- Tuning DB'yi okuyacak.
- 4 TSPLIB problemi üzerindeki Optuna sonuçlarının mod'unu (en sık karşılaşılan değer) alıp `universal_parameters_db.json` üretecek.

### 3. Otomatik Çalıştırıcı (Runner) Güncellemesi
#### [MODIFY] [run_isarc_experiments.py](file:///C:/Users/yekta/Masa%C3%BCst%C3%BC/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/run_isarc_experiments.py)
- `berlin52`, `eil51`, `st70`, `kroA100` için otomatik config üretecek şekilde güncellenecek.
- Adım 2.5 olarak `extract_universal_params.py` betiğini çalıştıracak.

### 4. Benchmark Veritabanı Değişimi
#### [MODIFY] [3_run_benchmark.py](file:///C:/Users/yekta/Masa%C3%BCst%C3%BC/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/3_run_benchmark.py)
- Klasik tuning DB yerine `universal_parameters_db.json` okuyacak şekilde düzeltilecek.

## Verification Plan
1. Optuna entegrasyonu sonrası `2_run_tuning.py` bir problemde çalıştırılıp Optuna logları teyit edilecek.
2. Sentezleme kodunun doğru bir ortalama (veya en sık tekrar eden) değeri bulduğu JSON dosyası kontrol edilerek doğrulanacak.
