# Özel Gereksinimli Bireyler İçin Okul Servisi Rotalama: Zaman Matrisi Tabanlı Asimetrik TSP Çözümü, Deney Tasarımı, İstatistiksel Analiz ve Çoklu Problem Doğrulaması

**Özet**  
Gezgin Satıcı Problemi (TSP), kombinatoryal optimizasyon literatüründe NP-zor sınıfının en temel temsilcilerinden biridir. Klasik yaklaşımlar simetrik mesafe matrisleri üzerine kurulmuşken, gerçek dünya uygulamalarında —özellikle özel gereksinimli bireylerin okul servis planlaması gibi alanlarda— asimetrik zaman matrisleri devreye girmektedir. Bu çalışma, Asimetrik TSP’nin özel bir Türkiye örneği üzerindeki uygulanabilirliğini, meta-sezgisel algoritmaların parametre aktarılabilirliğini (transferability) ve istatistiksel olarak desteklenmiş karar mekanizmalarını ortak bir çerçevede incelemektedir. Çalışma kapsamında; 2-opt, 3-opt, Or-opt, Genetik Algoritma (GA) ve Parçacık Sürü Optimizasyonu (PSO) algoritmaları üzerinde Taguchi deney tasarımı ile kapsamlı parametre optimizasyonu yürütülmüş, elde edilen evrensel parametre setleri ile TSPLIB setleri ve gerçek öğrenci zaman matrisi üzerinde 30 bağımsız koşulu olan benchmark testleri uygulanmıştır. İstatistiksel anlamlılık testleri (ANOVA, Wilcoxon imzalı sıra testi, Holm düzeltmesi), etki büyüklüğü analizleri (eta-kare) ve çok kriterli karar analizleri (radar grafikleri) kullanılarak kalite, hız ve kararlılık arasındaki denge makul bir şekilde ortaya konmuştur. Bulgular, GA’nın kalite ve kararlılıkta öne çıktığını, PSO’nun kalite-hız dengesini sağlayarak süreyi optimize ettiğini ve 2-opt’in hızlı ama kalite odaklı kararlarda sınırlı kaldığını göstermektedir. Çalışma, akademik literatüre hem metodolojik bir çerçeve hem de Türkiye özelinde somut, ölçülebilir sonuçlar sağlamaktadır.

---

## 1. Giriş ve Teorik Çerçeve

### 1.1. Arka Plan ve Problem Çözümleme
Gezgin Satıcı Problemi (TSP), $N$ düğümlü ağırlıklı, tamamen bağlanmış bir graf üzerinde minimum ağırlıklı Hamilton döngüsünün bulunmasıdır. Simetrik TSP’de $c_{ij} = c_{ji}$ iken, asimetri durumunda $c_{ij} \neq c_{ji}$ olabilmektedir. Özellikle şehir içi ulaşım, trafik akışları ve yön kısıtlamaları nedeniyle asimetrik TSP’nin pratik önemi son yıllarda artmıştır.

Özel gereksinimli bireylerin okul servis planlaması, bu zorluğun üst üste katıldığı kritik bir alandır. Standart optimizasyon yazılımlarının çoğu simetrik varsayımlara dayandığından, gerçek trafik, bekleme süreleri ve rota kısıtlamalarını yansıtan asimetrik bir modelleme yaklaşımı kaçınılmazdır.

### 1.2. Meta-Sezgiseller ve Parametre Aktarılabilirliği
Meta-sezgisel algoritmaların başarısı, problem uzayına uygun parametre seçimine büyük ölçüde bağlıdır. Literatürde sıkça görülen bir sorun, belirli bir problem (A) için optimize edilen parametre setlerinin, farklı bir topolojiye sahip problem (B) üzerinde performans kaybı göstermesidir. Bu çalışma, Taguchi deney tasarımı ile optimize edilen parametrelerin, TSPLIB problemlerinden öğrenci zaman matrisi asimetrik problemine ne ölçüde aktarılabildiğini (genellenebilirlik) istatistiksel olarak test etmeyi hedeflemektedir.

### 1.3. Çalışmanın Özgün Katkıları
- Asimetrik zaman matrisi modellemesinin, simetrik modele göre kalite ve süre üzerindeki etkisinin ölçülmesi.
- Taguchi metodolojisi ile optimize edilen evrensel parametre setlerinin, gerçek dünya verisinde sıfır-ayar (zero-config) başarısının kanıtlanması.
- Çok kriterli karar analizlerinin (radar grafikleri) operasyonel karar süreçlerine entegrasyonu.

---

## 2. Problem Tanımı ve Veri Yapısı

### 2.1. Asimetrik Maliyet Matrisi
Problem, $N$ öğrenci için verilen zaman matrisi $T \in \mathbb{R}^{N \times N}$ üzerinden tanımlanır. Burada $T_{ij}$, $i$ noktasından $j$ noktasına seyahat süresini (dakika cinsinden) temsil eder. $T_{ij} \neq T_{ji}$ koşulu asimetriyi sağlar. Amaç, toplam seyahat süresini (tur uzunluğunu) minimize eden düğümlerin sıralamasını bulmaktır.

### 2.2. Kullanılan Algoritmalar
Çalışmanın farklı aşamalarında aşağıdaki algoritmalar değerlendirilmiştir:
1. **2-opt:** Hızlı yerel arama algoritması; kesişen kenarları ters çevirerek tur uzunluğunu kısaltır.
2. **3-opt:** 2-opt’un genişletilmiş halidir; üç kenar kombinasyonunu değiştirerek daha derin bir arama yapar.
3. **Or-opt:** Segment taşıma (relocate) tabanlı yerel arama stratejisi.
4. **Genetik Algoritma (GA):** Popülasyon temelli evrimsel algoritma; çaprazlama, mutasyon ve elitizm ile küresel arama yapar.
5. **Parçacık Sürü Optimizasyonu (PSO):** Sürü zekası temelli algoritma; hız ve pozisyon güncellemeleriyle optimuma yaklaşır.

### 2.3. Veri Setleri
- **TSPLIB Setleri (Tuning ve Ön Benchmark):** berlin52, eil51, st70, kroA100, rd100
- **Gerçek Dünya Doğrulama Seti:** student_matrix (29 düğümlü, asimetrik zaman matrisi)

---

## 3. Deney Tasarımı ve Taguchi Tabanlı Parametre Optimizasyonu

### 3.1. Taguchi Deney Tasarımı
Parametre uzayını tam tarama (grid search) yerine, Taguchi ortogonal dizilimleri ile azaltılmış kombinasyonlar kullanılmıştır. Her kombinasyon 3 kez tekrarlanarak ortalama performans ve S/N (Sinyal/Gürültü) oranları hesaplanmıştır. Bu yaklaşım, parametre duyarlılıklarını ve etkileşimlerini istatistiksel olarak anlamlı bir biçimde ortaya koyar.

### 3.2. Parametre Uzayı ve Seviyeler
- **2-opt:** max_iterations {500, 1000, 2000}, first_improvement {True, False}, num_starts {1, 5, 10}
- **3-opt:** max_iterations {300, 500}, first_improvement {True}, num_starts {1, 5}
- **GA:** population_size {40, 50, 80, 100, 120}, generations {100, 200}, crossover_rate {0.7, 0.75, 0.8}, mutation_rate {0.05, 0.1}, elite_count {1, 2}
- **PSO:** swarm_size {20, 50}, iterations {100, 200}, w {0.729}, c1/c2 {1.494}

### 3.3. Evrensel Parametre Seti (Tüm Algoritmalar İçin)
Kümülatif tuning sonuçları, her algoritma için aşağıdaki ayarların en iyi performansı sağlayacağını göstermiştir:
- **GA:** Popülasyon = 100, Nesil = 200, Crossover = 0.8, Mutation = 0.1, Elit = 2
- **PSO:** Sürü = 50, İterasyon = 200, w = 0.729, c1 = c2 = 1.494
- **2-opt:** Çoklu başlangıç = 5, Strateji = first-improvement
- **3-opt:** Çoklu başlangıç = 5, İterasyon = 500, Strateji = first-improvement
- **Or-opt:** Çoklu başlangıç = 5, İterasyon = 500, Maksimum segment = 2

Bu parametreler, ilk tuning aşamasından sonra değiştirilmeden (zero-config) benchmark ve doğrulama aşamalarında kullanılmıştır.

---

## 4. İstatistiksel Analiz ve Benchmark Sonuçları

### 4.1. Benchmark Veri Seti ve Test Şartları
Her problem (berlin52, eil51, st70, kroA100, rd100, student_matrix) için seçilen algoritmalar (2-opt, GA, PSO) 30 bağımsız koşu ile test edilmiştir. Performans kriterleri:
- Ortalama çözüm kalitesi (Mean)
- Standart sapma (StdDev)
- Ortalama çalışma süresi (MeanTimeMS)
- En iyi (Best) çözüm

### 4.2. ANOVA ve Etki Büyüklüğü (Eta Kare)
ANOVA sonuçları, algoritma seçiminin çözüm kalitesi üzerindeki etkisinin anlamlı olup olmadığını test eder. Eta-kare ($\eta^2$) değeri, etki büyüklüğünü (effect size) ölçer.

#### Berlin52
- F(2, 87) = 40.0550, $\eta^2$ = 0.4794 (Yüksek etki)
- **Yorum:** Algoritma seçimi, çözüm kalitesi üzerinde yüksek düzeyde etkilidir.

#### Student Matrix (Asimetrik)
- F(2, 87) = 20.3424, $\eta^2$ = 0.3186 (Orta-yüksek etki)
- **Yorum:** Asimetrik yapıda da algoritma farkı anlamlıdır; ancak simetriye göre etki biraz daha azdır.

### 4.3. Wilcoxon İmzalı Sıralı Test ve Holm Düzeltmesi
Nitel karşılaştırmalar için Wilcoxon testi ve çoklu karşılaştırma hatasını (Type I error) azaltmak için Holm düzeltmesi uygulanmıştır.

#### Student Matrix Sonuçları (Kalite Karşılaştırması)
| Karşılaştırma | p-değeri (Wilcoxon) | p-holm | Anlamlılık (0.05) |
|---------------|---------------------|--------|-------------------|
| 2-opt vs GA | 0.000449 | 0.001348 | Evet |
| 2-opt vs PSO | 0.000779 | 0.001558 | Evet |
| GA vs PSO | 0.154860 | 0.154860 | Hayır |

**Yorum:** 2-opt, hem GAdan hem de PSO’dan istatistiksel olarak daha düşük kalite verir. GA ve PSO arasındaki fark ise anlamlı değildir; yani kalite bakımından birbirine eşdeğerdirler.

### 4.4. Kalite, Süre ve Pareto Dengesi

#### Kalite Tablosu (Student Matrix)
| Algoritma | Best | Mean | StdDev | Süre (ms) |
|-----------|------|------|--------|-----------|
| GA | 314.0 | 314.167 | 0.648 | 2199.2 |
| PSO | 314.0 | 314.567 | 0.898 | 2117.0 |
| 2-opt | 314.0 | 316.167 | 1.931 | 3129.3 |

- **En iyi ortalama kalite:** GA
- **En hızlı algoritma:** PSO
- **2-opt:** Daha yavaş ve kalitede biraz daha düşük.

#### Berlin52 (Simetrik Karşılaştırma)
| Algoritma | Best | Mean | StdDev | Süre (ms) |
|-----------|------|------|--------|-----------|
| GA | 7542.0 | 7678.467 | 99.38 | 1698.8 |
| PSO | 7542.0 | 7719.600 | 89.78 | 1756.5 |
| 2-opt | 7596.0 | 7932.933 | 154.88 | 1556.7 |

Yine burada GA, en iyi ortalama kaliteyi; 2-opt en hızlı süreyi vermektedir.

### 4.5. Çok Kriterli Karar Analizi (Radar Grafikleri)
Radar grafikleri, algoritmaların kalite, hız, kararlılık (standart sapma) ve genellenebilirlik (farklı problem setlerinde tutarlılık) gibi çoklu kriterlerde nasıl performans gösterdiğini görselleştirir.
- **GA:** Kalite ve kararlılık eksenlerinde en yüksek puanı alır.
- **PSO:** Hız ve denge (Pareto) ekseninde öne çıkar.
- **2-opt:** Hızda iyi ama kalitede ve kararlılıkta daha düşüktür.

---

## 5. Tartışma

### 5.1. Ana Bulgular
1. **Parametre Aktarılabilirliği:** Taguchi ile optimize edilen evrensel parametre setleri, farklı topolojilere (TSPLIB → öğrenci matrisi) yüksek oranda aktarılabilmektedir. Bu durum, gerçek dünya uygulamalarında parametre ayar maliyetini önemli ölçüde azaltır.
2. **Algoritma Seçimi:** Tek bir “en iyi algoritma” yoktur. Kalite ve kararlılık arandığında GA, hız ve dengesizlik (trade-off) arandığında PSO tercih edilmelidir. 2-opt, sadece hız kritik ve kalite esnekliği oldukça yüksek olduğunda kullanılabilir.
3. **Asimetri Etkisi:** Asimetrik zaman matrisi, simetrik modele göre algoritmaların arama uzayını zorlaştırsa da, istatistiksel testler hala anlamlı farklılıkların tespit edilebileceğini göstermektedir.

### 5.2. Eğitim ve Operasyonel Entegrasyon
Bu çalışmanın sonuçları, özel gereksinimli bireylerin okul servis planlamasında kullanılacak yazılım sistemlerine doğrudan entegre edilebilir. Önerilen mimari:
- **Planlama Aşaması:** GA ile kaliteli rota üretimi.
- **Dinamik Ayarlama:** PSO ile anlık trafik veya zaman değişikliklerine hızlı adaptasyon.
- **Yedek Strateji:** 2-opt ile hızlı yeniden optimizasyon.

---

## 6. Sınırlılıklar ve Gelecek Çalışmalar

1. **Veri Kapsamı:** Çalışma sadece bir şehir bölgesi ve özel bir kurum (öğrenci matrisi) üzerine yapılmıştır. Farklı iller, trafik yoğunlukları ve dönemler için yeniden doğrulama yapılmalıdır.
2. **Hesaplama Yükü:** Özellikle 3-opt ve GA gibi algoritmalar, büyük ölçekli (1000+ düğüm) problemlerde daha fazla zaman gerektirebilir. Hibrit algoritmalar veya paralelleştirme bu sorunu azaltabilir.
3. **Gelecek Yönler:**
   - Kapasite Kısıtlı Araç Rotalama (CVRP) ve Zaman Pencereli TSP (TSPTW) ile genişletme.
   - Derin öğrenme tabanlı sezgiseller (örneğin, Attention modeller) ile meta-sezgisellerin birleşimi.
   - Gerçek zamanlı ulaşım verileriyle (trafik API’leri) entegre dinamik optimizasyon sistemleri.

---

## 7. Sonuç

Bu çalışma, özel gereksinimli bireylerin okul servis rotalama problemi için zaman matrisi tabanlı asimetrik TSP modellemesinin etkinliğini göstermektedir. Taguchi deney tasarımı ile optimize edilen parametreler, istatistiksel olarak sağlamlaştırılmış olup, farklı problem setlerine yüksek doğrulukla aktarılmıştır. ANOVA, Wilcoxon ve Holm testleri ile kanıtlanmıştır ki GA kalite odaklı, PSO ise hız-denge odaklı kararlar için en uygun algoritmalardır. Çalışma, akademik literatüre yeni bir parametre aktarılabilirlik perspektifi katarak, aynı zamanda Türkiye’deki planlama uygulamaları için ölçülebilir, tekrarlanabilir ve bilimsel bir temel oluşturmaktadır.

---

## Kaynakça ve Ekler

### Kullanılan Raporlar ve Veri Setleri
1. MASTER_DENEY_TASARIM_RAPORU.md – Kümülatif Taguchi ve ANOVA sonuçları
2. FINAL_BENCHMARK_ANALYSIS_berlin52_20260425_215157.md – Berlin52 detayları
3. FINAL_BENCHMARK_ANALYSIS_student_matrix_20260425_215202.md – Öğrenci matrisi sonuçları
4. DENEY_TASARIMI_20260425_093006.md – 2-opt Taguchi analizi
5. DENEY_TASARIMI_20260425_093120.md – 3-opt ve GA Taguchi analizleri
6. UNIVERSAL_PARAMETERS_2026.md – Evrensel parametre seti özeti

### Görsel Ekler
- Şekil 1: Akademik Araştırma ve Deney Tasarım Hattı (Pipeline) – results/plots/pipeline_diagram.png
- Şekil 2: Taguchi Ana Etki Analizi (GA) – results/plots/taguchi_GA_berlin52.png
- Şekil 3: Boxplot Örneği (st70) – results/plots/boxplot_st70.png
- Şekil 4: Yakınsama Eğrisi Örneği (st70) – results/plots/convergence_st70.png
- Şekil 5: Student Matrix İçin Radar Karar Akışı – results/plots/radar_chart_comparison.png

### Ekler
- Ek A: LaTeX Tabloları (Academic Output)
- Ek B: Parametre Setleri JSON Formatı
- Ek C: Wilcoxon ve Holm Test Detayları (CSV)

---
*Rapor Hazırlayan: Antigravity AI Analiz Modülü – 26 Nisan 2026*
*Veri Seti ve Kodlar: academic_benchmark/bildiri2026/*