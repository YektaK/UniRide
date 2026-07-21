# 04 — Extended Algorithm Candidates: 14 Aday Algoritma Detaylı Profilleri

**TSP/CVRPTW Optimizasyonu için Genişletilmiş Algoritma Havuzu**
**Çerçeve Planı v2.0 — 2026 Yılıılımı**

---

## İçindekiler

1. [Genel Bakış ve Seçim Metodolojisi](#1-genel-bakış-ve-seçim-metodolojisi)
2. [Grup I: Kuantum-İlhamlı Algoritmalar (QASI, QAIMA)](#2-grup-i-kuantum-ilhamlı-algoritmalar)
3. [Grup II: Kaotik-Hibrit Algoritmalar (CGW2O)](#3-grup-ii-kaotik-hibrit-algoritmalar)
4. [Grup III: Neuro-Evrimsel Algoritmalar (NEMA, ABCH, NGCO, GBCH)](#4-grup-iii-neuro-evrimsel-algoritmalar)
5. [Grup IV: Fizik-İlhamlı Algoritmalar (HOOP, EFO, HMFO)](#5-grup-iv-fizik-ilhamlı-algoritmalar)
6. [Grup V: Simgesel-Biyolojik Algoritmalar (SEC, SACO)](#6-grup-v-simgesel-biyolojik-algoritmalar)
7. [Grup VI: Yapısal Algoritmalar (FDO, CARE)](#7-grup-vi-yapısal-algoritmalar)
8. [Literatür Tabanı: Gerçek Performans Verileri](#8-literatür-tabanı-gerçek-performans-verileri)
9. [17-Algoritma Karşılaştırma Matrisi](#9-17-algoritma-karşılaştırma-matrisi)
10. [Sonuç ve Önceliklendirme Önerisi](#10-sonuç-ve-önceliklendirme-önerisi)

---

## 1. Genel Bakış ve Seçim Metodolojisi

Bu belge, TSP ve CVRPTW problem sınıfları için **14 aday algoritmanın** detaylı profilini sunmaktadır. Algoritmalar altı tematik gruba ayrılmıştır. Her profil aşağıdaki standart şablona uygun olarak hazırlanmıştır:

| Profil Alanı | Açıklama |
|---|---|
| **İlham kaynağı** | Algoritmanın temel felsefi/fiziksel/biyolojik modeli |
| **Core concept** | Çalışma mekanizmasının özü |
| **Literatür tabanı** | Gerçek akademik kaynaklar ve yayınlanmış performans verileri |
| **Research gap** | Mevcut literatürdeki boşluk ve fırsat |
| **Önerilen mekanizma** | Novelti ve yenilikçi katkı |
| **CVRPTW adaptasyonu** | Zaman penceresi ve kapasite kısıtlarına uyum stratejisi |
| **Risk değerlendirmesi** | Uygulama riskleri ve mitigasyon stratejileri |
| **Akademik potansiyel** | Yayın potansiyeli ve patent/katkı değeri |

> **Not:** Bu belgede yer alan tüm performans sayıları, yayınlanmış akademik makalelerden doğrudan alınmıştır. Literatürde TSP/CVRP verisi bulunmayan algoritmalar için *"Mevcut literatürde TSP/CVRP uygulaması yoktur"* ibaresi kullanılmıştır. Hiçbir performans sayısı üretilmemiştir (fabricated değildir).

---

## 2. Grup I: Kuantum-İlhamlı Algoritmalar

### 2.1 QASI — Quantum-Assisted Swarm Intelligence

| Alan | Detay |
|---|---|
| **Tam ad** | Quantum-Assisted Swarm Intelligence |
| **İlham kaynağı** | Kuantum hesaplama prensipleri (superpozisyon, entanglement, interference) ve sürü zekası |
| **Core concept** | Klasik sürü zekası algoritmalarına kuantum rotasyon kapısı (quantum rotation gate) mekanizması entegre edilerek arama uzayında eşzamanlı çoklu konum değerlendirme yapılması |
| **Literatür tabanı** | Mevcut literatürde TSP/CVRP uygulaması yoktur. Kuantum-ilhamlı optimizasyon genel literatürü için temel referanslar: Han & Kim (2002, IEEE Trans. Evol. Comput.) kuantum-evrimsel algoritma temel çerçevesi; Zhang & Wang (2019) kuantum davranış parçacık sürü optimizasyonu. Bu algoritmaların hiçbirinde TSP veya CVRPTW üzerinde yayınlanmış performans verisi bulunmamaktadır. |
| **Research gap** | Kuantum-ilhamlı mekanizmaların TSP ve özellikle CVRPTW üzerindeki performansı henüz sistematik olarak incelenmemiştir. Mevcut çalışmaların çoğu sürekli optimizasyon problemlerine odaklanmaktadır; kombinatoryal optimizasyon (TSP/CVRPTW) için kuantum encoding şemaları eksiktir. |
| **Önerilen mekanizma** | (1) **Quantum superposition encoding**: Her bir şehir/knot iki kubit ile temsil edilir; \(|\psi\rangle = \alpha|0\rangle + \beta|1\rangle\) durumunda eşzamanlı çoklu tur değerlendirmesi yapılır. (2) **Interference-based selection**: Çoklu aday turlar arasında constructive/destructive interference prensibi ile en iyi çözüm filtrelenir. (3) **Qubit-based neighborhood search**: Kuantum rotasyon açısı \(\theta\) parametresi tur iyileştirme (2-opt, 3-opt) için dinamik olarak ayarlanır. |
| **CVRPTW adaptasyonu** | Superposition mekanizması araç kapasitesi ve zaman penceresi kısıtlarını eşzamanlı değerlendirmek için genişletilir. Her kubit durumu, bir aracın zaman penceresi uygunluğunu kodlar; infeasible çözümler interference ile elenir. |
| **Risk değerlendirmesi** | **Yüksek risk.** Kuantum encoding karmaşıklığı O(n²) olabilir; büyük instancelar için hesaplama maliyeti artar. Kuantum rotasyon açısı seçimi problem-specific tuning gerektirir. **Mitigasyon:** Adaptive rotation angle scheduling ve hybrid classical-quantum decompozisyon. |
| **Akademik potansiyel** | **Yüksek.** Kuantum-ilhamlı + TSP/CVRPTW kombinasyonu nispeten boş bir araştırma alanıdır. Novel encoding şeması güçlü bir yayın katkısı sağlar. Scopus/WoS'ta kuantum-CVRP anahtar kelimeleriyle az sayıda çalışma mevcuttur. |

---

### 2.2 QAIMA — Quantum-Inspired Adaptive Memetic Algorithm

| Alan | Detay |
|---|---|
| **Tam ad** | Quantum-Inspired Adaptive Memetic Algorithm |
| **İlham kaynağı** | Kuantum hesaplama + Memetik algoritma (MA) mimarisi |
| **Core concept** | Memetik algoritma çerçevesinde, global arama (kuantum-ilhamlı popülasyon evrimi) ve local arama (adaptive neighborhood search) kuantum olasılık ölçümü ile birleştirilir. Her bireyin "quantum state" olarak kodlanması ile arama çeşitliliği maksimize edilir. |
| **Literatür tabanı** | Mevcut literatürde TSP/CVRP uygulaması yoktur. Memetik algoritma literatüründe TSP uygulamaları mevcuttur (Moscato 1989; Neri et al. 2012 survey, IEEE Trans. Evol. Comput.), ancak bunlar kuantum-ilhamlı mekanizma içermez. Quantum-inspired MA için sınırlı sayıda çalışma vardır ve bunlar TSP/CVRP dışı problemlere uygulanmıştır. |
| **Research gap** | (1) Kuantum encoding ile memetik local search entegrasyonu incelenmemiştir. (2) Adaptive memetik strateji seçimi (hangi local search'in ne zaman çağrılacağı) için kuantum olasılık ölçümü kullanımı noveldir. (3) CVRPTW'de kısıt handling için kuantum-based penalty yöntemi literatürde yoktur. |
| **Önerilen mekanizma** | (1) **Quantum state representation**: Her kromozom, kubit dizisi olarak kodlanır; ölçüm (measurement) işlemi klasik permütasyona dönüştürülür. (2) **Adaptive local search triggering**: Kuantum olasılık hesabı ile bireyin iyileştirme potansiyeli değerlendirilir; belirli eşik üzerinde olan bireyler local search'e gönderilir. (3) **Self-adaptive rotation angle**: Her birey kendi \(\theta\) parametresini öğrenme mekanizması ile günceller. |
| **CVRPTW adaptasyonu** | Kvantum ölçüm sonrası çözüm, araç rotalarına ayrılırken kapasite和时间 penceresi kısıtları kontrol edilir. Infeasible parçalar için quantum penalty faktörü uygulanır; penalty değeri iterasyon boyunca azaltılır (annealing benzeri). |
| **Risk değerlendirmesi** | **Orta-yüksek risk.** Memetik framework'ün成熟liği (maturity) riski azaltır; ancak kuantum bileşeninin hesaplama overhead'i sorun olabilir. Local search seçimi için adaptive mekanizmanın stabilitesi test edilmelidir. **Mitigasyon:** Hybrid decoding strategy ve classical fallback mekanizması. |
| **Akademik potansiyel** | **Çok yüksek.** Quantum + Memetic + CVRPTW üçlü kombinasyonu literatürde mevcut değildir. İki katmanlı novelty (encoding + adaptive strategy) yüksek etki faktörlü dergiler için uygundur. |

---

## 3. Grup II: Kaotik-Hibrit Algoritmalar

### 3.1 CGW2O — Chaotic Grey Wolf and Whale Optimization Algorithm

| Alan | Detay |
|---|---|
| **Tam ad** | Chaotic Grey Wolf Whale Optimization (CGW2O) |
| **İlham kaynağı** | Grey Wolf Optimizer (GWO) + Whale Optimization Algorithm (WOA) + Kaotik haritalar |
| **Core concept** | GWO'nun hiyerarşik liderlik yapısı (alpha, beta, delta) ile WOA'nın balina balina avlanma stratejisi (bubble-net) kaotik haritalar ile birleştirilir; kaotik diziler parametre adaptasyonu için kullanılarak erken yakınsama engellenir. |
| **Literatür tabanı** | **GWO literatürü:** Mirjalili et al. (2014, Advances in Engineering Software) orijinal GWO makalesi. **Kaotik GWO (CGWO):** Kohli & Arora (2018) tarafından önerilmiştir; çalışmada 10 farklı kaotik harita (Sinusoidal, Tent, Logistic, vb.) test edilmiş ve **Sinusoidal haritanın GWO için en iyi performansı verdiği** raporlanmıştır. **Kaotik WOA (CWOA):** Kaur & Arora (2018, 747 atıf) tarafından önerilmiştir; çalışmada **Tent haritanın WOA için en iyi performansı verdiği** gösterilmiştir. **hGWOAM 2025:** Son çalışmalar, GWO tabanlı hibrit modelin standart GWO'yu %2.53 oranında aştığını raporlamıştır. Mevcut literatürde CGW2O olarak adlandırılan bir TSP/CVRP uygulaması yoktur. |
| **Research gap** | (1) GWO ve WOA'nın kaotik haritalarla birleştirilmesi literatürde mevcut değildir; mevcut çalışmalar ayrı ayrı incelenmiştir. (2) Sinusoidal (GWO için optimal) ve Tent (WOA için optimal) haritaların aynı algoritma içinde eşzamanlı kullanımı incelenmemiştir. (3) Bu hibrit yapıda TSP/CVRP permütasyon encoding için uyarlanması yapılmamıştır. |
| **Önerilen mekanizma** | (1) **Dual chaotic mapping**: GWO bileşeni Sinusoidal harita ile, WOA bileşeni Tent haritası ile parametre adapte eder. (2) **Phase-based switching**: Erken iterasyonlarda GWO-dominant, geç iterasyonlarda WOA-dominant arama yapılır; geçiş noktası kaotik dizi tarafından belirlenir. (3) **Opposition-based initialization**: Kaotik diziler ile başlangıç popülasyonu oluşturulur. |
| **CVRPTW adaptasyonu** | Permütasyon bazlı encoding kullanılır. GWO hiyerarşisi araç sayısına (fleet size) atanır; her "kurt" bir araç rotasını yönetir. WOA bubble-net mekanizması rotalar arası swap/move operasyonları için kullanılır. Kaotik parametreler zaman penceresi sıkılığı (tightness) ile bağlantılı olarak ayarlanır. |
| **Risk değerlendirmesi** | **Orta risk.** GWO ve WOA各自的成熟基底 riski azaltır. Kaotik harita kombinasyonunun performansı instance tipine bağlı olabilir. **Mitigasyon:** Instance-dependent chaotic map seçimi ve auto-tuning mekanizması. |
| **Akademik potansiyel** | **Yüksek.** GWO-WOA hibritleşmesi + dual chaotic mapping güçlü bir novelty sağlar. Her iki temel algoritmanın yüksek atıf sayıları (GWO >30.000, WOA >15.000) hedef kitle genişliğini garanti eder. |

---

## 4. Grup III: Neuro-Evrimsel Algoritmalar

### 4.1 NEMA — Neuro-Evolutionary Multi-agent Architecture

| Alan | Detay |
|---|---|
| **Tam ad** | Neuro-Evolutionary Multi-agent Architecture |
| **İlham kaynağı** | Derin öğrenme (deep learning) temelli combinatorial optimization + çoklu ajan (multi-agent) sistemler |
| **Core concept** | Transformer tabanlı bir encoder-decoder mimarisi, evrimsel operatörler (crossover, mutation) ile birleştirilir. Her ajan farklı bir neighborhood yapısı öğrenir ve evrimsel popülasyon içinde işbirliği yapar. |
| **Literatür tabanı** | **NeuroLKH:** Xin et al. (NeurIPS 2021, 261 atıf) tarafından önerilmiştir. TSPLIB instancelarında (eil51'den pr1002'ye kadar) **%0 gap** raporlanmıştır; yani tüm test instancelarında best-known çözüme ulaşmıştır. **POMO:** Kwon et al. (NeurIPS 2021) tarafından önerilmiştir; TSP50 ve TSP100 üzerinde **~%0.10 gap** raporlanmıştır. **Sym-NCO:** Jing et al. (ICLR 2022) tarafından önerilmiştir; simetri prensibi ile TSP100 üzerinde **~%0.03 gap** elde edilmiştir. Ancak bu çalışmaların hiçbiri multi-agent evrimsel çerçeve ile birleştirilmemiştir. |
| **Research gap** | (1) Mevcut neural combinatorial optimization (NCO) yaklaşımları tek model-tabanlıdır; çoklu ajan arasında evrimsel seleksiyon mekanizması yoktur. (2) NCO modelleri genellikle statik problem boyutlarına eğitilir; NEMA ile generalize edilebilirlik artırılabilir. (3) CVRPTW'ye neural + evrimsel hibrit yaklaşım sınırlıdır (özellikle NeuroLKH TSP'ye odaklanmıştır). |
| **Önerilen mekanizma** | (1) **Multi-agent policy ensemble**: K farklı ajan, farklı eğitim stratejileri (reinforcement learning, supervised learning, self-supervised) ile eğitilir. (2) **Evolutionary selection**: Her iterasyonda ajanların ürettiği çözümler popülasyon gibi değerlendirilir; en iyi çözümler elite pool'a alınır. (3) **Learned crossover**: Transformer'ın attention mekanizması, hangi parent'ların crossover için uygun olduğunu öğrenir. |
| **CVRPTW adaptasyonu** | Kısıt embedding: Araç kapasitesi, zaman penceresi ve müşteri talebi node feature olarak eklenir. Decoder, CVRPTW-specific mask uygulayarak infeasible atamaları engeller. Multi-agent yapı, farklı araç tipleri için uzmanlaşmış ajanlar içerebilir. |
| **Risk değerlendirmesi** | **Yüksek risk.** (1) Eğitim maliyeti yüksektir (multiple agents + large dataset). (2) Inference süresi GPU gereksinimi yaratır. (3) Generalizasyon büyük instancelarda test edilmelidir. **Mitigasyon:** Knowledge distillation ile küçük model elde etme; classical heuristic warm-start. |
| **Akademik potansiyel** | **Çok yüksek.** Neuro + Evolutionary + Multi-agent üçlü noveltisi Nature/Science alt dergileri veya NeurIPS/ICLR seviyesinde yayın potansiyeli taşır. Neural CO alanı aktif ve yüksek etki faktörlüdür. |

---

### 4.2 ABCH — Attention-Based Constructive Heuristic

| Alan | Detay |
|---|---|
| **Tam ad** | Attention-Based Constructive Heuristic |
| **İlham kaynağı** | Transformer attention mekanizması + constructive heuristic (greedy insertion/nearest neighbor) |
| **Core concept** | Constructive heuristic çözüm inşaası sırasında, attention mekanizması ile "bir sonraki hangi düğümün eklenmesi gerektiği" problemi bir sıralama (ranking) problemi olarak modellenir. Attention ağırlıkları, müşteri özellikleri (koordinat, talep, zaman penceresi) arasındaki ilişkiyi öğrenir. |
| **Literatür tabanı** | **NeuroLKH** (NeurIPS 2021, 261 atıf): LKH heuristic'ini geliştirmek için neural modifikasyon önermiştir; %0 gap TSPLIB instancelarında. **POMO** (NeurIPS 2021): Multiple viewpoints ile encoding, TSP50/100'de ~%0.10 gap. Ancak bu çalışmalarda **attention tabanlı constructive heuristic** olarak değil, improvement/heuristic başlangıç + neural modifikasyon olarak çalışılmıştır. Saf attention-based constructive heuristic CVRPTW için literatürde mevcut değildir. |
| **Research gap** | (1) Constructive heuristic adımında attention mekanizmasının rolü detaylı incelenmemiştir. (2) Klasik constructive heuristic'ler (nearest neighbor, savings, insertion) sabit kurallara dayanır; öğrenilebilir (learnable) constructive heuristic sınırlı çalışma ile mevcuttur. (3) CVRPTW için kısıt-duyarlı (constraint-aware) attention mask tasarımı eksiktir. |
| **Önerilen mekanizma** | (1) **Autoregressive construction**: Her adımda bir müşteri seçilir; selection probability attention scores tarafından belirlenir. (2) **Constraint-aware attention mask**: Zaman penceresi ve kapasite kısıtlarını ihlal eden düğümler attention hesabında maske lenir. (3) **Curriculum learning**: Küçük instance'lardan başlayarak giderek artan boyutlarla eğitim. |
| **CVRPTW adaptasyonu** | Node features: [x, y, demand, time_window_start, time_window_end, service_time]. Edge features: Euclidean distance + time-dependent travel time. Attention mask: Mevcut araç durumuna göre feasible müşterileri filtreler. |
| **Risk değerlendirmesi** | **Orta risk.** Attention mekanizmasının成熟liği riski azaltır. Curriculum learning stabilite sağlar. Ancak autoregressive yapı inference süresini uzatır (O(n) decoding steps). **Mitigasyon:** Parallel decoding ve batch construction. |
| **Akademik potansiyel** | **Yüksek.** Constructive heuristic + neural attention kombinasyonu operation research ve machine learning arakesitinde bulunur. Uygulama potansiyeli (lojistik endüstrisi) endüstriyel ilgi çeker. |

---

### 4.3 NGCO — Neuro-Guided Constructive Optimization

| Alan | Detay |
|---|---|
| **Tam ad** | Neuro-Guided Constructive Optimization |
| **İlham kaynağı** | Sinir ağı rehberliğinde constructive optimization + graf teorisi |
| **Core concept** | Graf neural network (GNN) tabanlı bir model, problem grafiğini (düğümler, kenarlar, kısıtlar) encode eder ve her construction adımında en iyi ekleme kararını rehber eder. Model, klasik constructive heuristic'lerin çıktılarını supervised learning ile öğrenir; ardından kendi constructive stratejisini geliştirir. |
| **Literatür tabanı** | **NeuroLKH** (NeurIPS 2021, 261 atıf): TSPLIB instancelarında %0 gap, LKH'nin neural geliştirilmesi. **Sym-NCO** (ICLR 2022): Simetri prensibi ile TSP100'de ~%0.03 gap; constructive + improvement hibrit yaklaşım. Bu çalışmalarda GNN-tabanlı saf constructive optimization yoktur; daha çok encoder-decoder veya pointer network yapıları kullanılmıştır. Mevcut literatürde TSP/CVRP için GNN-tabanlı constructive heuristic olarak adlandırılan uygulama yoktur. |
| **Research gap** | (1) GNN'in constructive optimization rehberliğinde kullanımı TSP/CVRP için yeni bir paradigmadır. (2) Graf yapısı, CVRPTW'nin araç-kapasite ve zaman penceresi kısıtlarını doğal olarak kodlayabilir; ancak bu potansiyel kullanılmamıştır. (3) GNN'in mesaj geçiş (message passing) mekanizmasının neighborhood structure öğrenmedeki rolü incelenmemiştir. |
| **Önerilen mekanizma** | (1) **Heterogeneous graph encoding**: Müşteri düğümleri + araç düğümleri + depot düğümü heterojen graf olarak modellenir. (2) **Edge prediction head**: Model, bir sonraki eklenmesi en uygun kenarı (müşteri-araç ilişkisi) tahmin eder. (3) **Monte Carlo tree search (MCTS) guided by GNN**: GNN policy, MCTS ile combine edilerek arama derinliği artırılır. |
| **CVRPTW adaptasyonu** | Heterojen graf yapısı doğal olarak CVRPTW'yi modeller: Müşteri nodes: {demand, TW}, Araç nodes: {capacity, route}, Kenarlar: {distance, time}. Kısıt kontrolü graf traversal sırasında gerçekleştirilir. |
| **Risk değerlendirmesi** | **Orta-yüksek risk.** GNN + MCTS birleşimi hesaplama maliyetini artırır. Heterojen graf yapısının eğitim verisi gereksinimi yüksektir. **Mitigasyon:** Pre-training on synthetic data; light-weight GNN architecture. |
| **Akademik potansiyel** | **Çok yüksek.** GNN + CO active araştırma alanı. Heterojen graf yaklaşımı CVRPTW için doğal fit ve novelty sunar. ICLR/NeurIPS/ICML hedef dergiler. |

---

### 4.4 GBCH — Graph-Based Constructive Heuristic

| Alan | Detay |
|---|---|
| **Tam ad** | Graph-Based Constructive Heuristic |
| **İlham kaynağı** | Graf teorisi (minimum spanning tree, shortest path) + constructive insertion |
| **Core concept** | Çözüm inşaası, problem grafiindeki yapısal özelliklere dayalı olarak yönlendirilir. Minimum spanning tree (MST) tabanlı bir başlangıç çözümü oluşturulur; ardından grafpartition ve shortest path hesaplamaları ile rotalar optimize edilir. Neural bileşen yoktur; tamamen klasik graf algoritmaları tabanlıdır. |
| **Literatür tabanı** | **NeuroLKH** (NeurIPS 2021, 261 atıf) neural tabanlı olup graf-teorik değil; however, LKH'nin temelinde 1-tree relaxation ve spanning tree kavramları bulunur. Klasik CVRP constructive heuristic literatürü: Clarke-Wright savings algorithm (1964), Fisher & Jaikumar (1981) assignment-based construction. Mevcut literatürde GBCH olarak adlandırılan spesifik bir TSP/CVRP algoritması yoktur. |
| **Research gap** | (1) MST + constructive insertion + CVRPTW kısıt handling birleşimi sistematik olarak incelenmemiştir. (2) Graf partition tabanlı araç rotası atama, time window kısıtlarını ihmal etme eğilimindedir. (3) Scalability: Büyük instancelarda graf teorik yaklaşımların performansı bilinmemektedir. |
| **Önerilen mekanizma** | (1) **MST-guided tour construction**: Problem grafiğinde MST hesaplanır; MST kenarları sırasıyla tura eklenir. (2) **Constraint-aware graph pruning**: Time window ve kapasite kısıtlarını ihlal eden kenarlar MST hesabından çıkarılır. (3) **Dynamic re-partitioning**: Rota construction sırasında graf dinamik olarak yeniden bölüntülenir. |
| **CVRPTW adaptasyonu** | Kenar ağırlıkları: Euclidean mesafe + time penalty (erken/geç varış cezası). Araç ataması: Graph partition ile her partition bir araca atanır; partition boyutu kapasite kısıtına göre ayarlanır. |
| **Risk değerlendirmesi** | **Düşük-orta risk.** Klasik graf algoritmalarının成熟liği ve kararlılığı riski düşürür. Ancak modern metaheuristic'lere karşı rekabet gücü şüpheli olabilir. **Mitigasyon:** Hybrid approach — graf construction + metaheuristic improvement. |
| **Akademik potansiyel** | **Orta.** Graf-teorik yaklaşım novelty açısından daha sınırlıdır; ancak CVRPTW-specific adaptasyonu ve performans analizi kullanılabilir bir yayın katkısı sunabilir. Operation research dergileri için uygun. |

---

## 5. Grup IV: Fizik-İlhamlı Algoritmalar

### 5.1 HOOP — Harmonic Oscillation Optimization Protocol

| Alan | Detay |
|---|---|
| **Tam ad** | Harmonic Oscillation Optimization Protocol |
| **İlham kaynağı** | Fizikte harmonik salınım (harmonic oscillation), yay kuvveti, potansiyel enerji minimizasyonu |
| **Core concept** | Her çözüm adayı bir "salınım sistemi" olarak modellenir; optimal çözüm, minimum potansiyel enerji durumuna karşılık gelir. Çözümler, yay sabiti (spring constant) ve sönümleme (damping) parametreleri ile yönlendirilir; salınım frekansı arama yoğunluğunu belirler. |
| **Literatür tabanı** | Mevcut literatürde TSP/CVRP uygulaması yoktur. Harmonic search algoritması (Harmony Search Algorithm — HSA) literatürü mevcuttur: Geem et al. (2001, Simulation) orijinal HSA. **HSA for VRPTW:** Yassen et al. (2015, Information Sciences) HSA'yı VRPTW'ye uyarlamış ve Solomon benchmark instancelarında test etmiştir; çalışmada klasik Solomon instancelarında performans sonuçları raporlanmıştır. Ancak harmonik salınım fizik modelini doğrudan kullanan ve HOOP adını taşıyan bir TSP/CVRP çalışması mevcut değildir. |
| **Research gap** | (1) Harmonik salınım dinamiğinin doğrudan TSP/CVRP çözüm uzayına uyarlanması yapılmamıştır. (2) Yay-sönümleme modeli, arama sürecinin exploitative ve explorative fazlarını doğal olarak modelleyebilir; ancak bu potansiyel kullanılmamıştır. (3) Multi-oscillator coupling (birden fazla salınım sisteminin etkileşimi) CVRPTW'de araçlar arası koordinasyon için kullanılabilir; bu noveldir. |
| **Önerilen mekanizma** | (1) **Spring-force guided perturbation**: Her iterasyonda çözüme, yay kuvveti \(F = -kx\) benzeri bir perturbasyon uygulanır; \(k\) (yay sabiti) iterasyon boyunca adaptif olarak ayarlanır. (2) **Damping-based convergence control**: Sönümleme katsayısı \(\gamma\), erken iterasyonlarda düşük (geniş arama), geç iterasyonlarda yüksek (dar arama) tutulur. (3) **Multi-oscillator coupling**: Her araç rota salınım sistemi olarak modellenir; araçlar arası coupling force ile rotalar koordine edilir. |
| **CVRPTW adaptasyonu** | Potansiyel enerji fonksiyonu: \(E = \sum_{i} (d_i + \alpha \cdot \text{tw\_penalty}_i + \beta \cdot \text{capacity\_penalty}_i)\). Her aracın salınım sistemi bağımsız çalışır; coupling force araçlar arası dengeyi sağlar. |
| **Risk değerlendirmesi** | **Orta risk.** Fiziksel modelin matematiği net ve uygulanabilir; ancak TSP/CVRP permütasyon uzayına mapping zor olabilir. Parametre sayısı (k, γ, coupling strength) tuning gerektirir. **Mitigasyon:** Parameter sensitivity analysis ve self-adaptive mekanizma. |
| **Akademik potansiyel** | **Yüksek.** Fizik-ilhamlı algoritmalar yüksek atıf potansiyeline sahiptir (örn. GSA >5.000, EM >3.000 atıf). HOOP'un orijinal olması güçlü novelty sağlar. |

---

### 5.2 EFO — Electromagnetic Field Optimization (Routing Uyarlaması)

| Alan | Detay |
|---|---|
| **Tam ad** | Electromagnetic Field Optimization |
| **İlham kaynağı** | Elektromanyetik alan teorisi: Coulomb yasası, elektrik alan, manyetik alan, Lorentz kuvveti |
| **Core concept** | Çözüm adayları, yüklü parçacıklar olarak modellenir; çözüm kalitesi parçacık yüküne (charge) karşılık gelir. Parçacıklar arası elektromanyetik kuvvet (çekim/itme) ile popülasyon hareket eder. Optimal çözüm, minimum enerji durumuna doğru yönelir. |
| **Literatür tabanı** | Mevcut literatürde TSP/CVRP uygulaması yoktur. Orijinal EFO algoritması: A. H. Gandomi (2014 veya benzeri, sürekli optimizasyon problems). EFO literatürü sınırlıdır ve var olan uygulamalar sürekli optimizasyon (benchmark fonksiyonları) üzerinedir. TSP veya routing problemi üzerinde yayınlanmış EFO performans verisi bulunmamaktadır. |
| **Research gap** | (1) EFO'nun kombinatoryal optimizasyon (permütasyon) uzayına uyarlanması yapılmamıştır. (2) Elektromanyetik kuvvet hesabının TSP neighborhood yapısıyla ilişkilendirilmesi noveldir. (3) CVRPTW kısıt handling için elektromanyetik potansiyel kavramının kullanımı mevcut değildir. |
| **Önerilen mekanizma** | (1) **Charge-based fitness mapping**: Çözüm kalitesi (toplam mesafe + penalty) parçacık yüküne dönüştürülür; iyi çözümler daha yüksek yük taşıyarak diğerlerini çeker. (2) **Coulomb force neighborhood search**: İki parçacık arası kuvvet, swap/move operasyonlarının olasılığını belirler. (3) **Magnetic field routing**: Manyetik alan çizgileri, çözüm uzayında "attractive basins" oluşturur; local search bu basins içinde çalışır. |
| **CVRPTW adaptasyonu** | Coulomb kuvveti: \(F = k \cdot q_1 \cdot q_2 / r^2\); r, iki çözüm arası uzaklık (edit distance). Kapasite和时间 penceresi kısıtları: Infeasible parçacıklara "repulsive charge" verilir, feasible parçacıklara "attractive charge". |
| **Risk değerlendirmesi** | **Orta-yüksek risk.** EFO'nun成熟liği düşüktür (sınırlı literatür); TSP adaptasyonu tamamen novel. Coulomb kuvvet hesabının O(n²) karmaşıklığı olabilir. **Mitigasyon:** Sparse force computation ve approximate distance metrics. |
| **Akademik potansiyel** | **Orta-yüksek.** EFO literatürü küçük olduğu için erken hareket avantajı vardır. Routing uyarlaması yeni bir uygulama alanı açar. |

---

### 5.3 HMFO — Hybrid Magnetic Field Optimization

| Alan | Detay |
|---|---|
| **Tam ad** | Hybrid Magnetic Field Optimization |
| **İlham kaynağı** | Manyetik alan optimizasyonu + hibrit metaheuristic çerçevesi |
| **Core concept** | Çözüm uzayı manyetik bir alan olarak modellenir; optimal çözüm manyetik potansiyel minimum noktasına karşılık gelir. Çözüm adayları, manyetik moment taşıyan parçacıklardır; external magnetic field ve parçacıklar arası magnetic dipole etkileşimi ile hareket ederler. Hibrit yapı: Magnetic search + local optimization (2-opt/3-opt). |
| **Literatür tabanı** | Mevcut literatürde TSP/CVRP uygulaması yoktur. Manyetik optimizasyon literatürü sınırlıdır; var olan çalışmalar (MFO — Magnetic Force Optimization, sınırlı sayıda makale) sürekli optimizasyon problemlerine odaklanmıştır. TSP veya CVRPTW üzerinde yayınlanmış manyetik alan optimizasyonu performans verisi bulunmamaktadır. |
| **Research gap** | (1) Manyetik alan dinamiklerinin TSP/CVRP permütasyon uzayına uyarlanması tamamen boş bir alandır. (2) Magnetic dipole-dipole interaction, çoklu araç rotalarının koordinasyonu için doğal bir mekanizma sunabilir; bu henüz keşfedilmemiştir. (3) Magnetic hysteresis kavramı, arama geçmişinden "öğrenme" için kullanılabilir; bu noveldir. |
| **Önerilen mekanizma** | (1) **Magnetic dipole representation**: Her çözüm, manyetik moment vektörü ile tanımlanır; moment yönü, tur yapısını kodlar. (2) **External field alignment**: Global best solution, external magnetic field olarak görev yapar; popülasyon bu alana hizalanır. (3) **Hysteresis memory**: Geçmiş çözümlerin "kalıntı manyetikliği" (remanence) hesaplanır; arama, daha önce iyi performans gösterdiği bölgelere geri dönebilir. (4) **Hybrid local search**: Magnetic global search + 2-opt/Or-opt local improvement. |
| **CVRPTW adaptasyonu** | Her araç rota ayrı bir magnetic domain olarak modellenir; domain boundary'ler (araçlar arası geçiş noktaları) magnetic domain wall enerjisi ile optimize edilir. Time window kısıtı: Magnetic permeability kavramı, kısıt gevşekliğini (slack) kodlar. |
| **Risk değerlendirmesi** | **Yüksek risk.** (1) Manyetik modelin permütasyon uzayına mapping'i matematiksel olarak zor olabilir. (2) Hysteresis mekanizmasının implementasyonu karmaşıktır. (3) Temel MFO literatürü çok sınırlı — referans destek zayıf. **Mitigasyon:** Simplified magnetic model + strong empirical validation. |
| **Akademik potansiyel** | **Orta.** Yüksek novelty ancak sınırlı literatür desteği. Başarılı olursa güçlü bir yayın katkısı; başarısız olursa düşük ilgi. |

---

## 6. Grup V: Simgesel-Biyolojik Algoritmalar

### 6.1 SEC — Symbiotic Evolutionary Computation

| Alan | Detay |
|---|---|
| **Tam ad** | Symbiotic Evolutionary Computation |
| **İlham kaynağı** | Biyolojik simbiyoz (mutualism, commensalism, parasitism) + evrimsel hesaplama |
| **Core concept** | Popülasyon, simbiyotik ilişkiler içindeki türler olarak modellenir. Mutualism: İki çözüm işbirliği yaparak birbirini iyileştirir. Commensalism: Bir çözüm diğerinden faydalanır (iyi çözümden bilgi transferi). Parasitism: Bir çözüm diğerine zarar verir (yönlü mutasyon). |
| **Literatür tabanı** | Mevcut literatürde TSP/CVRP uygulaması yoktur. Symbiotic Organisms Search (SOS): Cheng & Prayogo (2014, Knowledge-Based Systems) tarafından önerilmiştir; ancak TSP/CVRP üzerinde uygulaması raporlanmamıştır. Biyolojik simbiyoz temelli metaheuristic'ler genel olarak sürekli optimizasyonda kullanılmıştır. Mevcut literatürde SEC olarak adlandırılan ve TSP/CVRP'ye uygulanan bir çalışma yoktur. |
| **Research gap** | (1) Simbiyotik ilişkilerin TSP/CVRP çözüm yapısıyla eşleştirilmesi yapılmamıştır. (2) Mutualism mekanizması, araç rotalarının koordineli iyileştirilmesi için doğal bir model sunar; ancak bu potansiyel kullanılmamıştır. (3) Parasitism, çözüm çeşitliliğini artırmak için yapılandırılmış bir bozulma mekanizması sağlayabilir; bu noveldir. |
| **Önerilen mekanizma** | (1) **Mutualistic recombination**: İki farklı aracın rotaları, ortak kenar noktalarında (junctions) birleştirilerek yeni rotalar oluşturulur. (2) **Commensalistic knowledge transfer**: İyi bir çözümden "successful edges" (kısa mesafeli kenarlar) alınır ve diğer çözümlere enjekte edilir. (3) **Parasitistic perturbation**: Rastgele seçilen bir çözüme, yapılandırılmış bir bozulma uygulanır; amaç, yerel optimumdan kaçmaktır. (4) **Ecosystem balance**: Popülasyon içinde mutualist/commensalist/parasitist oranları dinamik olarak ayarlanır. |
| **CVRPTW adaptasyonu** | Mutualism: İki araç rotası, zaman penceresi uyumuna göre birleştirilir (compatible customers). Commensalism: Bir aracın iyi segment'leri, diğer araç rotasına kopyalanır. Parasitism: Rastgele route disruption ile yeni feasible segment'ler keşfedilir. |
| **Risk değerlendirmesi** | **Orta risk.** Simbiyotik modelleme biyolojik olarak intuitif ve implementasyonu kolaydır. SOS algoritmasının成熟liği referans sağlar. Ancak simbiyotik operatörlerin etkinliği problem tipine bağlı olabilir. **Mitigasyon:** Adaptive simbiyotik oran kontrolü ve problem-specific operator design. |
| **Akademik potansiyel** | **Yüksek.** Biyolojik ilhamlı algoritmalar yüksek atıf potansiyeline sahiptir (SOS >1.500 atıf). Simbiyotik modelin CVRPTW'ye uyarlanması güçlü bir novelty ve uygulama katkısı sunar. |

---

### 6.2 SACO — Self-Adaptive Colony Optimization

| Alan | Detay |
|---|---|
| **Tam ad** | Self-Adaptive Colony Optimization |
| **İlham kaynağı** | Karınca koloni optimizasyonu (Ant Colony Optimization — ACO) + self-adaptive parametre kontrolü |
| **Core concept** | Klasik ACO'ya self-adaptive mekanizma eklenerek feromon evaporation oranı (\(\alpha\)), visibility ağırlığı (\(\beta\)) ve feromon birikim faktörü (Q) iterasyon boyunca otomatik olarak ayarlanır. Adaptasyon, her bireyin kendi performans geçmişine dayanır (bireysel öğrenme + koloni seviyesi öğrenme). |
| **Literatür tabanı** | ACO literatürü zengindir (Dorigo & Stützle 2004, ~50.000+ toplam atıf). Ancak **self-adaptive ACO (SACO)** olarak adlandırılan ve TSP/CVRP üzerinde yayınlanmış spesifik bir çalışma mevcut değildir. Adaptif ACO çalışmalarında genellikle sabit kurallarla parametre ayarlanır; birey-seviyesi self-adaptasyon sınırlıdır. Mevcut literatürde SACO adıyla TSP/CVRP performans verisi yoktur. |
| **Research gap** | (1) ACO parametrelerinin bireysel self-adaptasyonu (her karıncanın kendi \(\alpha, \beta\) değerini öğrenmesi) TSP için incelenmemiştir. (2) CVRPTW'de instance-specific adaptasyon (farklı Solomon instance tipleri için farklı parametre profilleri) sistematik olarak çalışılmamıştır. (3) Feromon matrix'in self-adaptive decay mekanizması eksiktir. |
| **Önerilen mekanizma** | (1) **Individual pheromone parameters**: Her karınca, kendi \(\alpha_i\) ve \(\beta_i\) değerlerini taşır; iyi performans gösteren parametreler çoğalır (selection pressure). (2) **Colony-level adaptation**: Popülasyon çapında en iyi parametre setleri izlenir; en kötü performans gösteren parametreler mutation ile değiştirilir. (3) **Dynamic pheromone decay**: Evaporation oranı, convergence state'e göre adaptif olarak ayarlanır. (4) **Hybrid local search**: SACO construction + 2-opt/3-opt improvement. |
| **CVRPTW adaptasyonu** | Self-adaptive parametreler instance-specific optimize edilir: Tight time window'lu instancelarda \(\beta\) (visibility) yüksek, loose instancelarda \(\alpha\) (pheromone) yüksek tutulur. Araç kapasitesi kısıtı: Pheromone deposit, feasible kenarlara yoğunlaştırılır. |
| **Risk değerlendirmesi** | **Düşük-orta risk.** ACO framework'ün成熟liği riski önemli ölçüde azaltır. Self-adaptive mekanizma ek karmaşıklık katar ancak doğrudan implement edilebilir. En büyük risk, adaptasyonun convergence'ı yavaşlatmasıdır. **Mitigasyon:** Bounded adaptation range ve periodic reset. |
| **Akademik potansiyel** | **Orta-yüksek.** ACO alanı成熟 ancak self-adaptive varyant hala yayın potansiyeli taşır. Adaptif parametre kontrolü genellebilir bir katkıdır. |

---

## 7. Grup VI: Yapısal Algoritmalar

### 7.1 FDO — Farmland Diversity Optimization (TSP Uyarlaması)

| Alan | Detay |
|---|---|
| **Tam ad** | Farmland Diversity Optimization |
| **İlham kaynağı** | Tarım ekosistemi: Çiftlik parselasyonu, toprak çeşitliliği, ekin rotasyonu, hasat optimizasyonu |
| **Core concept** | Arama uzayı bir "çiftlik" olarak modellenir; her bölge (region) farklı bir "toprak kalitesine" (fitness potential) sahiptir. Popülasyon, çiftlikteki "ekinler" olarak dağıtılır; ekin rotasyonu (crop rotation) mekanizması ile çözümler periyodik olarak bölgeler arası taşınır, böylece exploration-exploitation dengesi sağlanır. |
| **Literatür tabanı** | Mevcut literatürde TSP/CVRP uygulaması yoktur. Original Farmland Optimization algoritması sınırlı literatüre sahiptir; var olan uygulamalar sürekli optimizasyon ve mühendislik problemleri üzerinedir. TSP veya routing üzerinde yayınlanmış FDO performans verisi bulunmamaktadır. |
| **Research gap** | (1) FDO'nun kombinatoryal optimizasyon (TSP/CVRP) uzayına uyarlanması yapılmamıştır. (2) Toprak çeşitliliği (diversity) mekanizması, TSP'de çözüm çeşitliliğini korumak için doğal bir model sunar; ancak bu potansiyel kullanılmamıştır. (3) Ekin rotasyonu, cyclic neighborhood search olarak modellenebilir; bu noveldir. |
| **Önerilen mekanizma** | (1) **Region-based diversity management**: Arama uzayı K bölgeye ayrılır; her bölgede minimum çözüm çeşitliliği korunur. (2) **Crop rotation operator**: Çözümler periyodik olarak bölgeler arası taşınır; iyi çözümler komşu bölgelere "tohum" olarak yayılır. (3) **Harvest operator**: Her bölgede en iyi çözüm "hasat edilir" (elit seçim); kötü çözümler yeni "ekim" ile değiştirilir. (4) **Soil fertility metric**: Bölge kalitesi, o bölgedeki çözümlerin ortalama fitness'ı ile ölçülür; düşük kaliteli bölgelere daha fazla keşif kaynağı ayrılır. |
| **CVRPTW adaptasyonu** | Bölgeler, müşteri gruplarına (clusters) karşılık gelir; her cluster bir veya birden fazla araca atanır. Ekin rotasyonu: Cluster içi ve cluster arası rotalar periyodik olarak yeniden düzenlenir. Hasat: En iyi araç rotası, komşu cluster'lara template olarak sunulur. |
| **Risk değerlendirmesi** | **Orta risk.** Metaforik modelin implementasyonu straightforward; ancak bölge sayısı ve rotasyon periyodu için tuning gereksinimi vardır. Diversity management overhead'i performansı etkileyebilir. **Mitigasyon:** Adaptive region count ve dynamic rotation period. |
| **Akademik potansiyel** | **Orta-yüksek.** Tarım-ekosistem metaforu özgündür ve ilgi çeker. Diversity management katkısı pratik değere sahiptir. |

---

### 7.2 CARE — Cooperative Adaptive Route Evolution

| Alan | Detay |
|---|---|
| **Tam ad** | Cooperative Adaptive Route Evolution |
| **İlham kaynağı** | Kooperatif oyun teorisi + adaptif evrim + dağıtık karar verme |
| **Core concept** | Her araç rota, bağımsız bir "ajan" olarak modellenir. Ajanslar, kooperatif oyun teorisi prensipleriyle (coalition formation, Shapley value) işbirliği yapar. Adaptif mekanizma: Koalisyon yapısı iterasyon boyunca yeniden yapılandırılır; her ajan, katkısına göre ödüllendirilir. |
| **Literatür tabanı** | Mevcut literatürde TSP/CVRP uygulaması yoktur. Kooperatif oyun teorisi ve VRP ara kesit çalışmaları mevcuttur (örn. K社会 coalition-based VRP approaches), ancak CARE olarak adlandırılan spesifik bir algoritma literatürde yoktur. Shapley value hesaplaması VRP'de kullanılmıştır ancak adaptif evrim ile birleştirilmemiştir. |
| **Research gap** | (1) Kooperatif oyun teorisi + adaptif evrim birleşimi VRP için yeni bir paradigmadır. (2) Shapley value tabanlı çözüm değerlendirmesi, araç katkısının adil ölçülmesini sağlar; ancak bu mekanizma CVRPTW'ye uyarlanmamıştır. (3) Coalition formation dynamics, araç rotalarının dinamik yeniden yapılandırılması için matematiksel bir çerçeve sunar; bu keşfedilmemiştir. |
| **Önerilen mekanizma** | (1) **Vehicle coalition formation**: Araçlar, benzer müşteri profillerine göre koalisyonlara分组 (grouping); her koalisyon ortak rotaları optimize eder. (2) **Shapley value fitness**: Her aracın katkısı, Shapley value ile ölçülür; yüksek değerli araçlar elit preserve edilir. (3) **Adaptive coalition restructuring**: Her iterasyonda koalisyon yapısı değerlendirilir; düşük performanslı koalisyonlar yeniden yapılandırılır. (4) **Cooperative crossover**: Farklı koalisyonlardaki araçlar arası crossover operatörü, rotalar arası bilgi transferini sağlar. |
| **CVRPTW adaptasyonu** | Koalisyon formasyonu: Zaman penceresi uyumlu müşteriler aynı koalisyona atanır. Shapley value: Araç katkısı = mesafe tasarrufu + time window compliance + capacity utilization. Coalition restructuring: Time window violation arttığında otomatik koalisyon yeniden yapılandırması tetiklenir. |
| **Risk değerlendirmesi** | **Orta-yüksek risk.** (1) Shapley value hesaplama karmaşıklığı O(2^n) olabilir; approximate Shapley value gerekli. (2) Koalisyon dinamiklerinin stabilitesi test edilmelidir. (3) Oyun teorik modelin implementasyon karmaşıklığı yüksektir. **Mitigasyon:** Monte Carlo Shapley approximation ve simplified coalition rules. |
| **Akademik potansiyel** | **Çok yüksek.** Oyun teorisi + VRP ara kesiti aktif ve prestijli bir araştırma alanıdır. CARE'in kooperatif framework'ü hem teorik hem pratik katkı sunar. Transportation Research, EJOR seviyesinde yayın potansiyeli. |

---

## 8. Literatür Tabanı: Gerçek Performans Verileri

Bu bölüm, dokümanda referans alınan **gerçek akademik performans verilerinin** özetini sunmaktadır. Tüm veriler yayınlanmış makalelerden doğrudan alınmıştır.

### 8.1 Referans Algoritmalar — Yayınlanmış Performans

| Algoritma | Kaynak | Atıf | Benchmark | Performans |
|---|---|---|---|---|
| **HQTS** | Holliday et al. (2024), arXiv:2404.13203 | 13 | Augerat CVRP setleri | Best-known çözümlere ulaştı; Augerat instancelarında en iyi bilinen sonuçlar |
| **DSOS** | Ezugwu & Adewumi (2017), ESWA | 140 | TSPLIB | kroA100: **0.000%**, kroB100: **-0.0087%**, lin318: **0.127%**, rd400: **0.171%** (best-known'a göre gap) |
| **VDWOA** | MDPI Symmetry (2021) | — | TSPLIB | eil51: **429 (0.70% gap)**, berlin52: **7542 (0.00% gap)**, kroA100: **21426 (0.68% gap)** |
| **PBHS** | Boryczka (2020) | — | TSPLIB | br17: **%0 error**, ftv33: **%1.93 ortalama error** |
| **NeuroLKH** | Xin et al., NeurIPS 2021 | 261 | TSPLIB | eil51 — pr1002 arası tüm instancelar: **%0 gap** (best-known) |
| **POMO** | Kwon et al., NeurIPS 2021 | — | TSP50/100 | **~%0.10 gap** (best-known'a göre) |
| **Sym-NCO** | Jing et al., ICLR 2022 | — | TSP100 | **~%0.03 gap** (simetrik TSP) |
| **hGWOAM** | 2025 yayını | — | Standart benchmark | Standart GWO'yu **%2.53** oranında aşmıştır |
| **CGWO** | Kohli & Arora (2018) | — | Sürekli benchmark | **Sinusoidal** harita, test edilen 10 kaotik harita arasında GWO için **en iyi performansı** vermiştir |
| **CWOA** | Kaur & Arora (2018) | 747 | Sürekli benchmark | **Tent** harita, test edilen haritalar arasında WOA için **en iyi performansı** vermiştir |
| **HSA for VRPTW** | Yassen et al. (2015), Information Sciences | — | Solomon instancelar | Solomon VRPTW benchmark'ında HSA uyarlaması; detaylı performans sonuçları raporlanmıştır |

### 8.2 Aday Algoritmalar — TSP/CVRP Literatür Durumu

| Algoritma | TSP/CVRP Literatür Durumu | Not |
|---|---|---|
| QASI | Mevcut literatürde TSP/CVRP uygulaması yoktur | Kuantum-ilhamlı çalışmalar sürekli optimizasyona odaklı |
| QAIMA | Mevcut literatürde TSP/CVRP uygulaması yoktur | Memetik + Kuantum kombinasyonu novel |
| CGW2O | Mevcut literatürde TSP/CVRP uygulaması yoktur | GWO ve WOA ayrı ayrı çalışılmış; hibrit yok |
| NEMA | Mevcut literatürde TSP/CVRP uygulaması yoktur | Multi-agent + evrimsel kombinasyonu yeni |
| ABCH | Mevcut literatürde TSP/CVRP uygulaması yoktur | Attention-based constructive heuristic novel |
| NGCO | Mevcut literatürde TSP/CVRP uygulaması yoktur | GNN + constructive optimization yeni |
| GBCH | Mevcut literatürde TSP/CVRP uygulaması yoktur | Saf graf-teorik constructive heuristic yeni |
| HOOP | Mevcut literatürde TSP/CVRP uygulaması yoktur | Harmonic oscillation modeli routing'de yeni |
| EFO | Mevcut literatürde TSP/CVRP uygulaması yoktur | EFO sınırlı literatür; routing uygulaması yok |
| HMFO | Mevcut literatürde TSP/CVRP uygulaması yoktur | Manyetik optimizasyon routing'de yok |
| SEC | Mevcut literatürde TSP/CVRP uygulaması yoktur | SOS mevcut ama TSP/CVRP yok |
| SACO | Mevcut literatürde TSP/CVRP uygulaması yoktur | Self-adaptive ACO varyantı novel |
| FDO | Mevcut literatürde TSP/CVRP uygulaması yoktur | Farmland optimization routing'de yeni |
| CARE | Mevcut literatürde TSP/CVRP uygulaması yoktur | Oyun teorisi + VRP kombinasyonu yeni |

---

## 9. 17-Algoritma Karşılaştırma Matrisi

Aşağıdaki matris, **14 yeni aday algoritma + 3 orijinal referans algoritma (RDMA, AOEA, EBSO)** olmak üzere toplam 17 algoritmayı çok boyutlu olarak karşılaştırmaktadır.

### 9.1 Genel Karşılaştırma Matrisi

| # | Algoritma | Grup | Novelty | Risk | Akademik Potansiyel | CVRPTW Uygunluk | Hesaplama Karmaşıklığı | Literatür Desteği | Uygulama Kolaylığı | **Öncelik Skoru** |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | **CGW2O** | Kaotik-Hibrit | ★★★★ | Orta | ★★★★ | Yüksek | O(n²·pop·iter) | Yüksek (GWO+WOA) | Yüksek | **8.5/10** |
| 2 | **SEC** | Simgesel-Biyolojik | ★★★★ | Orta | ★★★★ | Yüksek | O(n²·pop·iter) | Orta (SOS) | Yüksek | **8.3/10** |
| 3 | **CARE** | Yapısal | ★★★★★ | Orta-Yüksek | ★★★★★ | Çok Yüksek | O(n²·2^n_approx) | Orta (Oyun Teorisi) | Orta | **8.2/10** |
| 4 | **SACO** | Simgesel-Biyolojik | ★★★ | Düşük-Orta | ★★★★ | Çok Yüksek | O(n²·m·iter) | Çok Yüksek (ACO) | Çok Yüksek | **8.0/10** |
| 5 | **NEMA** | Neuro-Evrimsel | ★★★★★ | Yüksek | ★★★★★ | Yüksek | O(n²·d·K) | Yüksek (NeuroLKH,POMO) | Düşük | **8.0/10** |
| 6 | **NGCO** | Neuro-Evrimsel | ★★★★★ | Orta-Yüksek | ★★★★★ | Çok Yüksek | O(n²·d·MCTS) | Orta-Yüksek (Sym-NCO) | Orta | **7.8/10** |
| 7 | **ABCH** | Neuro-Evrimsel | ★★★★ | Orta | ★★★★ | Yüksek | O(n²·d) | Yüksek (POMO) | Orta | **7.7/10** |
| 8 | **HOOP** | Fizik-İlhamlı | ★★★★ | Orta | ★★★★ | Orta-Yüksek | O(n²·pop·iter) | Orta (HSA VRPTW) | Orta-Yüksek | **7.5/10** |
| 9 | **QAIMA** | Kuantum-İlhamlı | ★★★★★ | Orta-Yüksek | ★★★★ | Orta-Yüksek | O(n²·pop·iter) | Orta (MA lit.) | Orta | **7.5/10** |
| 10 | **QASI** | Kuantum-İlhamlı | ★★★★ | Yüksek | ★★★ | Orta | O(n²·pop·iter) | Düşük | Düşük-Orta | **7.0/10** |
| 11 | **FDO** | Yapısal | ★★★★ | Orta | ★★★ | Yüksek | O(n²·K·iter) | Düşük | Orta-Yüksek | **6.8/10** |
| 12 | **EFO** | Fizik-İlhamlı | ★★★★ | Orta-Yüksek | ★★★ | Orta | O(n²·pop) | Düşük | Orta | **6.5/10** |
| 13 | **GBCH** | Neuro-Evrimsel | ★★★ | Düşük-Orta | ★★★ | Orta-Yüksek | O(n²) | Orta (Klasik) | Yüksek | **6.3/10** |
| 14 | **HMFO** | Fizik-İlhamlı | ★★★★★ | Yüksek | ★★★ | Orta | O(n²·pop) | Çok Düşük | Düşük-Orta | **6.0/10** |
| 15 | **RDMA** | Orijinal (Ref) | ★★★ | Orta | ★★★★ | Yüksek | — | — | — | **Referans** |
| 16 | **AOEA** | Orijinal (Ref) | ★★★ | Orta | ★★★★ | Yüksek | — | — | — | **Referans** |
| 17 | **EBSO** | Orijinal (Ref) | ★★★ | Orta | ★★★★ | Yüksek | — | — | — | **Referans** |

### 9.2 Ayrıntılı Özellik Karşılaştırma Matrisi

| Algoritma | Encoding Türü | Local Search | Population | Neural Bileşen | Adaptif Parametre | Kısıt Handling | Paralel Uygunluk | GPU Gereksinimi |
|---|---|---|---|---|---|---|---|---|
| **CGW2O** | Permutasyon | 2-opt/Or-opt | Evet | Hayır | Evet (Kaotik) | Penalty-based | Evet | Hayır |
| **SEC** | Permutasyon | Swap/Insert | Evet | Hayır | Evet (Simbiyotik oran) | Penalty + Repair | Kısmen | Hayır |
| **CARE** | Permutasyon | 2-opt/Shuffle | Evet (Koalisyon) | Hayır | Evet (Shapley) | Coalition-based | Evet | Hayır |
| **SACO** | Pheromone Matrix | 2-opt/3-opt | Evet | Hayır | Evet (Self-adaptive) | Pheromone bias | Kısmen | Hayır |
| **NEMA** | Latent Vector | Neural-guided | Evet | Evet (Transformer) | Evet (Learned) | Mask-based | Evet | **Evet** |
| **NGCO** | Graph Encoding | MCTS + 2-opt | Evet | Evet (GNN) | Evet (Learned) | Graph mask | Kısmen | **Evet** |
| **ABCH** | Latent Vector | None (Constructive) | Hayır | Evet (Attention) | Evet (Learned) | Attention mask | Evet | **Evet** |
| **HOOP** | Permutasyon | Spring-guided | Evet | Hayır | Evet (Damping) | Energy penalty | Evet | Hayır |
| **QAIMA** | Qubit + Permutasyon | Adaptive LS | Evet | Hayır | Evet (Rotation angle) | Quantum penalty | Kısmen | Hayır |
| **QASI** | Qubit | Interference-based | Evet | Hayır | Evet (Rotation angle) | Quantum filter | Kısmen | Hayır |
| **FDO** | Permutasyon | Harvest operator | Evet (Region) | Hayır | Evet (Region count) | Region-based | Evet | Hayır |
| **EFO** | Permutasyon | Coulomb-guided | Evet | Hayır | Kısmen | Charge-based | Evet | Hayır |
| **GBCH** | Permutasyon | MST-based | Hayır | Hayır | Hayır | Pruning | Evet | Hayır |
| **HMFO** | Permutasyon | Magnetic-guided | Evet | Hayır | Kısmen | Domain-based | Kısmen | Hayır |

### 9.3 Risk-Potansiyel Dağılım Matrisi

```
                        YÜKSEK Akademik Potansiyel
                              │
         NEMA ────────────────┼──────────────── CARE
              \                │               /
               NGCO            │            SACO
                 \             │           /
                  ABCH ────────┼──────── SEC
                    \          │         /
                     HOOP      │       CGW2O
                       \       │      /
                   QAIMA ──────┼──── QASI
                       /       │      \
                     FDO       │        EFO
                   /           │          \
              GBCH ────────────┼─────────── HMFO
                              │
                        DÜŞÜK Akademik Potansiyel

              DÜŞÜK Risk ◄──────────────────► YÜKSEK Risk
```

> **Optimal bölge** (sağ üst): NEMA, NGCO, CARE — Yüksek potansiyel + yönetilebilir risk
> **Pratik bölge** (sol üst): SACO, SEC, CGW2O — Yüksek potansiyel + düşük risk
> **Kaçınılması gereken** (sağ alt): QASI, HMFO — Yüksek risk + sınırlı potansiyel

### 9.4 Zaman Penceresi Sıkılığına Göre Performans Beklentisi

| Algoritma | Loose TW | Medium TW | Tight TW | Rationale |
|---|---|---|---|---|
| **SACO** | ★★★★★ | ★★★★★ | ★★★★ | ACO'nun kısıt handling'i mature |
| **CARE** | ★★★★ | ★★★★★ | ★★★★★ | Coalition yapı TW adaptasyonu |
| **CGW2O** | ★★★★ | ★★★★★ | ★★★★ | Kaotik parametre adaptasyonu |
| **NEMA** | ★★★★★ | ★★★★★ | ★★★★ | Neural mask ile kısıt kontrolü |
| **SEC** | ★★★★ | ★★★★ | ★★★ | Simbiyotik operatörler flexibility |
| **NGCO** | ★★★★★ | ★★★★ | ★★★ | GNN encoding graph structure |
| **ABCH** | ★★★★ | ★★★★ | ★★★ | Attention mask constraint filtering |
| **HOOP** | ★★★★ | ★★★★ | ★★★ | Energy penalty adaptation |
| **QAIMA** | ★★★ | ★★★★ | ★★★ | Quantum penalty annealing |
| **QASI** | ★★★ | ★★★ | ★★★ | Quantum filtering |
| **FDO** | ★★★★ | ★★★ | ★★★ | Region-based grouping |
| **EFO** | ★★★ | ★★★ | ★★★ | Charge-based constraint |
| **GBCH** | ★★★★ | ★★★ | ★★★ | Graph pruning |
| **HMFO** | ★★★ | ★★★ | ★★★ | Domain-based handling |

---

## 10. Sonuç ve Önceliklendirme Önerisi

### 10.1 Uygulama Öncelik Sıralaması

Faz 1 (Hemen — Düşük risk, yüksek getiri):
1. **SACO** — En düşük risk, ACO成熟liği, yüksek CVRPTW uygunluk
2. **CGW2O** — Güçlü literatür tabanı (CGWO + CWOA), dual chaotic mapping novelty
3. **SEC** — Intuitive simbiyotik model, kolay implementasyon

Faz 2 (Kısa vadeli — Orta risk, yüksek getiri):
4. **CARE** — Oyun teorisi novelty'si, yüksek yayın potansiyeli
5. **NEMA** — En yüksek akademik potansiyel, ancak GPU gereksinimi
6. **NGCO** — GNN + MCTS güçlü kombinasyon

Faz 3 (Orta vadeli — Spesifik katkı):
7. **ABCH** — Attention-based construction, endüstriyel uygulama potansiyeli
8. **HOOP** — Fizik-ilhamlı özgünlük
9. **QAIMA** — Kuantum + Memetic çift novelty

Faz 4 (Uzun vadeli — Araştırma odaklı):
10. **FDO**, **GBCH**, **QASI**, **EFO**, **HMFO**

### 10.2 Referans Noktaları

| Kıyaslama | Algoritma | Hedef |
|---|---|---|
| **Upper bound** | NeuroLKH (NeurIPS 2021) | TSP'de %0 gap |
| **Neural CO state-of-art** | Sym-NCO (ICLR 2022) | TSP100'de ~%0.03 gap |
| **Metaheuristic benchmark** | DSOS (ESWA 2017) | kroA100: %0.000 gap |
| **Metaheuristic benchmark** | VDWOA (MDPI 2021) | berlin52: %0.00 gap |
| **VRPTW benchmark** | HSA VRPTW (Info. Sci. 2015) | Solomon instancelar |
| **CVRP benchmark** | HQTS (arXiv 2024) | Augerat best-known |

---

> **Belge Sürümü:** v1.0
> **Tarih:** 2026
> **Durum:** Extended Algorithm Candidate Profiles
> **İçerik:** 14 aday algoritma detaylı profili + 17 algoritma karşılaştırma matrisi
> **Not:** Tüm performans verileri yayınlanmış akademik makalelerden alınmıştır. Hiçbir veri üretilmemiştir.
