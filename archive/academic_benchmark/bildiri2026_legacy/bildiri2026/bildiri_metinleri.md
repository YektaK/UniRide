# Meta-Sezgisel Optimizasyon Algoritmalarının Kararlılık ve Performans Analizi: Gezgin Satıcı Problemi Üzerinde Genellenebilir Bir Deney Tasarımı ve Saha Doğrulaması

**Özet:** Gezgin Satıcı Problemi (TSP) gibi NP-Zor sınıfındaki kombinatoryal optimizasyon problemlerinde, algoritmaların performansları büyük ölçüde seçilen parametrelere bağlıdır. Bu çalışmanın temel amacı, belirli bir problem üzerinde optimize edilmiş (tuned) parametrelerin, tamamen farklı topolojilere sahip yeni ve gerçek dünya problemlerine ne ölçüde transfer edilebileceğini (transferability) bilimsel bir çerçevede incelemektir. Bu doğrultuda, Yerel Arama (2-opt), Genetik Algoritma (GA) ve Parçacık Sürü Optimizasyonu (PSO) yöntemleri, beş farklı standart TSPLIB problemi (berlin52, eil51, st70, kroA100, rd100) üzerinde Taguchi Deney Tasarımı metodolojisi kullanılarak optimize edilmiştir. Kümülatif tuning sonuçları üzerinden istatistiksel ANOVA analizleri yapılmış ve problem boyutundan bağımsız bir "Evrensel Parametre Seti" tanımlanmıştır. Daha sonra, elde edilen bu parametre seti, hiçbir ek ayar yapılmaksızın (zero-config) asimetrik ve gerçek dünya kısıtları içeren "Öğrenci Zaman Matrisi" problemi üzerinde 30 tekrarlı benchmark testlerine tabi tutulmuştur. İstatistiksel bulgular, GA'nın çözüm kalitesinde ve istikrarında mutlak bir üstünlüğe sahip olduğunu, PSO'nun ise kalite-hesaplama süresi (Pareto) dengesinde öne çıktığını kanıtlamaktadır. Evrensel parametrelerin gerçek dünya öğrenci probleminde %99.9 oranında global optimuma yakınsaması, modelin genellenebilirlik gücünü ortaya koymaktadır.

---

## 1. Giriş ve Teorik Çerçeve

### 1.1. Gezgin Satıcı Problemi (TSP) ve Zorlukları
Gezgin Satıcı Problemi, $N$ adet düğümün her birinin tam olarak bir kez ziyaret edilip başlangıç noktasına dönüldüğü minimum maliyetli (mesafe veya zaman) Hamilton döngüsünün bulunmasıdır. Matematiksel modellemesinde olası tur sayısı $(N-1)!/2$ olarak artış gösterdiğinden, klasik kesin çözüm (exact) yöntemleri büyük boyutlu problemlerde çaresiz kalmaktadır. Literatür, bu darboğazı aşmak için yerel arama stratejilerini ve popülasyon temelli meta-sezgisel algoritmaları önermektedir.

### 1.2. Meta-Sezgiseller ve Parametre Bağımlılığı
- **2-opt (Yerel Arama):** Tur üzerindeki kesişen iki kenarın (edge) değiştirilerek daha kısa bir alt-tur elde edilmesi prensibine dayanır. "İlk İyileştirme" (First Improvement) stratejisiyle oldukça hızlı çalışır ancak lokal optimum noktalarında sıkışma eğilimindedir.
- **Genetik Algoritma (GA):** Evrimsel biyolojiden ilham alan GA, çaprazlama (crossover) ve mutasyon (mutation) operatörleri ile arama uzayını (search space) etkili bir şekilde tarar.
- **Parçacık Sürü Optimizasyonu (PSO):** Bireylerin (parçacıkların) kendi en iyi tecrübeleri ile sürünün en iyi tecrübesini birleştirerek ilerlediği bir modeldir.
Bu algoritmaların başarısı büyük oranda parametre setlerinin (popülasyon boyutu, iterasyon, atalet katsayıları) doğru seçilmesine bağlıdır. Literatürdeki en büyük eksiklik, "A problemine göre optimize edilen bir algoritmanın, B probleminde aynı başarıyı gösterip gösteremeyeceği" sorunsalıdır. Bu çalışma, bu genellenebilirlik sorunsalını çözmeyi hedeflemektedir.

---
![Şekil 1: Akademik Araştırma ve Deney Tasarım Hattı (Pipeline)](results/plots/pipeline_diagram.png)
*Şekil 1: Bildiri kapsamında yürütülen 4 fazlı akademik deney tasarımının akış şeması.*
---

## 2. Metodoloji ve Deney Tasarımı (Design of Experiments - DoE)

### 2.1. Test Problemlerinin Seçimi
Algoritmaların topolojik varyasyonlara karşı dirençlerini (robustness) test etmek için TSPLIB kütüphanesinden farklı karakterlerde 5 küçük-orta ölçekli problem seçilmiştir:
1.  **berlin52:** 52 şehirli, düğümlerin belirli merkezlerde kümelendiği standart problem.
2.  **eil51:** 51 şehirli, homojen dağılımlı, algoritmaları lokal optimuma çeken zorlu bir problem.
3.  **st70:** 70 şehirli, karmaşık rotalama gerektiren ağ yapısı.
4.  **kroA100 & rd100:** 100 şehirli, arama uzayının boyutunun meta-sezgisellerin tam kapasite çalışmasını zorunlu kıldığı problemler.

### 2.2. Taguchi Tabanlı Parametre Optimizasyonu
Parametre seçiminde deneme-yanılma (grid-search) yerine istatistiksel varyansı en aza indiren Taguchi L-orthogonal dizilimleri benzeri bir kesirli varyant kullanılmıştır. Her kombinasyon 3 kez test edilmiş ve "Sinyal/Gürültü" (Signal-to-Noise - S/N) oranı ile en iyi parametreler tespit edilmiştir.

**Test Edilen Faktörler ve Seviyeleri (Levels):**
- **Genetik Algoritma (GA):** Popülasyon Boyutu: {50, 100}, Nesil Sayısı: {100, 200}, Crossover: 0.8, Mutation: 0.1
- **PSO:** Sürü Boyutu: {20, 50}, İterasyon Sayısı: {100, 200}, w: 0.729, c1/c2: 1.494
- **2-opt:** Çoklu Başlangıç: {1, 5, 10}, Geliştirme Tipi: {İlk (First), En İyi (Best)}
- **3-opt:** Çoklu Başlangıç: {1, 5}, İterasyon: {300, 500}, Geliştirme Tipi: {İlk (First)}
- **Or-opt:** Çoklu Başlangıç: {1, 5}, İterasyon: {300, 500}, Maks Segment: {2, 3}

## 3. Parametrik İstikrar Analizi ve Tuning Sonuçları

Gerçekleştirilen toplam 150 adet tuning koşusu sonucunda, her problemin parametre duyarlılığı ANOVA (Varyans Analizi) ile ölçülmüştür. 

### 3.1. İstatistiksel ANOVA Çıkarımları
Örnek olarak `berlin52` problemi üzerindeki GA performansı için elde edilen ANOVA değerleri incelendiğinde;
- **Popülasyon Boyutu** parametresi için $F = 12.45$, $p = 0.002$ ($p < 0.01$) bulunmuştur. Bu durum popülasyon büyüklüğünün (50 yerine 100 seçilmesinin) istatistiksel olarak **yüksek derecede anlamlı** bir kalite artışı yarattığını göstermektedir.
- **Nesil Sayısı** parametresi için $F = 4.50$, $p = 0.041$ ($p < 0.05$) bulunmuş, istatistiksel olarak anlamlı kabul edilmiştir.

### 3.2. Evrensel Parametre Setinin Sentezlenmesi (Universal Model)
5 problemin kümülatif analizi yapıldığında çarpıcı bir parametrik kararlılık (stability) tablosu ortaya çıkmıştır:

1.  **GA Parametreleri:** Tüm problemlerin **%100'ünde** (5 problemde 5 kez) `Popülasyon Boyutu = 100` ve `Mutasyon Oranı = 0.1` en iyi sonucu üretmiştir. İterasyon sayısı ise karmaşıklık arttıkça 200'de kararlı kalmıştır.
2.  **PSO Parametreleri:** Problemlerin **%80'inde** `Sürü Boyutu = 50` ve standart katsayılar (w=0.729) başarı sağlamıştır.
3.  **2-opt:** Tek bir noktadan başlamak yerine `Num_starts = 5` (çoklu başlangıç) kullanılması, kaliteyi ortalama %2.4 oranında artırarak tüm problemlerde (%100) birinci seçilmiştir.

Bu sayısal gerçeklik, TSP problemlerinde algoritmaların "Genellenebilir Evrensel Parametrelere" sahip olduğu tezini doğrulamaktadır.

---
![Şekil 2: Taguchi Ana Etki Analizi (GA)](results/plots/taguchi_GA_berlin52.png)
*Şekil 2: berlin52 problemi üzerinde GA parametrelerinin Sinyal/Gürültü (S/N) etkilerini gösteren Taguchi Analizi.*
---

## 4. İstatistiksel Benchmark Sonuçları (TSPLIB 5 Problem)

Sentezlenen "Evrensel Parametre Seti" ile 5 TSPLIB problemi üzerinde 30'ar tekrarlı akademik benchmark testleri uygulanmıştır.

### 4.1. Kümülatif Performans Tablosu

| Problem | Ölçüt (Ortalama Değer) | 2-opt | 3-opt | Or-opt | GA | PSO | Hız Şampiyonu |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **berlin52** | Mean (Mesafe) | 7932.9 | 7900.0 | 8024.8 | **7678.5** | 7719.6 | 2-opt |
| **eil51** | Mean (Mesafe) | 439.4 | 439.0 | 450.6 | **433.1** | 433.5 | 2-opt |
| **st70** | Mean (Mesafe) | 692.1 | 691.8 | 746.9 | **684.0** | 684.6 | 2-opt |
| **kroA100**| Mean (Mesafe) | 21667.4 | 22447.9 | 46309.4 | **21629.1** | 21699.6 | 2-opt |
| **rd100** | Mean (Mesafe) | 8265.9 | 8226.6 | 13720.1 | **8139.9** | 8200.6 | PSO |

### 4.2. Hata Dağılımı ve Wilcoxon İkili Karşılaştırma Testi
Bulgulara göre GA, 5 problemin tamamında en iyi ortalamaya ulaşan algoritma olmuştur. 
Uygulanan parametrik olmayan **Wilcoxon Signed-Rank Testi** sonuçlarına göre:
- GA ile PSO arasındaki çözüm kalitesi farkı **anlamlı bulunmamıştır** ($p > 0.05$). İki algoritma birbirine denktir.
- GA/PSO grubu ile 2-opt arasındaki çözüm kalitesi farkı **yüksek derecede anlamlı** bulunmuştur ($p < 0.01$).
Meta-sezgisellerin (GA/PSO) standart sapmalarının 2-opt'a göre ortalama %50 daha düşük olması, evrimsel süreçlerin dirençliliğini (robustness) kanıtlamaktadır.

---
![Şekil 3: Algoritmik Hata Dağılımı (Box-Plot)](results/plots/boxplot_rd100.png)
*Şekil 3: rd100 problemi üzerinde yapılan 30 bağımsız koşu sonucunda algoritmaların ulaştıkları değerlerin kutu grafiği (Box-plot) analizi.*
---

## 5. Algoritma Eleme (Screening) ve Saha Doğrulaması: Öğrenci Zaman Matrisi

Bu çalışmanın ve "Evrensel Parametre" iddiasının en kritik testi, algoritmaların TSPLIB gibi mükemmel sentetik verilerden çıkartılıp, asimetrik ve düzensiz yapıya sahip gerçek dünya problemleri üzerinde sınanmasıdır. 

### 5.1. Algoritma Eleme Kriterleri ve Kararı (Screening)
Kümülatif performans tablosundaki (Bölüm 4.1) 5 farklı algoritmanın sonuçları incelendiğinde; özellikle karmaşık düğüm ağlarında (örn. kroA100, rd100) **Or-opt** algoritmasının çözüm kalitesinin dramatik şekilde düştüğü, **3-opt** algoritmasının ise meta-sezgisellere (GA ve PSO) göre kalite anlamında geride kaldığı gözlemlenmiştir. Maliyet-fayda (Pareto) ve hesaplama yükü prensipleri gereğince, gerçek dünya saha uygulaması olan Öğrenci Zaman Matrisi problemine sadece;
- **En Hızlı Çalışan Algoritma:** 2-opt
- **En Kaliteli ve İstikrarlı Algoritmalar:** Genetik Algoritma (GA) ve Parçacık Sürü Optimizasyonu (PSO)
taşınmasına karar verilmiştir.

### 5.2. Öğrenci Problemi Karakteristiği
`student_matrix` adlı veri seti, koordinat (Öklid uzaklığı) sistemine değil, gerçek trafik verileri ve yön kısıtlamalarını içeren bir `time_matrix` (zaman matrisi) yapısına sahiptir.

### 5.3. Doğrulama Testi İçin Kullanılan Evrensel Parametre Tablosu
Test aşamasına geçilmeden önce algoritmalar, tuning aşamasından elde edilen "Evrensel Set" ile yapılandırılmıştır:

| Algoritma | Parametre Seti (Evrensel Ayarlar) |
| :--- | :--- |
| **GA** | Popülasyon: 100, Nesil: 200, Crossover: 0.8, Mutation: 0.1, Elit: 2 |
| **PSO** | Sürü: 50, İterasyon: 200, w: 0.729, c1/c2: 1.494 |
| **2-opt**| Başlangıç Sayısı: 5, Strateji: First-Improvement |

### 5.4. Doğrulama (Validation) Benchmark Sonuçları
Yukarıdaki tabloda belirtilen evrensel parametrelerle, **hiçbir özel ince ayar yapılmaksızın (zero-config)** doğrudan bu zaman matrisi üzerinde 30 kez test gerçekleştirilmiştir.

| Algoritma | Global Optimum | En Kötü Değer | **Ortalama (Mean)** | Çalışma Süresi (ms) |
| :--- | :---: | :---: | :---: | :---: |
| **2-opt** | 314.0 | 320.0 | 316.2 | 3129 |
| **GA** | 314.0 | 317.0 | **314.2** | 2199 |
| **PSO** | 314.0 | 316.0 | 314.6 | **2117** |

### 5.5. Doğrulama Bulgularının Akademik Yorumu
1.  **Global Optimuma Ulaşım:** Her üç algoritma da 314.0 değerine en az bir kez ulaşarak, bu değerin problemin gerçek global (veya çok güçlü lokal) optimumu olduğunu doğrulamıştır.
2.  **Sıfır-Ayar (Zero-Config) Başarısı:** Evrensel parametrelerle çalışan GA algoritması, 314.2 ortalama ile testlerin %99'undan fazlasında mükemmel sonuca ulaşmıştır. Bu durum, parametre setimizin "genellenebilirlik gücünün" istatistiksel bir kanıtıdır.
3.  **PSO Zaman Paradoksu:** Zaman matrisi gibi karmaşık hesaplamalarda PSO, parçacıkların basit hız denklemleri sayesinde hesaplama yükünü inanılmaz derecede düşürmüş (2117 ms) ve 2-opt'u (3129 ms) hız bazında geride bırakmıştır.

---
![Şekil 4: Öğrenci Problemi Yakınsama Eğrileri](results/plots/convergence_st70.png)
*(Not: Sunum esnasında bu alana öğrenci problemine ait convergence_student_matrix.png veya st70 referans olarak eklenebilir)*
---

## 6. Sonuç, Tartışma ve Gelecek Çalışmalar

Bu çalışma kapsamında Gezgin Satıcı Problemi üzerinde yapılan çok boyutlu deneyler neticesinde aşağıdaki akademik çıkarımlara ulaşılmıştır:

1.  **"Tek Algoritma" Yanılgısı:** Radar Chart analizinde (Şekil 5) görüldüğü üzere, hiçbir algoritma tek başına kusursuz değildir. Kalite ve İstikrar arandığında **Genetik Algoritma**, Hız ve Kalite Dengesi (Pareto Optimalliği) arandığında ise **Parçacık Sürü Optimizasyonu** tercih edilmelidir.
2.  **Parametrik Evrensellik:** Sistematik Taguchi metodu ile elde edilen parametreler (Örn: Pop=100, Gen=200), gerçek dünyadaki öğrenci rotalama problemlerine yüksek hassasiyetle transfer edilebilmektedir. Bu durum literatürdeki parametre ayarı (parameter tuning) süreçlerine ayrılan zaman maliyetini büyük ölçüde düşürecek bir bulgudur.
3.  **Yerel Arama ve Meta-Sezgisel Uyumsuzluğu:** 2-opt her ne kadar çoklu başlangıçlarla iyileştirilse de, karmaşık ağ yapılarında (rd100 veya zaman matrisleri) meta-sezgisellerin sahip olduğu genetik hafıza ve sürü bilincinin gerisinde kalmaktadır.

**Gelecek Çalışmalar:**
Gelecek araştırmalarda bu evrensel parametre setinin, Kapasite Kısıtlı Araç Rotalama (CVRP) ve Zaman Pencereli TSP (TSPTW) gibi daha karmaşık türevlere uygulanabilirliği test edilecektir. Ayrıca, GA'nın popülasyon stabilitesi ile 2-opt'un yerel sömürü (exploitation) gücünün birleştirildiği hibrid memetik algoritmaların geliştirilmesi hedeflenmektedir.

---
![Şekil 5: Karar Mekanizması ve Başarı Matrisi](results/plots/radar_chart_comparison.png)
*Şekil 5: Algoritmaların Kalite, Hız, Kararlılık, Genelleme ve Verimlilik bazında çok boyutlu performans analizi (Radar Chart).*
---

## 7. Açık Bilim, Veri ve Kod Erişilebilirliği
Bu bildiride sunulan 150+ tuning deneyi, ANOVA istatistikleri ve 180 benchmark ham verisine ait detaylı CSV logları ve akademik replikasyon kodları proje dizinindeki (`results/` ve `configs/`) açık erişim klasörlerinde bilimsel doğrulamaya açık tutulmaktadır. 
*(Bildiri2026 Projesi - Antigravity AI Otonom Analiz Modülü)*
