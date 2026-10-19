# UniRide için yeni algoritma tasarımları

**Hazırlayan:** Codex; tasarım ve matematik incelemesine GPT-6 Astra katkısıyla. **Tarih:** 2026-10-14. **Durum:** tasarım önerisi; uygulanmadı, ölçülmedi.

Görev: [00_PROMPT_ASTRA6_YENI_ALGORITMA_TASARIMI.md](00_PROMPT_ASTRA6_YENI_ALGORITMA_TASARIMI.md). BRIEF bu dosyanın bulunduğu klasördür. Kaynak kod yeniden incelenmedi; mevcut davranış hakkındaki olgular izin verilen belgelerden, özellikle BRIEF/01–02 ve istemin §3'ünden kabul edildi. Aşağıdaki sözde kodlar, testler, deneyler ve entegrasyon adımları gelecekte yapılacak işlerdir.

## 1. Özet

- **TSP birincil öneri: A1, Candidate Partition ILS.** Aynı hızlı yerel aramalı ILS üzerine yalnız katkısı ölçülebilen GPX2 eklenir. Entropi denetimi ilk sürümün zorunlu parçası değildir.
- **Bugünkü dalga ölçeğinde birincil öneri: A4, Certified Route Pool.** Mevcut GA-Split tanığı korunur; bağımsız sertifikalı rota kolonları birlikte seçilir. Küçük örneklerde eksiksiz sayım, gelecekte kesin referans sağlayabilir.
- **Gün düzeyinde birincil öneri: A5, Anchored Day Route-Pool LNS.** Rota süresinin araç yeniden kullanımına etkisi ortak seçim/atama modelinde değerlendirilir.
- A2, yönlü ve metrik olmayan ATSP için yön koruyan yerel arama temelidir. A3, CVRP/CVRPTW'den Sw/So ve heterojen filoya uzanan HGS tasarımıdır.
- A6, P5 dalgaları için büyük örnek profili ve P8 için ayrı eşlenik pickup–delivery profili sunar. P8'e geçiş yeni DARP olurluluk denetimi gerektirir.
- A7, ebeveyn mesafesine koşullu operatör seçimini araştırır. Etkileşim ve uniform kontrole katkı gösterilmezse bu tasarım sadeleştirilir.
- Yedi tasarımın hiçbiri için üstünlük veya SOTA iddiası yoktur. A1–A6'da çekirdek algoritmik yenilik iddiası yok; A7'nin özgünlüğü doğrulanmamıştır.
- Sabit amaç-değerlendirme bütçesinde aşım **sıfırdır**. İstemdeki %5 toleransı yalnız ayrıca raporlanan süre aşımına uygulanır; kapalı backend çağrısı tek değerlendirme sayılamaz.
- GPX2'nin garantisi, tanımladığı erişilebilir rekombinasyon uzayı içindir. Ham çaprazlama ile ardından gelen serbest yerel aramanın sözleşmeleri ayrıdır.
- P5'in beklemesiz, ortak R'li dalgasında segment olurluluğu prefix toplamlarla O(1) hesaplanabilir. Genel DARP için aynı sonuç çıkarılamaz.
- Güncel resmi PyVRP belgesi çok boyutlu yükü doğruluyor. Bununla birlikte v0.13.0 motoru HGS'den ILS'e geçti; tarihsel HGS ve güncel PyVRP ayrı referanslar olmalıdır.
- Rota havuzu optimumu, sabit rotalar için filo minimumu ve tüm rotalar üzerindeki ortak optimum ayrı kanıt etiketleridir. Google süre birimleri ve kesirli saniye davranışı planlanan entegrasyon için hâlâ doğrulanmamıştır.

## 2. Kaynak bulgu tablosu

**Okuma anahtarı:** DOĞRULANDI yalnız belirtilen içeriğin bu çalışmada açılmış birincil kaynakta görüldüğü anlamına gelir; deneyi yeniden üretmek anlamına gelmez. Özet görüldüyse yöntem ayrıntıları da okunmuş sayılmaz. DOĞRULANMADI satırları tasarım için araştırma izi olup içerik kanıtı değildir. BRIEF/06 ve /07 künyeleri başlangıç noktasıdır. Sayısal performans kazancı öngörülmemiştir. §7'deki kişi-günler, görevde ayrıca istenen **bize ait planlama tahminleri**dir; deney sonucu değildir.

| No | İddia ve sınırı | Kaynak: künye + DOI/URL | Tür | Güven | DOĞRULANDI? |
|---|---|---|---|---|---|
| R1 | Başlangıç fikirleri, L1–L10 ve G0–G2 henüz ölçülmemiş yeniden tasarım önerileridir. | UniRide (2026), [Redesign Work Plan](03_REDESIGN_WORK_PLAN_2026-10-13.md), §3–8; [görev](00_PROMPT_ASTRA6_YENI_ALGORITMA_TASARIMI.md), §3–10. | Depo belgesi | Yüksek: belgenin söylediği için | DOĞRULANDI; tasarım önerisi |
| R2 | Üçlünün sessiz mekanizma ve adaptör sorunları bu görevin kabul edilmiş olgularıdır; bu rapor yeni bir kod denetimi değildir. | UniRide (2026), [Family Evaluation](01_SOTA_FAMILY_EVALUATION_2026-10-13.md), [Cross Check](02_CROSS_CHECK_CODEX_VS_SCIENCE_2026-10-13.md), özellikle §1–3. | İnceleme/ölçüm raporu | Görev gereği kabul edilmiş | DOĞRULANDI: rapor içeriği; ölçümler tekrar edilmedi |
| R3 | Depolu yönlü dalga, ayrı kapasite havuzları, yönlü R, sabit matris, koşullu filo minimumu; Google birimleri belirsiz. | UniRide, [Daily Student Transport Planning Method](../../../paper/DAILY_STUDENT_TRANSPORT_PLANNING_METHOD.md), §1–4, özellikle satır 15–38, 44–48, 72–82; [envanter](09_ALGORITHM_INVENTORY_FOR_SCIENCE_2026-10-13.md), §1–2. | Depo belgesi | Yüksek: tanımlı sözleşme için | DOĞRULANDI; canlı kaynak kod doğrulaması değil |
| R4 | Tam amaç değerlendirmesi bütçesi, atomik üst sınır, ayrı native protokol ve gerçek istatistiksel eşleştirme gerekir. | UniRide, [Fairness Protocol](../../../../ACADEMIC_FAIRNESS_PROTOCOL_DESIGN.md); [Study Unification](../../../../ACADEMIC_STUDY_UNIFICATION_DESIGN.md), Hybrid composition semantics, Experimental Protocol, Statistical Protocol. | Tasarım sözleşmesi | Yüksek | DOĞRULANDI |
| R5 | Aday kenarlar, k-opt, tur birleştirme ve backbone yönlendirmesi bilinen LKH bileşenleridir; bütün aramaya polinom garanti vermez. | Keld Helsgaun (2009), “General k-opt submoves for the Lin–Kernighan TSP heuristic”, Mathematical Programming Computation 1:119–163. [DOI](https://doi.org/10.1007/s12532-009-0004-6), [makale PDF](https://www2.seas.gwu.edu/~simhaweb/champalg/tsp/papers/Helsgaun2.pdf), §3–5. | Hakemli makale | Yüksek | DOĞRULANDI; ilgili tam metin |
| R6 | GPX2 ortak kenarları korur ve ebeveyn birleşimindeki kenarları kullanır; tanımlanan bağımsız bileşen kombinasyonlarını optimize eder. | Renato Tinós, Darrell Whitley, Gabriela Ochoa (2020), “A New Generalized Partition Crossover for the Traveling Salesman Problem: Tunneling Between Local Optima”, Evolutionary Computation 28(2):255–288. [DOI](https://doi.org/10.1162/evco_a_00254), [kabul edilmiş yazar PDF'i](https://storre.stir.ac.uk/bitstream/1893/28894/1/Gen_Partitition-crossover-ecj2019.pdf), §2, Theorem 6 ve sonuç. | Hakemli; okunan yazar sürümü | Yüksek | DOĞRULANDI; O(n), fusion tekrarlarının sabit tutulduğu operatör içindir |
| R7 | EAX'in etkinliği yalnız çaprazlama adından gelmez; yerelleştirme, onarım/arama ve çeşitlilik seçimi birlikte tanımlanır. | Yuichi Nagata, Shigenobu Kobayashi (2013; çevrimiçi 2012), “A Powerful Genetic Algorithm Using Edge Assembly Crossover for the Traveling Salesman Problem”, INFORMS Journal on Computing. [Yayıncı/DOI](https://pubsonline.informs.org/doi/10.1287/ijoc.1120.0506). | Hakemli | Yüksek: özet kapsamı | DOĞRULANDI; yayıncı özeti |
| R8 | Asimetrik problem için LK türü yerel arama ayrı ele alınmıştır; simetrik delta doğrudan aktarılamaz. | Paris C. Kanellakis, Christos H. Papadimitriou (1980), “Local Search for the Asymmetric Traveling Salesman Problem”, Operations Research 28(5):1086–1099. [Yayıncı/DOI](https://pubsonline.informs.org/doi/10.1287/opre.28.5.1086). | Hakemli | Yüksek: kapsam; hamle ayrıntıları için sınırlı | DOĞRULANDI; özet, burada önerilen Or-opt'un birebir kaynağı olduğu iddia edilmiyor |
| R9 | ATSP için ayrı genetik/EAX çalışması bibliyografyada var; seçilecek GA-EAX yazılımının ATSP desteği bundan çıkmaz. | Yuichi Nagata, David Soler (2012), “A new genetic algorithm for the asymmetric traveling salesman problem”, Expert Systems with Applications 39(10):8947–8953. [DOI](https://doi.org/10.1016/j.eswa.2012.02.029); BRIEF/06. | Hakemli | Künye yüksek; yöntem ayrıntısı belirsiz | DOĞRULANMADI; yayınevi erişimi/kurumsal arşiv bot engeli, BRIEF raporuna dayanarak |
| R10 | Giant-tour + Split, yeni bir temsil değildir; mevcut üretim yöntemi de bu soy ağacına bağlanır. | Christian Prins (2004), “A simple and effective evolutionary algorithm for the vehicle routing problem”, Computers & Operations Research. [DOI](https://doi.org/10.1016/S0305-0548(03)00158-8); BRIEF/06, R3 §4.1. | Hakemli | Künye yüksek; içerik dolaylı | DOĞRULANMADI; BRIEF ve yöntem belgesine dayanarak |
| R11 | HGS ailesi popülasyon aramasını, güçlü komşuluk iyileştirmesini ve çeşitlilik yönetimini birlikte kullanır. | Thibaut Vidal, Teodor Gabriel Crainic, Michel Gendreau, Nadia Lahrichi, Walter Rei (2012), “A Hybrid Genetic Algorithm for Multidepot and Periodic Vehicle Routing Problems”, Operations Research. [Yayıncı/DOI](https://pubsonline.informs.org/doi/10.1287/opre.1120.1048). | Hakemli | Yüksek: özet kapsamı | DOĞRULANDI |
| R12 | Statik yük ve klasik TW için alt-dizi özetleri birleştirilebilir. Sabit sayıda önhesaplanmış parçanın testi O(1) olabilir; güncelleme/önhesaplama ve genel DARP bunun dışında. | Thibaut Vidal, Teodor Gabriel Crainic, Michel Gendreau, Christian Prins (2014), “A unified solution framework for multi-attribute vehicle routing problems”, EJOR 234(3):658–673. [DOI](https://doi.org/10.1016/j.ejor.2013.09.045), [CIRRELT yazar raporu](https://www.cirrelt.ca/documentstravail/cirrelt-2013-22.pdf), §3, denklemler 9–15. | Hakemli; okunan 2013 yazar raporu | Yüksek: belirtilen klasik TW için | DOĞRULANDI; lunch-break veya DARP genellemesi yapılmıyor |
| R13 | SWAP* farklı rotalardaki müşterileri yerinde kalma zorunluluğu olmadan değiştirir; HGS-CVRP için uygun referans bileşendir. | Thibaut Vidal (2022), “Hybrid genetic search for the CVRP: Open-source implementation and SWAP* neighborhood”, Computers & Operations Research 140:105643. [DOI](https://doi.org/10.1016/j.cor.2021.105643), [yazar kaydı/özet](https://arxiv.org/abs/2012.10384). | Hakemli makale; arXiv yazar sürümü | Yüksek: özet kapsamı | DOĞRULANDI; Sw/So/R uzatması bu makalenin sonucu değil |
| R14 | 2024 PyVRP makalesi HGS tabanlı CVRP/VRPTW çözücüsünü anlatır. | Niels A. Wouda, Leon Lan, Wouter Kool (2024), “PyVRP: A High-Performance VRP Solver Package”, INFORMS Journal on Computing 36(4):943–955. [Yayıncı/DOI](https://pubsonline.informs.org/doi/10.1287/ijoc.2023.0055). | Hakemli | Yüksek | DOĞRULANDI; yayıncı özeti |
| R15 | PyVRP v0.13.0, HGS'den ILS'e geçti; genetik popülasyon/crossover bileşenleri kaldırıldı. | PyVRP geliştiricileri, [v0.13.0 sürüm notu](https://github.com/PyVRP/PyVRP/releases/tag/v0.13.0), giriş ve Breaking changes. Erişim: 2026-10-14. | Resmi belge | Yüksek | DOĞRULANDI; yerel kurulu sürüm incelenmedi |
| R16 | Çok boyutlu yük ve bir boyutta sıfır kapasite resmen destekleniyor. Sw/So yük vektörü kurulabilir; tüm P5 ride semantiği ayrıca doğrulanmalı. | PyVRP geliştiricileri, [Load and vehicle capacities](https://pyvrp.readthedocs.io/en/stable/notebooks/load.html), Multiple load dimensions; açılan belge v0.14.0. Erişim: 2026-10-14. | Resmi belge | Yüksek: yük boyutu için | DOĞRULANDI |
| R17 | SISR, komşu müşteri dizilerini kaldırma ve blink içeren greedy yeniden kurmayı kullanır; kısıtlı VRP tasarımında aktarılabilir bileşenler sunar. | Jan Christiaens, Greet Vanden Berghe (2020), “Slack Induction by String Removals for Vehicle Routing Problems”, Transportation Science 54(2):417–433. [Yayıncı/DOI](https://pubsonline.informs.org/doi/10.1287/trsc.2019.0914). | Hakemli | Yüksek: özet kapsamı | DOĞRULANDI |
| R18 | PDPTW'de eşlenik pickup/delivery aynı araçta ve doğru sırada olmalı; ALNS geçmiş başarılara göre alt-sezgisel kullanımını değiştirir. | Stefan Ropke, David Pisinger (2006), “An Adaptive Large Neighborhood Search Heuristic for the Pickup and Delivery Problem with Time Windows”, Transportation Science. [Yayıncı/DOI](https://pubsonline.informs.org/doi/10.1287/trsc.1050.0135). | Hakemli | Yüksek: özet kapsamı | DOĞRULANDI |
| R19 | Heterojen filoda ILS/RVND ve set-partitioning birleşimi önceki çalışmadır; her tip-atama entegrasyonu otomatik fayda sağlamaz. | Puca Huachi Vaz Penna, Anand Subramanian, Luiz Satoru Ochi, Thibaut Vidal, Christian Prins (2017 çevrimiçi), “A hybrid heuristic for a broad class of vehicle routing problems with heterogeneous fleet”, Annals of Operations Research. [DOI](https://doi.org/10.1007/s10479-017-2642-9), [yazar kaydı/özet](https://arxiv.org/abs/1803.01930). | Hakemli makalenin yazar sürümü | Yüksek: özet kapsamı | DOĞRULANDI |
| R20 | Belirli max-wait/max-ride DARP olurluluğu difference constraints ve özel interval graph yapısıyla ele alınabilir; bu, keyfî DARP hamlesine O(1) teoremi değildir. | Murat Firat, Gerhard J. Woeginger (2011), “Analysis of the dial-a-ride problem of Hunsaker and Savelsbergh”, Operations Research Letters 39(1):32–35. [DOI](https://doi.org/10.1016/j.orl.2010.11.004), [yazar kurumu kaydı/özet](https://research.ou.nl/en/publications/analysis-of-the-dial-a-ride-problem-of-hunsaker-and-savelsbergh/). | Hakemli | Yüksek: özet kapsamı | DOĞRULANDI |
| R21 | Operatör seçimi durağan olmayabilir; kayan pencereli bandit geçmiş maruziyetin kalıcı avantajını azaltacak bir seçenektir. | Álvaro Fialho, Luis Da Costa, Marc Schoenauer, Michèle Sebag (2010), “Analyzing bandit-based adaptive operator selection mechanisms”, Annals of Mathematics and Artificial Intelligence 60:25–64. [Yayıncı/DOI](https://link.springer.com/article/10.1007/s10472-010-9213-y). | Hakemli | Yüksek: yöntem ailesi | DOĞRULANDI; özet |
| R22 | GPX/MGA ile EAX birleştirmek başlı başına yeni değildir; A1/A7 bu çalışma ile karşılaştırılmalıdır. | Swetha Varadarajan, Darrell Whitley (2021), “A Parallel Ensemble Genetic Algorithm for the Traveling Salesman Problem”, GECCO. [DOI](https://doi.org/10.1145/3449639.3459281), [konferans PDF](https://www.cmap.polytechnique.fr/~nikolaus.hansen/proceedings/2021/GECCO/proceedings/proceedings_files/p636-varadarajan.pdf), özet. | Hakemli konferans | Yüksek | DOĞRULANDI |
| R23 | Yerel optimum ilişkilerinden operatör seçimine bilgi aktarmak da önceki çalışmadır; ebeveyn mesafesine koşullama ile aynı mekanizma olduğu iddia edilmez. | Jiyuan Pei, Hao Tong, Jialin Liu, Yi Mei, Xin Yao (2023), “Local Optima Correlation Assisted Adaptive Operator Selection”, GECCO. [DOI](https://doi.org/10.1145/3583131.3590399), [yazar özeti](https://arxiv.org/abs/2305.02805). | Hakemli konferansın yazar sürümü | Yüksek: özet kapsamı | DOĞRULANDI |
| R24 | LKH aday stratejileri, backbone ve MAB birleştirilmiş bir araştırma yönüdür; UniRide'a kazanç veya özgünlük kanıtı değildir. | Long Wang, Jiongzhi Zheng, Zhengda Xiong, Kun He (2025), “Multi-armed Bandit and Backbone boost Lin-Kernighan-Helsgaun Algorithm for the Traveling Salesman Problems”. [arXiv:2501.04072](https://arxiv.org/abs/2501.04072), DOI 10.48550/arXiv.2501.04072. | Ön baskı; hakemli yayın durumu doğrulanmadı | Orta | DOĞRULANDI: arXiv özeti; hakemsiz kanıt olarak ele alındı |
| R25 | LAHC için yörüngeye ait geçmiş tutma düşüncesi bilinen kabul ailesine dayanır; kabul oranının monoton düşmesi şart değildir. | Edmund K. Burke, Yuri Bykov (2017), “The late acceptance Hill-Climbing heuristic”, EJOR 258(1):70–78. [DOI](https://doi.org/10.1016/j.ejor.2016.07.012); BRIEF/07. | Hakemli | Künye yüksek; ayrıntı dolaylı | DOĞRULANMADI; BRIEF raporuna dayanarak. §4.0'daki sade kabul kuralı bizim açık tanımımız |
| R26 | irace otomatik yapılandırma sağlar; eğitim örnekleri ile görülmemiş değerlendirme örneklerini ayırmak gerekir. | Manuel López-Ibáñez, Jérémie Dubois-Lacoste, Leslie Pérez Cáceres, Mauro Birattari, Thomas Stützle (2016), “The irace package: Iterated racing for automatic algorithm configuration”, Operations Research Perspectives 3:43–58. [DOI](https://doi.org/10.1016/j.orp.2016.09.002), [yayıncı makalesinin arşiv PDF'i](https://www.econstor.eu/bitstream/10419/178265/1/1-s2.0-S2214716015300270-main.pdf), §1–2. | Hakemli | Yüksek | DOĞRULANDI |
| R27 | Parametrik olmayan karşılaştırma yöntemleri için istenen metodoloji kaynağıdır; bu çalışmada ayrıntıları tam metinden doğrulanmadı. | Joaquín Derrac, Salvador García, Daniel Molina, Francisco Herrera (2011), “A practical tutorial on the use of nonparametric statistical tests as a methodology for comparing evolutionary and swarm intelligence algorithms”, Swarm and Evolutionary Computation 1(1):3–18. [DOI](https://doi.org/10.1016/j.swevo.2011.02.002); BRIEF/06. | Hakemli | Künye yüksek; içerik dolaylı | DOĞRULANMADI; BRIEF raporuna dayanarak; uygulanacak seçim ayrıca R4'e dayanır |
| R28 | Hibritin parçaları ayrı sınanmalı; çözümler, değerlendirme tanımı, donanım ve ayar süreci raporlanmalıdır. | Graham Kendall, Ruibin Bai, Jacek Błazewicz, Patrick De Causmaecker, Michel Gendreau, Robert John, Jiawei Li, Barry McCollum, Erwin Pesch, Rong Qu, Nasser Sabar, Greet Vanden Berghe, Angelina Yee (2016), “Good Laboratory Practice for optimization research”, JORS 67(4):676–689. [DOI](https://doi.org/10.1057/jors.2015.77), [yazar PDF'i](https://www.graham-kendall.com/papers/ketal2016.pdf), §3.5–3.14. | Hakemli | Yüksek | DOĞRULANDI |
| R29 | Gün içinde aynı araca birden çok sefer atayan memetik/Split yaklaşımı literatürde var; A5'in genel fikri yeni değildir. | Diego Cattaruzza, Nabil Absi, Dominique Feillet, Thibaut Vidal (2014), “A memetic algorithm for the Multi Trip Vehicle Routing Problem”, EJOR 236(3):833–848. [DOI](https://doi.org/10.1016/j.ejor.2013.06.012), [yayıncı](https://www.sciencedirect.com/science/article/pii/S0377221713005006). | Hakemli | Orta: yayıncı arama özeti | DOĞRULANMADI; sayfa açılışı 403, yalnız araştırma izi |
| R30 | Yazılım adları aynı lisansı paylaşmaz; izinler seçilen dağıtıma göre belirlenmeli. | GA-EAX, PyVRP, OR-Tools, VROOM ve GPX2 geliştiricilerinin §2.1'de bağlanan resmi lisans dosyaları. | Resmi yazılım belgeleri | Yüksek: açılan dosyalar | DOĞRULANDI; LKH-3 istisnası §2.1 |
| R31 | Pozitif kazanç ölçütünü gevşeterek LKH hızlandırma çalışması yeni referans adayıdır; burada kazanç büyüklüğü benimsenmez. | Ammann, Ostermann, Stiller, de Wolff (2026), “A speed-up for Helsgaun's TSP heuristic by relaxing the positive gain criterion”, Computers & Operations Research. [DOI](https://doi.org/10.1016/j.cor.2026.107443); BRIEF/07. | Hakemli olarak kayıtlı künye | Künye BRIEF; yöntem belirsiz | DOĞRULANMADI; BRIEF raporuna dayanarak |
| R32 | AB-cycle olurluluğu ve onarım ihtiyacı EAX için ayrı incelenmiştir; EAX'i yeniden yazma maliyetini hafife almamak gerekir. | Jonathan Heins, Darrell Whitley, Pascal Kerschke (2025), “To Repair or Not to Repair? Investigating the Importance of AB-Cycles for the State-of-the-Art TSP Heuristic EAX”. [arXiv:2505.00803](https://arxiv.org/abs/2505.00803), DOI 10.48550/arXiv.2505.00803. | Açılan sürüm ön baskı | Orta | DOĞRULANDI: özet. Kayıt ilgili ACM DOI 10.1145/3712256.3726436 gösteriyor; o yayının içeriği/hakem durumu burada doğrulanmadı |
| R33 | FRR-MAB, doğrudan UniRide/TSP performans kanıtı değildir; ayrı aktarım deneyi gerekir. | Ke Li, Álvaro Fialho, Sam Kwong, Qingfu Zhang (2014), “Adaptive Operator Selection With Bandits for a Multiobjective Evolutionary Algorithm Based on Decomposition”, IEEE Transactions on Evolutionary Computation. [DOI](https://doi.org/10.1109/TEVC.2013.2239648); BRIEF/07. | Hakemli | Künye yüksek; içerik dolaylı | DOĞRULANMADI; BRIEF raporuna dayanarak, ilk sürümde zorunlu değil |

### 2.1 Yazılım ve lisans sınırları

| Referans | Açılan resmi kanıt | Sonuç ve kullanım kararı |
|---|---|---|
| LKH / LKH-3 / elkai | [LKH-3 yazar sitesi](http://akira.ruc.dk/~keld/research/LKH-3/) erişilemedi; R5 yalnız LKH-2 için akademik/ticari olmayan kullanım ifadesi içeriyor. | **LKH-3'ün seçilecek dağıtımının lisansı DOĞRULANMADI.** LKH-2 bilgisini LKH-3/elkai'ye otomatik aktarmıyorum. Deneyden önce tam dağıtım ve lisans arşivlenmeli; üretim kullanımına bu raporla izin verilmiş sayılmaz. |
| GA-EAX | [nagata-yuichi/GA-EAX LICENSE](https://github.com/nagata-yuichi/GA-EAX/blob/main/LICENSE) | MIT; DOĞRULANDI. Bu dağıtımın ATSP desteği DOĞRULANMADI. Başka restart çatallarının lisansı ayrı olabilir. |
| PyVRP | [LICENSE.md](https://github.com/PyVRP/PyVRP/blob/main/LICENSE.md) | MIT; DOĞRULANDI. Motor sürümü ayrıca sabitlenmeli. |
| OR-Tools | [stable/LICENSE](https://github.com/google/or-tools/blob/stable/LICENSE) | Apache-2.0; DOĞRULANDI. CP-SAT ile Routing/GLS farklı deney kollarıdır. |
| VROOM | [master/LICENSE](https://github.com/VROOM-Project/vroom/blob/master/LICENSE) | BSD-2-Clause metni; DOĞRULANDI. P5'e tam semantik uyum bundan çıkmaz. |
| GPX2 yazar uygulaması | [rtinos/gpx2 LICENSE](https://github.com/rtinos/gpx2/blob/master/LICENSE) | GNU GPL v3 metni; DOĞRULANDI. Kodun alınması ile makaledeki yöntemin bağımsız uygulanması ayrı kararlardır; dağıtım uyumu netleşmeden kod kopyalanmaz. |

## 3. Problem → bileşen eşlemesi

Tablodaki “başarı bileşeni” ilgili kaynakta kullanılan bileşendir; UniRide'da başarılı olduğu ölçülmüş değildir. Ham veri/kurulu yazılım envanteri yeniden denetlenmedi. İstemdeki ATSP mevcudiyeti bilgisi deney kurulurken sürümlü manifestle tazelenmelidir.

| Problem | Korunacak sözleşme | Uygun bileşenler / kaynak | Referanslar ve önerilen tasarım |
|---|---|---|---|
| P1 TSP | Son–ilk kenarlı Hamilton çevrimi; simetrik matris | Aday listeli LS, kick, GPX2, çeşitlilik; R5–7, R22 | Aynı LS'li ILS, LKH-3, GA-EAX, ALNS-TSP, OR-Tools GLS; **A1 birincil**, A7 koşullu |
| P2 ATSP | Yön korunur; üçgen eşitsizliği yok | Gelen/giden yay adayları, yön koruyan Or-opt/or-3opt; R8–9 | A2, yönlü ILS; doğrulanmış 2n dönüşümüyle LKH-3; varsa ayrı EAX-ATSP |
| P3 CVRP | Sert kapsam/kapasite; burada lex rota sayısı sonra maliyet | Giant-tour/Split, eğitim LS, granüler komşuluk, SWAP*; R10–13 | A3, GA-Split; HGS-CVRP, sürümü belirtilen PyVRP, OR-Tools, VROOM |
| P4 CVRPTW | TW ve servis/bekleme tanımı ayrıca korunur | TW alt-dizi özetleri, regret repair, HGS/ALNS; R12, R14, R18 | A3/A6; PyVRP-HGS tarihsel kolu ve güncel PyVRP-ILS, OR-Tools, VROOM; uyumlu BKS |
| P5 dalga | Occurrence kimliği, tek yön/çapa, depolu süre, ayrı Sw/So, T ve yönlü R | Sertifikalı rota havuzu, yönlü Split; R3, R19; §4.0'daki kendi türetimimiz | Bugünkü 2–20 yolcu/dalga ölçeğinde **A4 birincil**; A3 alternatif, A6 ölçek kolu; ga_split, ga_split_hf, planlanan exact |
| P6 heterojen filo | Tip, ortak toplam kapasite varsa ayrıca, büyük araç kotası | Tipli decoder, kaynak cezaları, havuz master'ı; R11–13, R19 | A3/A4; ga_split_hf. Sedan Sw=0 model varsayımı; Doblò ortak toplam sınırı karar H03'e göre korunur |
| P7 gün | Anchor intervali, cooldown, fiziksel araç uyumu; rota sayısı ≠ araç sayısı | Gün amaçlı kolon seçimi, kritik dalga LNS, atama; R3, R19, R29 | **A5 birincil**; sabit menü CP-SAT + mevcut sabit-rota ataması kontrolü |
| P8 paratransit | Eşlenik talep, sıra, TW, araç içi yük, kişi başına ride, taahhütler | Request-level SISR/ALNS, exact schedule check, rolling horizon; R17–18, R20 | A6'nın ayrı P8 profili; PDPTW kontrolü ancak max-ride semantiği eklenirse DARP kontrolüdür |

**İki belge ayrılığı:** BRIEF/03'teki “depoya bağlı açık yol” ifadesi P5 amaç tanımı olarak kullanılmıyor; R3 ve görev §4, boş gidiş/dönüş dahil **depo-kapalı tur** tanımlıyor. P7'nin genel filo amacı ile sahip olunan minibüs sabitken ödünç sedan hedefi de aynı tuple değildir (§4/A5). Google tam sayı saniye, P8 için hedef veri sözleşmesidir; doğrulanmış canlı yanıt birimi değildir (R3, yöntem satır 21).


## 4. Algoritma portföyü

### 4.0 Bütün kartların ortak sözleşmesi

**Gösterimler.** n talep occurrence'ı/TSP düğümü; L bir rotadaki en fazla occurrence sayısı; K aday komşu sayısı; m popülasyon büyüklüğü; h araç tipi; Q tek kota sayacının alabileceği durum sayısı; M rota kolonu sayısı. P8'de bir talep iki servis düğümü üretir. Fiziksel konum eşitliği occurrence eşitliği değildir. Maliyetler aynı snapshot ve tam sayı ızgarasında karşılaştırılır; centi-dakika ile saniye deney içinde karıştırılmaz.

**Tam değerlendirme ve atomiklik (R4).** P1/P2 için bir FE, tek tam Hamilton çevriminin bütün yönlü yaylarıyla amaç hesabıdır. P3–P6 için önerilen uzatma, tüm talepleri atayan bir çok-rotalı adayın aynı kısıt/amaç profiliyle tam değerlendirilmesidir; bu eşleme mevcut katalog tarafından kabul edilmiş varsayılmayacak, protokol kapısında doğrulanacaktır. İnşa başlangıçları, restart, offspring, eğitim, son polish ve adaptörün tekrar hesapları dahil bütün arama amaç çağrıları ortak sayaçtan tüketir. Önbellekten yalnız önceden sayılmış, değişmemiş çözüm/snapshot değeri okunabilir.

Hamle deltalari, segment maliyetleri ve yapısal olurluluk filtreleri **FE değildir**; sayıları ve süreleri ayrı telemetridir. Tam çözümün amaç değeri delta ile hesaplanıp sıralama/kabulde kullanılmışsa bunu “yalnız filtre” diyerek ücretsiz bırakamazsın: primary uygulama tam değerlendirme yolundan geçirir. Aday listesi taramasında tam değerlendirilmeyen hareketlerin sayısı ayrıca görünür. Bu kural, O(1) delta ile O(n) tam aday hesabını ayırır; aynı FE eşit işlem süresi değildir. Nihai bağımsız doğrulamanın arama dışındaki süresi ve tekrar hesapları ayrıca raporlanır; bütçe bitince gizli polish yapılamaz.

Steady-state döngüde bir tam aday puanlaması atomik birimdir; popülasyon başlangıcı veya deterministik paket için güvenli üst sınır önceden rezerve edilir. Kalan bütçe sınırı karşılamıyorsa paket başlatılmaz. Rezervasyon ile gerçek tüketim ayrı kaydedilir; eğitimin her tam adayı aynı sayaçta kontrol edilir. Kesilen offspring değerlendirilmiş geçerli son haliyle tutulabilir; yarım aday döndürülemez. İç döngüde deadline kontrolü ve backend'e kalan toplam süre iletimi gerekir. **FE aşımı=0; native süre aşımı≤%5 kabul kapısıdır**, garanti varsayımı değil: aşan koşu raporlanır ve zaman uyum kapısını geçmez.

A4/A5'in CP-SAT/MIP iç araması tam FE olarak izlenemiyorsa bütün matheuristic kolu yalnız **native** olur. Bir master solve, bir FE veya bir CP düğümüyle eşitlenmez. Rota üretimi ve master aynı uçtan uca zaman zarfını paylaşır; ayrı aşama süreleri de yazılır. Native referansları primary sıralamaya eklememek bir eksiklik gizleme yöntemi değildir: muhasebe kapısının sonucudur.

**Tekrarlanabilirlik.** Instance kimliği + tekrar indeksinden SHA-256 kök tohumu; bileşen adından kararlı alt-tohum; kararlı sıralama, tie-break, snapshot, sürüm ve parametre hash'i. Aynı seed garantisi sabit FE/deterministik iş sınırı için sınanır. Duvar saati kesmesi veya paralel backend için bit düzeyi aynı çıktı garanti edilmez; native manifestte timing-dependent olarak belirtilir.

**Değişmez çeşitlilik.** P1'de yönsüz kenar kümesi E kullanılarak d(A,B)=1−|E(A)∩E(B)|/n; tur rotasyonu ve ters yönü eşdeğerdir. P2'de yönlü yay kümesi kullanılır: rotasyon eşdeğer, ters tur genellikle **eşdeğer değildir**. Popülasyon permütasyonu ortalama tüm-çift mesafesini değiştirmez. Örnekleme gerekiyorsa kararlı birey kimlikleri ve ayrı seed kullanılır. VRP'de rota listesinin sırası değişmezliktir; depoya bağlı rotanın ters çevrilmesi P5/P6'da değişmezlik değildir.

Entropi yalnız opsiyonel P1/P2 ablasyonudur. En az üç düğümlü turlarda f_e kenar frekansı, p_e=f_e/(mn), H=−Σp_e log p_e, U=min(mn,M_edges) olsun. M_edges=n(n−1)/2 (P1) veya n(n−1) (P2). U>n ise H_norm=(H−log n)/log(U/n), değilse 0. Bu, **bizim sınırlandırılmış normalizasyon tanımımızdır**: özdeş popülasyon 0 verir; 1'in her n,m için erişilebilir olduğunu iddia etmez. Boş/küçük örnekler ayrı trivial sözleşmedir. Rota sayısı değişken VRP'ye bu formül taşınmaz. İlk sürümde ortalama kenar mesafesi yeterlidir.

**Kabul ve kredi.** Sade, yörüngeye özel late acceptance varyantında geçmiş dizisi başlangıç maliyetiyle dolar; aday mevcut maliyetten veya seçili geçmiş değerinden kötü değilse kabul edilir; sonra ilgili slot kabul sonrası mevcut maliyetle güncellenir. Bu tanım R25'in bütün optimizasyonlarını birebir uygulama iddiası değildir. Sözleşme kabul oranının zamanla azalması değil, tanımlanan indis/karar/geçmiş eşitliğidir. Kalibre SA için pilot pozitif kötüleşmelerden T0=−median(Δ+)/log(p0), 0<p0<1; bu **tasarım kuralıdır**, tüm dağılımın kabul oranını tam p0 yapma garantisi değildir. Pilot FE ve süresi bütçeye dahildir. Pozitif örnek yoksa greedy kabul kullanılır. Lexicographic araç/rota sayısı keyfî sıcaklıkla süreye katılmaz: ilk hedef korunarak alt hedefte kabul veya açıkça ayrı araştırma profili kullanılır.

Operatör kredisi, sabit FE denemelerinde aynı LS paketi sonrası tam puanlanmış iyileşmenin harcanan FE'ye oranı ya da önceden tanımlı başarı oranıdır. Sıfır deneme/FE ayrı ele alınır. Kayan pencere, keşif tabanı ve seçilmeyen operatörlerin kredi yaşlanması açık tanımlanır. Süreye bölünmüş ödül farklı native varyanttır. Ham çaprazlama başarısı ile çaprazlama+LS başarısı ayrı kaydedilir; LS katkısı operatöre otomatik mal edilmez.

**P5 segment hesabı — bizim türetimimiz (R3'ten).** Sabit giant-tour parçası vi,…,vj için Pij=Σ(k=i..j−1)c(vk,vk+1), Cij=c(D,vi)+Pij+c(vj,D). Negatif olmayan yaylar, ortak R, servis/bekleme yok varsayımlarında en uzun pickup ride=Pij+c(vj,D), en uzun drop-off ride=c(D,vi)+Pij. İlkinde en erken binen, ikincide en son inen yolcu belirleyicidir. Sw/So ve yay prefix toplamlarıyla segmentin yükü, Cij≤T ve ride≤R testi O(1); homogeneous Split O(nL), h tip ve tek kota durumu ile O(hQnL) olur. Bu formül **mevcut decoder'ın yeni ölçülmüş karmaşıklığı değildir**; önerilen özel P5 decoder içindir. R1 mevcut pickup-TW modunu O(nL²) diye bildirir.

Sabit i için Sw/So aşımı ve beklemesiz drop-off ride aşımı segment uzatılınca sürer. Buna karşılık kapalı C ve pickup ride son depo yayı değiştiği için azalabilir. c(vj,vj+1)+c(vj+1,D)<c(vj,D) olan nonmetric durumda ilk ihlalde uzatmayı kesmek yanlıştır. Prefix'in kendisi, negatif olmayan devam yayları nedeniyle güvenli alt sınır olabilir; ham doğrudan depo yayı değildir. İsteğe bağlı yönlü shortest-path relaxation yalnız budama alt sınırı içindir, gerçek matrisi/sertifikayı değiştiremez. qSw=0 ve nSw>0 ise tip uygunsuz; nSw=0 ise ilgili kapasite tabanı 0'dır; sıfıra bölme yapılmaz. So için aynı kural.

**Ortak bileşen tablosu C0.** Aşağıdaki satırlar bütün kartların bileşen tablosunun parçasıdır. Sert kısıt veya sertifika kaldırılması kalite ablasyonu değildir; bunlar yalnız negatif sözleşme testleriyle sınanır.

| Bileşen | Kaynak | Sözleşme testi (planlanan) | Telemetri | Ablasyon / kontrol |
|---|---|---|---|---|
| Snapshot, kapsam, fail-closed doğrulama | R3–4 | Eksik/ters yay, yinelenen occurrence, yanlış birim ve depo ihlalini reddet; aynı duraktaki ayrı yolcular korunur | snapshot_id, reject_reason, missing_arc, unit_profile | Aynı doğrulayıcı tüm kollarda sabit; kapatılmaz |
| Ortak sayaç ve deadline | R4, kendi atomik tanımımız | Init/search/polish toplamı ledger ile aynı; yetersiz bütçede atomik işi başlatma; FE=cap sınırı | reserved, consumed, delta_checks, stage_ms, overshoot, stop_reason | Aynı muhasebe bütün kollarda; kapatılmaz |
| Best-so-far arşivi | R1 L7, R2 | Her injection/restart/repair sonrası geçerli yeni en iyi korunur; current ile best karışmaz | archive_updates, candidate_best, returned_best | Elit çeşitlilik politikası aç/kapat; doğru best arşivi sabit |
| Bileşen/ayar etkinliği | R1 L1/L8 | Her ilan edilen operatör kontrollü girdide çağrılır; her ayar en az bir tanımlı kararı etkiler | eligible, selected, completed, accepted, improved, error | Her isteğe bağlı mekanizma açık/kapalı; işlevsiz ayar kaldırılır |
| Çeşitlilik ve klon eleme | R6–7, R11; yukarıdaki tanım | P1 rotasyon+reversal, P2 yalnız rotasyon; popülasyon sırası değişmez; özdeş d=0 | clone_count, mean_edge_distance, entropy_optional | Çeşitlilik seçimi kapalı / açık; entropy ayrı |
| Kabul / pencere kredisi | R18, R21, R25; yukarıdaki tanım | Yörünge geçmişleri ayrık; yaşlanan kredi; sıfır-pozitif-Δ uç durumları; RNG tekrarları | uphill_attempts, accepts, reward_window, arm_pulls | Greedy / LAHC / kalibre SA; uniform / adaptive |

İmza mekanizması selected/all_search_decisions oranı %5'in altındaysa uyarı üretilir (R1). eligible/all ve selected/eligible ayrıca raporlanır; az sayıdaki uygun fırsat “mekanizma çalışıyor” diye saklanmaz. Tamamlanamayan çağrılar ayrı sayılır. Bu oran kalite veya doğruluk ispatı değildir.

### 4.1 A1 — Candidate Partition ILS (TSP birincil öneri)

| Alan | Tasarım |
|---|---|
| Ad ve önerilen kimlik | Candidate Partition ILS; **Core-CPILS-TSP** |
| Hedef problemler ve düzey | P1; akademik TSP. P5'e doğrudan fitness/adaptör olarak aktarılmaz. |
| Soy ağacı | ILS/kick ve aday kenar araması R1/R5; partition crossover R6; çeşitlilik R7/R11; ensemble önceli R22. |
| Eski fikirle bağ | EB-PXILS/E2BSO'nun çoklu arama ve rekombinasyon fikri kalır. Faz/entropi denetimi zorunlu değil; kenar zorlama GPX2 sözleşmesine dönüşür. L1–L8, C0 ile; L9–L10 üretim dışı yetenek sınırıyla karşılanır. |
| Temsil | Kapalı Hamilton permütasyonu; kararlı rotasyon/reversal normalizasyonu; küçük elit havuz, her biri ayrı kabul geçmişli ILS yörüngeleri. |
| Olurluluk yönetimi | Sert Hamilton ve tam maliyet kontrolü. Sw/So, T, R, TW, tip/kota uygulanmaz; böyle bir instance bu kimlikle reddedilir. |
| Bütçe muhasebesi | C0 tam tur FE'si; GPX ham çocuğu ve her LS tam adayı ortak ledger'da. Fusion/komponent skorları tanısal işlemler; bunlarla tam aday sıralanırsa FE kuralı uygulanır. İç LS/kick/restart deadline'ı. |
| Karmaşıklık | K-adaylı 2-opt geçişi O(nK) hareket; delta O(1), primary tam değerlendirme O(n), dizi ters çevirme O(n) olabilir. GPX2 R6 koşullarında O(n); küçük elit havuz uzaklık güncellemesi O(mn). Aramanın toplam iterasyon sayısı için polinom iddiası yok. |
| Yönlü ve metrik olmayan matris | Bu kimlik yalnız simetrik. Metriklik gerektirmeyen maliyet adayı kullanılabilir; geometrik yakınlık garantisi yok. ATSP A2'ye gider; GPX2'yi yönlü matris üzerinde simetrikmiş gibi çalıştırmaz. |
| Neden başarılı olması bekleniyor — kaynaklar | R5 arama maliyetini sınırlayan aday setlerini; R6 bileşen rekombinasyonunu; R22 mevcut GPX/EAX birleşimlerini destekler. |
| Neden başarılı olması bekleniyor — bizim yorumumuz | Ortak hızlı LS ve yeni kenar üreten kick, GPX2'nin ebeveyn kenarlarıyla sınırlı aramasını tamamlayabilir. Entropi denetimini ertelemek katkı ayrıştırmasını kolaylaştırır; kazanç garantisi değildir. |
| Performans hipotezi | Aynı LS'li ILS'e karşı test örneklerinde daha düşük açık: **orta** güven; LKH-3/GA-EAX'e yaklaşma: **düşük** güven, üstünlük beklentisi kurulmadı. Yanlışlama: eşit bütçeli held-out GPX ablasyonu katkı göstermiyorsa rekombinasyon çıkarılır; referanslara uzaklık kapanmıyorsa referans-düzeyi beklenti reddedilir. |
| Yenilik | En yakın R6, R7, R22. **Çekirdek yenilik yok.** Fark kesin FE ve UniRide katalog sözleşmesiyle denetlenebilir bileşimdir; yayın katkısı deney sonucu olmadan kurulmaz. |
| Uygulama | ObjectiveEvaluationBudget, improve_two_opt_budgeted, improve_or_opt_budgeted, improve_three_opt ve fairness denetleyicisi; yeni aday/DLB yönetimi, GPX2, elit havuz. Ortak altyapı sonrası **8–15 kişi-gün tahmin**; GPX2 lisans/uygulama kararı bağımlılığı. |
| Riskler ve açık sorular | Yanlış komponent birleştirme; GPX ortak kenar testini LS sonrasına uygulama; K küçükken iyi yayları dışlama; sıfır bileşen/klon ebeveynler. DLB bir bütün komşuluğu tüketmiş olma garantisi sayılmaz. |
| Kabul kapısı | G0 sözleşmeleri ve muhasebe → CANDIDATE; G2 mekanizma kanıtı ve dondurulmuş test raporu → yalnız P1 kapsamlı VERIFIED değerlendirmesi. Üretim yeteneği verilmez. |

**Sözde kod**

~~~text
snapshot ve simetri sözleşmesini doğrula
bütçeye sığan başlangıç yörüngelerini üret ve tam değerlendir
her yörüngenin kabul geçmişini kendi maliyetiyle başlat
best ve elit havuzu güncelle
bütçe ve deadline uygunsa tekrarla:
  kararlı kuralla bir yörünge seç
  uygun farklı ebeveyn varsa sabit olasılıkla GPX2 uygula
  aksi halde yönsüz double-bridge/kick uygula
  ham çocuğun yapısını denetle; tam puanla ve best'i güncelle
  aynı bütçeden aday listeli LS çalıştır; her tam adayda best'i güncelle
  yörüngeye özel kabul kuralını uygula
  klon ve çeşitlilik kuralıyla elit havuzunu güncelle
  her kararı ve harcamayı kaydet
bağımsız Hamilton kontrolünden geçen best'i döndür
~~~

| Bileşen | Kaynak | Sözleşme testi | Telemetri | Ablasyon |
|---|---|---|---|---|
| Aday listesi + DLB/aktif kuyruk | R1 L2, R5 | Hareket delta/full eşitliği; değişen uçların invalidasyonu; sınır kontrolü | scans, skipped_nodes, reactivated, kicks/s | Aday açık/kapalı; DLB açık/kapalı ayrı |
| GPX2 | R6 | Ham çocuk Hamilton; bütün ortak kenarlar korunur; ebeveyn birleşimi dışı kenar yok; küçük komponentlerde exhaustive kombinasyonla karşılaştır; geçerli ayrışmada en iyi ebeveynden kötü değil | components, eligible_pairs, child_gain_raw, child_gain_after_ls | GPX yok; GPX; OX+aynı LS; restart+aynı LS |
| Kick ve çoklu yörünge | R1, R5 | Permütasyon korunur; küçük n için tanımlı davranış; her aday puanlanır | kick_size, restarts, trajectory_gain | Tek ILS / çoklu ILS; kick türü sabit |
| Entropi denetimi (ertelenmiş) | R1; §4.0 türetimi | Özdeş=0; tur/popülasyon dönüşüm testleri | entropy, mode_switch, signature_ratio | Sabit GPX olasılığı / entropy controller |

### 4.2 A2 — Directed Candidate ILS

| Alan | Tasarım |
|---|---|
| Ad ve önerilen kimlik | Directed Candidate ILS; **Core-DCILS-ATSP** |
| Hedef problemler ve düzey | P2; ATSP. P5/P6'nın rota içi LS bileşeni olarak ancak kendi decoder/sertifikaları altında yeniden kullanılır. |
| Soy ağacı | Asimetrik yerel arama R8; aday seti fikri R5; yön koruyan Or-opt/or-3opt mevcut bileşen sözleşmesi R1. EAX-ATSP R9 ilk sürümün parçası değil. |
| Eski fikirle bağ | R2DMA'nın LS'siz perturb adımı yerine her kick sonrası bütçeli eğitim; L2/L3/L6/L9'u doğrudan ele alır; C0 diğer sessiz hataları engeller. |
| Temsil | Yönlü Hamilton çevrimi; yalnız rotasyon normalizasyonu; ayrı incoming/outgoing adaylar ve aktif düğüm kuyruğu. |
| Olurluluk yönetimi | Sert Hamilton, eksik yay reddi ve yönlü maliyet. Sw/So, T/R, TW, kota burada yok; üretimde çağıran decoder bu kısıtları uygular. |
| Bütçe muhasebesi | P2 tam çevrim FE; C0. Hareket ve kick sonrasında tam aday; candidate genişletme ve preprocessing süresi dahil; deadline iç döngüde. |
| Karmaşıklık | Sabit uzunluklu Or-opt delta O(1), uygulanması diziyle O(n); K adayla O(nK) öneri. Burada tanımlanan iki aday bağlantılı üç kesim taraması O(nK²) öneri; her puanlanan tam aday O(n). Incoming/outgoing listeleri yoğun matristen çıkarılırken matris okuma O(n²) olabilir. |
| Yönlü ve metrik olmayan matris | Taşınan segmentin yönü korunur; kesilen/eklenen bütün yaylar kendi yönleriyle hesaplanır. Metrik budama, simetrik 2-opt deltası ve ters yay yedeği yok. Seyrek aday grafiği kalite garantisi vermez; periyodik geniş tarama ayrı ablasyondur. |
| Neden başarılı olması bekleniyor — kaynaklar | R8 asimetrik yerel aramanın ayrı tasarım alanı olduğunu; R5 adayların arama uzayını sınırlandırdığını gösterir. |
| Neden başarılı olması bekleniyor — bizim yorumumuz | Yanlış yön aktarımını baştan kaldırmak ve daha çok geçerli komşu değerlendirmek güvenilir temel sağlayabilir. Rasgele nonmetric matrislerde fayda tersine dönebilir. |
| Performans hipotezi | Tam taramalı aynı Or-opt/3-opt ILS'e eşit native sürede daha iyi kalite-zaman dengesi: **orta**; eşit FE'de daraltmanın kaliteyi koruması: **düşük**. LKH-3'e yaklaşma **düşük**. Yanlışlama: hold-out nonmetric sınıfta anlamlı/pratik kötüleşme; bu durumda K/geniş tarama yeniden tasarlanır. |
| Yenilik | En yakın R8, R5, R9; **yok**. Yönlü doğruluk ve muhasebe mühendisliği önerisidir. |
| Uygulama | improve_or_opt_budgeted, improve_three_opt, ObjectiveEvaluationBudget; yeni directed candidates/aktif kuyruk. Ortak altyapı sonrası **5–9 kişi-gün tahmin**. A1'in GPX modülüne bağımlı değil. |
| Riskler ve açık sorular | Dense matris belleği, adayların yön yanlılığı, DLB'nin çok düğümlü hareketlerde eskimesi. Kesin hareket listesi ve maliyet önbelleği arayüzü uygulama öncesi belirlenmeli. |
| Kabul kapısı | Yönlü property testleri, nonmetric karşı örnekler, FE kapısı ve G0 → CANDIDATE; G2 + P2 veri sınıflarıyla sınırlı VERIFIED. Yönlü doğruluk tek başına kalite kanıtı değil. |

**Sözde kod**

~~~text
snapshot, yön ve eksik yay sözleşmesini doğrula
incoming/outgoing adaylarını kararlı biçimde kur
başlangıç turunu tam puanla; best'i kaydet
bütçe ve deadline uygunsa tekrarla:
  aktif düğüm ve izinli yönlü hareket seç
  yalnız yapısal/kanıtlı filtre uygula
  yönü koruyarak tam adayı kur ve bütçeli puanla
  iyileşeni uygula; etkilenen kuyruk kayıtlarını geçersizleştir
  geçerli her adaydan best'i güncelle
  durgunlukta yön koruyan kick + aynı LS uygula
  önceden belirlenen iş sayısında daha geniş tarama yap
  delta, FE ve kuyruk telemetrisini yaz
bağımsız yönlü çevrim kontrolüyle best'i döndür
~~~

| Bileşen | Kaynak | Sözleşme testi | Telemetri | Ablasyon |
|---|---|---|---|---|
| Directed Or-opt/or-3opt | R1 §5, R8; kendi hamle tanımı | Delta/full eşitliği; ters yayları çok farklı matriste doğru maliyet; permütasyon | move_type, full_eval, delta_error | Or-opt / or-3opt / birlikte |
| Incoming/outgoing adaylar | R5'ten yönlü aktarım önerimiz | Satır/sütun yönleri doğru; eşit maliyette kararlı tie-break | candidate_hit, widened_gain, preprocessing_ms | Tam tarama / dar liste / genişletmeli |
| Kuyruk ve kick | R1 L2; §4.0 | Değişen bağlantıların yeniden etkinleşmesi; deadline | reactivation, inactive_fraction, kick_gain | Kuyruk kapalı; kick+LS / restart+LS |

2n dönüşümü ayrı native referans içindir: twin-edge zorunluluğu, yasak kenarlar, inverse mapping ve özgün ATSP maliyeti eşitliği kanıtlanmadan çalışmaya alınmaz. Simetrik GPX2'nin dönüştürülmüş uzaydaki verimi **DOĞRULANMADI** olarak kalır; A2 buna bağımlı değildir.


### 4.3 A3 — Vector-resource HGS-Split

| Alan | Tasarım |
|---|---|
| Ad ve önerilen kimlik | Vector-resource HGS-Split; **Core-VHGS-VRP**; P3/P4/P5/P6 profilleri ayrı manifest |
| Hedef problemler ve düzey | P3/P4 akademik VRP; P5/P6 dalga. Önce CVRP, sonra TW, ardından Sw/So ve tip/kota profili. |
| Soy ağacı | Giant-tour/Split R10; HGS eğitim+çeşitlilik R11–12; SWAP* R13. PyVRP yeniden kullanım adayı R14–16; onun güncel motorunun HGS olduğu varsayılmaz. |
| Eski fikirle bağ | D1 yönü; karmaşık TSP genlerini üretim amacına taşımak yerine kısıt-aware evaluator. L3/L6/L7/L9/L10 ve C0. |
| Temsil | Occurrence permütasyonu + decoder'ın ürettiği tipli depo-kapalı rotalar; feasible ve infeasible altpopülasyonları ayrı; yalnız feasible best arşivi. |
| Olurluluk yönetimi | Kapsama/occurrence/depo/yön sert. Arama içinde Sw, So, varsa ortak toplam, T, R ve TW ihlal vektörüne ayrı uyarlanabilir cezalar; tip uyumsuzluğu ve kota sert veya ayrı açık ceza profili. P5'te bireysel TW icat edilmez; P4/P8 semantiği ayrı evaluator. Dış feasible sıra P3/P5'te rota sayısı→süre, P6'da ödünç-tip rota sayısı→süre. İhlal cezası çıktı olurluluğunu ikame etmez. |
| Bütçe muhasebesi | C0 çok-rotalı tam aday FE uzatması onaylanınca primary. Decode/eğitimde puanlanan tam adaylar sayılır; decoder segment maliyetleri, penaltı güncellemesi ve eğitim zamanı ayrıca. Repair hiçbir zaman ücretsiz polish değil. |
| Karmaşıklık | Önerilen özel P5 Split O(hQnL); çoklu kotalar durum uzayını büyütür. Klasik statik TW için desteklenen sabit-parça concat O(1), kabul sonrası özet yenileme O(L); generic tam aday hesabı en az O(n). Granüler tarama O(nK) basit hareket önerisi olabilir; SWAP* taramasının bütün maliyeti O(1) değildir. Genel pickup-TW/DARP için P5 formülü geçersiz. |
| Yönlü ve metrik olmayan matris | Decoder tüm segment yaylarını yönlü toplar; A2 türü eğitim. Süre/R ihlalinde kör segment break yok. Tip başına aynı matris varsayımı değişirse kolon/özet tip anahtarıyla tutulur. |
| Neden başarılı olması bekleniyor — kaynaklar | R11–13 eğitim ve çeşitliliği aynı aramada kullanır; R16 vektör yük modellemesine olanak tanır. |
| Neden başarılı olması bekleniyor — bizim yorumumuz | R3'te iç minimum-süre decoder ile dış rota-öncelikli amacın farkını açık profile taşımak ve gerçek kısıtlarla eğitim yapmak yararlı olabilir. P5'e uygun lex decoder **yeni varyanttır**, mevcut GA-Split'in örtük değişikliği değildir. |
| Performans hipotezi | ga_split/ga_split_hf'ye karşı daha iyi lex çözüm dağılımı: **orta**; HGS-CVRP/güncel PyVRP'ye göre rekabetçi kalite: **düşük**. Yanlışlama: eğitim/diversity/typed lex ablasyonu held-out'ta katkı göstermiyor veya sertifika başarısızlığı doğuruyorsa ilgili mekanizma/aktarımı reddet. |
| Yenilik | En yakın R11, R12, R13. **Algoritmik yenilik yok**; ayrı kaynak ve yönlü ride sözleşmesine mühendislik uyarlaması. Yeni problem formülasyonu/kapsamlı deney ayrı katkı olabilir, henüz kanıtlanmadı. |
| Uygulama | SplitDecoder, linear_split_decoder, typed_split_decoder, objective_rank.py, feasibility_certificate.py; kontrol ga_split/ga_split_hf. Yeni profile özgü lex DP, SWAP*/granular kısıt denetimi ve penalty denetleyici. Ortak altyapı sonrası **12–25 kişi-gün tahmin**; decoder amaç kararı ve P4 TW sözleşmesi bağımlılığı. |
| Riskler ve açık sorular | Penalty ölçeğinin rota önceliğini bozması; uygun olmayan backend evaluator; zero-capacity tipler; çoklu kota state patlaması. H01/H04 golden parity korunmalı; yeni davranış yeni kimlik altında. |
| Kabul kapısı | Her problem profili ayrı cert ve muhasebe kapısı; G0/G2 + karşılaştırılabilir objective manifesti. Üretim için ayrıca admission/snapshot/typed-day uçtan uca sözleşmesi; yalnız test setinde iyi sonuç yeterli değil. |

**Sözde kod**

~~~text
problem profilini, yönlü snapshot'ı ve araç kaynaklarını doğrula
bütçeli başlangıç giant-tour'larını oluştur
her tam decode sonucunu puanla; feasible arşivi güncelle
bütçe ve deadline uygunsa tekrarla:
  ebeveynleri kalite ve değişmez çeşitlilikle seç
  OX ile occurrence permütasyonu üret
  profile özgü kaynak-aware Split uygula
  tüm tam adayları aynı ledger ile değerlendir
  bütçeli yönlü inter/intra-route eğitim uygula
  feasible/infeasible havuzuna açık ihlal vektörüyle ekle
  feasible best'i ve diversity survivor seçimini güncelle
  belirli iş penceresinde kaynak cezalarını güncelle
  repair denenirse aynı sayaçtan harca
sertifikalı feasible best veya açık no-witness durumunu döndür
~~~

| Bileşen | Kaynak | Sözleşme testi | Telemetri | Ablasyon |
|---|---|---|---|---|
| Giant-tour + kaynak-aware Split | R10/R12; §4.0 türetimi | Küçük sabit permütasyonda tüm kesimler/typelerle DP paritesi; Sw/So/T/R/TW sınırları; nonmetric uzatma | segments, prune_reason, states, violation_vector | Aynı aramada cost decoder / lex decoder ayrı kimlik; sertifikalar sabit |
| OX + survivor diversity | R1, R11–12 | Occurrence tam bir kez; klon tanımı rota listesi sırasından bağımsız | parent_distance, clones, survival_age | Quality-only / diversity-biased |
| Granular LS ve SWAP* uyarlaması | R12–13 | Hamle sonrası tam evaluator eşitliği; değişen bütün rota kısıtları | moves_by_type, feasible_moves, education_gain | Eğitim yok / relocate-swap / +SWAP*; aynı bütçe |
| Kaynak cezaları ve repair | R11–12; kendi profil tasarımımız | Her ihlal ayrı ölçülür; feasible arşive ihlalli çözüm giremez | penalty_by_resource, feasible_ratio, repair_FE | Sabit / adaptive penalty; repair açık/kapalı |

**PyVRP kararı:** Sw/So için iki yük boyutu, varsa ortak toplam koltuk için ek toplam boyutu modellenebilir (R16'dan modelleme çıkarımımız). Pickup/drop-off yönü, depodan boş çıkış/dönüş, bireysel R, T, kota, sıfır Sw ve lex hedef için küçük oracle örnekleriyle iç evaluator paritesi gerekir. Yalnız dönen rotayı sonradan sertifikalamak, aramanın yanlış hedefini düzeltmez. Uyum yoksa PyVRP P3/P4 referansı olarak kalır. Uyum varsa yeni adaptör önerilebilir; yerel adaptörün bunu yaptığı doğrulanmadı.

### 4.4 A4 — Certified Route Pool (bugünkü dalga birincil öneri)

| Alan | Tasarım |
|---|---|
| Ad ve önerilen kimlik | Certified Route Pool; **Core-CRP-Wave** |
| Hedef problemler ve düzey | P5/P6 dalga; istem §4'teki yaklaşık 2–20 yolcu ölçeği. Büyük örneklerde eksik havuz sezgiseli, yeterince küçüklerde tam sayım profili. |
| Soy ağacı | GA/Split R10 ve mevcut kontrol R3; route-pool/set-partitioning matheuristic R19; planlanan kesin referansın veri sözleşmesi R1/istem §5. |
| Eski fikirle bağ | D2 yönünü benimser. E2BSO/R2DMA/P-AOEA genlerini taşımaz; L6/L7/L9/L10'u gerçek rotalar ve korunan incumbent ile karşılar. |
| Temsil | Kolon=(wave, occurrence sırası, tip, yön, çapa, snapshot, kaynak profili, tam süre/ride bilgisi, sertifika). Aynı yerden farklı yolcular farklı kapsama satırlarıdır. |
| Olurluluk yönetimi | Kolon oluştururken Sw/So, ortak toplam, T, yönlü R ve tip sert; P5 TW yok. Master'da occurrence tam kapsama ve kota sert. İhlalli rota “cezalı kolon” olarak feasible havuza girmez. |
| Bütçe muhasebesi | Başlangıç GA, yeni rota üretimi, sertifikalama ve master aynı native zaman zarfı içinde. Tam rota/çok-rotalı kontroller ayrıca sayılır; tek rota değerlendirmesi tam-wave FE sayılmaz. Exact backend muhasebesi olmadığı sürece **native-only**. |
| Karmaşıklık | Bir sıranın rota sertifikası O(L); prefix ile uzatma filtresi uygun P5 koşullarında O(1). Tüm sıralı altkümeler için üst sınır Σ(l=1..L) n!/(n−l)!; tam sayım genel durumda faktöriyel. M kolonlu set partitioning NP-hard; “20 küçük olduğundan kolay” varsayımı yok. |
| Yönlü ve metrik olmayan matris | İleri/ters rota farklı kolon; missing arc reddi. Süre veya pickup R ihlalinde uzatma otomatik kesilmez. Baskın kolon eleme yalnız aynı kapsam/tip/uyum ve ilgili amaç/kaynaklar için kanıtlanır; gün için değerli daha uzun rotayı kör eleme yok. |
| Neden başarılı olması bekleniyor — kaynaklar | R19, farklı sezgisel rotalarını set-partitioning ile birleştirmenin önceki örneğidir; R3 bağımsız sertifika ister. |
| Neden başarılı olması bekleniyor — bizim yorumumuz | Birçok permütasyonun rota parçalarını tek master'da seçmek, tek giant-tour'un ardışık kesim kısıtını kaldırabilir. Tanık havuzda korunursa çıktı başlangıç tanığından kötüleştirilmez; sıkı iyileşme garanti değildir. |
| Performans hipotezi | ga_split/ga_split_hf'ye göre lex iyileşme yönü: **orta**. Tam exact referansa açığın azalması: **orta**, sıfır açık garantisi yalnız tam sayım + gerekli master ispatlarıyla. Yanlışlama: eşit uçtan uca sürede havuz kontrolü iyileştirmiyor veya maliyeti artırıp katkı sağlamıyorsa çoklu üretici çıkarılır. |
| Yenilik | En yakın R19, R10 ve R1'deki exact plan. **Yok**; üretim sözleşmesiyle birleştirme. |
| Uygulama | ga_split, ga_split_hf, solve_typed_menu, feasibility_certificate.py, objective_rank.py; exact/wave_instance.py yalnız arayüz adı olarak. Yeni kolon deposu, duplicate anahtarı, güvenli enumerator ve master. **8–15 kişi-gün tahmin**, ortak cert/ölçek sözleşmesi sonrası. Exact solver henüz yok; WP-E0 loader var olması çalışan exact backend değildir. |
| Riskler ve açık sorular | Bellek/sayım patlaması, hatalı dominance, kısmi sayımı “tam” etiketleme, mevcut arşivlerin tüm alternatif rota ayrıntılarını içermemesi. Veri eksikse yeniden üretim gerekir; şu an yapılmadı. |
| Kabul kapısı | Tiny exhaustive oracle paritesi, kaynak/rota sertifikaları ve aşama kanıt etiketleri → native CANDIDATE. Tam FE kapısı olmadan primary VERIFIED deneme hakkı yok. Üretim tanık koruma ve aynı snapshot sözleşmesine bağlı. |

**Master — bizim formülasyonumuz.** x_r ikili kolon seçimi ve a_ir kolonun occurrence i'yi kapsama katsayısı olsun. Her i için Σ_r a_ir x_r=1. Büyük-tip kota profiline göre Σ_(r büyük) x_r≤q; “tümü büyük” profilinde diğer tip kolonları kapalıdır. Homojen amaç lex(Σ_r x_r, Σ_r C_r x_r); typed amaç lex(Σ_(r ödünç tip) x_r, Σ_r C_r x_r). Kota üst sınır mı tam kullanım mı olduğu manifestte açık olmalıdır; burada **üst sınır** tasarlandı. Araç başına gün yeniden kullanımı bu wave master'ın amacı değildir.

Lex ilk aşama optimum olarak kapatılmadan ikinci aşamaya geçmek global lex ispatı vermez. Süre kaldığında bulunan ilk-hedef tanığını sabitleyip süreyi iyileştirmek ayrı **heuristic** alt-aşama olabilir; incumbent korunur, durum etiketi değişmez. Tüm aşamalar tek toplam süre zarfını paylaşır.

**Sözde kod**

~~~text
başlangıç baseline tanığını aynı toplam süre zarfında üret ve sertifikala
tanığın tüm rotalarını havuza kilitli incumbent referansıyla ekle
izinli üreticilerle kolon üret; her kolonu bağımsız doğrula
tam sayım seçilmişse güvenli budamayla sırayla kolonları tara
bütçe kesildiyse enumeration_complete=false yaz
kolonları kararlı kimlikle tekilleştir
coverage + tip/kota master'ını kur; başlangıç tanığını ver
kalan sürede ilk lex hedefini çöz
OPTIMAL ise ilk hedefi sabitle ve ikinci hedefe kalan süreyi ver
aksi halde yalnız açıkça heuristic incumbent iyileştirmesi dene
seçilen rotaları ve amaç tuple'ını bağımsız yeniden doğrula
başlangıçtan kötü aday yerine korunan tanığı döndür
pool_hash, enumeration_complete ve her solver status'u birlikte yaz
~~~

| Bileşen | Kaynak | Sözleşme testi | Telemetri | Ablasyon |
|---|---|---|---|---|
| Rota üreticileri ve havuz | R3/R19 | Baseline rotaları kaybolmaz; occurrence/tip/snapshot anahtarı çakışmaz | columns_by_generator, duplicates, certified_rejects | Yalnız GA / çoklu başlangıç / +A3; eşit toplam süre |
| Enumerator ve budama | R3 + §4.0 türetimi | Küçük exhaustive evrenle tam eşitlik; nonmetric uzatma karşı örneği | expanded, prune_reason, complete, cap_reason | Sayım yok / güvenli sayım; kısıtlar kapatılmaz |
| Lex set partitioning | R19; yukarıdaki formülasyon | Küçük kolon altkümeleriyle exhaustive optimum; kota ve kapsam sınırları | objective_vector, bound_scope, status_by_stage, master_ms | Master yok / aynı kolon havuzunda master; generation süresi kontrolü |
| Tanık ve kanıt etiketleri | R3–4 | Timeout/unknown sonucu global infeasible veya optimal olmaz | incumbent_retained, proof_scope, no_witness | Sabit güvenlik sözleşmesi |

**Kanıt sınırı:** Havuz eksikse OPTIMAL yalnız **restricted-pool optimum**dur. Restricted-master LP/MIP alt sınırı da bütün rota evreni için global alt sınır değildir. Global dalga optimumu ancak bütün ilgili tipli olurlu rotaların eksiksizliği ve lex aşamalarının optimal kapanışıyla söylenebilir. Eksik havuzdaki infeasible sonucu tüm problem için olursuzluk kanıtı değildir.

### 4.5 A5 — Anchored Day Route-Pool LNS (gün birincil öneri)

| Alan | Tasarım |
|---|---|
| Ad ve önerilen kimlik | Anchored Day Route-Pool LNS; **Core-ADRPLNS-Day** |
| Hedef problemler ve düzey | P7; P5/P6 dalga üreticilerini gün amaçlarıyla birleştirir. P8'in gerçek zamanlı dispatch'i bu ilk sürümün parçası değil. |
| Soy ağacı | Route-pool matheuristic R19; multi-trip fikri R29 (içerik doğrulaması sınırlı); mevcut anchored reuse ve CP-SAT sözleşmesi R3/istem §4. Formülasyon aşağıda bizim önerimizdir. |
| Eski fikirle bağ | D3 yönü; L9/L10: dalga rota sayısını günlük fiziksel araç sayısı diye kullanmaz. L6/L7: toplam backend bütçesi ve incumbent koruma. |
| Temsil | Gün boyunca alternatif rota-tip kolonları ve açık fiziksel araç atama değişkenleri. Her kolon tek wave'in yönünü/çapasını korur. Dalgalar arası LNS, birkaç dalganın kararını birlikte yeniden açar; farklı anchor yolcularını aynı wave'e birleştirmez. |
| Olurluluk yönetimi | Kolonda Sw/So, ortak toplam, T/R ve tip sert; master'da occurrence coverage, araç uygunluğu/availability, cooldown ve filo envanteri sert. Rota sertifikasına gün atama sertifikası eklenir. |
| Bütçe muhasebesi | A4 gibi **native-only**: kolon üretimi, kritik dalga seçimi, CP ve doğrulama tek toplam süre zarfında. Her lex aşama ve LNS turu kalan süreyi kullanır; FE-labeled kapalı backend yok. |
| Karmaşıklık | V aday fiziksel araç ve M kolon için O(MV) atama değişkeni; basit bütün-çift conflict üretimi O(M²), araç bazlı kısıtlar O(VM²) olabilir. Master NP-hard. Her yeni rota sertifikası O(L); olay zamanlı alternatif modelin daha küçük oluşu semantik eşdeğerlik koşullarına bağlı. |
| Yönlü ve metrik olmayan matris | Kolonun t süresi özgün yönlü matristen; interval bundan türetilir. Daha kısa yolculuk varsayımıyla doğrudan yay alt sınırı yok. Ortak depo dışına genişletilirse rotalar arası deadhead ayrıca modellenir. |
| Neden başarılı olması bekleniyor — kaynaklar | R3 mevcut minimumun sabit rotalara koşullu olduğunu açıklar. R19/R29, rota kombinasyonu ve çok sefer kararlarının bilinen araştırma alanları olduğunu gösterir. |
| Neden başarılı olması bekleniyor — bizim yorumumuz | Bir dalgada toplam süreyi biraz değiştiren alternatif, kritik çakışmayı kaldırabilir. Bu yüzden gün amacıyla kolon üretmek ardışık çözümün kaçırdığı seçimleri açabilir; her veri setinde kazanç beklenmez. |
| Performans hipotezi | Sabit-menü seçim + mevcut atamaya göre ödünç araç/ödünç dakika tuple'ında iyileşme: **orta**. Eksiksiz ortak gün modeline yaklaşma: **düşük**, henüz böyle bir referans koşulmadı. Yanlışlama: aynı toplam sürede kritik-dalga LNS, uniform dalga seçimini ve sabit havuzu geçmiyorsa hedefli LNS çıkarılır. |
| Yenilik | En yakın R19, R29 ve mevcut gün-seçim yaklaşımı. **Genel algoritmik yenilik yok.** Occurrence/anchor/Sw–So sözleşmesi üzerinde uygulama katkısı olabilir; yenilik taraması ve deney gerekir. |
| Uygulama | planning/typed_day_selection.py, typed-fleet-assignment.ts, assignPhysicalVehicles, solve_typed_menu ve sertifika arayüzleri. Yeni route-level master, kaynak kritikliği ölçüsü, kolon üretimi bağlantısı. A4 sonrası **12–20 kişi-gün tahmin**; P7 amaç profili ve araç availability arayüzü açık karar. |
| Riskler ve açık sorular | Toplam filo ve ödünç sedan hedefini karıştırma; araç/dakika ile cooldown busy-time karışması; seçenek indekslerinin havuz büyüdükçe değişmesi; CP kanıt kapsamı. E01 mevcut exact projesi wave düzeyindedir; ortak gün modeli o iş paketine sessizce dahil edilemez. |
| Kabul kapısı | Küçük günlerde açık atama oracle'ı; sınırda cooldown eşitliği; bütün fiziksel araç/rota sertifikaları; native bütçe ve koşullu proof etiketleri. CANDIDATE→VERIFIED kapsamı sabit snapshot/gün profilidir; üretim için amaç kararı ve yeni paket onayı gerekir. |

**Gün master'ı — bizim formülasyonumuz.** Kolon r için x_r, araç v'ye atama z_rv, aracın kullanımı y_v ikili olsun. Σ_v z_rv=x_r; her occurrence i için Σ_r a_ir x_r=1; z_rv≤y_v. Uygun olmayan tip/availability için z_rv=0. Pickup intervali [a_r−t_r,a_r], drop-off [a_r,a_r+t_r]; aynı v için sonraki başlangıç önceki bitiş+cooldown'dan **erken olamaz**. Eşitlik uygundur. Çakışan kolon çiftleri için z_rv+z_sv≤1 veya eşdeğer optional NoOverlap kullanılır. Her kolon gerçek bir depo-kapalı rota olduğu için mevcut tek-depo profilinde araya ayrıca transfer yayına gerek yoktur.

**İki ayrı amaç profili:**

| Profil | Lexicographic hedef | Kapsam |
|---|---|---|
| Genel sanal/homojen filo | Kullanılan farklı araç sayısı; sonra açıkça tanımlanan travel-minute alt hedefleri | İstemdeki genel araç minimumu; rota sayısı veya tek-wave eşzamanlılığı yerine gerçek gün ataması |
| Sabit sahip olunan minibüs envanteri, ödünç sedan | B=Σ_(v ödünç) y_v; ardından Σ_(r,v ödünç) t_r z_rv; ardından Σ_r t_r x_r; son olarak kararlı tie-break | Envanter §1–2'deki belirli typed-day/Pareto profilinin karşılığı; borrowed-car hedefi genel toplam filo diye adlandırılmaz |

Bu rapor A5 hipotezini ikinci profile bağlar. Cooldown kaynak meşguliyetine girer; seyahat araç-dakikasına otomatik eklenmez. Başlangıç menü indeks toplamı, değişen rota havuzlarında aynı fiziksel nicelik değildir: legacy kontrolün indeksi ayrıca saklanır, yeni kolon kimlikleri kararlı tutulur; esas kıyas ilk fiziksel hedefler üzerinde yapılır. Haftalık ε karşılaştırmasında owned-minibus sayısı sabitlenir; max günlük B ve haftalık borrowed süre aynı koşullarda hesaplanır.

Tip içi araçlar tamamen eşdeğer, aynı depolu, sabit interval ve yalnız cooldown kısıtlıysa olay zamanlarındaki eşzamanlılık ile interval coloring daha küçük bir master verebilir. Bireysel availability, sürücü, farklı depo veya deadhead varsa bu sadeleştirme yeterli değildir; varsayılan öneri açık z_rv modelidir. Tam rota evreni yokken gün master'ının optimumu yalnız havuza koşulludur.

**Sözde kod**

~~~text
amaç profilini ve fiziksel filo snapshot'ını dondur
mevcut menü + atamadan sertifikalı gün tanığını al
tanığın kolonlarını ve atamasını incumbent olarak koru
toplam deadline içinde tekrarla:
  kaynak çakışmasının kritik olduğu wave kümesini seç
  o wave'lerin rota kararlarını serbest bırak; diğerlerini sabitle
  aynı anchor/yön içinde A4 veya A3 ile yeni kolonlar üret
  bütün kolonları kaynak sertifikasından geçir
  gün master'ını kalan süre ve mevcut tanıkla çöz
  lex aşamalarının status/bound kapsamını ayrı tut
  rota ve fiziksel araç atamasını bağımsız doğrula
  yalnız daha iyi geçerli tuple'ı incumbent yap
  kolon katkısı ve kritik-interval telemetrisini yaz
kanıt kapsamıyla birlikte sertifikalı incumbent'ı döndür
~~~

| Bileşen | Kaynak | Sözleşme testi | Telemetri | Ablasyon |
|---|---|---|---|---|
| Anchor ve fiziksel araç master'ı | R3 + kendi modelimiz | Farklı anchorlar birleşmez; cooldown eşitliği; Sw/So/availability; tiny exhaustive atama | overlaps, used_by_type, borrowed_count, certificate_failure | Sabit menü / route-level havuz; bütün kısıtlar sabit |
| Kritik-dalga LNS | R18'den destroy/repair fikrinin gün düzeyine aktarımı; R29 | Açılmayan kararlar sabit kalır; kaynak yükü doğru intervalden gelir | waves_opened, criticality, improvements_by_neighborhood | Uniform wave seçimi / kritik wave seçimi |
| Gün amaçlı kolon zenginleştirme | R19; A4 | Aynı snapshot; tanık korunur; dominance gün atamasını bozmaz | new_columns_used, generation_ms, master_ms | Zenginleştirme yok / dalga amaçlı / gün geri bildirimli |
| Lex ve kanıt yönetimi | R3–4 | İlk hedef ispatlanmadan tüm tuple optimal olmaz; timeout tanığı korur | stage_status, restricted_bound, incumbent_tuple | Güvenlik kapatılmaz; eşit toplam sürede aşama tahsisi ayarlanır |


### 4.6 A6 — Paired-request SISR/ALNS

| Alan | Tasarım |
|---|---|
| Ad ve önerilen kimlik | Paired-request SISR/ALNS; **Core-PRALNS-DARP**. P5 wave profili ile P8 paired-request profili ayrı yetenek kimlikleridir. |
| Hedef problemler ve düzey | P5'in daha büyük dalga örnekleri ve P8 belediye ölçeği; P3/P4 statik doğrulama köprüsü. Bu, P5 için A4'ten farklı ikinci ölçek tasarımıdır. |
| Soy ağacı | String removal/blink R17; request-level ALNS R18; yük/TW özetleri R12; max-wait/ride feasibility için R20. Adaptif seçim R21; FRR-MAB R33 yalnız sonraki ablation. |
| Eski fikirle bağ | BA-LNS/P-AOEA'nın destroy/repair fikri kalır, genom evrimi çıkar. L4'te kayan kredi ve uniform kontrol; L5'te kalibre kabul; L9'da tam iç kısıtlar; L10'da depolu amaç. |
| Temsil | P5: tek yön/anchor wave içindeki occurrence rotaları. P8: eşlenik pickup-delivery servis düğümleri, aynı araç ilişkisi, zaman programı, araç durumu ve kilitli taahhütler. Aynı fiziksel durak birleşimi yolcu kimliğini kaybetmez. |
| Olurluluk yönetimi | P5 Sw/So ve varsa toplam, T/R, tip/kota sert; bireysel TW yok. P8 araç içindeki her konumda kaynak yükü, pickup-before-delivery, same-vehicle, bireysel TW, max ride ve availability sert. Kısmi onarım geçici unassigned kümesi taşıyabilir; eksik talepli çözüm feasible incumbent olamaz. Reddedilen yerleştirmeler başka konum/araçla onarılır; sonunda tanık yoksa açık no-witness. |
| Bütçe muhasebesi | Tam ve tüm talepleri içeren adayın profil evaluator'ı bir FE; kısmi insertion delta/feasibility ayrı işlemler. Tam adayla kabul ve ödül ortak ledger'da. İterasyonun repair iç döngüsünde süre denetimi. Black-box alt-solver eklenirse o varyant, iç muhasebe yoksa native-only. |
| Karmaşıklık | P5 özel segment filtreleri O(1), tam rota kontrolü O(L). P8'de bir talebin pickup/delivery konum çiftleri O(L²); genel tam schedule check maliyeti ayrıca. Aşağıdaki statik difference-constraints modelinde O(L²) güvenli basit sınırla naive tüm-konum insertion O(L⁴)/rota/talep olabilir. Granüler kısa liste maliyeti düşürmeyi amaçlar; worst-case garantiyi kaldırmaz. |
| Yönlü ve metrik olmayan matris | SISR yakınlığı gerçek yönlü yay/rota yakınlığıdır; geometrik üçgen eşitsizliğine dayalı eleme yok. Zaman değişken matris tek statik cache gibi kullanılamaz; snapshot değişince süre özetleri geçersizleşir. |
| Neden başarılı olması bekleniyor — kaynaklar | R17 string/blink, R18 request-aware arama, R12 sınırlı concat, R20 belirli DARP feasibility yöntemleri sağlar. |
| Neden başarılı olması bekleniyor — bizim yorumumuz | Request bazlı yerel onarım bütün popülasyonu decode etmekten daha hedefli olabilir. P5'te hesap kazancı, P8'de ise ölçeklenebilir geçerli çözüm üretimi hipotezdir; dinamik gerçek trafik henüz kapsanmış değildir. |
| Performans hipotezi | Büyük P5 dalgalarında GA-Split'e göre kalite-zaman dengesini iyileştirme: **orta**. Statik P8 DARP örneklerinde aynı checker ve operatörlere sahip uniform request-aware ALNS'e göre adaptive/Bandit katkısı: **düşük**. P5'te uyumlu PyVRP, P8'de aynı DARP kısıtlarını uygulayan güçlü SISR/ALNS referansına yaklaşma: **düşük**. Yanlışlama: blink/string/adaptiveness ablation'ları fayda göstermiyorsa çıkar; herhangi bir yanlış-feasible schedule sonucu yetenek geçişini durdurur. |
| Yenilik | En yakın R17, R18, R20. **Çekirdek yenilik yok.** Kaynak tipleri, anchor profili ve DARP uzatması problem mühendisliğidir. Öğrenme eklemek tek başına yenilik değildir. |
| Uygulama | destroy_ops.py/repair_ops.py adları ve ALNS_TSP ağırlık mantığı, feasibility_certificate.py, objective_rank.py. Mevcut operatörlerin DARP'yi desteklediği varsayılmaz. Yeni paired removal/insertion, schedule checker, occupancy özetleri; **20–40 kişi-gün statik çekirdek tahmini**. Canlı trafik/dispatch bu tahmine dahil değil. |
| Riskler ve açık sorular | Waiting/biniş ve kişi bazlı max-ride tanımı; onboard yolcuların geçmiş süresi; in-flight rota taahhütleri; matris tazeliği; O(1) filtreden yanlış sertifika üretme. P8 özellikleri ayrı sahip kararlarıdır. |
| Kabul kapısı | Önce statik P3/P4, sonra P5 ve bağımsız DARP oracle testleri; her profil ayrı CANDIDATE. P8 VERIFIED için eşlenik coverage/occupancy/schedule ve veri modeli onayı. Canlı üretim ayrıca replan/freeze/time-data kapıları gerektirir. |

**O(1) sınırı ve önerilen kesin kontrol.** R12'deki klasik statik TW özeti, önceden hesaplanmış sabit sayıda parçanın birleştirilmesini hızlandırır. Waiting ve her pickup'ın teslimi arasındaki ride bağımlılığı yüzünden P8'de tek toplam süre prefix'i yeterli olmaz. R20'nin özel lineer algoritması da bütün P8 özelliklerinin doğrudan uygulaması diye sunulmaz.

İlk statik P8 checker önerimiz: sabit bir rota sırası için servis zamanı değişkenleri b_i; ardışık yol/servis süresi alt sınırları, TW alt/üst sınırları ve her eşlenik talep için b_delivery−b_pickup−pickup_service≤R_i gibi **onaylanacak ride tanımına bağlı** difference constraints. İsteğe bağlı max-wait sınırları da tanımlanmışsa eklenir. Her düğüm yalnız bir request'e ait ve tüm süreler statikse düğüm/kenar sayısı O(L); Bellman–Ford tipi negatif çevrim denetimi O(L²) üst sınırı verir. Kapasite ve precedence ayrı O(L) geçişle kontrol edilir. Bu bizim ilk doğrulayıcı tasarımımızdır; çalıştırılmış ya da genel time-dependent DARP için kanıtlanmış bir implementasyon değildir. Öğrenilmiş veya ucuz filtre yalnız bazı adayları eler; kabul edilen tam çözüm exact schedule checker'dan geçer.

P5 profilinde kaldırma bir occurrence'ı o wave içinde taşır; öğrencinin başka anchor/direction'daki ayağını aynı rotaya katmaz. P8'de henüz binmemiş talebin iki düğümü birlikte kaldırılır. Onboard pickup geçmişte kalmıştır: araç değiştirilemez, yalnız izinli teslim/sıralama kararları açılır ve geçmiş ride süresi taşınır. Dinamik genişlemede frozen horizon/taahhüt politikası sahibi tarafından belirlenmeden canlı dispatch yoktur.

**Sözde kod**

~~~text
statik profili, snapshot'ı ve varsa kilitli taahhütleri doğrula
tam sertifikalı başlangıcı bütçeli puanla; best'i tut
bütçe ve deadline uygunsa tekrarla:
  uniform veya açık ağırlık kuralıyla removal/repair seç
  P5 occurrence'larını veya P8 izinli bütün request'lerini kaldır
  konum adaylarını yönlü maliyet ve güvenli kaynak filtresiyle sırala
  her insertion için profile özgü kesin feasibility kontrolü yap
  regret/blink ile onar; deadline'ı iç döngüde denetle
  tüm talepler atanmadıysa partial durumu feasible sayma
  tam çözümü ortak ledger'dan puanla
  lex profiline uygun kabul kararını ver
  feasible best'i güncelle; pencere kredisini tamamlanan işe göre yaz
bağımsız rota/schedule sertifikasıyla best veya no-witness döndür
~~~

| Bileşen | Kaynak | Sözleşme testi | Telemetri | Ablasyon |
|---|---|---|---|---|
| String/request removal | R17–18; P5/P8 aktarımı bizim | P8 eşlenikler birlikte; onboard/frozen kararlar korunur; P5 anchor değişmez | removed_requests, paired_violations, frozen_skips | Random / Shaw / string; aynı removal büyüklüğü |
| Greedy-regret-blink repair | R17–18, R1 §5 | Tam kapsam; her yerleştirme exact feasibility; blink tüm seçenekleri atladıysa tanımlı yeniden deneme/no-witness | insertion_positions, filters, exact_checks, repair_failures | Greedy / regret-2 / regret-3; blink açık/kapalı |
| TW/ride feasibility katmanları | R12/R20; kendi fark-kısıtı tasarımımız | Küçük sabit sıralarda bağımsız schedule oracle; waiting, max-ride ve occupancy karşı örnekleri | filter_reject, checker_ms, false_feasible | Full checker / cache+aynı checker; doğruluk kapatılmaz |
| ALNS seçimi ve kabul | R18/R21, R33 opsiyonel | Maruziyet yerine pencere oranı; uniform testte kollar erişilebilir; C0 kabul testleri | arm_pulls, rewards, uphill_accept | Uniform / Ropke–Pisinger / kayan bandit; FRR-MAB ayrı sonraki kol |

### 4.7 A7 — Distance-context Recombination

| Alan | Tasarım |
|---|---|
| Ad ve önerilen kimlik | Distance-context Recombination; **Core-DCRM-TSP** |
| Hedef problemler ve düzey | İlk sürüm yalnız P1, akademik TSP. P2'ye aktarım ancak ayrı yönlü crossover kanıtıyla; bugünkü üretim önceliği değil. |
| Soy ağacı | GPX2 R6, ensemble R22, sliding-window AOS R21, local-optima bilgisi R23; R24 araştırma önceli. |
| Eski fikirle bağ | DAR-MA/R2DMA'nın benzerlik düşüncesi ölçülebilir yönsüz edge distance'a dönüşür. P-AOEA'nın maruziyet kredisi yerine pencere oranı; L3/L4/L6/L8. Rastgele swap dalı yerine aynı LS ile eğitim. |
| Temsil | A1 ile aynı elit turlar; seçilen ebeveyn çifti, önceden dondurulmuş mesafe dilimi ve operatör kayıtları. Bin sınırları geliştirmede belirlenir; testte yeniden ayarlanmaz. |
| Olurluluk yönetimi | Sert Hamilton; GPX/OX/kick sonrası eğitim ve full score. Sw/So/T/R/TW/tip-kota yok; böyle instance reddedilir. |
| Bütçe muhasebesi | C0 tam tur FE; her operatöre aynı eğitim paketi sınırı. Context ve kredi hesaplarının zamanı/işi ayrıca. Ödül FE'ye veya başarı oranına dayanır; runtime ödüllü sürüm native olarak ayrılır. |
| Karmaşıklık | Edge distance O(n), elit çeşitlilik güncellemesi O(mn); küçük sabit operatör/bucket sayısında seçim sabit maliyetlidir. LS maliyeti A1, toplam bütçe context tarafından artırılamaz. |
| Yönlü ve metrik olmayan matris | P1'de metrik olmayan simetri kabul edilebilir; öğrenilmiş coğrafi varsayım yok. P2 reversalı benzer saymak yasak; bu kimlik henüz P2 yeteneği vermez. |
| Neden başarılı olması bekleniyor — kaynaklar | R21 dinamik AOS; R22 GPX/EAX ensemble; R23 operatör başarısını yerel optimum ilişkileriyle inceleme önceli sunar. |
| Neden başarılı olması bekleniyor — bizim yorumumuz | Ebeveyn mesafesi, ebeveyn kalitesi ve instance özellikleri kontrol edildikten sonra operatörün ek faydasını öngörüyorsa context değer taşıyabilir. Yalnız mesafe-kazanç korelasyonu yeterli değildir. |
| Performans hipotezi | H1: operator×distance etkileşimi unseen instance'larda sürer: **düşük**. H2: contextual seçim aynı operatörlü uniform ve non-context bandit'i eşit FE'de geçer: **düşük**. R22 benzeri ensemble/LKH/GA-EAX'e yaklaşma: **düşük**. H1 yoksa context, H2 yoksa bandit kaldırılır; A1/ILS'e dönülür. |
| Yenilik | En yakın R21, R22, R23; ek yakın yön R24. Mesafe-koşullu eğitim kazancı ve FE bağlamının tam birleşiminin yeniliği **DOĞRULANMADI**. “İlk” iddiası yok; ayrı odaklı tarama gerekir. |
| Uygulama | A1 altyapısı + ALNS_TSP'nin mevcut ağırlık fikri; yeni context logger, bucket seçimi, pencere kredisi. A1 ve D2 arazi deneyi sonrası **5–10 kişi-gün tahmin**; H1 başarısızsa yapılmaz. |
| Riskler ve açık sorular | Seçim yanlılığı; kaliteli ebeveynin zaten daha iyi olması; ham GPX kazancının LS kazancıyla karışması; boş bucket; yakın-klonlar; tuning sızıntısı. |
| Kabul kapısı | D2 H1 ve G0; sonra CANDIDATE. G2'de uniform ve non-context bandit kontrolleri, context-shuffle negatif kontrolü ve held-out kanıt olmadan VERIFIED/yenilik iddiası yok. |

**Sözde kod**

~~~text
H1 geliştirme kapısının kararını ve dondurulmuş bucket sınırlarını yükle
A1 ile aynı başlangıç/LS/bütçe düzenini kur
bütçe ve deadline uygunsa tekrarla:
  kaliteye göre kararlı şekilde hedef ebeveyn ve eş seç
  değişmez edge distance ile context hesapla
  keşif tabanlı uniform veya context-window seçimiyle operatör seç
  GPX2, OX ya da hedef ebeveyne kick uygula
  aynı LS iş üst sınırı içinde çocuğu tam puanla/eğit
  ham ve eğitim sonrası kazancı ayrı yaz
  hedef ebeveyne göre önceden tanımlı ödülü hesapla
  yalnız seçilen context/kolun pencere kredisini güncelle
  C0 kabul, arşiv ve diversity kurallarını uygula
sertifikalı best ve operator×context telemetrisini döndür
~~~

| Bileşen | Kaynak | Sözleşme testi | Telemetri | Ablasyon |
|---|---|---|---|---|
| Mesafe context'i | R1, R23; kendi tanımımız | Aynı çiftin rotasyon/reversalında aynı bucket; test bucket'ı öğrenilmez | context_counts, distance, parent_quality | Context yok / gerçek context / shuffled context |
| Sliding-window seçim | R21; kendi FE ödülümüz | Boş pencere, keşif, kredi yaşlanması ve deterministik tie-break | pulls, reward_per_FE, age, exploration | Uniform / non-context bandit / context bandit |
| Operatör portföyü + eş eğitim | R6/R22 | Her kol Hamilton ve eş LS üst sınırında; ham/post-LS skor ayrılığı | raw_gain, educated_gain, FE_by_arm | GPX2 / OX+LS / kick+LS / birleşim |
| H1 arazi deneyi | R1 karar D2; R23 | Ebeveyn çifti/kalitesi ve LS bütçesi kontrollü; instance dışı doğrulama | interaction_effect, uncertainty, bucket_coverage | Mesafe yerine rastgele bucket; sabit ebeveyn kalitesi tabakaları |

### 4.8 Başlangıç fikirleri, eski bileşenler ve D1–D6 kararları

| Fikir/yön | Karar | Kaynak ve gerekçe | Koşul / elenen iddia |
|---|---|---|---|
| EB-PXILS | A1 olarak sadeleştir | R5–6/R22; kick+LS+GPX2 sınanabilir | Entropi fazları ayrı ablasyon; özdeş popülasyon tabanını threshold ayarıyla örtme yok |
| DAR-MA | A7 olarak koşullu tut | R21–23; bağlamın ek öngörü değeri gösterilmeli | D2/H1 yoksa yeni algoritma yerine A1; R24 hakemsiz kanıt |
| BA-LNS | A6 ile P5/P8'e taşı | R17–18; kısıtlı routing'e doğal eşleme | Genom evrimi yok; FRR-MAB ancak uniform ve daha basit adaptiveness'i geçerse |
| BB-Merge | Bağımsız tasarım yerine ertelenmiş A1/A7 modülü | R5 tour merging/backbone ve R6 | Ortak kenar global optimum kanıtı değildir. Donmuş kenarlar çözüm uzayını yanlış daraltabilir |
| EAX-MA | Referans wrapper olarak tut | R7/R30/R32 | Yeni algoritma/yenilik yok. “Tavan kolu” matematiksel kalite üst sınırı anlamına gelmez |
| D1 HGS | A3; önce P3/P4, sonra P5/P6 | R11–16 | PyVRP vector load doğrulandı; R/T/lex uyumu açık. Güncel PyVRP'ye HGS adı verilmez |
| D2 route pool | A4; kısa vadeli üretim önceliği | R19/R3 | Eksik havuz optimumu global diye yazılmaz; 2–20 boyutta tam sayım her zaman kolay değil |
| D3 entegre gün | A5; A4'ten sonra | R3/R19/R29 | Wave exact projesinden ayrı araştırma paketi; anchor ve amaç profili korunur |
| D4 SISR/ALNS | A6; aşamalı statik → dinamik | R17–18/R12/R20 | P5 O(1), klasik TW concat O(1) ve genel DARP farklıdır; tek prefix ile tüm olurluluk iddiası reddedilir |
| D5 ATSP | A2 yön koruyan LS; ayrı dönüşümlü referans | R8/R9/R5 | GPX2+2n verimi, GA-EAX ATSP ve elkai parametre erişimi açık sorular |
| D6 öğrenme | A7 bandit ablasyonu kabul; öğrenilmiş adaylar ilk sürümden çıkar | R21/R23/R24 | Eğitim maliyeti ve out-of-distribution nonmetric test olmadan learned candidate önerilmez; büyük veri/NN geliştirme görevi açılmaz |

**BB-Merge modülü için gerekli sözleşme:** Ortak kenarlar yalnız path bileşenleri oluşturuyorsa sıkıştır; tam ortak Hamilton çevrimini özel durum say. Simetrik zincirin iki orientation'ı ve sınır maliyetleri korunmalı; yönlü zincir ters çevrilemez. Tek bir “supernode distance” bunları kaybedebilir. Açılım tam turu ve maliyeti geri vermeli. Telemetri: sabitlenen kenar, komponent, arama uzayı, serbest bırakma sonrası kazanç. Ablasyon: hiç sabitleme / geçici sabitleme+serbest bırakma. Yeni kenar keşfi kapatılamaz. Bu modül ilk sürüm eforuna dahil değildir.

**Eski mekanizmaların akıbeti:** CPSO/metafor güncellemeleri, boyuta bağlı rezonans kesimi, LS'siz perturb, toplam maliyetten doğrudan SA sıcaklığı, maruziyet biriktiren genom seçimi kaldırılır. OX yalnız eğitimle kontrol kolu olarak tutulur. Entropi, LAHC ve diversity düzeltilmiş açık sözleşmeleriyle isteğe bağlıdır. R2'de kaybın belirli koşularda gözlenmemesi, best arşivi açığını kabul etme gerekçesi değildir. Eski kimlikler tarihsel tekrar üretimi için dondurulabilir; bu rapor onları düzenlememiştir.

## 5. Portföy karşılaştırması

Beklentilerin tümü hipotezdir. “Orta/düşük” başarı olasılığına dair nitel tasarım yargısıdır; istatistiksel güven aralığı değildir. Kişi-günler ortak altyapı sonrası ek iş tahminidir; ortak modülleri tekrar sayarak toplanmamalı.

| Tasarım | Problemler | Kontrole göre beklenti | Referansa göre beklenti | Güven | Yenilik | Ek efor | Üretim değeri | Ana risk |
|---|---|---|---|---|---|---|---|---|
| A1 CPILS | P1 | Aynı LS'li ILS'e GPX katkısı | LKH/GA-EAX'e yaklaşma, üstünlük iddiası yok | Kontrol orta; referans düşük | Yok | 8–15 kişi-gün | Bugünkü küçük rotalarda sınırlı; akademik temel | GPX katkısı LS maliyetini karşılamayabilir |
| A2 DCILS | P2 | Native sürede daha çok yararlı yönlü hareket | Dönüşümlü LKH'ye yaklaşma | Orta / düşük | Yok | 5–9 kişi-gün | Yönlü LS'nin güvenilir yeniden kullanımı | Candidate pruning nonmetric kalitede kayıp |
| A3 VHGS | P3–P6 | GA-Split'e gerçek kaynak-aware eğitim katkısı | HGS/PyVRP kalitesine yaklaşma | Orta / düşük | Çekirdek yok | 12–25 kişi-gün | Çoklu rota ve heterojen filo | Kısıt/lex aktarımı ve penalty ölçeği |
| A4 CRP | P5/P6 | Korunan GA tanığını iyileştirme | Tam exact'e açık kapatma | Orta / orta | Yok | 8–15 kişi-gün | **Bugünkü dalga için yüksek öncelik** | Eksik havuzun kanıt diye sunulması |
| A5 ADRPLNS | P7 | Ardışık routing+assignment tuple'ını iyileştirme | Gelecekteki tam ortak modele yaklaşma | Orta / düşük | Genel fikir yeni değil | 12–20 kişi-gün | **Gün için yüksek öncelik** | Yanlış filo amacı ve atama modeli |
| A6 PRALNS | P5/P8; P3/P4 köprü | P5: GA-Split'e kalite-zaman katkısı; P8: uniform request-aware ALNS'e adaptiveness katkısı | Uyumlu SISR/VRP-DARP referansına yaklaşma | P5 kontrol orta; P8 kontrol ve referans düşük | Çekirdek yok | 20–40 kişi-gün statik | Belediye hedefi için anlamlı; bugün gereğinden geniş olabilir | DARP feasibility ve dinamik taahhütler |
| A7 DCRM | P1; P2 ileride | Uniform/non-context seçime ek bilgi | Ensemble/EAX/LKH'ye yaklaşma | Düşük / düşük | DOĞRULANMADI | 5–10 kişi-gün | Bugünkü üretimde düşük öncelik | Context katkısının genellenmemesi |


## 6. Deney ve ablasyon planı — henüz çalıştırılmadı

### 6.1 Veri, geliştirme/test ayrımı ve ölçüler

| Aile | Geliştirme / ayar | Kilitli test | Ölçü ve karşılaştırma sınırı |
|---|---|---|---|
| P1 | R1 §4 Faz 3 önerisi: yaklaşık 15 TSPLIB örneği, 100–1000 düğüm; D1/D2 için belirtilen geliştirme altkümesi | R1: yaklaşık 20 örnek, 1000–20 000 düğüm ve uygun National TSP altkümesi; boyut dağılımı farklı olduğu ayrıca raporlanır | Optimum biliniyorsa açık; değilse BKS'ye açık. Held-out küçük/orta örnekler ayrıca ayrılarak yalnız boyut ekstrapolasyonu ile genel başarı karıştırılmaz. |
| P2 | TSPLIB ATSP geliştirme altkümesi ve anonim yönlü nonmetric matris aileleri; exact-ID manifesti uygulamada dondurulur | Ayrı ATSP örnekleri ve farklı snapshot/üretim aileleri | Yönlü kapalı maliyet, geçerlilik, optimum/BKS açık, süre/FE; tek ft53 genelleme kanıtı değildir. Güncel ithalat durumu bu görevde incelenmedi. |
| P3/P4 | CVRPLIB / Solomon geliştirme kümeleri, kapasite ve TW sıkılığına göre tabakalama | Ayrı aile/örnekler; aynı örneğin yeniden ölçeklenmiş kopyası test bağımsızlığı sayılmaz | Olurluluk önce; benchmark'ın araç/maliyet sırası ve yuvarlama kuralı birebir eşit. UniRide lex profili farklıysa BKS kıyası ayrı profil. |
| P5/P6 | Mevcut snapshot dalgaları yalnız geliştirme ve regresyon; Sw/So karışımı, yön, T/R ve tip/kota sınırları | Ayrı gün/hafta/snapshot aileleri; küçük exact çözülebilir kontrollü örnekler ve büyüyen sentetik aileler | Route count, borrowed-type route count, süre, kişi bazlı ride; sertifika oranı; exact yalnız ispatlıysa optimum açığı. Aynı haftadaki dalgalar bağımsız deney birimi varsayılmaz. |
| P7 | Belirli amaç profili ve owned-fleet değeri sabit; kontrol aynı başlangıç menüsü | Bütün gün/hafta bloklarıyla ayrılmış veri | B, borrowed minutes, total travel minutes, gerçek fiziksel atama, proof_scope. Günün rota sayısı filo sayısı yerine geçmez. |
| P8 | Statik DARP/PDPTW köprü örnekleri; max-ride/same-vehicle/occupancy sözleşmesi eşitlenir | Görülmemiş statik demand aileleri; dinamik olay akışları ancak ayrı sonraki protokolde | Feasible service coverage, ride/TW, araç ve süre tuple'ı, runtime dağılımı. Genel PDPTW BKS'si ek DARP kısıtlı instance'ın BKS'si değildir. |

İstemdeki mevcut ölçek ve dosya sayıları veri mevcudiyetinin bu çalışmada yeniden doğrulanmış envanteri değildir. Üretim haftası için **bir snapshot hafta, hücre başına bir koşu, seed 42, native** etiketi korunur; bu tarihsel arşiv yeni çok-tohum deneyin yerine geçmez (istem §3–4; R3). P8'de yüzlerce–binlerce talep hedef ölçeğidir, gerçekleşmiş kapasite ölçümü değildir. Kişisel yolcu verisi yayın paketine taşınmaz; occurrence ilişkisi korunmuş anonim manifest gerekir.

### 6.2 Bütçe, tohum ve ayar

| Konu | Plan |
|---|---|
| Primary | P1–P4 ve uygunluğu kanıtlanan P5/P6 sezgisel profillerinde **atomic_upper_bound_v1**, aynı instance için aynı tam amaç FE sınırı. G0 pilotundan sonra B(n,profil) dondurulur; bu rapor ölçülmemiş bir B sayısı uydurmuyor. Init/search/LS/polish payları kaydedilir; gizli son iyileştirme yok. |
| Native | Sabit uçtan uca süre veya açık algoritmik sonlanma; ayrı manifest ve tablolar. LKH/GA-EAX/PyVRP/OR-Tools/VROOM/CP backend'leri iç muhasebe doğrulanana kadar burada. Matheuristic'te üretici+master+doğrulama süreleri beraber görünür. |
| Tohumlar | R1 Faz 3: örnek başına en az **10**, küçük örneklerde en az **20** tekrar. R4'e göre SHA-256(instance_id, repetition_index); kararlı stage seed'leri. Exact deterministik referans “çok seed” ile istatistik büyütmez; status ve bound raporlar. |
| Eşit tuning | ILS ve bütün ayarlanabilir kollar aynı irace toplam hedef-koşu/hesap zarfı, aynı geliştirme örnekleri ve tuning seed listesi ile ayarlanır (R26). FE ve native için ayrı yapılandırma/manifest; başarısız koşuların maliyeti de tuning defterine girer. |
| Parametreler | K, kick, GPX oranı, LAHC geçmişi, penalty ve bandit pencere/bucket ayarları geliştirmede seçilir. Test sonuçlarına bakarak değişiklik varsa yeni sürüm ve yeni kilitli test gerekir. Parametresiz ya da sabit referans “ayar hakkı varmış” gibi sahte harcama yapmaz; ayrılan/kullanılan bütçe ayrı yazılır. |
| Donanım ve başlangıç | Aynı thread sınırı, CPU/OS/derleyici/paket sürümü; JIT cold ve warm süreleri ayrı. Dense matris hazırlama/cache maliyeti tüm kollarda aynı raporlama kuralıyla; aynı makinede tek tek veya dengeli sıra. |
| Sonuç kaydı | Çözüm yolları, snapshot/hash, occurrence sırası, seed, parametreler, FE ledger, delta/decoder iş sayaçları, tüm operatör sayaçları, exception ve fallback bilgisi. Fallback ayrı algoritma kimliği; sessiz başarı yok. |

### 6.3 Zorunlu kontrol ve referans kolları

| Aile | Kontrol | Güçlü referans / uygunluk kapısı |
|---|---|---|
| TSP | Aynı hızlı LS, aynı init/kick/bütçeli **ILS**; ALNS-TSP | LKH-3 (ayrı sabit RUNS ve GPX2 parametresi profili), GA-EAX, OR-Tools GLS. R31 hızlandırması ve R32 EAX varyantları ancak sürüm/kaynak/erişim doğrulanırsa ek referans; zorunlu ilk uygulama değil. |
| ATSP | Aynı yön koruyan Or-opt/or-3opt ILS; A2 candidate ablasyonları | Dönüşüm + inverse mapping testlerinden geçmiş **2n LKH-3**; bulunur ve doğrulanırsa EAX-ATSP. Simetrik GA-EAX'i ATSP etiketiyle çalıştırma yok. |
| CVRP/CVRPTW | Mevcut GA-Split; profil izin verirse aynı LS'li çok-başlangıç/ILS | **Tarihsel PyVRP-HGS/HGS-CVRP** ve **güncel PyVRP-ILS** ayrı sürümler; OR-Tools, VROOM; objective/rounding/feasibility uyumlu BKS. Kapasite veya TW desteği olmayan kol o profile alınmaz. |
| UniRide wave | ga_split, ga_split_hf; aynı giriş/snapshot/tip/kota | PyVRP yalnız Sw/So yanında T/R/lex evaluator uyumu kanıtlanırsa. Küçük dalgada gelecekte rota sayımı + set partitioning; **planned, not executed**, WP-E0 loader solver değildir. |
| UniRide day | Aynı menü üzerinde mevcut CP-SAT seçimi + sabit rota ataması; A4 çıktısını ardışık atama | A5'in aynı havuz üzerinde tam master çözümü restricted-pool referansıdır. Tam ortak gün optimumu elde edilmiş gibi raporlanmaz. |
| P8 | Uniform request-aware ALNS; aynı removal/repair/LS/schedule checker | SISR/ALNS ve uyumlu PDPTW/DARP çözücüleri; seçilecek dağıtımın eşlenik talep, max ride, waiting ve kaynak modeli ayrı doğrulanır. Uyumsuz PyVRP/VROOM çıktıları “kötü solver” sonucu sayılmaz. |

### 6.4 Ablasyonlar ve yanlışlama

Bütün kollarda evaluator, sertifika ve bütçe aynı kalır. Kısıtları kaldırıp daha ucuz çözüm elde etmek algoritmik ablasyon değildir. Kritik bir etkileşim iddiasında yalnız leave-one-out yetmez; ilgili bileşenlerin faktöriyel açık/kapalı kombinasyonu geliştirmede değerlendirilir. Önceden belirlenen hipotez ve sonuç ölçüsüyle çalışılır.

| Tasarım / hipotez | Zorunlu kollar | Hipotezi reddettiren sonuç / karar |
|---|---|---|
| A1 GPX katkısı | Aynı LS'li ILS; çoklu ILS; +GPX2; OX+LS; restart+LS; ayrıca entropy açık/kapalı | GPX'nin post-LS katkısı kontrolün üstüne çıkmıyor veya eşit toplam süreyi bozuyorsa GPX tasarımı desteklenmez. Entropi ek katkı göstermiyorsa çıkar. |
| A2 hız/kalite | Tam tarama; candidate; candidate+aktif kuyruk; candidate+geniş tarama | FE başına kalite kötüleşmesi ve native hız kazancı bunu karşılamıyorsa liste politikası reddedilir. Yanlış directed maliyet doğrudan doğruluk kapısı ihlalidir. |
| A3 HGS aktarımı | Cost/lex decoder ayrı variant; eğitim kapalı; +relocate/swap; +SWAP*; diversity kapalı; sabit/adaptive penalty | Kaynak-aware eğitim ek yarar sağlamıyor veya violation artışı feasible çıktıda saklanıyorsa ilgili aktarım başarısız. İç amaç değişikliğinin etkisi HGS etkisi diye yazılmaz. |
| A4 kolon/master | Aynı baseline; yalnız tek üretici havuzu; çoklu havuz; aynı havuz + master; küçüklerde eksiksiz sayım | Aynı uçtan uca süre altında ek üretici/kolonlar katkı vermiyorsa çıkar. Master’ın incumbent koruması bozulursa correctness başarısız; iki kol zaten optimumsa sıfır fark üstünlük iddiası üretmez. |
| A5 gün entegrasyonu | Sabit menü; sabit route pool; uniform-wave LNS; critical-wave LNS; aynı havuzla tek master | Kritik wave seçimi uniform'u geçmiyorsa criticality çıkar. Havuz değişimi ile atama değişiminin etkileri ayrılmazsa mekanizma iddiası kurulmaz. |
| A6 SISR/adaptiveness | Random/Shaw/string; greedy/regret; blink kapalı/açık; uniform/RP/window-bandit; aynı schedule checker | String/blink/adaptiveness katkısızsa ilgili bileşen çıkar; P8 transferinde yanlış-feasible varsa bütün P8 yeteneği durur. |
| A7 H1/H2 | R1 D2'de örnek başına **50 ILS yerel optimumu**; aynı çiftlerde GPX/OX/kick+eş LS; uniform/non-context/context/shuffle | Kalite ve instance etkileri kontrol edildiğinde operator×distance etkileşimi genellenmiyorsa H1 reddedilir. Context uniform ve non-context'i geçmiyorsa H2 reddedilir. |

R1'deki altı eski benchmark örneği ve arazi pilotu yalnız geliştirme/regresyon içindir; tasarım bu sonuçlardan etkilenmiş olduğundan kör test diye sunulamaz. Eski üçlü onarımlarına ilişkin Faz 1, yeni portföyden ayrı bilimsel kapanış çalışmasıdır; burada o algoritmaların onarımı veya testi yapılmaz.

### 6.5 İstatistik ve raporlama

R4'ün istatistik sözleşmesi esas, R27 istenen yöntem kaynağı ve R28 deney şeffaflığı dayanağıdır.

- **Eşleştirme birimi:** Aynı bağımsız instance'lar üzerinde, önceden seçilmiş seed-özetini (örneğin medyan) kullanarak algoritma çiftlerini Wilcoxon signed-rank + Holm ile karşılaştır. Çok algoritma için aynı instance bloklarında Friedman; anlamlı omnibus sonrası önceden tanımlı post-hoc/Holm. Aynı sayısal seed, farklı arama süreçlerinde kendi başına eşleştirilmiş örnek kanıtı değildir.
- Tek instance üzerinde bağımsız tekrar dağılımları için R4'ün bağımsız örnek yaklaşımı (Kruskal–Wallis / Mann–Whitney + Holm) korunur. Aynı instance'ın seed satırlarını bağımsız problem gibi Friedman'a havuzlama yok. Gerçek aynı başlangıç/aynı instance ablation blokları kurulursa eşleştirme gerekçesi açık yazılır.
- P5/P7'de gün/hafta ve demand ailesi bağımlılıkları korunur; aynı snapshot'taki dalgalarla örnek sayısı yapay büyütülmez. Etki büyüklüğü, instance bazlı farklar, kazanma/eşitlik/kaybetme ve uygun bloklu belirsizlik aralıkları birlikte verilir. Gerektiğinde instance üst düzey, seed alt düzey olacak biçimde yeniden örnekleme kullanılır.
- R1 G1/G2'nin Holm p<0,05 koşulu korunur. Ancak p≥0,05 “eşit” veya “yenilmiyor” kanıtı değildir. G1(c) için pratik kötüleşme marjı sahibin onayıyla önceden konur ve farkın güven aralığına bakılır; marj belirlenmeden non-inferiority iddiası yok.
- Olursuz/no-witness/timeout koşuları silinmez; oranları ayrı, çözüm kalitesi yalnız açık feasible koşullu tabloda verilir. İlk lex hedef farklıyken yalnız yüzde süre açığıyla kazanan seçilmez. Alt hedef karşılaştırması üst hedef eşitliğine koşulludur.
- Anytime eğrileri hem FE hem süre ekseninde; primary ve native ayrı. Hedefe erişim performans profilleri/dolanmayan koşu oranları ve bütçede kalite ECDF'leri kullanılır. Hedef kaçırılan koşular sansürlü/başarısız olarak görünür; sıfır optimum açığına bölme yapılmaz.
- “Optimum” yalnız doğrulanmış exact/BKS statüsünde kullanılır. BKS kanıtlı değilse BKS açığı denir. A4/A5 restricted bound'ı global gap hesabında kullanılmaz. Referans ve konfigürasyon sürümleri, lisans/erişim durumu, bütün ham çözümler ve analysis planı arşivlenir.

## 7. Uygulama yol haritası — öneri, yürütülmedi

**Mimari bağımlılık:** Kanonik algoritma/evaluator/feasibility uniride_core'a, veri/protokol/analiz academic_benchmark'a aittir (AGENTS Required Academic Boundaries ve R4). Bu yerleştirme kaynak dosya incelemesine dayalı yeni mimari denetim değildir. Study unification'ın dört kapısının mevcut kapanış durumunu bu görev araştırmadı; uygulama başlamadan ilgili kapı kanıtı aranmalı, eksik önceki paket atlanmamalıdır. Eski study içine bağımsız yeni solver engine konmaz.

### 7.1 Ortak altyapı ve bağımlılık sırası

| Sıra / paket | İş ve çıktı | Bağımlılık / efor tahmini | Kabul kanıtı |
|---|---|---|---|
| C0-a | Amaç profilleri, snapshot/birim, occurrence, atomik FE ve stage ledger | Önce onaylı protokol/kapı durumu; **2–4 kişi-gün** | Sayaç, invalid-input, deterministik sıralama, fail-closed sözleşmeleri |
| C0-b | Candidate LS + aktif kuyruk/DLB; simetrik 2-opt, yönlü Or-opt/or-3opt; aynı LS'li ILS | C0-a; **4–7 kişi-gün** | Delta/full paritesi, deadline, nonmetric karşı örnek, D1 hız/kalite raporu |
| C0-c | Değişmez diversity/klon ölçüsü, yörünge kabulü, telemetry | C0-a; **2–4 kişi-gün** | C0 ve L1–L10 testleri; her ayar/operatör etkin |
| C0-d | GPX2 tanımı ve uygulaması, lisans kararı, küçük exhaustive operator oracle | C0-a/c; **4–7 kişi-gün** | Ham child/common-edge/komponent optimum testleri; LS sonrası test ayrımı |
| C0-e | Manifest, native referans sürümleri, veri ayrımı, irace ve analysis planı | C0-a; **2–4 kişi-gün**, deney hesap süresi hariç | Comparator objective eşitliği; kaynak/lisans/parametre arşivi |
| A1/A2 | Akademik TSP ve yönlü temel | C0-b/c/d; A2, GPX'i beklemek zorunda değil | G0, G2 ve sınırlı problem VERIFIED paketi |
| A4 | Sertifikalı dalga havuzu ve native master | C0-a/e, wave sertifikası; A3 zorunlu değil | Tiny exact oracle, incumbent koruma, proof_scope |
| A5 | Gün route-master + kritik wave LNS | A4, P7 amaç ve araç eligibility sözleşmesi | Gün atama oracle'ı ve gün amaçlı ablation |
| A3 | Çok kaynaklı HGS/Split | C0-a/b/c/e, decoder kararları | Her profil için eşit amaç ve sertifika; GA golden parity |
| A6 | Statik paired-request ALNS, sonra P8 | A3'ün kodu zorunlu değil; resource evaluator ve DARP sözleşmesi gerekli | Statik schedule oracle; yeni dinamik kapsam ayrı paket |
| A7 | Mesafe-koşullu operatör seçimi | A1 + H1 olumlu karar | Uniform/non-context/context kontrollü sonuç |

Kişi-günler görevin istediği ilk planlama aralıklarıdır; geliştirici yetkinliği, lisans seçimi ve arayüz ayrıntıları netleşince yenilenir. Eforu sonuca dönüştüren ölçüm yoktur. Tablo satırları kısmen örtüşür; toplam takvim diye toplanmaz. R1'in yaklaşık iki haftalık Faz 0 hedefi, bütün portföyün iki haftada biteceği anlamına gelmez.

### 7.2 İlk iki hafta

| Zaman | Yapılacak iş | Çıkış / durma koşulu |
|---|---|---|
| İlk hafta başı | C0-a; unit/snapshot/FE sözleşmesi; L1–L10 kontrol listesi; objective ve yetenek kimlikleri | Kaynak belirsizliği olan arayüzler açık; impl başlamadan bilimsel muhasebe tanımı sabit |
| İlk hafta ortası | C0-b simetrik ve yönlü minimal LS; aynı LS'li ILS; directed/nonmetric/property test taslağı ve uygulaması | Tam maliyet eşitliği ve deadline sağlanmadan yeni hibrit yok |
| İlk hafta sonu | Candidate/DLB ayrı D1 ölçümü; cold/warm JIT; R1'in a280/pr1002 geliştirme ölçümü | Native hız ile FE kalitesi ayrı rapor; mevcut ölçüm gibi yazılmaz |
| İkinci hafta başı | GPX2 ham operatör testi, invariant diversity; lisans kararı; bir yörüngelik LAHC kontrolü | Bileşen garantisi kaynak teoremiyle uyumlu; serbest LS'ye yanlış garanti yüklenmez |
| İkinci hafta ortası | R1 D2 arazi ve D3 Δ pilotu; aynı altı geliştirme örneğinde H1 kararı; pilot harcamayı kaydet | H1 zayıfsa A7 ertelenir; pozitif Δ yoksa SA zorlanmaz |
| İkinci hafta sonu | G0 raporu ve çözülmeyen maddeler; A4/P7 objective sözleşmesini tasarım düzeyinde sabitle; sonraki paketleri sırala | G0 tamam değilse G1/G2'ye “geçti” denmez. A4 güvenlik/kanıt tasarımı bağımsız ilerleyebilir; açık kapılar saklanmaz |

Bu takvim öncelik sırasıdır; C0 efor aralıkları iki haftayı aşabilir. Eksik GPX veya muhasebeyi takvime yetiştirmek için geçilmiş kabul etme yoktur.

### 7.3 G0–G2 ile açık uyum ve gerekli kararlar

| Kapı | R1'deki koşul | Bu portföyde uygulama / çatışma çözümü |
|---|---|---|
| G0 doğruluk | Bütün sözleşmeler, etkin ayarlar, belirlenimcilik ve bilimsel protokol kabulü | C0 testleri; bütün P1/P2 tam FE ledger'ı; bütün production profillerinde cert. Native-only A4/A5, bilimsel FE kapısını geçmiş diye etiketlenmez. |
| G0 hız | a280'de kalite ±%0,5 ve en az **50 kat kick/s**; K=8–10 başlangıç önerisi | Bunlar R1 §4 Faz 0'ın **ölçülmemiş hedefleri**. D1'de aynı donanım/LS anlamıyla sınanır; beklenen kazanç diye tekrarlanmaz. Sağlanmazsa R1'e göre G0 hız maddesi geçmez; dış LS veya eşik revizyonu sahibin açık kararıdır. Primary tam-FE maliyetiyle native delta hızını karıştırma yok. |
| G0 bütçe | “Aşım≤%5” | R4 kesin FE üst sınırı daha belirgindir: **FE aşımı sıfır**, yalnız süre≤%5. Native wall-cut tekrarları deterministik çıktı diye sunulmaz. |
| G0 kabul testi | R1 “LAHC kabul oranı zamanla düşüyor” | Bu bir LAHC teoremi değildir. Sözleşme, §4.0'ın tam geçmiş/indis/karar eşitliğidir. Kalibre SA başlangıç kabulü için R1'in hedefe ±0,05 pilot testi korunabilir; tüm dağılıma formülden garanti çıkarılmaz. Bu maddede önerilen düzeltme açıkça sahibin kararına sunulur. |
| G1 mekanizma | Kararların≥%5'inde imza; açık kol Holm p<0,05; aynı LS'li ILS'e eşit sürede yenilmeme | Toplam/uygun fırsat/başarılı çağrı payları ayrı. p≥0,05 eşitlik kanıtı değil; önceden marj ve belirsizlik şartı §6.5. Katkısız mekanizma taşınmaz. |
| G2 kalite | Yeni bileşim geliştirmede ILS'i eşit bütçede Holm p<0,05 ile geçer; her bileşen katkı gösterir | TSP için aynen. VRP'de güçlü uygun kontrol, gün için aynı menü/atama kontrolü; native-only master kolları ayrı bütçe ekseninde. Kilitli test sonuçları ayrıca gerekir. |
| Doğruluk ile yenilik ayrımı | R1'de performans odaklı geçiş | A4 ile kontrol ikisi de exact optimumsa strict superiority gösterilemez: mekanizma üstünlüğü/G2 geçti denmez. Yine de doğruluk, üretim yararı ve yetenek VERIFIED değerlendirmesi ayrı olabilir. Katalog sahibinin ölçüt kararı gerekir; bu rapor kataloğa kayıt yapmaz. |

## 8. Riskler ve sahibin vermesi gereken kararlar

| Karar / risk | Bu raporun önerisi | Açık durum ve doğrulama yolu |
|---|---|---|
| Bugünkü üretim mi TSP yayın hattı mı? | Üretimde A4→A5; akademik ortak altyapıda A2/A1. A7'yi H1'e bağla. | Beklenen kazanç ölçülmedi; öncelik ürün hedefinden seçilmeli. |
| P7 amaç tuple'ı | İlk araştırma profili sabit owned-minibus altında borrowed-car sayısı/dakikası; genel toplam filo ayrı. | Envanterdeki belirli profil ile istemin genel ifadesi ayrıldı; seçilecek üretim profili sahibi tarafından sabitlenmeli. |
| GA-Split inner/outer amaç ayrılığı | A3 lex decoder yeni varyant; H01/H04 kontrol ve golden parity korunur. | [DECISION_LOG](../../../DECISION_LOG.md) O05/H01–H04; mevcut baseline'ı sessizce değiştirme yok. |
| Native-only master ve harici backend | Tam muhasebe kanıtlanana kadar ayrı native reference. | “Bir çağrı=bir FE” ile scientific gate aşılmaz. A4/A5 için tam FE desteği varmış gibi katalog kararı verilmez. |
| GPX2/GA-EAX/LKH | GA-EAX MIT ve GPX2 GPL v3 dosyaları görüldü; LKH-3 seçilen dağıtım lisansı açık. | LKH-3 lisansı; elkai RECOMBINATION erişimi; GPX2+2n verimi; GA-EAX yönlü destek **DOĞRULANMADI**. Kaynak kodu bu görevde açarak tamamlanmadı. |
| PyVRP | Çok boyutlu yük doğrulandı; tarihsel HGS ve güncel ILS ayrı. | Yerel sürüm, adapter, yöne özgü R/T, lex hedef, kota ve load semantics oracle kontrolü eksik. |
| P5→P8 | Ayrı paired-request/occupancy/schedule evaluator. | Waiting ve biniş ride süresine dahil mi; bireysel ride/TW; onboard/frozen kuralları; araç uygunluğu sahibi kararı. |
| Google ve birimler | Bugünkü authoritative centi-minute snapshot korunur. | Tam sayı saniye hedefi canlı response kanıtı değildir. Google duration birimi ve fractional-second dönüşümü **DOĞRULANMADI** (R3 §2). |
| Complete enumeration / exact | Wave reference planlı; WP-E0 loader ayrı. | A4'ün bütün rota evreni sayımı + solver proof gerekiyor. A5 ortak gün modeli E01'in mevcut wave-only exact paketinin dışında. |
| Ölçek / bellek | Küçük wave'de A4, büyük statikte A6; kolon ve matris maliyetleri kaydedilir. | Dense O(n²) matris ve faktöriyel sayım; kaynak kısıtına gelince açık partial/no-proof sonucu. |
| Öğrenme ve yenilik | Context/bandit yalnız ablation; NN aday öğrenimi ertelendi. | A7 yeniliği odaklı taramada açık; test sızıntısı ve tuning maliyeti saklanamaz. |
| G0/G1 yorumları | FE sıfır aşım; doğru LAHC sözleşmesi; non-inferiority için önceden marj. | R1'in test/kapı metnindeki önerilen değişiklikler bu raporda açık; onaylı belgeyi veya kodu değiştirmedik. |

## 9. Arama günlüğü ve doğrulama kapsamı

**Yöntem:** Önce BRIEF/06–07 künyeleri, BRIEF/04–05 eşlemeleri ve BRIEF/03 fikirleri kullanıldı. Sonra yayıncı sayfaları, yazar/kurum PDF'leri, resmi sürüm/lisans belgeleri açıldı. Bu turda yeni OpenAlex/CrossRef API taraması çalıştırılmadı; önceki paketin künye doğrulaması ile bu turdaki içerik doğrulaması ayrı tutuldu. Web erişimleri 2026-10-13/14 araştırma oturumunda yapıldı; belge tamamlanma tarihi 2026-10-14'tür. Sistematik/tüketici bir “literatürde hiç yok” taraması yapıldığı iddia edilmez.

| Ana sorgu / doğrudan açılış grubu | Kabul edilen kanıt / sonuç |
|---|---|
| GPX2 “common edges”, “respectful”, theorem/complexity; Tinós–Whitley–Ochoa yazar PDF'i | R6; ortak kenar garantisi ham operatör için, reachable combinations kapsamı |
| HGS / “A unified solution framework” / subsequence concatenation time windows | R11–13; O(1) yalnız belirtilen statik özet/hamle kapsamı |
| PyVRP multi-dimensional load; v0.13.0 release; 2024 solver paper | R14–16; Sw/So yük olanağı ve HGS→ILS sürüm değişimi |
| “Slack Induction by String Removals”; adaptive large neighborhood search pickup delivery time windows | R17–18; string/blink ve paired-request aktarımı |
| “Analysis of the dial-a-ride problem of Hunsaker and Savelsbergh” | R20; max wait/ride için difference constraints/özel graph yöntemi; genel O(1) çıkarılmadı |
| “A hybrid heuristic for a broad class ... heterogeneous fleet” | R19; ILS/RVND/set-partitioning; joint tip kararının her zaman kazanç sağlamadığı sınırı |
| “multi trip vehicle routing problem route generation set partitioning Cattaruzza” | R29 künye ve yayıncı arama özeti; tam açılış engelli, DOĞRULANMADI |
| “A Parallel Ensemble Genetic Algorithm” ve “Local Optima Correlation Assisted Adaptive Operator Selection” | R22–23; A7'ye yakın öncüller; yenilik iddiası ertelendi |
| Fialho sliding-window bandit; Wang 2025 MAB backbone LKH | R21/R24; dinamik kredi ve öğrenme yönü; hakemsiz iddia etiketlendi |
| “The irace package”; “Good Laboratory Practice for optimization research”; Derrac tutorial | R26/R28 tam metin bölümleri; R27 yalnız BRIEF kaynak izi |
| “A speed-up for Helsgaun” 107443; Heins AB-cycles | R31 BRIEF künye; R32 arXiv özeti, ayrıca related ACM DOI görüldü. Güncel varyant araştırma adayları; performans sayıları aktarılmadı |
| GA-EAX / PyVRP / OR-Tools / VROOM / GPX2 LICENSE; LKH-3 author site | §2.1; seçilen resmi dosyalar görüldü, LKH-3 erişimi başarısız |

### 9.1 Reddedilen veya kapsamı daraltılan kaynaklar

| Kaynak / erişim sorunu | İşlem ve nedeni |
|---|---|
| Elsevier sayfalarında 403/DOI açılış hataları; Nagata–Soler UPV arşivinde bot challenge | Engeli aşmaya çalışılmadı. R9/R10/R25/R27/R29 için tam içerik doğrulaması iddia edilmedi; BRIEF ya da yayıncı arama izi açık yazıldı. |
| LKH-3 akira.ruc.dk ve webhotel4.ruc.dk erişim hatası | LKH-2 makalesindeki izin ifadesi LKH-3 lisansına genellenmedi. Mirror/fork açıklaması resmi dağıtım lisansının yerine kullanılmadı. |
| Turkeš–Sörensen–Hvattum adaptiveness meta-analysis için bulunan 2019 DTU dosyası | Açılan sürüm bibliyografik olarak 2021 makalesiyle aynı sürüm diye doğrulanamadı. Sayısal ortalama kazanç aktarılmadı; uniform kontrol kararı R21 ve deney tasarımımıza dayandırıldı. |
| Hunsaker–Savelsbergh (2002), DOI 10.1016/S0167-6377(02)00120-7 | Tam yöntem açılışı başarısız. Sonraki Firat–Woeginger R20'nin görülen özeti kullanıldı; özgün algoritmanın bütün doğruluk/karmaşıklık özellikleri doğrulanmış sayılmadı. |
| UHGS için “A note on A unified solution framework ...” [yayıncı izi](https://www.sciencedirect.com/science/article/pii/S0377221723008780) | Astra araştırmasında lunch-break kısmına ilişkin düzeltme izi görüldü; burada tam doğrulanmadı. R12 klasik TW denklemleriyle sınırlandı; lunch-break formülleri öneriye alınmadı. |
| ResearchGate özetleri, Wikipedia, arama motoru AI özetleri, ticari solver tanıtımları | İçerik doğrulama/üstünlük kanıtı olarak kullanılmadı. Yalnız birincil kaynak adresini bulma amacıyla görülen sonuçlar literatür kanıtına çevrilmedi. |
| arXiv üzerinde görülen güçlü performans ifadeleri | UniRide'a sonuç aktarılmadı. Yazar sürümü olan hakemli yayın ile hakemli durumu doğrulanmamış ön baskı ayrıldı; R32'de related DOI olması “kesin hakemsizdir” diye kestirilmedi. |

### 9.2 Teslim kapsamı

Yalnız **ASTRA6_YENI_ALGORITMA_TASARIMLARI.md** oluşturuldu. UniRide solver kaynakları açılmadı; kod, test, benchmark, veri ithalatı, canlı servis çağrısı, commit, push, checkout/switch yapılmadı. Raporun kontrolü bölüm/kart kapsamı, kaynak işaretleri, yerel bağlantılar ve matematiksel/protokol tutarlılığıyla sınırlıdır. Önerilen testlerin geçtiği veya tasarımların çalıştığı iddia edilmez.

**Son belge kontrolü:** Yedi kartın zorunlu alanları ve sözde kod sınırları, bölüm kapsamı, R atıfları, Markdown tabloları ve yerel belge bağlantıları kontrol edildi. Astra'nın dar matematik/protokol kontrolünde saptanan P5/P8 kontrol-kolu ayrılığı düzeltildi. Bu kontrol, kaynak tablosunun bağımsız tam fact-check'i veya algoritma doğrulaması değildir.
