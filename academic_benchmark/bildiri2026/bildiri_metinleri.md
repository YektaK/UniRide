# Bildiri 2026 - Time-Matrix Tabanlı Asimetrik TSP ile Okul Servis Rotalama

## Özet

Bu çalışmada, okul servis rotalama problemi zaman matrisi tabanlı bir Asimetrik Gezgin Satıcı Problemi (ATSP) olarak ele alınmıştır. Geliştirilen deney hattı üç aşamalıdır: (i) parametre konfigürasyonu üretimi, (ii) parametre optimizasyonu ve deney tasarımı analizi, (iii) seçilen en iyi parametrelerle nihai benchmark. İlk aşamada TSPLIB standardındaki `eil76` problemi üzerinde algoritma-parametre uzayı tanımlanmış; ikinci aşamada tam faktöriyel tarama ve gerekli durumlarda fraksiyonel (fractional fallback) örnekleme ile parametre araması gerçekleştirilmiştir; üçüncü aşamada elde edilen en iyi parametre setleri gerçek 29 düğümlü öğrenci zaman matrisi problemi üzerinde 30 bağımsız koşu ile test edilmiştir. Sonuçlar, GA ve PSO'nun çözüm kalitesi açısından en düşük ortalamayı verdiğini; 2-opt'un ise açık biçimde en hızlı algoritma olduğunu göstermektedir. Böylece kalite-hız ödünleşimi nicel olarak ortaya konmuştur.

Anahtar kelimeler: Asimetrik TSP, okul servis rotalama, zaman matrisi, parametre optimizasyonu, deney tasarımı, ANOVA, Wilcoxon.

## 1. Giriş

Klasik TSP, düğümler arası maliyetlerin simetrik olduğu varsayımı altında bir turun toplam maliyetini minimize etmeyi amaçlar. Ancak gerçek şehir içi trafik koşullarında $i \to j$ ve $j \to i$ yönleri çoğu zaman aynı değildir; tek yön yollar, kavşak geometrisi, sinyalizasyon ve yoğunluk farkları yön-bağımlı seyahat süreleri üretir. Bu nedenle uygulama problemi simetrik TSP'den çok ATSP karakteri taşımaktadır.

Bu çalışmanın uygulama bağlamında maliyetler coğrafi Öklidyen uzaklıkla değil, Google Maps tabanlı yol ağı seyahat sürelerinden elde edilen zaman matrisi ile modellenmiştir. Böylece amaç, geometrik en kısa turu değil operasyonel olarak en düşük toplam servis süresini veren turu bulmaktır.

Modelin amaç fonksiyonu:

$$
\min \sum_{i=0}^{n} \sum_{j=0}^{n} c_{ij} x_{ij}
$$

Burada $c_{ij}$ düğüm $i$'den $j$'ye geçiş süresini, $x_{ij}$ ise ilgili yayın turda seçimini ifade eder.

## 2. Materyal ve Yöntem

### 2.1 Veri kaynakları

Çalışmada iki veri ailesi kullanılmıştır:

1. TSPLIB eğitim problemi: `eil76`.
2. Nihai uygulama problemi: `student_matrix` (29 düğüm; depo + öğrenci noktaları).

`student_matrix` veri setinde maliyetler dakika cinsinden zaman matrisi olarak tutulur. Matris yapısı yönlüdür ve bu nedenle problem ATSP niteliğindedir.

### 2.2 Karşılaştırılan algoritmalar

Bu çalışmada beş yöntem karşılaştırılmıştır:

1. 2-opt (yerel arama)
2. 3-opt (yerel arama)
3. Or-opt (blok taşıma tabanlı yerel arama)
4. GA (Genetik Algoritma)
5. PSO (Ayrık Parçacık Sürü Optimizasyonu)

### 2.3 Programın genel akışı (3 aşamalı boru hattı)

Deney altyapısı aşağıdaki modüler akışla çalışır:

1. Aşama-1 (`1_generate_config.py`):
	Problem, algoritma ve parametre seviyeleri etkileşimli olarak seçilir; çalışma planı `configs/config_*.json` dosyasına yazılır.
2. Aşama-2 (`2_run_tuning.py`):
	Parametre kombinasyonları test edilir; her kombinasyon için ortalama performans hesaplanır ve `tuning_progress_*.csv` dosyasına artımlı (append-only) yazılır; en iyi setler veritabanına kaydedilir.
3. Aşama-3 (`3_run_benchmark.py`):
	Seçilen model kimlikleri, hedef problem üzerinde çoklu bağımsız koşu ile çalıştırılır; ham koşu ve özet çıktılar üretilir (`benchmark_progress_*.csv`, `benchmark_summary_*.csv`).

Ek analiz araçları:

1. `analyze_tuning.py`: parametre optimizasyon çıktılarını ANOVA ve Taguchi S/N bakış açısıyla raporlar.
2. `analyze_benchmark.py`: nihai benchmark için sıralama, ANOVA, ikili Wilcoxon ve Holm düzeltmesi üretir.

## 3. Parametre Optimizasyon Süreci ve Deney Tasarımı

### 3.1 Deney tasarımı seçenekleri

Çalışma çatısı, üç farklı tarama yaklaşımını destekleyecek şekilde tasarlanmıştır:

1. Tam faktöriyel (full grid) tarama: tüm seviye kombinasyonlarının denenmesi.
2. Fraksiyonel/fractional arama: kombinasyon sayısı eşik üstüne çıktığında alt örnekleme.
3. Taguchi/LHS tabanlı tasarım: analiz ve raporlama katmanında S/N oranı ve faktör etkileriyle değerlendirilen deneysel tasarım yaklaşımı.

Bu çalışma özelinde kullanılan aktif strateji `fractional_fallback` olup, kombinasyon sayısı eşik değeri (`max_combinations_per_algo=27`) aşmayan algoritmalarda tam grid, aşanlarda fraksiyonel örnekleme uygulanmıştır.

### 3.2 Arama uzayı ve çalıştırılan kombinasyonlar

`eil76` eğitim probleminde, kombinasyon başına 5 tekrar ile tarama yapılmıştır.

| Algoritma | Teorik kombinasyon | Uygulanan kombinasyon | Yöntem |
|-----------|---------------------|------------------------|--------|
| 2-opt | 18 | 18 | Tam grid |
| 3-opt | 18 | 18 | Tam grid |
| Or-opt | 27 | 27 | Tam grid |
| GA | 48 | 27 | Fraksiyonel örnekleme |
| PSO | 81 | 27 | Fraksiyonel örnekleme |

Toplam kombinasyon sayısı 117'dir. Her kombinasyon 5 bağımsız tekrar içerdiğinden toplam 585 tuning koşusu yürütülmüştür.

### 3.3 Deney tasarımı bulguları (tuning çıktıları)

`tuning_progress_20260424_232923.csv` ve `tuned_parameters_db.json` bulgularına göre en iyi ortalama maliyeti veren parametre setleri aşağıda özetlenmiştir:

| Algoritma | En iyi ortalama (eil76) | Seçilen parametreler |
|-----------|--------------------------|----------------------|
| 2-opt | 559.0 | max_iterations=500, first_improvement=True, num_starts=10 |
| 3-opt | 563.8 | max_iterations=400, first_improvement=True, num_starts=5 |
| Or-opt | 576.0 | max_iterations=600, max_segment_size=3, num_starts=5 |
| GA | 554.6 | population_size=120, generations=100, crossover_rate=0.85, mutation_rate=0.25, elite_count=1 |
| PSO | 555.2 | swarm_size=60, max_iterations=300, inertia_weight=0.6, cognitive_coeff=1.0 |

Bu sonuçlar, meta-sezgisel yöntemlerin (`GA`, `PSO`) eğitim probleminde daha düşük ortalama maliyete inebildiğini; klasik yerel arama ailesinde ise çoklu başlangıç (`num_starts`) ve iyileştirme modunun belirleyici olduğunu göstermektedir.

## 4. Nihai Problem Çalıştırması (29 Öğrenci Time Matrix)

### 4.1 Deney protokolü

Tuning aşamasından seçilen model kimlikleri (ID 6-10), `student_matrix` problemi üzerinde aşağıdaki protokolle test edilmiştir:

1. Her algoritma için 30 bağımsız koşu.
2. Çıktı ölçütleri: Best, Worst, Mean, StdDev, MeanTimeMS.
3. Tüm ham koşular `benchmark_progress_20260425_002216.csv`; özet sonuçlar `benchmark_summary_20260425_002216.csv` dosyasına kaydedilmiştir.

### 4.2 Sonuçlar

| Problem | Algoritma | ModelID | Best | Worst | Mean | StdDev | MeanTimeMS |
|---------|-----------|---------|------|-------|------|--------|------------|
| student_matrix | 2-opt | 6 | 314.0 | 318.0 | 314.9 | 1.2415 | 293.93 |
| student_matrix | 3-opt | 7 | 314.0 | 322.0 | 316.7333 | 2.5587 | 347.88 |
| student_matrix | Or-opt | 8 | 314.0 | 330.0 | 318.7667 | 4.4851 | 373.81 |
| student_matrix | GA | 9 | 314.0 | 314.0 | 314.0 | 0.0 | 752.74 |
| student_matrix | PSO | 10 | 314.0 | 314.0 | 314.0 | 0.0 | 684.69 |

Kalite sıralaması (Mean, düşük daha iyi):

1. GA (314.000)
2. PSO (314.000)
3. 2-opt (314.900)
4. 3-opt (316.733)
5. Or-opt (318.767)

Hız sıralaması (MeanTimeMS, düşük daha iyi):

1. 2-opt (293.93 ms)
2. 3-opt (347.88 ms)
3. Or-opt (373.81 ms)
4. PSO (684.69 ms)
5. GA (752.74 ms)

## 5. İstatistiksel Değerlendirme ve Yorum

### 5.1 ANOVA

Algoritmalar arası performans dağılımı için tek yönlü ANOVA özeti:

$$
F(4,145)=22.4567, \quad \eta^2=0.3825
$$

Bu sonuç, algoritma etkisinin orta-yüksek büyüklükte olduğunu göstermektedir.

### 5.2 İkili karşılaştırmalar (Wilcoxon + Holm)

Holm düzeltmeli ikili testlerde GA/PSO ile Or-opt karşılaştırmaları ve 2-opt ile 3-opt karşılaştırması anlamlı bulunmuştur; GA ile PSO arasında anlamlı fark görülmemiştir. Bulgular, kalite açısından GA/PSO eşdeğerliğini; hız açısından 2-opt üstünlüğünü desteklemektedir.

### 5.3 Operasyonel yorum

1. Kalite öncelikli senaryolarda GA veya PSO tercih edilmelidir.
2. Gerçek zamanlı/çevrimiçi karar gerektiren senaryolarda 2-opt hesaplama süresi avantajı sunar.
3. Uygulama düzeyinde tek bir "en iyi algoritma" yerine, kalite-hız hedeflerine göre adaptif seçim daha uygundur.

## 6. Sonuç

Bu makale, standart TSP probleminden gerçek dünyaya geçişte zaman matrisi tabanlı ATSP modellemesinin gerekliliğini göstermiştir. Üç aşamalı deney hattı sayesinde parametre optimizasyonu sistematik biçimde gerçekleştirilmiş, eğitim probleminden elde edilen en iyi parametreler saha problemine aktarılmış ve 29 öğrencili gerçek zaman matrisi üzerinde doğrulanmıştır. Sonuçlar, meta-sezgisel yöntemlerin kalite, yerel arama yöntemlerinin ise hız tarafında güçlü olduğunu net biçimde ortaya koymaktadır.

## 7. Tekrarlanabilirlik ve Raporlama Dosyaları

Bu metindeki bulgular aşağıdaki çıktılara dayanmaktadır:

1. `configs/config_eil76_20260424_232832.json`
2. `results/old/tuning_progress_20260424_232923.csv`
3. `data/tuned_parameters_db.json`
4. `results/benchmark_progress_20260425_002216.csv`
5. `results/benchmark_summary_20260425_002216.csv`
6. `results/reports/FINAL_BENCHMARK_ANALYSIS_student_matrix_20260425_002309.md`
