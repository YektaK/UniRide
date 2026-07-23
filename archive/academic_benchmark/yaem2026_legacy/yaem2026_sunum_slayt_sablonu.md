# YAEM 2026 Sunum Şablonu (Slayt Slayt)

*Bu dosya, Optuna Tuning ve Benchmark analizlerinden elde edilen GERÇEK değerlerle doldurulmuş sunum şablonudur. Doğrudan kopyalayarak slaytlarınıza aktarabilirsiniz.*

---

## SLAYT 15.5: Literatür Araştırması - İleri Düzey Yerel Aramalar (ALNS & LKH)
*(Not: Önceki sunumda Slayt 15'te yer alan 2-opt ve 3-opt tablosundan hemen sonra, YAEM 2026'ya özel eklediğimiz bu modern algoritmaları açıklamak için kullanılmalıdır.)*

- **ALNS (Adaptive Large Neighborhood Search - Adaptif Büyük Komşuluk Araması):** 
  - **Mekanizma:** Mevcut rotanın büyük bir kısmını "silme (destroy)" operatörleriyle bozar ve ardından akıllı "onarma (repair)" sezgiselleriyle yeniden inşa eder. Geçmiş başarılarına göre hangi operatörün daha iyi çalıştığını öğrenir (adaptif).
  - **Rolü:** GWO ve HHO'nun bulduğu küresel çözümlerin yerel optimumlara takılmasını engelleyerek, arama uzayında devasa ve akıllı sıçramalar yapmak.
- **LKH (Lin-Kernighan Heuristic):** 
  - **Mekanizma:** 2-opt ve 3-opt algoritmalarının genelleştirilmiş, en gelişmiş halidir (k-opt). Dinamik olarak rotadan $k$ adet kenarı silip en uygun kombinasyonla yeniden bağlar.
  - **Rolü:** TSPLIB gibi literatürdeki en zorlu problemleri çözme konusunda rüştünü ispatlamış olan LKH, meta-sezgisellerin bulduğu rotayı "parlatmak (polishing)" ve son rötuşları yapmak amacıyla kullanılmıştır.

---

## SLAYT 16: Uygulama Özeti
- Problem NP-zor yapıda bir kombinatoryal optimizasyon problemidir ve aşağıdaki saf meta-sezgisel yöntemler ile bunların geliştirilmiş memetik (hibrit) türevleri kullanılarak çözülmüştür:
  - Temel Yerel Aramalar: 2-opt, 3-opt, Or-opt
  - Saf Meta-sezgiseller: Gri Kurt Optimizasyonu (GWO), Harris Şahini Optimizasyonu (HHO)
  - Memetik (Hibrit) Operatörler: GWO-ALNS, HHO-ALNS, HHO-LKH vb.
- Uygulama aşamasında, farklı topolojik boyutlardaki TSPLIB problemleri üzerinde kapsamlı bir parametre ayarlama (tuning) süreci yürütülmüştür. 
- Parametre ayarlamanın kalitesini maksimize etmek amacıyla makine öğrenmesi destekli Bayesian Optimizasyonu (Optuna TPE) yöntemi kullanılmıştır. Optuna analizleri sonucunda sentezlenen "Evrensel Parametre Setleri", modele özel hiçbir ince ayar yapılmadan, doğrudan asimetrik ulaşım süresi matrisi problemine entegre edilmiştir. 
- İstatistiksel analizler Kruskal-Wallis, ANOVA ve Wilcoxon testleriyle gerçekleştirilmiş olup, algoritmaların performansları kıyaslanmıştır.

---

## SLAYT 17: Uygulama Özeti (Fazlar)
- Elde edilen evrensel parametre seti, asimetrik gerçek dünya kısıtları içeren "Öğrenci Zaman Matrisi" problemi üzerinde 30 tekrarlı benchmark testlerine tabi tutulmuştur.

**[GÖRSEL BLOK: 4 Aşamalı Şema]**
1. **Faz 1:** Optuna TPE Tabanlı Tuning (4 TSPLIB Problemi, ~960 Deneme)
2. **Faz 2:** Modal Analiz ve Parametrik İstikrar (Evrensel Set Çıkarımı)
3. **Faz 3:** Kapsamlı Benchmark (TSPLIB Doğrulaması)
4. **Faz 4:** Gerçek Hayat Verisi Doğrulaması (Öğrenci Zaman Matrisi)

---

## SLAYT 18: Uygulama Özeti (Ön Bulgular)
- İstatistiksel bulgular, Saf (Pure) meta-sezgisel algoritmaların büyük problemlerde optimumdan saptığını, ALNS ve LKH gibi güçlü yerel arama operatörleriyle desteklenmiş **Hibrit/Memetik** versiyonların (HHO-ALNS, GWO-ALNS) ise çözüm kalitesini ve robustlığı muazzam derecede (kroA100 problemi için ~5 kat) artırdığını gösterir.
- Sentezlenen evrensel parametre seti gerçek dünya öğrenci probleminde **%100** oranında global optimuma (`314.0` skoru) sıfır varyans (sapma) ile yakınsayarak, modelin "sıfır-ayar (zero-shot) genellenebilirlik" gücünü ortaya koymaktadır.

---

## SLAYT 19: TSPLIB: Test Problemlerinin Seçimi
- Algoritmaların topolojik varyasyonlara karşı dirençlerini (robustness) test etmek için TSPLIB kütüphanesinden farklı karakterlerde 4 küçük-orta ölçekli problem seçilmiştir:
  - **berlin52:** 52 şehirli, düğümlerin belirli merkezlerde kümelendiği standart problem.
  - **eil51:** 51 şehirli, homojen dağılımlı, algoritmaları lokal optimuma çeken zorlu problem.
  - **st70:** 70 şehirli, karmaşık rotalama gerektiren ağ yapısı.
  - **kroA100:** 100 şehirli, arama uzayının boyutunun saf meta-sezgiselleri zorladığı ve hibridizasyonu mecburi kılan problem.

---

## SLAYT 20: Optuna (TPE) Tabanlı Parametre Optimizasyonu
- **Test Edilen Parametre Uzayları:**
  - **GWO (Grey Wolf Optimizer):** Sürü Boyutu (30-70), Maksimum İterasyon (150-350), Keşif Oranı, Başlangıç A Değeri.
  - **HHO (Harris Hawks Optimization):** Şahin Sayısı (30-70), Sıçrama Olasılığı, Enerji Parametreleri, Levy Uçuş Skalası.
  - **2-opt / 3-opt / Or-opt:** Çoklu Başlangıç Sayıları (1-10), Geliştirme Stratejileri (İlk/En İyi), Segment Boyutları.
  - **Memetik Operatörler (ALNS / LKH):** Silme (Remove) Oranları (0.10-0.20), Parlatma (Polish) İterasyonları (50-150).

---

## SLAYT 21: Parametrik İstikrar Analizi ve Tuning Sonuçları
- Gerçekleştirilen toplam **960 adet** yapay zeka (Optuna) destekli tuning denemesi sonucunda algoritmaların parametre karakteristiği belirlenmiştir.
- 4 problemin modal frekans analizi yapıldığında çarpıcı bir parametrik kararlılık tablosu ortaya çıkmıştır:
  - **HHO Parametreleri:** Problemlerin büyük çoğunluğunda Sıçrama Olasılığı (Jump Probability) = 0.5 kararlılık göstermiştir.
  - **ALNS Operatörü:** Silme oranı (Remove Ratio) genel olarak %15 ila %20 bandında en yüksek başarıyı sağlamıştır. İterasyon sayısı karmaşık ağlarda 150'ye dayanmıştır.

---

## SLAYT 22: Evrensel Parametre Seti - Özet

| Algoritma | Evrensel Parametre Seti |
|-----------|------------------------|
| **GWO-ALNS** | `Sürü: 70, İter: 250, Keşif: 0.4, ALNS İter: 150, ALNS Silme: %20` |
| **GWO-Pure** | `Sürü: 70, İter: 250, Keşif: 0.4` |
| **HHO-ALNS** | `Şahin: 50, İter: 250, Levy: 0.3, ALNS İter: 150, ALNS Silme: %15` |
| **HHO-Pure** | `Şahin: 50, İter: 250, Jump: 0.5, Levy: 0.3` |
| **2-opt** | `Başlangıç Sayısı: 10, İter: 2000, Strateji: İlk (First Improvement)` |
| **3-opt** | `Başlangıç Sayısı: 5, İter: 800, Strateji: İlk (First Improvement)` |
| **Or-opt** | `Başlangıç Sayısı: 5, İter: 600, Maks Segment Boyutu: 3` |

---

## SLAYT 23: İstatistiksel Benchmark Sonuçları (TSPLIB 4 Problem)

**Tablo 1: Meta-Sezgisel ve Memetik (Hibrit) Algoritmalar**

| Problem | Ölçüt | GWO-ALNS | HHO-ALNS | GWO-Pure | HHO-Pure | BKS (Optimum) |
|---------|-------|----------|----------|----------|----------|---------------|
| **berlin52** | Mean | `7542.0` | `7542.0` | `14990.5` | `19797.6` | `7542.0` |
| **eil51**    | Mean | `426.8`  | `426.9`  | `849.6`   | `1129.6`  | `426.0`  |
| **st70**     | Mean | `675.9`  | `675.4`  | `2014.0`  | `2560.7`  | `675.0`  |
| **kroA100**  | Mean | `21285.3`| `21282.3`| `108547.6`| `121342.5`| `21282.0`|

**Tablo 2: Temel Yerel Arama (Local Search) Algoritmaları**

| Problem | Ölçüt | 2-opt | 3-opt | Or-opt | BKS (Optimum) |
|---------|-------|-------|-------|--------|---------------|
| **berlin52** | Mean | `7830.6` | `7941.6` | `8026.4` | `7542.0` |
| **eil51**    | Mean | `436.3`  | `446.6`  | `448.0`  | `426.0`  |
| **st70**     | Mean | `688.3`  | `741.6`  | `740.6`  | `675.0`  |
| **kroA100**  | Mean | `21650.1`| `27692.3`| `34550.0`| `21282.0`|

**Tablo 3: Algoritmaların Çalışma Süreleri (Ortalama milisaniye - ms)**

| Problem | GWO-ALNS | HHO-ALNS | GWO-Pure | HHO-Pure | 2-opt | 3-opt | Or-opt |
|---------|----------|----------|----------|----------|-------|-------|--------|
| **berlin52** | `14242.9` | `18291.7` | `3600.4` | `2388.6` | `693.8` | `2764.7` | `856.2` |
| **eil51**    | `11850.6` | `16241.5` | `3506.9` | `2317.5` | `642.8` | `2225.6` | `817.7` |
| **st70**     | `27039.2` | `37270.5` | `3534.9` | `2709.9` | `974.8` | `7560.7` | `1246.0`|
| **kroA100**  | `81435.5` | `114810.2`| `3164.6` | `2969.4` | `1874.3`| `33060.4`| `1858.2`|

---

## SLAYT 23.5: İstatistiksel Anlamlılık Testleri (ANOVA & Wilcoxon)
- Uygulama özetinde bahsettiğimiz hipotez testleri hem TSPLIB kıyaslamalarında hem de **gerçek hayat Öğrenci Zaman Matrisi (student_matrix)** üzerinde tutarlı bir şekilde doğrulanmıştır.
- **Varyans Analizi (ANOVA):** ANOVA sonuçlarına göre algoritma türünün (Saf vs Hibrit) maliyet üzerindeki etkisi tüm problemlerde istatistiksel olarak kesin anlamlıdır ($p < 0.05$). Etki büyüklüğü ($\eta^2$) değerleri her zaman **>0.91** (Örn: kroA100 için 0.94, student_matrix için 0.91) olarak ölçülmüştür. Bu durum, tur maliyetlerindeki varyansın (değişkenliğin) muazzam bir kısmının doğrudan kullanılan algoritma türünden kaynaklandığını ispatlar.
- **Wilcoxon & Holm-Bonferroni Düzeltmesi:** Gerçek hayat problemi olan Öğrenci Zaman Matrisinde, sunuma dahil edilen **ALNS tabanlı algoritmalar ile 2-opt ve 3-opt gibi temel yerel aramalar** arasındaki performans farkı istatistiksel olarak tamamen anlamlı bulunmuştur ($p_{holm} < 0.01$). ALNS'in üstünlüğü tesadüfi değildir.
- **Temel Çıkarım:** GWO-ALNS ile HHO-ALNS arasındaki performans farkı ise istatistiksel olarak **anlamsız** bulunmuştur. Bu istatistiksel sonuç; arama kalitesinde asıl aklı ALNS operatörünün kattığını, GWO ve HHO'nun ise yalnızca ALNS'yi besleyen bir "global kâşif" rolü oynadığını matematiksel olarak ispatlar.

---

## SLAYT 24: Algoritma Kıyaslama
- Algoritmaların sonuçları incelendiğinde; büyük verilerde (örn. kroA100) Saf GWO ve HHO varyantlarının optimumdan tamamen koptuğu (121 bin maliyet), ancak ALNS hibrit (memetik) versiyonlarının 21282 optimumunu nokta atışı bulduğu gözlemlenmiştir. 
- Maliyet-fayda (Pareto) ve hesaplama yükü prensipleri gereğince, gerçek hayat uygulaması olan Öğrenci Zaman Matrisi problemine sadece;
  - **En Hızlı Çalışan Algoritmalar:** `Numba-optimize 2-opt ve 3-opt`
  - **En Kaliteli ve Robust Algoritmalar:** `GWO-ALNS ve HHO-ALNS`

---

## SLAYT 25: Öğrenci Zaman Matrisi (Doğuş Üniversitesi Verisi) – Uygulama Sonuçları

| Algoritma | En İyi | En Kötü | Ortalama | Çalışma Süresi |
|-----------|--------|---------|----------|----------------|
| **GWO-ALNS** | `314.0` | `314.0` | `314.0` | `3347 ms` |
| **HHO-ALNS** | `314.0` | `314.0` | `314.0` | `4169 ms` |
| **2-opt** | `314.0` | `320.0` | `315.7` | `610 ms` |
| **3-opt** | `314.0` | `320.0` | `317.7` | `764 ms` |

---

## SLAYT 26: Algoritma Performans Dağılımı ve Yakınsama (Grafikler)
- Aşağıdaki grafikler "student_matrix" (Öğrenci Zaman Matrisi) için sunumdaki 4 algoritmaya (HHO-ALNS, GWO-ALNS, 2-opt, 3-opt) özel olarak daraltılmış ve yüksek çözünürlüklü çizdirilmiştir.
- (Dosyaları sunumunuza sürükleyip bırakabilirsiniz.)

**Algoritma Performans Karşılaştırma Matrisi (Radar Chart):**
![Radar Chart Kıyaslama](file:///C:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/results/plots/radar_chart_yaem2026.png)

**Öğrenci Zaman Matrisi (Boxplot Karşılaştırması):**
![Boxplot Student Matrix](file:///C:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/results/plots/boxplot_student_matrix_sunum.png)

**Öğrenci Zaman Matrisi (Yakınsama Eğrisi):**
![Convergence Student Matrix](file:///C:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/results/plots/convergence_student_matrix.png)

**kroA100 Zorlu Problem Kıyaslaması (Boxplot):**
![Boxplot kroA100](file:///C:/Users/yekta/Masaüstü/AiCode/FirebaseUniRide/UniRide/academic_benchmark/yaem2026/results/plots/boxplot_kroA100.png)

## SLAYT 27: Sonuç
- Bu çalışma kapsamında Gezgin Satıcı Problemi üzerinde yapılan çok boyutlu deneyler neticesinde aşağıdaki akademik çıkarımlara ulaşılmıştır:
  - **"Saf Algoritma" Yanılgısı:** Büyük arama uzaylarında hiçbir saf meta-sezgisel tek başına kusursuz değildir. Küresel keşif gücünün yerel sömürü gücüyle (Memetik/Hibrit yapı) birleştirilmesi mutlak bir zorunluluktur.
  - **Sıfır-Ayar (Zero-Shot) Parametrik Evrensellik:** Yapay Zeka tabanlı Optuna TPE ile elde edilen parametreler, asimetrik gerçek dünyadaki öğrenci rotalama problemlerine **ek bir tuning maliyeti olmadan** (Sıfır Sapma ile %100 başarı) yüksek hassasiyetle transfer edilebilmektedir.
  - **Yerel Arama ve Meta-Sezgisel Dengesi:** Basit yerel aramalar (2-opt) hız açısından önde olsa da, karmaşık ağ yapılarında ALNS tabanlı memetik mimarilerin sahip olduğu yıkıp-yeniden-kurma (destroy/repair) bilincinin gerisinde kalmaktadır.

---

## SLAYT 28: Sonuç (Devam)
- **Gelecek Çalışmalar:** Gelecek araştırmalarda bulunan ALNS evrensel parametre setinin, Kapasite Kısıtlı Araç Rotalama (CVRP) ve Zaman Pencereli TSP (TSPTW) gibi daha karmaşık kısıtlara sahip varyasyonlara ve dinamik filolara uygulanabilirliği test edilecektir.

---

## SLAYT 29: Kaynaklar
*(Not: Önceki sunumdaki kaynakçaya ek olarak YAEM 2026 sunumunda kullanılan modern algoritmaların temel atıfları eklenmiştir.)*

- **Akiba, T., vd. (2019).** Optuna: A next-generation hyperparameter optimization framework. *Proceedings of the 25th ACM SIGKDD*. (Optuna TPE Referansı)
- **Ropke, S., & Pisinger, D. (2006).** An adaptive large neighborhood search heuristic for the pickup and delivery problem with time windows. *Transportation Science, 40*(4), 455-472. (ALNS Referansı)
- **Helsgaun, K. (2000).** An effective implementation of the Lin–Kernighan traveling salesman heuristic. *European Journal of Operational Research, 126*(1), 106-130. (LKH Referansı)
- **Mirjalili, S., vd. (2014).** Grey wolf optimizer. *Advances in Engineering Software, 69*, 46-61. (GWO Referansı)
- **Heidari, A. A., vd. (2019).** Harris hawks optimization: Algorithm and applications. *Future Generation Computer Systems, 97*, 849-872. (HHO Referansı)
- **Alweshah, M., vd. (2022).** Vehicle routing problems based on Harris Hawks Optimization. *Journal of Big Data, 9*(42).
- **Faramarzzadeh, M., & Akpınar, Ş. (2023).** A Grey Wolf Optimizer algorithm for the vehicle routing problem with time windows... *Endüstri Mühendisliği, 34*(2).
- **Huang, G., vd. (2024).** A Grey Wolf Optimizer Algorithm for Multi-Objective Cumulative Capacitated Vehicle Routing Problem... *Biomimetics, 9*(6).
- **Ke, X. (2005).** School bus selection, routing and scheduling. *University of Windsor*.
- **Peng, Z., vd. (2024).** Improved Harris Hawks Optimizer algorithm to solve the multi-depot open vehicle routing problem. *Evolutionary Intelligence, 17*.
