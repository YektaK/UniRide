# Özel Gereksinimli Bireyler İçin Okul Servisi Rotalama Problemi
## Uygulama Özeti ve Analiz Raporu (YAEM 2026)

Bu belge, önceki çalışmalardaki (ISARC) temel kurgunun üzerine inşa edilen ve **YAEM 2026** kongresi için yapay zeka ve meta-sezgisel hibrit yaklaşımlarıyla modernize edilen metodolojinin uygulama özetini içermektedir.

---

### 1. Çalışmanın Amacı ve Genel Çerçeve
Uygulamanın temel bilimsel amacı; belirli standart test problemleri (TSPLIB) üzerinde makine öğrenmesi destekli hiper-parametre optimizasyonu kullanılarak eğitilen algoritmaların, tamamen farklı ağ topolojisine ve asimetrik (gidiş-dönüş süreleri farklı) kısıtlara sahip **Gerçek Dünya Öğrenci Zaman Matrisi** problemleri üzerindeki genellenebilirlik (transfer edilebilirlik) gücünü test etmektir.

Çalışma, geleneksel istatistiksel deney tasarımları yerine, yapay zeka güdümlü bir mimari ile **4 aşamalı (faz) bir boru hattı (pipeline)** olarak yürütülmüştür:

- **Faz 1 - Bayesian Tuning (Optuna TPE):** Seçili TSPLIB problemleri üzerinde algoritmaların hiper-parametre uzayları Optuna'nın TPE (Tree-structured Parzen Estimator) modeli ile akıllı şekilde (kendi hatalarından öğrenerek) taranmıştır.
- **Faz 2 - Evrensel Set Çıkarımı (Modal Analiz):** Farklı problemlerde elde edilen en başarılı parametre kümelerinin frekansları (modları) analiz edilerek, problem boyutundan ve topolojiden bağımsız, genellenebilir bir **"Evrensel Parametre Seti"** sentezlenmiştir.
- **Faz 3 - Kapsamlı Benchmark (TSPLIB):** Algoritmalar, bu evrensel parametre setini (ek bir ince ayar yapılmaksızın) kullanarak zorlu standart test problemlerini çözmek üzere benchmark testine (her algoritma için 30 tekrarlı) tabi tutulmuştur.
- **Faz 4 - Gerçek Dünya Doğrulaması:** TSPLIB'de başarılı olan hibrit modeller, İstanbul'un dinamik trafik koşullarından elde edilmiş asimetrik "Öğrenci Zaman Matrisi" verisine uygulanarak nihai çözüm performansları ölçülmüştür.

---

### 2. Algoritma Seçimi ve Hibrit (Memetik) Mimariler
Önceki çalışmalarda incelenen geleneksel (GA, PSO) yöntemlerin yerine, modern doğa-esinli algoritmalar ve bunların güçlü yerel arama (Local Search) operatörleriyle desteklenmiş **Hibrit (Memetik)** varyasyonları kullanılmıştır:

- **Temel Algoritmalar:** Harris Hawks Optimization (HHO), Grey Wolf Optimizer (GWO)
- **Hibrit (Memetik) Operatörler:** ALNS (Adaptive Large Neighborhood Search), LKH (Lin-Kernighan Heuristic), 2-opt.

Çalışmada, algoritmaların **Saf (Pure)** halleri (örn: HHO-Pure, GWO-Pure) ile **Memetik (Hibrit)** halleri (örn: HHO-ALNS, GWO-LKH) arasındaki performans farkı doğrudan test edilmiştir.

---

### 3. Test Problemlerinin Karakteristiği (TSPLIB ve Gerçek Veri)
Algoritmaların topolojik varyasyonlara karşı dirençlerini (robustness) ve asimetrik yapı uyumluluklarını test etmek için 4 standart, 1 gerçek hayat veri seti kullanılmıştır:
1. **berlin52:** 52 düğümlü, noktaların belirli merkezlerde kümelendiği standart problem.
2. **eil51:** 51 düğümlü, homojen dağılımlı, algoritmaları lokal optimum tuzaklarına çeken zorlu topoloji.
3. **st70:** 70 düğümlü, karmaşık ağ yapısı.
4. **kroA100:** 100 düğümlü, arama uzayı boyutunun saf meta-sezgiselleri zorladığı, hesaplama yükü yüksek problem.
5. **Öğrenci Zaman Matrisi (Gerçek Veri):** Kuş uçuşu öklid mesafesi yerine, İstanbul'un gerçek trafik ve güzergâh kısıtlarına dayanan, yöne bağlı asimetrik seyahat sürelerini içeren vaka problemi.

---

### 4. İstatistiksel Benchmark ve Kıyaslama Sonuçları

Geniş çaplı benchmark sonuçları ve uygulanan istatistiksel testler (ANOVA, Wilcoxon) incelendiğinde, meta-sezgisel algoritmaların memetik (hibrit) yapıya bürünmesinin **kesin bir zorunluluk** olduğu matematiksel olarak kanıtlanmıştır:

- **İstatistiksel Anlamlılık ve Etki Büyüklüğü:** Yapılan ANOVA testlerine göre algoritma türünün (Saf vs Hibrit) maliyet üzerindeki etkisi tüm problemlerde istatistiksel olarak kesin anlamlıdır ($p < 0.05$). Etki büyüklüğü ($\eta^2$) değerleri her zaman **>0.91** (Örn: kroA100 için 0.94) olarak ölçülmüş olup, maliyetlerdeki değişimin neredeyse tamamının kullanılan algoritma mimarisinden kaynaklandığı ispatlanmıştır.
- **Hibrit Yaklaşımların Üstünlüğü (TSPLIB):** Ağ boyutu büyüdükçe (örn. kroA100), GWO ve HHO'nun **saf (pure)** versiyonları optimum çözümlerden dramatik şekilde uzaklaşmıştır (HHO-Pure ortalama skoru ~121.000). Buna karşın, ALNS ile desteklenmiş versiyonlar aynı uzayda **~21.282** optimum seviyesine inerek çözüm kalitesini muazzam derecede artırmış ve Holm-Bonferroni düzeltmeli ikili (pairwise) analizlerde bu üstünlük istatistiksel olarak ($p_{holm} < 0.001$) kanıtlanmıştır.
- **Gerçek Veri Başarısı ve Yerel Aramalarla Kıyas:** Evrensel parametre setiyle desteklenmiş HHO-ALNS ve GWO-ALNS, asimetrik Öğrenci Zaman Matrisi probleminde `314.0` optimum skoruna sıfır sapmayla ulaşmıştır. Öğrenci matrisinde ALNS tabanlı algoritmalar ile hızlı temel yerel aramalar (2-opt, 3-opt) kafa kafaya çarpıştırılmış olup, ALNS'in 2-opt ve 3-opt'a karşı üstünlüğü de istatistiksel olarak anlamlı ($p_{holm} < 0.01$) bulunmuştur.
- **Hız (Pareto Dengesi):** Numba kullanılarak hızlandırılan basit yerel arama yöntemleri (örn: 2-opt) çok yüksek hızlarda (ortalama 600 ms) çalışarak verimli bir hız-kalite dengesi sunsa da, ALNS tabanlı memetik mimarilerin sahip olduğu "yıkıp-yeniden-kurma (destroy/repair)" kaynaklı optimum kalitesine erişememektedir.

---

### 5. Sonuç ve Akademik Çıkarımlar

Bu çalışma kapsamında Gezgin Satıcı Problemi ve Gerçek Zamanlı Okul Servisi Rotalama senaryoları üzerinde yapılan çok boyutlu (Optuna destekli) deneyler neticesinde aşağıdaki akademik çıkarımlara ulaşılmıştır:

1. **"Saf Meta-Sezgisel" Yanılgısı:** Çalışma, doğa esinli algoritmaların tek başlarına büyük arama uzaylarında (kroA100 vb.) yetersiz kaldığını açıkça göstermiştir. Üstün kaliteli ve istikrarlı çözümler arandığında, küresel keşif (global exploration) yeteneği yüksek HHO/GWO gibi algoritmaların, ALNS veya LKH gibi yerel sömürü (local exploitation) operatörleriyle **kesinlikle hibritlenmesi (Memetik Algoritmalar)** gerekmektedir.
2. **Bayesian Tabanlı Parametrik Evrensellik:** Yapay zeka tabanlı Optuna (TPE) ile sentezlenen parametrelerin, hiçbir ek müdahaleye gerek kalmadan standart TSPLIB topolojilerinden tamamen asimetrik gerçek dünya problemlerine (Öğrenci Zaman Matrisi) **%100'e yakın doğrulukta** transfer edilebildiği kanıtlanmıştır. Bu bulgu, yeni bir şehirde/bölgede ulaşım planlaması yapılacağı zaman parametre ayarı (tuning) için harcanacak muazzam zaman maliyetlerini ortadan kaldıracaktır.
3. **Gelecek Çalışmalar:** Gelecek araştırmalarda, geliştirilen HHO-ALNS ve GWO-ALNS mimarilerinin ve evrensel parametre setinin, Kapasite Kısıtlı Araç Rotalama (CVRP) ve Zaman Pencereli TSP (TSPTW) gibi daha karmaşık ve eş zamanlı kısıtlara sahip türevlere uygulanabilirliği test edilecektir.
