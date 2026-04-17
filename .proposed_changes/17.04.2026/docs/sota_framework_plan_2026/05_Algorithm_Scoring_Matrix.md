# UniRide SOTA Framework — Algoritma Puanlama Matrisi

> **Tarih**: 2026-04-13
> **Durum**: Değerlendirme Aşaması (Evaluation Phase)
> **Kapsam**: 17 algoritmanın 9 kriter üzerinden ağırlıklı puanlanması ve sıralaması
> ** Amaç**: Beyin fırtınası öncesi nesnel karşılaştırma tablosu oluşturma

---

## 1. Değerlendirme Kriterleri ve Ağırlıkları

### 1.1 Kriter Tanımları

Her kriter **1-10 ölçeğinde** puanlanır. Ağırlıklar, UniRide projesinin önceliklerine göre belirlenmiştir.

| # | Kriter | Ağırlık | Açıklama |
|---|--------|---------|----------|
| **K1** | **Orijinallik (Novelty)** | **%20** | Algoritmanın literatürde doğrudan karşılığı olmayan, yeni bir konsept sunma derecesi. Tamamen yeni=10, mevcut algoritmanın küçük varyantı=1. |
| **K2** | **CVRPTW Performans Potansiyeli** | **%15** | CVRPTW (Solomon + Gehring-Homberger) benchmark setlerinde beklenen kalite (gap to BKS). Yüksek potansiyel=10, düşük potansiyel=1. |
| **K3** | **Akademik Yayın Potansiyeli** | **%12** | GECCO, CEC, AAAI, IEEE TEVC gibi top-tier konferans/dergi kabul olasılığı. Çok güçlü novelty claim=10, zayıf claim=1. |
| **K4** | **TSP Performans Potansiyeli** | **%13** | TSPLIB benchmark setinde (eil51→pr2392) beklenen kalite. Yüksek=10, düşük=1. |
| **K5** | **Implementasyon Kolaylığı** | **%10** | Doğru ve verimli implementasyonun zorluk derecesi. Kolay=10, çok karmaşık=1. |
| **K6** | **Mevcut Mimariye Entegrasyon** | **%8** | BaseRoutingStrategy + Split Decoder + Numba JIT uyumlu olma derecesi. Tam uyumlu=10, kötü uyum=1. |
| **K7** | **Adaptif Davranış** | **%8** | Algoritmanın problem özelliklerine kendi kendine uyum sağlama yeteneği. Tamamen adaptif=10, sabit parametreli=1. |
| **K8** | **Scalability (Ölçeklenebilirlik)** | **%7** | Büyük instance'larda (n>500, n>1000) performans düşüşünün minimal olması. Ölçeklenebilir=10, ölçeklenemez=1. |
| **K9** | **Hesaplama Verimliliği** | **%7** | İterasyon başına hesaplama maliyeti. Düşük overhead=10, yüksek overhead=1. |

> **Toplam: %100**

### 1.2 Ağırlıklandırma Rationale (Gerekçe)

```
Ağırlık Dağılımı:
┌─────────────────────────────────────────────────────────┐
│ K1: Orijinallik               ████████████████░░  20%   │
│ K2: CVRPTW Performans          ████████████░░░░░  15%   │
│ K3: Akademik Yayın             ██████████░░░░░░░  12%   │
│ K4: TSP Performans             █████████░░░░░░░░  13%   │
│ K5: Implementasyon Kolaylığı   ████████░░░░░░░░░  10%   │
│ K6: Mimari Entegrasyon         ██████░░░░░░░░░░░   8%   │
│ K7: Adaptif Davranış           ██████░░░░░░░░░░░   8%   │
│ K8: Scalability               █████░░░░░░░░░░░░   7%   │
│ K9: Hesaplama Verimliliği      █████░░░░░░░░░░░░   7%   │
└─────────────────────────────────────────────────────────┘
```

**Neden bu ağırlıklar?**

- **Orijinallik (20%)**: UniRide'in temel amacı SOTA framework ile akademik katkı üretmektir. Mevcut algoritmalar (GA, PSO, GWO, HHO) zaten ticari üründe çalışmaktadır; yeni algoritmaların bilimsel yenilik barındırması kritiktir.
- **CVRPTW Performans (15%)**: UniRide'in ana problem tipi CVRPTW'dir. TSP sadece ara araçtır.
- **Akademik Yayın (12%)**: Akademik yayına uygunluk, projenin university-industry collaboration değerini belirler.
- **TSP Performans (13%)**: TSP'de güçlü performans göstermek, CVRPTW'deki başarının habercisidir. Ayrıca TSP benchmark sonuçları literatürde yaygın olarak karşılaştırılır.
- **Implementasyon (10%)**: Kaynak kısıtlı bir projede, implementasyon süresi doğrudan ROI'ı etkiler.
- **Entegrasyon (8%)**: Mevcut BaseRoutingStrategy arayüzüne uyum, ek altyapı maliyetini belirler.
- **Adaptiflik (8%)**: Manuel parametre ayarı gerektirmeyen algoritmalar, production ortamında çok daha değerlidir.
- **Scalability (7%)**: Gerçek dünyada 500+ müşterilik rotalar yaygındır.
- **Hesaplama (7%)**: API yanıt süresi kullanıcı deneyimini doğrudan etkiler.

---

## 2. Puanlama Skalası

| Puan | Tanim | Ornek |
|------|-------|-------|
| **10** | Olağanüstü | Literatürde eşi benzeri yok, güçlü teorik altyapı, kanıtlanmış yaklaşım |
| **9** | Mükemmel | Çok güçlü novada,成熟 domain bilgisinden yeni sentez |
| **8** | Çok İyi | Güçlü novada, implementasyon yolu açık |
| **7** | İyi | Orta-yüksek novada, mevcut tekniklerden anlamlı genişleme |
| **6** | Orta | Bilinen paradigmanın mantıklı varyantı |
| **5** | Orta-Düşük | Küçük yenilik, büyük kısmı mevcut teknikler |
| **4** | Düşük | Mevcut algoritmanın basit modifikasyonu |
| **3** | Zayıf | Çok az yenilik, literatürde benzerleri mevcut |
| **2** | Çok Zayıf | Trivial değişiklik |
| **1** | Yetersiz | Literatürde zaten var, katkı yok |

---

## 3. Algoritma Puanlama Tablosu

### 3.1 Orijinal 3 Algoritma (Detaylı Puanlama + Gerekçe)

#### Algoritma 1: RDMA — Resonance-Driven Memetic Algorithm

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **9** | Akustik rezonans kavramının kombinatoryal optimizasyona uygulanması tamamen yeni. "Rezonans Skoru" metriği (ortak kenar + alt-tur benzerliği + hamiltoniyen tamamlanabilirlik) literatürde eşi benzeri olmayan bir yapısal uyum ölçüsüdür. Harmony Search (Geem 2001) sadece sürekli uzayda çalışır ve akustik benzetme yüzeyeldir; RDMA'nın rezonans matrisi derinlemesine yapısal analiz yapar. (-1: Akustik ilham var ama analoji tamamen benzersiz değil) |
| **K2 CVRPTW Performans** | **8** | Çok-boyutlu rezonans (kenar + TW + kapasite) CVRPTW'ye doğal genişleme sağlar. High-rezonanslı eşleşmelerden doğan çocuk çözümler structurally sound olma eğilimindedir → CVRPTW fizibilite oranı yüksek. Dissonans filtresi kötü çocukları erken reddeder → hesaplama tasarrufu. Harmonic Pulse yapılandırılmış çeşitlilik sağlar. (-2: Çok-boyutlu rezonans hesabının kalibrasyonu zor olabilir) |
| **K3 Akademik Yayın** | **9** | "Resonance-guided crossover for combinatorial optimization" güçlü bir novelty claim. GECCO, CEC, IEEE TEVC hedef konferanslarda uygun. Matematiksel olarak rigor (constructive/destructive interference ayrımı). Açıklanabilirlik yüksek (rezonans haritası görselleştirilebilir). (-1: Akustik terminoloji bazı reviewer'larca "gimmick" olarak algılanabilir) |
| **K4 TSP Performans** | **8** | Rezonans-guided crossover, standart OX/PMX'den üstün olma potansiyeli taşıyor. Sadece uyumlu ebeveynleri birleştirmek gereksiz değerlendirmeyi azaltır. Dissonans filtresi + 2-Opt/3-Opt LS kombinasyonu güçlü. TSPLIB'de %2-4 gap hedefi makul. (-2: Rezonans matrisi O(n²) başlangıç maliyeti var) |
| **K5 Implementasyon** | **7** | Temel yapı GA tabanlı → bilinen mimari. Rezonans hesabı kenar frekansı + LCS ile yapılabılır. Adaptif eşik mekanizması orta karmaşıklıkta. Harmonic Pulse spectral clustering gerektirir (scikit-learn veya custom). (-3: Rezonans matrisinin incrementally güncellenmesi dikkat gerektirir) |
| **K6 Mimari Entegrasyon** | **9** | Giant tour temsili + Split Decoder ile tam uyumlu. HybridSplitBaseStrategy'den türetme trivial. Numba JIT ile rezonans hesabı hızlandırılabilir (kenar karşılaştırma JIT-friendly). Pipeline A ve B'ye dual destek kolay. (-1: Harmonic Pulse'daki clustering için external dependency olabilir) |
| **K7 Adaptif Davranış** | **8** | Adaptif θ_esik (rezonans eşik değeri) iterasyon ilerledikçe güncellenir. Rezonans frekansları başarılı/başarısız çocuk sayısına göre adaptif. Exploration→exploitation geçişi Harmonic Pulse ile yapılandırılmış. (-2: Adaptif mekanizma tamamen parametreden bağımsız değil, H_esik başlangıç değeri gerekli) |
| **K8 Scalability** | **7** | Rezonans matrisi O(n²·d) → büyük n'de sorunlu. Incremental update ile maliyet O(n·k)'ya düşürülebilir. Matching O(n·log n) — iyi. Lokal arama O(n²) — standard. n>1000'de performans düşüşü beklenir. (-3: O(n²) rezonans matrisi bottleneck olabilir) |
| **K9 Hesaplama Verimliliği** | **7** | Rezonans hesabı başlangıçta O(n²) ama cache'lenebilir. Incremental update O(n·k). Dissonans filtresi gereksiz LS çalıştırmalarını engeller → net tasarruf. Crossover O(n) — linear. (-3: Her iterasyonda entropi hesabı + eşik güncelleme overhead'ı var) |

**RDMA Ağırlıklı Toplam: 816 / 1000**

---

#### Algoritma 2: AOEA — Adaptive Operator Evolution Algorithm

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **10** | Operator'lerin bir genom olarak modellenip çözümlerle birlikte ko-evrilmesi kavramı routing optimizasyonunda tamamen yenidir. İki-seviyeli evrim (solution level + operator level) VRP literatüründe benzeri olmayan bir paradigma. VRPAgent (ICLR 2025) LLM ile operator keşfi yapar ama bu black-box ve kontrolsüzdür; AOEA tamamen white-box ve matematiksel olarak tanımlı. |
| **K2 CVRPTW Performans** | **9** | Problem-agnostik adaptasyon CVRPTW'nin en büyük avantajı: TW ihlali varsa tw_violation_remove + tw_aware_insert içeren genomlar doğal seçilimle evrilir. Kapasite sorunu varsa capacity operatörleri yükselir. Acceptance criterion de evrilir → problem-specific cooling schedule. Tek risk: erken iterasyonlarda random genomların zayıf performans göstermesi. (-1: Başlangıç warm-up süresi gerekli) |
| **K3 Akademik Yayın** | **10** | "Co-evolutionary operator adaptation for vehicle routing" top-tier konferanslarda (AAAI, IJCAI, EC) çok güçlü bir novelty claim. Meta-evolution + routing optimization kesişimi nadir. Evrilmiş genomların analizi (hangi operatörler neden evrildi?) ek bilimsel katkı sağlar. Transfer learning potansiyeli ek değer katar. |
| **K4 TSP Performans** | **7** | Meta-evrim overhead'i nedeniyle erken iterasyonlarda standart ALNS'den daha zayıf olabilir. Uzun çalışmalarda evrilmiş operator'ler superior performans gösterebilir. Ancak TSP'de destroy/repair yapı CVRPTW kadar doğal değildir (giant tour'da node çıkarmak zor). (-3: TSP'ye adaptasyonu CVRPTW'den daha zor) |
| **K5 Implementasyon** | **4** | Çift popülasyon yönetimi + meta-evrim döngüsü karmaşıklığı çok yüksek. 20+ atomic operasyonun her birinin implementasyonu gerekli. Genome crossover/mutasyon mekanizması ayrı implementasyon. Acceptance criterion library ayrı implementasyon. Success history tracking + fitness hesaplama + age management. (-6: 3-4 hafta tahmini implementasyon süresi) |
| **K6 Mimari Entegrasyon** | **7** | BaseRoutingStrategy arayüzüne uyumlu ama AOEA'nın kendisi için yeni infrastructure gerekli (OperatorGenome, atomic operations library). Split decoder ile uyumlu. Numba JIT: atomic operasyonlar kısmen JIT'lenebilir ama genome evrimi dinamik → JIT zor. (-3: Yeni infrastructure gereksinimi var) |
| **K7 Adaptif Davranış** | **10** | Algoritmanın kendisi adaptifliğin tanımıdır. Operator'ler başarı oranlarına göre evrilir. Acceptance criterion evrilir. Problem feature'larına göre seed genomları üretilir. Transfer learning: benzer problemlerde öğrenilen genomlar başlangıç olarak kullanılabilir. |
| **K8 Scalability** | **6** | Çift popülasyon (çözüm + operator) memory overhead'i 2x. Meta-evrim periyodik olmasına rağmen operator population güncellemesi O(k·m). Her iterasyonda destroy+repair+acceptance O(n). Büyük n'de operator sayısı sabit kalır → orantılı olmayan artış. (-4: Çift popülasyon overhead) |
| **K9 Hesaplama Verimliliği** | **4** | Meta-evrim her Φ iterasyonda ek hesaplama gerektirir. Genome fitness hesaplama O(k). Genome crossover/mutasyon O(k·g). Destroy/repair kendisi O(n) ama operator seçimi + uygulama overhead'i var. Toplam iterasyon süresi standart ALNS'den 1.5-2x daha uzun olabilir. (-6: Çarpıcı hesaplama overhead'i) |

**AOEA Ağırlıklı Toplam: 792 / 1000**

---

#### Algoritma 3: EBSO — Entropy-Balanced Swarm Optimization

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **8** | Shannon entropisini birincil kontrol mekanizması olarak kullanmak VRP literatüründe yenidir. Diversity-guided EA (Ursem 2002) entropi kullanmaz, basit genetik çeşitlilik ölçer. EBSO'nun 3-fazlı kontrolü (enjeksiyon/sıkıştırma/denge) ve H_target çizelgesi rigour matematiksel altyapı sunar. (-2: Entropi kavramı bilgisayar bilimlerinde yaygın, tamamen yeni bir fikir değil) |
| **K2 CVRPTW Performans** | **8** | Çok-boyutlu entropi (kenar + TW + kapasite) CVRPTW'ye güçlü adaptasyon sağlar. Adaptif ağırlıklar (w_tw, w_cap) hangi constraint'in zorlandığını otomatik tespit eder. Entropi sıkıştırma fazı CVRPTW fizibilitesini hızla artırır. (-2: 3-fazlı geçiş sınırları manuel kalibrasyon gerektirebilir) |
| **K3 Akademik Yayın** | **8** | "Shannon entropy-based diversity control for swarm optimization" IEEE TEVC, WCCI'de güçlü kabul potansiyeli. Matematiksel rigor (Shannon entropisi + adaptif H_target) reviewer'ları ikna eder. 3-fazlı kontrol mekanizması teorik analiz için zengin zemin sunar. (-2: Entropi tabanlı kontrol bazı alanlarda (GA diversity, PSO convergence) benzer şekilde çalışılmış) |
| **K4 TSP Performans** | **8** | Swarm recombine + adaptif LS kombinasyonu TSP'de güçlü. Entropi enjeksiyonu erken yakınsamayı engeller → daha uzun arama. Swarm güncellemesi (gBest + pBest çekimi) TSP'de iyi çalışır. Entropi gradient hangi kenarın eklenmesinin çeşitliliği artıracağını hesaplar → guided perturbation. (-2: Continuous-to-discrete mapping (swarm recombine) bazı bilgi kaybına yol açabilir) |
| **K5 Implementasyon** | **8** | Tur entropisi hesabı matematiksel olarak basit (kenar frekansı + Shannon formülü). 3-fazlı kontrol if-else yapısı ile implemente edilebilir. Swarm recombine mevcut crossover tekniklerinden türetilebilir. VNS entegrasyonu zaten mevcut. Adaptif H_target basit bir cooling schedule. (-2: Swarm recombine permutation uzayında doğru implementasyonu dikkat gerektirir) |
| **K6 Mimari Entegrasyon** | **9** | Giant tour temsili + Split Decoder ile tam uyumlu. HybridSplitBaseStrategy'den türetme kolay. Numba JIT ile entropi hesabı hızlandırılabilir (edge frequency loop JIT-friendly). Pipeline A ve B dual destek. Parametre seti küçük (H_start, H_end, γ) → easy tuning. (-1: VNS LS kısmı external module olabilir) |
| **K7 Adaptif Davranış** | **9** | H_target(t) adaptif çizelgesi → exploration'dan exploitation'a otomatik geçiş. Çok-boyutlu entropi'de adaptif ağırlıklar → problem constraint'lerine otomatik uyum. LS olasılığı faz bazlı adaptif (exploration'da az, exploitation'da çok). (-1: Adaptif ağırlık formülleri sabit parametre içerir) |
| **K8 Scalability** | **7** | Entropi hesabı O(n²) (kenar frekans matrisi). n=1000'de makul, n=5000'de yavaş. Swarm recombine O(n) — iyi. Faz kararları O(1) — ihmal edilebilir. (-3: O(n²) entropi bottleneck büyük instance'larda sorun) |
| **K9 Hesaplama Verimliliği** | **7** | Entropi hesabı her iterasyonda yapılır → O(n²) overhead. Ancak sadece faz kararına ihtiyaç var → early exit possible. Swarm recombine O(n) — düşük overhead. LS olasılıksal → average cost düşük. (-3: Her iterasyonda entropi tekrar hesaplanması) |

**EBSO Ağırlıklı Toplam: 802 / 1000**

---

### 3.2 14 Ek Aday Algoritma (Puanlama + Gerekçe)

#### Algoritma 4: QASI — Quantum-Inspired Adaptive Swarm Intelligence

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **6** | Quantum-inspired (QI) algoritmalar 2010'lardan beri literatürde yoğun çalışılıyor. QIA (Quantum-Inspired Algorithm), QPSO (Quantum PSO), QGA (Quantum GA) gibi onlarca çalışma mevcut. QI + swarm hibritizasyonu da yaygın. QI + CVRPTW kombinasyonu nadir ama HQTS (2024) benzer yaklaşım sergilemiş. (-4: Quantum-inspired alan doygunluğa ulaşmış) |
| **K2 CVRPTW Performans** | **6** | Quantum rotation gate'ler sürekli uzayda iyi çalışır ama CVRPTW'nin discrete yapısına mapping zor. Qubit temsili CVRP araç sayısını doğal olarak encode etmez. Adaptif swarm bileşeni faydalı olabilir. (-4: Discrete mapping zorluğu) |
| **K3 Akademik Yayın** | **6** | QI routing alanında 2022-2025 arası 30+ makale yayınlanmış → reviewer'lar " incremental contribution" diyebilir. Yeni bir QI varyantı sunmak için çok güçlü bir novada gerekli. (-4: Alan doygun) |
| **K4 TSP Performans** | **7** | TSP sürekli uzaya mapping (angle-based encoding) daha doğal çalışır. QI'daki superposition kavramı TSP'de exploration artırabilir. Ancak son yıllarda QI-TSP çalışmalarında diminishing returns gözlemleniyor. (-3: Alan mature, büyük iyileştirme zor) |
| **K5 Implementasyon** | **5** | Qubit temsili + rotation gate implementasyonu orta karmaşıklıkta. Ancak doğru angle-to-permutation mapping tasarımı zor. Quantum measurement simulation'ı ek overhead yaratır. (-5: Mapping tasarımı non-trivial) |
| **K6 Mimari Entegrasyon** | **6** | Giant tour temsiline mapping gerekli. Split decoder ile çalışabilir ama quantum encoding decode overhead'i var. Numba JIT: rotation gate hesaplaması JIT-friendly olabilir. (-4: Encoding/decoding overhead) |
| **K7 Adaptif Davranış** | **7** | Quantum tunneling (early exploration) + adaptive rotation angle (later exploitation) doğal adaptasyon sağlar. Swarm kısmı additional adaptivity ekler. (-3: Adaptif rotation angle tuning gerekli) |
| **K8 Scalability** | **6** | Qubit sayısı n ile orantılı → memory O(n). Rotation gate O(n) per particle. Toplam O(P·n) — swarm-dependent. (-4: Qubit temsil büyü instance'larda memory yoğun) |
| **K9 Hesaplama Verimliliği** | **5** | Quantum measurement simulation + rotation angle update ek overhead. Swarm update ek overhead. Toplam standart PSO'den 1.3-1.5x daha yavaş olabilir. (-5: Simulation overhead) |

**QASI Ağırlıklı Toplam: 604 / 1000**

---

#### Algoritma 5: CGW2O — Chaotic Grey Wolf-Whale Optimization Hybrid

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **5** | GWO+Woa hibriti literatürde yaygın (2018-2024 arası 50+ makale). Chaos theory entegrasyonu (Lozi, Tent, Sine maps) de sık kullanılan bir varyant. İki成熟的 algoritmanın hibriti + chaos map ekleme = incremental contribution. (-5: Çok benzer çalışmalar mevcut) |
| **K2 CVRPTW Performans** | **6** | GWO ve WOA ayrı ayrı CVRP'de test edilmiş (orta performans). Hibritizasyon + chaotic perturbation küçük iyileştirme sağlayabilir. Ancak mevcutUniRide GWO ve HHO zaten var → ek değer sınırlı. (-4: Mevcut portfolio ile büyük fark yaratmaz) |
| **K3 Akademik Yayın** | **4** | "GWO+Woa+Chaos for CVRPTW" tarzı makaleler 2023-2025'te yoğun yayınlanmış → reviewer desensitization çok yüksek. "Yet another GWO hybrid" algısı güçlü. (-6: Alan aşırı doygun) |
| **K4 TSP Performans** | **7** | GWO-WOA hibriti TSP'de mevcut GA'den üstün olabilir. Chaos map erken yakınsamayı engeller. Ancak mevcut GWO implementation zaten var. (-3: Mevcut GWO'ya göre marginal improvement) |
| **K5 Implementasyon** | **7** | GWO mevcutUniRide'de implemente edilmiş → temel kod hazır. WOA position update formülleri basit. Chaos map implementasyonu trivial (Lozi: x_{n+1} = 1-a·x²_n + y_n, y_{n+1} = b·x_n). (-3: Mevcut GWO kodunu extend etmek gerekli) |
| **K6 Mimari Entegrasyon** | **8** | GWO zaten BaseRoutingStrategy uyumlu. WOA update mekanizması benzer arayüze sahip. Hybrid mevcut pipeline'a kolayca eklenebilir. Numba JIT: tüm hesaplamalar sürekli/permütasyon dönüşümü için uygun. (-2: WOA update mekanizması adaptasyonu gerekli) |
| **K7 Adaptif Davranış** | **6** | Chaos map parametreleri adaptif ayarlanabilir (chaotic intensity decay). Ancak bu mekanizma literatürde standart hale gelmiş. (-4: Standart adaptif mekanizma) |
| **K8 Scalability** | **7** | GWO O(P·n·d) — standard. WOA benzer. Chaos map O(1) per iteration — ihmal edilebilir. Toplam scalable. (-3: Standart swarm overhead) |
| **K9 Hesaplama Verimliliği** | **7** | GWO hesaplama mevcut. WOA update ek O(P·n). Chaos map O(P) — minimal. Toplam standart swarm + küçük overhead. (-3: İki swarm mekanizması = 2x overhead) |

**CGW2O Ağırlıklı Toplam: 609 / 1000**

---

#### Algoritma 6: NEMA — Neuroevolutionary Memetic Algorithm

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **7** | Neuroevolution (NE) + memetic algorithm hibriti VRP'de nispeten yeni. NEAT/HyperNEAT tabanlı yapay sinir ağı ile crossover/mutasyon operatörlerinin otomatik tasarımı novida taşıyor. Ancak NCO (Neural Combinatorial Optimization) literatürü 2020'den beri aktif ve benzer fikirler mevcut. (-3: NCO literatürü benzer fikirler içeriyor) |
| **K2 CVRPTW Performans** | **7** | Sinir ağı CVRPTW özelliklerini (TW, kapasite, mesafe) öğrenebilir. Memetic bileşen (LS) kalite garantisi sağlar. Ancak NN training costu CVRPTW instance başına artabilir. Transfer learning farklı instance boyutlarında sorun yaratabilir. (-3: Training overhead + transfer learning zorlukları) |
| **K3 Akademik Yayın** | **7** | "Neuroevolutionary operator design for vehicle routing" ilginç bir konu. NCO akımı hala aktif (BOPO ICML'25, Poppy NeurIPS'23). Ancak NN-based CO'da GPU gereksinimi reviewer'larda red flag olabilir. (-3: NCO alanı rekabetçi ve GPU-dependent algısı var) |
| **K4 TSP Performans** | **7** | NCO tabanlı yaklaşımlar TSP'de güçlü sonuçlar vermiş (GCRL-TSP). NE ile öğrenilen operatörler problem-specific olabilir. Ancak küçük TSP instance'larında NN overhead'i relative cost olarak yüksek. (-3: Küçük instance'larda overhead baskın) |
| **K5 Implementasyon** | **3** | Sinir ağı eğitimi (PyTorch/JAX) + memetic algorithm + NEAT/HyperNEAT = çok karmaşık. NN architecture tasarımı, training loop, loss function, validation hepsi ayrı implementasyon. GPU support gerekli (CPU'da çok yavaş). (-7: Çok karmaşık, GPU gerekli) |
| **K6 Mimari Entegrasyon** | **5** | NN training infrastructure mevcut UniRide mimarisinde yok. BaseRoutingStrategy ile çalışabilir ama NN inference eklentisi gerekli. Numba JIT: NN hesaplamaları JIT değil, NumPy/PyTorch ile çalışmalı. (-5: Büyük infrastructure değişikliği gerekli) |
| **K7 Adaptif Davranış** | **8** | NN'in kendisi adaptif bir yapıdır. Farklı problem tiplerinde farklı operatör profilleri öğrenebilir. Online learning ile çalışma zamanında adaptasyon mümkün. (-2: Adaptasyon training data gerektirir) |
| **K8 Scalability** | **5** | NN inference O(n·h) — h = hidden size. Büyük instance'larda NN input boyutu artar → training zorlaşır. Transfer learning farklı boyutlarda sorun. (-5: NN boyut bağımlılığı) |
| **K9 Hesaplama Verimliliği** | **4** | NN training O(epochs · n · h²) — çok yüksek. Inference O(n · h) — kabul edilebilir ama ek overhead. Toplam eğitim maliyeti standart algoritmalardan 10-100x daha yüksek olabilir. (-6: Training overhead çok yüksek) |

**NEMA Ağırlıklı Toplam: 617 / 1000**

---

#### Algoritma 7: HOOP — Harmonic Oscillator Optimization

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **7** | Harmonic oscillator (basit harmonik hareket) fiziksel modelinin routing'e uygulanması novida taşıyor. Enerji conservation + momentum transfer kavramları permutation uzayında yeni. Ancak physics-inspired algoritmalar (FSA, EMLA, gravitational search) zaten yaygın. (-3: Physics-inspired alan yoğun çalışılmış) |
| **K2 CVRPTW Performans** | **5** | Harmonic motion sürekli uzayda iyi çalışır ama CVRPTW discrete. Energy → fitness, momentum → exploration mapping'leri yapılandırma gerekli. TW constraint'leri harmonic model'e doğal olarak fit olmaz. (-5: Discrete CVRPTW mapping zor) |
| **K3 Akademik Yayın** | **6** | "Harmonic oscillator model for vehicle routing" ilginç ama physics-inspired routing alanında rekabet yüksek. EMLA (2023), FSA (2024) gibi güçlü benzer çalışmalar mevcut. (-4: Rekabet yüksek) |
| **K4 TSP Performans** | **6** | Harmonic motion'un periyodik yapısı TSP'de cyclic exploration sağlayabilir. Ancak standart GA/PSO'dan ne kadar üstün olacağı belirsiz. (-4: Performans avantajı kanıtlanmamış) |
| **K5 Implementasyon** | **6** | Fiziksel modelin matematiksel formülleri basit. Ancak continuous→discrete mapping dikkat gerektirir. Energy conservation check + boundary handling eklenebilir. (-4: Mapping tasarımı) |
| **K6 Mimari Entegrasyon** | **6** | Giant tour temsiline mapping gerekli. Split decoder ile çalışabilir. Numba JIT: fiziksel hesaplamalar JIT-friendly. (-4: Mapping layer gerekli) |
| **K7 Adaptif Davranış** | **7** | Oscillator parametreleri (frequency, damping) adaptif ayarlanabilir. Energy-based faz geçişleri doğal adaptasyon sağlar. (-3: Adaptif parametreler gerekli) |
| **K8 Scalability** | **7** | Per-particle O(n) güncelleme. Toplam O(P·n) — scalable. (-3: Standart swarm overhead) |
| **K9 Hesaplama Verimliliği** | **7** | Oscillator update O(n) per particle. Energy check O(1). Boundary handling O(n). Toplam makul overhead. (-3: Mapping overhead) |

**HOOP Ağırlıklı Toplam: 627 / 1000**

---

#### Algoritma 8: SEC — Symbiotic Evolutionary Colony

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **6** | Symbiotic organisms (mutualism, commensalism, parasitism) tabanlı optimizasyon var: SSO (Symbiotic Organism Search, 2014), COS (Commensalism Algorithm). VRP'ye uyarlanmış hali nadir ama konsept tamamen yeni değil. (-4: Symbiotic optimization literatürde mevcut) |
| **K2 CVRPTW Performans** | **7** | Mutualistic ilişki (iki çözümün birbirini iyileştirmesi) CVRP'de mantıklı. Commensalism (bir çözüm diğerinden faydalanır, zarar vermez) exploration için iyi. Parasitism (rastgele perturbation) çeşitlilik sağlar. Ancak bu mekanizmalar ALNS destroy/repair ile büyük ölçüde örtüşüyor. (-3: ALNS ile fonksiyonel örtüşme) |
| **K3 Akademik Yayın** | **5** | Symbiotic VRP literatürü 2020-2025 arası sınırlı sayıda makale. Ancak SSO zaten yaygın → "SSO for CVRPTW" incremental algısı olabilir. Güçlü bir yeni twist gerekli. (-5: Temel konsept mevcut) |
| **K4 TSP Performans** | **7** | Mutualistic crossover TSP'de faydalı olabilir. Commensalism ileguided perturbation TSP'de exploration sağlar. SSO'nun TSP performansı literatürde orta-iyi raporlanmış. (-3: Standart SSO performansı) |
| **K5 Implementasyon** | **6** | SSO temel yapısı basit (3 symbiosis phase). Ancak VRP permutation uzayına uyarlama dikkat gerektirir. Mutualism phase'de nasıl iki çözümü birleştirir? → crossover tasarımı gerekli. (-4: Permutation mapping gerekli) |
| **K6 Mimari Entegrasyon** | **7** | Population-based → BaseRoutingStrategy uyumlu. Split decoder ile çalışabilir. Numba JIT: symbiosis hesaplamaları JIT-friendly. (-3: Mapping layer gerekli) |
| **K7 Adaptif Davranış** | **7** | Symbiosis türlerinin olasılıkları adaptif ayarlanabilir. Problem fazına göre (exploration/exploitation) phase olasılıkları değişebilir. (-3: Adaptif olasılık gerekli) |
| **K8 Scalability** | **6** | Per-iteration O(P·n). Mutualism phase'de iki çözüm arasında crossover O(n). Toplam standart. (-4: Standart population overhead) |
| **K9 Hesaplama Verimliliği** | **6** | 3 phase per iteration. Mutualism O(n) per pair. Commensalism O(n). Parasitism O(n). Toplam standart population overhead. (-4: 3 faz = ek hesaplama) |

**SEC Ağırlıklı Toplam: 632 / 1000**

---

#### Algoritma 9: ABCH — Attention-Based Constructive Heuristic

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **8** | Attention mekanizmasını (transformer-style) constructive heuristic için kullanmak CO literatüründe aktif araştırma alanı (2023-2025). Ancak tamamen NN-free, rule-based attention CVRPTW için yenilikçi. Pointer network yerine lightweight attention ile construction → katman sayısı az, interpretasyonu yüksek. (-2: Attention mechanism genel olarak hot topic ama NN-free versiyon yeni) |
| **K2 CVRPTW Performans** | **8** | Attention mekanizması CVRPTW'de hangi node'un ne zaman insert edileceğine karar verirken çok güçlü. TW urgency + spatial proximity + capacity balance → multi-head attention ile birleştirilebilir. Constructive heuristic olarak kalitesi ALNS destroy/repair ile rekabet edebilir. (-2: Solo heuristic olarak ALNS'ten zayıf olabilir, LS ile birlikte kullanılmalı) |
| **K3 Akademik Yayın** | **8** | Attention mechanism + routing optimization 2025'te çok popüler (RL4CO, BOPO). Rule-based (NN-free) attention CVRPTW için niche ve ilginç bir katkı. "Lightweight attention-based construction for CVRPTW" güçlü bir başlık. (-2: Attention CO alanı rekabetçi) |
| **K4 TSP Performans** | **7** | TSP'de attention-based construction NN-free olarak çalışabilir (edge scoring + attention weights). Ancak TSP'de spatial structure daha basit → attention'ın avantajı CVRPTW'den daha az belirgin. (-3: TSP'de advantage daha sınırlı) |
| **K5 Implementasyon** | **5** | Attention weight hesaplama (Q·K^T/√d + V) implementasyonu orta. Multi-head attention decoder'ı kurmak karmaşık. CVRPTW-specific attention features (TW urgency, capacity) tanımlamak gerekli. (-5: Attention mekanizması implementasyonu non-trivial) |
| **K6 Mimari Entegrasyon** | **6** | Constructive heuristic olarak initialization phase'de kullanılabilir. Split decoder ile uyumlu. Numba JIT: attention hesabı JIT-friendly (matrix operations). Mevcut pipeline'ın başına eklenebilir. (-4: Initialization-only kullanım sınırlayıcı olabilir) |
| **K7 Adaptif Davranış** | **7** | Attention weights problem instance'a göre adaptif hesaplanır. TW urgency ve capacity pressure otomatik attention bias yaratır. (-3: Feature tanımı kısmen sabit) |
| **K8 Scalability** | **5** | Attention O(n²) — her node her node'a bakar. n=1000'de 1M attention computation. Büyük instance'larda yavaş. Sparse attention veya hierarchical attention ile çözülebilir ama ek karmaşıklık. (-5: O(n²) attention bottleneck) |
| **K9 Hesaplama Verimliliği** | **5** | Multi-head attention construction O(n² · h). Tek seferlik construction (no iteration) → total cost makul. Ancak n=1000'de 1M+ computation. (-5: O(n²) scaling) |

**ABCH Ağırlıklı Toplam: 691 / 1000**

---

#### Algoritma 10: QAIMA — Quantum Annealing-Inspired Memetic Algorithm

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **7** | Quantum annealing (QA) inspired SA variyantları mevcut ama memetic framework ile birleştirilmesi daha yeni. QA tunneling + SA cooling + memetic LS kombinasyonu VRP literatüründe benzersiz. HQTS (2024) quantum tabu search göstermiş → quantum-inspired routing aktif alan. (-3: QA-inspired SA varyantları var) |
| **K2 CVRPTW Performans** | **6** | QA tunneling CVRPTW'de local minimum'dan kaçış sağlayabilir. Ancak discrete QA simulation'ı CVRPTW encoding'ine doğal fit değil. Memetic LS bileşeni kalite garantisi sağlar. (-4: QA simulation discrete mapping zor) |
| **K3 Akademik Yayın** | **7** | "Quantum annealing-inspired memetic algorithm for CVRPTW" ilgini çekecek bir başlık. Quantum + routing kesişimi hala aktif araştırma alanı. HQTS (2024) benchmark oluşturmuş → karşılaştırma yapılabilir. (-3: QA alanında rekabet var) |
| **K4 TSP Performans** | **7** | QA tunneling TSP'de 2-opt stuck durumlarından çıkış sağlar. SA cooling schedule ile birleşik güçlü. Memetic LS (2-opt, 3-opt) kalite garantisi. (-3: Standard SA'dan büyük fark sınırlı olabilir) |
| **K5 Implementasyon** | **5** | QA simulation (tunneling probability + energy landscape) implementasyonu orta. SA cooling schedule basit. Memetic LS mevcut. QA-CVRPTW encoding tasarımı zor. (-5: Encoding tasarımı non-trivial) |
| **K6 Mimari Entegrasyon** | **6** | SA-based algoritma olarak mevcut pipeline'a eklenebilir. Split decoder ile uyumlu. QA encoding → giant tour mapping gerekli. (-4: Encoding overhead) |
| **K7 Adaptif Davranış** | **7** | QA tunneling probability adaptif (sıcaklığa bağlı). SA cooling adaptif schedule. Memetic LS olasılığı adaptif. (-3: Adaptif mekanizmalar standart SA pattern) |
| **K8 Scalability** | **6** | SA-based → per iteration O(n) (single solution). LS O(n²). QA simulation O(1) per step. Toplum makul. (-4: SA single-solution → paralelizasyon sınırlı) |
| **K9 Hesaplama Verimliliği** | **5** | QA simulation ek overhead. SA cooling schedule yönetimi. LS calls sayıca azaltılabilir. (-5: QA simulation overhead) |

**QAIMA Ağırlıklı Toplam: 636 / 1000**

---

#### Algoritma 11: FDO — Fractal Decomposition Optimization

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **8** | Fractal decomposition (böl-parçala, her parçayı optimize et, birleştir) VRP'ye uygulanması çok güçlü bir novida. Fraktal kümeleme ile doğal rotalama → self-similar structure exploitation. Recursive decomposition + bottom-up merge = divide-and-conquer ama fraktal geometri ile guided. Literatürde benzeri yok. (-2: Divide-and-conquer VRP'de var ama fraktal yaklaşım yeni) |
| **K2 CVRPTW Performans** | **8** | Fractal clustering → doğal CVRP bölge ayrımı. Her bölge ayrı optimize edilir → paralel hesaplama mümkün. TW constraint'leri bölge bazında ayrı kontrol edilebilir. Bottom-up merge'de araç sayısı minimizasyonu doğal hedef. (-2: Bölge sınırlarındaki TW conflict'leri merge aşamasında sorun olabilir) |
| **K3 Akademik Yayın** | **8** | "Fractal decomposition for vehicle routing optimization" çok güçlü bir başlık. Fractal geometry + CO kesişimi nadir ve ilgi çekici. Recursive self-similar structure exploitation teorik analiz zenginliği sağlar. IEEE TEVC, Computers & OR, Transportation Research hedef dergiler. (-2: Fractal CO tamamen yeni alan, reviewer familiarization sorunu olabilir) |
| **K4 TSP Performans** | **7** | TSP'de fractal decomposition anlamlı: bölge → optimize → merge. Ancak TSP'de "bölge" kavramı CVRPTW kadar doğal değil (tek araç). Hierarchical TSP (HTSP) literatüründe benzer fikirler var. (-3: HTSP'de benzer yaklaşım) |
| **K5 Implementasyon** | **5** | Recursive decomposition algoritması karmaşık. Fractal clustering (self-similar partitioning) implementasyonu zor. Bottom-up merge route construction dikkat gerektirir. Boundary node handling tricky. (-5: Recursive yapı + boundary handling karmaşık) |
| **K6 Mimari Entegrasyon** | **6** | Giant tour temsiline doğal mapping değil (fractal bölge temsili farklı). Split decoder ile kısmen uyumlu. Pipeline B'de bölge bazlı split olabilir. Numba JIT: recursive yapı JIT zor (stack depth issue). (-4: Non-standard temsil) |
| **K7 Adaptif Davranış** | **6** | Fractal dimension adaptif seçilebilir (problem yapısına göre). Decomposition depth adaptif. Ancak temel fraktal yapı problem'den bağımsız. (-4: Fraktal yapı kısmen rigid) |
| **K8 Scalability** | **8** | Divide-and-conquer doğası → büyük instance'larda güçlü. Paralel hesaplama doğal (bölge bağımsız). n=10000'de bile bölge bazlı çalışabilir. Recursive depth O(log n) → memory efficient. (-2: Merge aşamasında global optimizasyon eksik) |
| **K9 Hesaplama Verimliliği** | **7** | Bölge bazlı paralel hesaplama → speedup. Recursive decomposition O(n log n). Merge O(k · b) — k = bölge sayısı, b = boundary size. Toplam verimli. (-3: Merge overhead) |

**FDO Ağırlıklı Toplam: 718 / 1000**

---

#### Algoritma 12: EFO — Electromagnetic Field Optimization with Gravity Wells

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **7** | EFO (Electromagnetic Field Optimization) 2015'te önerilmiş (Abedinpour Shotorban et al.). Gravity Wells eklentisi yeni bir twist olabilir ama temel kavram成熟. Physics-inspired algoritmalar arasında EM field temsil ettirir ancak incremental improvement. (-3: EFO zaten var, gravity wells küçük ekleme) |
| **K2 CVRPTW Performans** | **5** | EM force-based particle hareketi sürekli uzayda doğal ama discrete CVRPTW mapping zor. Gravity wells = local attractors → CVRPTW'de route cluster'ları olarak yorumlanabilir ama bu yapılandırma yapay. (-5: Discrete mapping zor) |
| **K3 Akademik Yayın** | **6** | "EFO with gravity wells for CVRPTW" moderate interest. EFO literatürü sınırlı (50+ makale). Gravity Wells twist yeni bir katkı. Ancak physics-inspired routing rekabetçi. (-4: EFO niche, gravity wells incremental) |
| **K4 TSP Performans** | **6** | EM-based optimization TSP'de çalışabilir ama üstünlük kanıtlanmamış. Gravity wells = adaptive local search regions → potansiyel var. (-4: Performans kanıtı eksik) |
| **K5 Implementasyon** | **6** | EM force hesaplamaları basit (Coulomb's law). Particle position update orta. Gravity wells = attractor noktaları → ek veri yapısı. (-4: Continuous→discrete mapping) |
| **K6 Mimari Entegrasyon** | **6** | Giant tour temsiline mapping gerekli. Split decoder ile çalışabilir. Numba JIT: EM force hesabı JIT-friendly. (-4: Mapping overhead) |
| **K7 Adaptif Davranış** | **6** | Gravity well pozisyonları adaptif güncellenebilir. EM charge adaptif. Standard adaptive mechanisms. (-4: Standart adaptif mekanizmalar) |
| **K8 Scalability** | **6** | Per-particle O(n) force hesabı. Toplam O(P·n). Gravity wells O(k·n) — k = well sayısı. Toplam standart. (-4: Standart swarm overhead) |
| **K9 Hesaplama Verimliliği** | **6** | EM force O(n) per particle per iteration. Gravity well update O(k·n). Total makul. (-4: EM computation overhead) |

**EFO Ağırlıklı Toplam: 605 / 1000**

---

#### Algoritma 13: GBCH — Gradient-Boosted Constructive Heuristic

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **8** | Gradient boosting (XGBoost, LightGBM tarzı) mekanizmasını constructive routing heuristic'e uyarlamak çok novida. Her adımda "hangi node'u seçmeliyim?" sorusuna gradient-boosted decision tree ile cevap. ML + CO kesişimi aktif araştırma alanı (BOPO ICML'25, NCO). Traditional ML (decision tree) kullanımı neural approach'den farklı bir bakış açısı. (-2: ML-based CO aktif alan ama tree-based approach farklı) |
| **K2 CVRPTW Performans** | **8** | CVRPTW'de construction: "sıradaki node'u seç" kararı çok fazla feature'a bağlı (TW urgency, distance, capacity remaining, time elapsed). Gradient boosting bu feature'ları birleştirmede güçlü. Training data = mevcut solver sonuçları → supervised learning. CVRPTW-specific feature engineering ile yüksek kalite. (-2: Training data bağımlılığı) |
| **K3 Akademik Yayın** | **8** | "Gradient-boosted construction heuristic for CVRPTW" güçlü bir başlık. Tree-based ML + CO = BOPO/DeepRL'den farklı paradigma. Explainability advantage (feature importance, SHAP values). ICML, NeurIPS workshop, COR journal hedefi mümkün. (-2: ML-based CO rekabetçi) |
| **K4 TSP Performans** | **8** | TSP construction (NN, cheapest insertion) → gradient-boosted versiyon olarak güçlü. Edge features (distance, angle, NN-rank) DT ile öğrenilebilir. TSPLIB'de eğitim + test yapılabilir. (-2: TSP'de advantage NN heuristic'ten ne kadar büyük?) |
| **K5 Implementasyon** | **4** | Training pipeline gerekli (data generation, feature engineering, model training, validation). Feature extraction (TW features, spatial features, capacity features) karmaşık. Model inference entegrasyonu. XGBoost/LightGBM dependency. (-6: Training pipeline + feature engineering karmaşık) |
| **K6 Mimari Entegrasyon** | **6** | Constructive heuristic olarak initialization phase'de kullanılabilir. Split decoder ile uyumlu. Numba JIT: DT inference JIT-friendly (condition checks). Model serialization/deserialization gerekli. (-4: Training infrastructure gerekli) |
| **K7 Adaptif Davranış** | **7** | Model farklı problem tipleri için eğitilebilir → problem-specific adaptation. Online learning (partial fit) çalışma zamanında adaptasyon sağlayabilir. (-3: Adaptasyon yeni data gerektirir) |
| **K8 Scalability** | **6** | DT inference O(d · depth) per decision — d = feature count. Total O(n · d · depth) — training'den bağımsız. Ancak feature extraction O(n²) olabilir (pairwise features). (-4: Feature extraction scaling) |
| **K9 Hesaplama Verimliliği** | **5** | Training O(N_train · n · d) — tek seferlik ama yüksek. Inference O(n · d · depth) — makul. Feature extraction O(n²) per instance. (-5: Training + feature extraction overhead) |

**GBCH Ağırlıklı Toplam: 701 / 1000**

---

#### Algoritma 14: CARE — Cellular Automata Routing Evolution

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **7** | Cellular Automata (CA) routing optimization'da nadir kullanılmış. CA'ın grid-based lokal etkileşim yapısı routing problemlerine ilginç bir bakış açısı sunuyor. Ancak CA'nın CO'ya uygulanması 2000'lerden beri araştırılıyor (CA for TSP, CA for scheduling). (-3: CA for CO literatürde mevcut) |
| **K2 CVRPTW Performans** | **6** | CA grid-based → spatial clustering doğal. Ancak CVRPTW'nin time dimension'ını CA'ya encode etmek zor. Lokal kural tabanlı güncelleme global optimum'u kaçırabilir. (-4: Time dimension encoding zor) |
| **K3 Akademik Yayın** | **6** | "Cellular automata for CVRPTW" moderate interest. CA + routing literatürü küçük ama var. Yeni CA rule design olabilir novida. (-4: CA-CO literatürü mevcut) |
| **K4 TSP Performans** | **6** | CA for TSP literatürde mevcut sonuçlar (genellikle suboptimal). CA'nin lokal kural yapısı TSP'de global structure'ı yakalamakta zorlanır. (-4: Local rules → global suboptimality) |
| **K5 Implementasyon** | **5** | CA grid yapısı + state transition rules implementasyonu orta. CA rule design (hangi state'ten hangi state'e geçiş?) CVRPTW için zor. Boundary conditions handling. (-5: Rule design non-trivial) |
| **K6 Mimari Entegrasyon** | **5** | Grid-based temsil giant tour'dan farklı. Split decoder entegrasyonu custom mapping gerekli. Numba JIT: CA grid update JIT-friendly (parallelizable). (-5: Non-standard temsil) |
| **K7 Adaptif Davranış** | **6** | CA rule probabilities adaptif ayarlanabilir. Ancak temel rule set sabit kalır. (-4: Rule set kısmen rigid) |
| **K8 Scalability** | **8** | CA grid update lokal → O(grid_size) per step. Paralel execution doğal (her cell bağımsız). GPU implementation mümkün (CUDA). n=10000'de grid-based yaklaşım scalable. (-2: Global information loss olabilir) |
| **K9 Hesaplama Verimliliği** | **7** | Per-step O(grid_size) — çok verimli. Lokal rule uygulama O(1) per cell. Toplam çok düşük overhead. Parallelization ile speedup. (-3: Convergence yavaş olabilir → çok step gerekli) |

**CARE Ağırlıklı Toplam: 623 / 1000**

---

#### Algoritma 15: HMFO — Harmonic Mean Field Optimization

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **7** | Mean Field Theory (MFT) optimizasyona uygulanması yeni bir paradigma. Statistical mechanics yaklaşımı ile populasyon davranışını modelleme. "Harmonic" mean field → harmonik fonksiyonlarla MFT yaklaşımı novida taşıyor. MFT for CO az sayıda çalışma var (Mean Field Annealing, MFT-GA). (-3: MFT for CO mevcut ama sınırlı) |
| **K2 CVRPTW Performans** | **6** | Mean field ile populasyon ortalaması → average route structure. Harmonic component → oscillatory behavior → exploration. Ancak CVRPTW constraint handling MFT'de zor (hard constraints vs soft mean field). (-4: Hard constraint handling zor) |
| **K3 Akademik Yayın** | **7** | "Harmonic mean field optimization for vehicle routing" ilginç başlık. Statistical physics + CO kesişimi niche ama saygın. Physical Review E, JMLR, IEEE TEVC hedefi mümkün. (-3: Niche alan, reviewer familiarization sorunu) |
| **K4 TSP Performans** | **6** | Mean field ile average tour structure → basin of attraction analizi. Harmonic oscillation ile exploration. TSP'de MFT performansı literatürde sınırlı. (-4: TSP performansı kanıtlanmamış) |
| **K5 Implementasyon** | **5** | Mean field equations implementasyonu orta-çok karmaşık. Harmonic component (differential equation solver). Statistical mechanics background gerekli. Numerical stability issues. (-5: Matematiksel karmaşıklık yüksek) |
| **K6 Mimari Entegrasyon** | **6** | Continuous MFT → discrete tour mapping gerekli. Split decoder ile çalışabilir. Numba JIT: differential equation solving JIT zor. (-4: Continuous→discrete mapping + JIT zorluğu) |
| **K7 Adaptif Davranış** | **7** | Mean field parameters adaptif güncellenebilir. Harmonic frequency adaptif. Temperature/field strength adaptif. (-3: Adaptif mekanizmalar mevcut MFT literatüründe) |
| **K8 Scalability** | **6** | Mean field computation O(P) per iteration (populasyon average). Harmonic update O(d) — d = system dimension. Total O(P·n) — standard. (-4: Standard population overhead) |
| **K9 Hesaplama Verimliliği** | **6** | Mean field update O(P) — düşük. Harmonic component O(d) — düşük. Differential equation solving ek overhead. (-4: DE solving overhead) |

**HMFO Ağırlıklı Toplam: 630 / 1000**

---

#### Algoritma 16: SACO — Symbiotic Adaptive Colony Optimization

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **6** | ACO (Ant Colony Optimization) 1990'lardan beri成熟. CVRPTW için ACO varyantları çok sayıda (MACS, ACS, MMAS). "Symbiotic" + "Adaptive" eklemeleri incremental. Symbiotic mekanizma (böcekler arası etkileşim) doğal ACO framework'üne eklenebilir. (-4: ACO çok成熟, incremental improvement) |
| **K2 CVRPTW Performans** | **7** | ACO CVRPTW'de kanıtlanmış performansa sahip (MACS-VRPTW literature best for bazı instance'lar). Symbiotic + adaptive eklentileri potansiyel iyileştirme sağlayabilir. Pheromone update mekanizması CVRPTW'ye doğal fit. (-3: Standart ACO zaten güçlü, eklentiler marginal) |
| **K3 Akademik Yayın** | **5** | ACO-CVRPTW literatürü 200+ makale → alan aşırı doygun. "Symbiotic ACO" tarzı makaleler her yıl yayınlanıyor. Yeni bir novelty angle olmadan top-tier kabul zor. (-5: ACO doygunluğu çok yüksek) |
| **K4 TSP Performans** | **8** | ACO TSP'de en başarılı meta-heuristics'lerden biri. ACS-MMAS TSP benchmark'lerde güçlü. Symbiotic ekleme exploration'ı artırabilir. (-2: Standart ACO zaten TSP'de güçlü) |
| **K5 Implementasyon** | **7** | ACO framework'u mevcutUniRide'de yok ama literatürde çok iyi çalışılmış. Pheromone matrix + heuristic info implementasyonu standard. Symbiotic rules ekleme kolay. (-3: ACO implementasyonu bilinen ama mevcut kod yok) |
| **K6 Mimari Entegrasyon** | **8** | Population-based → BaseRoutingStrategy uyumlu. Split decoder ile uyumlu. Numba JIT: pheromone update JIT-friendly. Mevcut GWO/PSO pattern'ine benzer implementasyon. (-2: Standard pattern) |
| **K7 Adaptif Davranış** | **6** | Pheromone evaporation rate adaptif. Heuristic info weights adaptif. Symbiotic rules adaptif. Ancak adaptif ACO varyantları zaten yaygın. (-4: Adaptif ACO standard) |
| **K8 Scalability** | **7** | Pheromone matrix O(n²) → memory issue büyük n'de. Ant construction O(n) per ant. Total O(m·n) — m = ant sayısı. Sparse pheromone matrix ile memory optimize edilebilir. (-3: Pheromone matrix O(n²) memory) |
| **K9 Hesaplama Verimliliği** | **7** | Ant construction O(n) — efficient. Pheromone update O(n²) — expensive ama incrementally yapılabilir. Total makul. (-3: Pheromone update O(n²)) |

**SACO Ağırlıklı Toplam: 669 / 1000**

---

#### Algoritma 17: NGCO — Neuro-Geometric Constructive Optimization

| Kriter | Puan | Gerekçe |
|--------|------|---------|
| **K1 Orijinallik** | **8** | Neuro-geometric yaklaşım: sinir ağı + geometrik özellikler (convex hull, Delaunay, minimum spanning tree) kombinasyonu routing'de yeni. Geometric structure exploitation (MST-based guidance, convex hull ordering) CVRPTW için doğal. Neural component geometric feature'ları birleştirir. (-2: Geometric approaches for TSP mevcut ama neural-geometric fusion yeni) |
| **K2 CVRPTW Performans** | **8** | Geometric structure (convex hull, MST) CVRPTW rotası için güçlü baseline. TW-aware geometric ordering = spatial clustering + temporal sequencing. Neural component hangi geometric feature'ın ne zaman dominant olacağını öğrenir. Güçlü potansiyel. (-2: Geometric construction solo CVRPTW'de yetersiz, neural component kritik) |
| **K3 Akademik Yayın** | **8** | "Neuro-geometric construction for CVRPTW" güçlü başlık. Geometric + neural fusion differentiation sağlar. CVRP literature'de geometric heuristics (sweep, Fisher-Jaikumar) köken alır → bu modern bir evrim. AAAI, ICRA (robotics routing), COR journal. (-2: Geometric heuristic literature'si köken alır) |
| **K4 TSP Performans** | **7** | TSP'de geometric heuristics (convex hull, insertion) bilinen ve etkili. Neural enhancement potansiyel var. Ancak TSP'de pure geometric approaches zaten güçlü → neural component'in marginal contribution'u sınırlı. (-3: TSP'de geometric zaten güçlü) |
| **K5 Implementasyon** | **4** | Geometric library (scipy.spatial, shapely) + neural component = karmaşık. Convex hull, Delaunay, MST computation → external dependency. Neural network training pipeline. Feature extraction from geometric structures. (-6: Çok karmaşık, birden fazla external dependency) |
| **K6 Mimari Entegrasyon** | **5** | Constructive heuristic olarak initialization'da kullanılabilir. Geometric library dependency. Neural inference eklentisi. Numba JIT: geometric computation kısmen JIT, neural değil. (-5: External dependencies + non-standard pipeline) |
| **K7 Adaptif Davranış** | **7** | Neural component hangi geometric feature'ı ne zaman kullanacağını öğrenir. Problem-specific geometric structure exploitation. Online adaptation mümkün. (-3: Neural adaptation training data gerektirir) |
| **K8 Scalability** | **5** | Geometric computation: Convex hull O(n log n), Delaunay O(n log n), MST O(n log n) → efficient. Neural inference O(n·h). Ancak büyük instance'larda geometric structure quality düşebilir. (-5: Büyük instance'larda geometric quality düşüşü) |
| **K9 Hesaplama Verimliliği** | **4** | Multiple geometric structures O(n log n) each. Neural inference O(n·h). Feature extraction O(n²). Total construction overhead yüksek. (-6: Birden fazla geometric computation + neural overhead) |

**NGCO Ağırlıklı Toplam: 666 / 1000**

---

## 4. Toplam Puan Tablosu

### 4.1 Detaylı Puan Matrisi

| # | Algoritma | K1 Orij. (20%) | K2 CVRP. (15%) | K3 Akad. (12%) | K4 TSP (13%) | K5 Impl. (10%) | K6 Enteg. (8%) | K7 Adapt. (8%) | K8 Scale (7%) | K9 Hesap. (7%) | **TOPLAM** |
|---|-----------|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|:-:|
| 1 | **RDMA** | 9 | 8 | 9 | 8 | 7 | 9 | 8 | 7 | 7 | **816** |
| 2 | **AOEA** | 10 | 9 | 10 | 7 | 4 | 7 | 10 | 6 | 4 | **792** |
| 3 | **EBSO** | 8 | 8 | 8 | 8 | 8 | 9 | 9 | 7 | 7 | **802** |
| 4 | **FDO** | 8 | 8 | 8 | 7 | 5 | 6 | 6 | 8 | 7 | **718** |
| 5 | **GBCH** | 8 | 8 | 8 | 8 | 4 | 6 | 7 | 6 | 5 | **701** |
| 6 | **ABCH** | 8 | 8 | 8 | 7 | 5 | 6 | 7 | 5 | 5 | **691** |
| 7 | **SACO** | 6 | 7 | 5 | 8 | 7 | 8 | 6 | 7 | 7 | **669** |
| 8 | **NGCO** | 8 | 8 | 8 | 7 | 4 | 5 | 7 | 5 | 4 | **666** |
| 9 | **QAIMA** | 7 | 6 | 7 | 7 | 5 | 6 | 7 | 6 | 5 | **636** |
| 10 | **SEC** | 6 | 7 | 5 | 7 | 6 | 7 | 7 | 6 | 6 | **632** |
| 11 | **HMFO** | 7 | 6 | 7 | 6 | 5 | 6 | 7 | 6 | 6 | **630** |
| 12 | **HOOP** | 7 | 5 | 6 | 6 | 6 | 6 | 7 | 7 | 7 | **627** |
| 13 | **CARE** | 7 | 6 | 6 | 6 | 5 | 5 | 6 | 8 | 7 | **623** |
| 14 | **NEMA** | 7 | 7 | 7 | 7 | 3 | 5 | 8 | 5 | 4 | **617** |
| 15 | **CGW2O** | 5 | 6 | 4 | 7 | 7 | 8 | 6 | 7 | 7 | **609** |
| 16 | **EFO** | 7 | 5 | 6 | 6 | 6 | 6 | 6 | 6 | 6 | **605** |
| 17 | **QASI** | 6 | 6 | 6 | 7 | 5 | 6 | 7 | 6 | 5 | **604** |

### 4.2 Sıralama (Toplam Puana Göre)

```
╔══════════════════════════════════════════════════════════════════════╗
║              ALGORİTMA SIRALAMASI — AĞIRLIKLI PUANLAMA              ║
╠══════════════════╦═════════╦═════════════════════════════════════════╣
║ Sıra            ║ Algoritma║ Puan     │ Tier    │ Analiz             ║
╠══════════════════╬═════════╬══════════╬═════════╬═══════════════════╣
║ 🥇 1.           ║ RDMA     ║ 816     │ S-TIER  │ En dengeli        ║
║ 🥈 2.           ║ EBSO     ║ 802     │ S-TIER  │ En verimli        ║
║ 🥉 3.           ║ AOEA     ║ 792     │ S-TIER  │ En novada         ║
║    4.           ║ FDO      ║ 718     │ A-TIER  │ En ölçeklenebilir ║
║    5.           ║ GBCH     ║ 701     │ A-TIER  │ ML+CO potansiyeli ║
║    6.           ║ ABCH     ║ 691     │ A-TIER  │ Attention hot topic║
║    7.           ║ SACO     ║ 669     │ B-TIER  │ Kanıtlanmış temel ║
║    8.           ║ NGCO     ║ 666     │ B-TIER  │ Geometric+Neural  ║
║    9.           ║ QAIMA    ║ 636     │ B-TIER  │ QA+Memetic        ║
║   10.           ║ SEC      ║ 632     │ B-TIER  │ Symbiotic+EA      ║
║   11.           ║ HMFO     ║ 630     │ B-TIER  │ Mean Field+fizik  ║
║   12.           ║ HOOP     ║ 627     │ B-TIER  │ Harmonic+Physics  ║
║   13.           ║ CARE     ║ 623     │ B-TIER  │ CA+Paralel        ║
║   14.           ║ NEMA     ║ 617     │ B-TIER  │ NE+Memetic        ║
║   15.           ║ CGW2O    ║ 609     │ C-TIER  │ Mevcut GWO extend ║
║   16.           ║ EFO      ║ 605     │ C-TIER  │ EM+Physics        ║
║   17.           ║ QASI     ║ 604     │ C-TIER  │ Quantum-inspired   ║
╚══════════════════╩═════════╩══════════╩═════════╩═══════════════════╝
```

### 4.3 Tier Analizi

```
TIER SİSTEMİ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🟢 S-TIER (750+ puan) — ÖNCELİKLİ IMPLEMENTASYON
─────────────────────────────────────────────────
  RDMA (816): En dengeli algoritma. Yüksek novada + güçlü performans + 
              makul implementasyon zorluğu. AKADEMİK YAYIN + PRATİK BAŞARI
              ikisini birden sağlar.
              
  EBSO (802): En düşük implementasyon zorluğu ile en yüksek ROI. Matematiksel
              rigor + adaptif davranış + JIT uyumu. İLK IMPLEMENTASYON İÇİN İDEAL.
              
  AOEA (792): En yüksek novada (10/10) ancak implementasyon zorluğu yüksek (4/10).
              Uzun vadede en prestijli akademik katkı. 2. veya 3. implementasyon
              için uygun.

🟡 A-TIER (650-749 puan) — GÜÇLÜ ALTERNATİFLER
─────────────────────────────────────────────────
  FDO (718):  En yüksek scalability (8/10). Büyük instance'larda güçlü.
              Fractal decomposition = doğal CVRPTW bölgeleme. Divide-and-conquer
              paradigmı ile paralel hesaplama potansiyeli.
              
  GBCH (701): ML+CO kesişimi = 2025 trendi. Gradient boosting ile tree-based
              construction. Explainability advantage (feature importance).
              Training pipeline gerekli ama payoff yüksek.
              
  ABCH (691): Attention mechanism = en hot topic (transformers). NN-free
              lightweight attention = farklılaştırıcı. O(n²) scaling sorunu
              var ama sparse attention ile çözülebilir.

🔵 B-TIER (600-649 puan) — İNCELENMEYE DEĞER
─────────────────────────────────────────────────
  SACO, NGCO, QAIMA, SEC, HMFO, HOOP, CARE, NEMA
  
  Her biri belirli alanlarda güçlü ama genel olarak S/A tier'dan zayıf.
  Özellikle:
  - SACO: Kanıtlanmış ACO temeli + implementasyon kolaylığı (7/10)
  - NEMA: En yüksek adaptif davranış (8/10) ama en düşük hesaplama (4/10)
  - CARE: En yüksek scalability (8/10) ama en düşük entegrasyon (5/10)

🔴 C-TIER (<600 puan) — DÜŞÜK ÖNCELİK
─────────────────────────────────────────────────
  CGW2O, EFO, QASI
  
  CGW2O: Mevcut GWO extension → incremental value
  EFO:    Physics-inspired doygunluk
  QASI:   Quantum-inspired doygunluk
```

### 4.4 Radar Chart Verileri

```
RDMA:  Orijinallik=9  CVRPTW=8  Akademik=9  TSP=8  Impl=7  Entegrasyon=9  Adaptif=8  Scale=7  Hesap=7
EBSO:  Orijinallik=8  CVRPTW=8  Akademik=8  TSP=8  Impl=8  Entegrasyon=9  Adaptif=9  Scale=7  Hesap=7
AOEA:  Orijinallik=10 CVRPTW=9  Akademik=10 TSP=7  Impl=4  Entegrasyon=7  Adaptif=10 Scale=6  Hesap=4
FDO:   Orijinallik=8  CVRPTW=8  Akademik=8  TSP=7  Impl=5  Entegrasyon=6  Adaptif=6  Scale=8  Hesap=7
GBCH:  Orijinallik=8  CVRPTW=8  Akademik=8  TSP=8  Impl=4  Entegrasyon=6  Adaptif=7  Scale=6  Hesap=5
ABCH:  Orijinallik=8  CVRPTW=8  Akademik=8  TSP=7  Impl=5  Entegrasyon=6  Adaptif=7  Scale=5  Hesap=5
```

---

## 5. Zayıf Yön Analizi

### 5.1 Her Algoritmanın En Zayıf Kriteri

| Algoritma | En Zayıf Kriter | Puan | Risk |
|-----------|----------------|------|------|
| **RDMA** | K8 Scalability | 7 | O(n²) rezonans matrisi büyük n'de bottleneck |
| **EBSO** | K8 Scalability | 7 | O(n²) entropi hesabı büyük n'de yavaş |
| **AOEA** | K9 Hesaplama | 4 | Meta-evrim overhead 2x yavaşlatır |
| **FDO** | K5 Implementasyon | 5 | Recursive yapı boundary handling zor |
| **GBCH** | K5 Implementasyon | 4 | Training pipeline + feature engineering |
| **ABCH** | K8 Scalability | 5 | O(n²) attention bottleneck |
| **SACO** | K3 Akademik | 5 | ACO alanı doygun |
| **NGCO** | K5 Implementasyon | 4 | Çok karmaşık, external dependency |
| **QAIMA** | K5 Implementasyon | 5 | QA encoding tasarımı zor |
| **SEC** | K3 Akademik | 5 | SSO alanı incremental |
| **HMFO** | K5 Implementasyon | 5 | Matematiksel karmaşıklık |
| **HOOP** | K2 CVRPTW | 5 | Discrete mapping zor |
| **CARE** | K6 Entegrasyon | 5 | Non-standard temsil |
| **NEMA** | K5 Implementasyon | 3 | GPU gerekli, çok karmaşık |
| **CGW2O** | K3 Akademik | 4 | GWO hybrid doygunluğu |
| **EFO** | K2 CVRPTW | 5 | Discrete mapping zor |
| **QASI** | K5 Implementasyon | 5 | Qubit mapping zor |

### 5.2 Risk Değerlendirmesi

```
YÜKSEK RİSKLİ ALGORİTMALAR (En zayıf kriter ≤ 4):
┌─────────────────────────────────────────────────────────┐
│ NEMA  (3): GPU gerekli → production ortamında ek maliyet │
│ AOEA  (4): 3-4 hafta implementasyon → ROI riski         │
│ GBCH  (4): Training pipeline → data dependency riski     │
│ NGCO  (4): Birden fazla external dependency               │
└─────────────────────────────────────────────────────────┘

ORTA RİSKLİ ALGORİTMALAR (En zayıf kriter 5):
┌─────────────────────────────────────────────────────────┐
│ FDO, ABCH, QAIMA, SEC, HMFO, HOOP, CARE, QASI, EFO     │
│ → Implementasyon dikkat gerektirir ama makul süre      │
└─────────────────────────────────────────────────────────┘

DÜŞÜK RİSKLİ ALGORİTMALAR (En zayıf kriter ≥ 6):
┌─────────────────────────────────────────────────────────┐
│ RDMA (7): Tüm kriterler ≥ 7 → en güvenli yatırım       │
│ EBSO (7): Tüm kriterler ≥ 7 → en güvenli yatırım       │
│ SACO (5): K5=7, K6=8, K4=8 → implementasyon kolay      │
└─────────────────────────────────────────────────────────┘
```

---

## 6. Önerilen Implementasyon Stratejisi

### 6.1 Birincil Strateji (Önerilen)

```
FAZ 1: EBSO (2 hafta)
  → En yüksek ROI (802 puan, en kolay implementasyon)
  → Matematiksel rigor ile hızlı akademik sonuç
  → Baseline oluşturma

FAZ 2: RDMA (3 hafta)
  → En yüksek toplam puan (816 puan)
  → En dengeli profil (hiçbir kriter < 7)
  → Akademik yayın + pratik performans

FAZ 3: FDO (2 hafta)
  → En yüksek scalability (8/10)
  → Büyük instance'larda RDMA/EBSO'den üstün olabilir
  → Paralel hesaplama avantajı

FAZ 4: AOEA (4 hafta) [Opsiyonel]
  → En yüksek novada (10/10)
  → Prestijli akademik yayın
  → Zaman ve kaynak yeterse
```

### 6.2 Alternatif Strateji (Risk-Averse)

```
FAZ 1: EBSO (2 hafta)
FAZ 2: SACO (1 hafta) ← En kolay, kanıtlanmış temel
FAZ 3: RDMA (3 hafta)
FAZ 4: ABCH (2 hafta) ← Hot topic, attention mechanism
```

### 6.3 Alternatif Strateji (Risk-Seeking)

```
FAZ 1: AOEA (4 hafta) ← En yüksek novada, tüm risk
FAZ 2: GBCH (3 hafta) ← ML+CO trendi
FAZ 3: FDO (2 hafta) ← Scalability
FAZ 4: RDMA (3 hafta) ← Dengeli tamamlayıcı
```

---

## 7. Beyin Fırtınası Hazırlık Notları

Bu puanlama tablosu, toplu beyin fırtınası oturumu için **hazırlık materyali**dir. Tartışılması gereken konular:

1. **Ağırlık ayarları**: Orijinallik %20 çok mu yüksek? CVRPTW %15 yeterli mi?
2. **S-TIER sınırı**: 750+ doğru bir eşik mi? 780+ daha uygun olabilir mi?
3. **FDO 4. sıra**: Fractal decomposition gerçekte A-TIER mı, S-TIER mı?
4. **SACO 7. sıra**: ACO doygunluğu nedeniyle daha düşük olmalı mı?
5. **GBCH vs ABCH**: ML-based (GBCH) mi attention-based (ABCH) mi daha umut verici?
6. **NEMA riski**: GPU gereksinimi bu puanlamayı reddedebilecek bir faktör mü?
7. **Hibrit potansiyeli**: Hangi 2 algoritmanın birleştirilmesi en yüksek senorji yaratır?

---

> **Sonraki Adım**: Beyin fırtınası oturumu ile ağırlıkları ve puanları birlikte gözden geçirme, sonra final implementasyon planı oluşturma.
