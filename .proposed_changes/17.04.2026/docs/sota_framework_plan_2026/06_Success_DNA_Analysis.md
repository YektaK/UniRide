# UniRide SOTA Framework — Başarı DNA'sı Analizi

> **Tarih**: 2026-04-14
> **Durum**: Stratejik Analiz
> **Amaç**: TSPLIB ve CVRPTW'de en yüksek başarıya sahip yöntemlerin başarı faktörlerini analiz etmek ve bu bilgileri RDMA, EBSO, AOEA algoritmalarımıza entegre etmek

---

## 1. Soru: "Neden en iyiler bu kadar iyi?"

TSPLIB'de %0 gap (optimal) ve CVRPTW'de <1% gap üreten yöntemlerin ortak özellikleri nelerdir? Bu analiz, 2022-2026 literatür ve DIMACS challenge sonuçlarından çıkarılan **10 temel başarı DNA'sı**nı ortaya koyuyor.

---

## 2. TSPLIB Şampiyonlarının Başarı DNA'sı

### 2.1 Tier S — %0 Gap (Optimal Çözücü Ulaştıran)

| Yöntem | Tür | TSPLIB Performansı | İlk Yayın |
|--------|-----|-------------------|-----------|
| **Concorde** | Exact (Branch-and-Cut) | %0 tüm instancelarda | 1999 |
| **LKH-3** | Meta-heuristic (L-K + k-opt) | %0 eil51→pr2392 | 2017 |
| **NeuroLKH** | Neural + LKH Hybrid | %0 eil51→pr1002 | NeurIPS 2021 |
| **Sym-NCO** | Neural (Symmetry-augmented) | ~%0.03 TSP100 | ICLR 2022 |

### 2.2 Tier A — <1% Gap

| Yöntem | Tür | Performans | İlk Yayın |
|--------|-----|-----------|-----------|
| **POMO** | Transformer (Multi-viewpoint) | ~%0.10 TSP100 | NeurIPS 2021 |
| **DSOS** | Differential Symbiotic Org. Search | 0.000% kroA100 | 2017 |
| **MatNet** | Multi-Attention + RL | ~%0.12 TSP500 | NeurIPS 2020 |

### 2.3 Tier B — 1-5% Gap

| Yöntem | Tür | Performans | İlk Yayın |
|--------|-----|-----------|-----------|
| **VDWOA** | Chaotic WOA | 0.70% eil51 | 2021 |
| **HSA** | Harmony Search | 1-3% medium instances | 2001 |
| **Standard GA/PSO** | Meta-heuristic | 3-15% tipik | 1990s |

---

## 3. CVRPTW Şampiyonlarının Başarı DNA'sı

### 3.1 DIMACS Challenge Kazananları

| Yöntem | Solomon Seti | Gehring-Homberger | Teknik |
|--------|-------------|-------------------|--------|
| **HGS (Vidal 2012)** | Top sıralar | Top sıralar | GA + Split + Adaptif Çeşitlilik |
| **ALNS (Ropke 2006)** | Çok güçlü | Güçlü | Adaptif Destroy/Repair |
| **PyVRP** | DIMACS 2021 kazananı | — | HGS modern implementasyonu |
| **OR-Tools** | Güçlü | Güçlü | CP-SAT + Local Search |

### 3.2 Solomon Benchmark Referans Sonuçları

```
Instance Sınıfı     | Ortalama Araç | Ortalama Mesafe Gap | En İyi Yöntem
────────────────────┼───────────────┼─────────────────────┼──────────────────
RC1 (Random Cluster) | 12-14         | <0.5%              | HGS, ALNS
C1  (Clustered)      | 10            | <0.3%              | HGS
R1  (Random)         | 12-13         | <1.0%              | ALNS
RC2 (Random Cluster) | 3-4           | <1.5%              | HGS
C2  (Clustered)      | 3             | <0.5%              | HGS
R2  (Random)         | 2-4           | <1.0%              | ALNS
```

---

## 4. 10 BAŞARI DNA'SI — Derinlemesine Analiz

### DNA #1: PROBLEM-STRUCTURE AWARE OPERATÖRLER

**Ne yapıyorlar?** Generic crossover/mutation yerine, problem yapısını anlayan operatörler kullanıyorlar.

**Örnekler:**
- **LKH**: Lin-Kernighan yöntemi sadece "swap 2 edges" demez → her adımda k-opt derinliğini adaptif olarak belirler, yarı-optimality gap'i hesaplar
- **Shaw Removal**: Müşterileri sadece rastgele değil, benzerlik fonksiyonuna göre kaldırır (mesafe + TW + demand)
- **Regret Insertion**: "Eğer bu müşteriyi şimdi eklemessen, sonra çok pahalı olur" fikrini matematiksel olarak ifade eder

**Neden bu kadar kritik?**
```
Generic Operator (OX crossover):
  Parent1: [1,2,3,4,5,6]  →  Child: [1,2,4,5,3,6]  (yapısal ilişki YOK)

Problem-Aware Operator (Shaw Removal + Regret Insertion):
  "Rota 3'teki müşteriler 14, 17, 22 birbirine çok yakın ve TW'leri uyumlu
   → Birlikte kaldır, birlikte geri yerleştir → Rota yapısı korunur"
```

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | Rezonans skoru zaten problem-aware (ortak kenar + alt-tur) | ✅ İYİ — Rezonans zaten yapısal uyum ölçer. Ama Shaw benzerlik fonksiyonunu rezonans hesabına entegre et → `R_shaw = w1*R + w2*Shaw_similarity` |
| **EBSO** | Entropi hesabı kenar frekansı tabanlı | ⚠️ ORTA — Kenar frekansı yapısal bilgi verir ama constraint-aware değil. Entropiyi çok-boyutlu yap → `H = H_edge + H_tw + H_capacity` |
| **AOEA** | Operator'ler evrilir ama atomic operations küçük set | ✅ ÇOK İYİ — AOEA'nın en büyük gücü bu. Ama atomic operation kütüphanesini zenginleştir: Shaw-related destroy, TW-aware repair, Regret insertion ekle |

**Öncelikli Aksiyon:** AOEA'ya CVRPTW-specific atomic operations ekle (Task ID: 4.1)

---

### DNA #2: BÜYÜK KOMŞULUK ARAMASI (Large Neighborhood Search)

**Ne yapıyorlar?** Tek edge swap yerine, çözümün %10-40'ını kaldırıp yeniden inşa ediyorlar.

**Matematiksel Arkaplan:**
```
2-opt neighborhood size:     C(n,2) = n(n-1)/2     → n=1000'de ~500K
3-opt neighborhood size:     C(n,3) = n(n-1)(n-2)/6 → n=1000'de ~166M
Or-opt (relocate):           4n(n-1)                → n=1000'de ~4M
ALNS destroy/repair:         Yapılandırılmış arama  → Etkili neighborhood çok daha büyük

Sonuç: ALNS, her iterasyonda ~10⁶+ equivalent neighborhood evaluation yapar
       ama bunu YAPILANDIRILMIŞ şekilde yapar (Shaw + Regret = smart arama)
```

**Neden etkili?**
- Küçük değişiklikler (2-opt) → yerel optimum'da takılıp kalma riski
- Büyük değişiklikler (ALNS destroy %30) → yeni bölgeleri keşfet ama yapılandırılmış
- **Anahtar fikir:** "Büyük mahalle = geniş arama, ama akıllı rebuild = kalite garantisi"

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | Rezonans crossover yapısal ama "küçük mahalle" | 🔴 KRİTİK — Rezonans crossover'a "destructive interference" modunu genişlet: Düşük rezonanslı eşleşme → chunk-level destroy/repair (ALNS-stil) yap. Yani düşük R → sadece scramble değil, Shaw-stil kaldır-yeniden-yerleştir |
| **EBSO** | Swarm güncellemesi tek node düzeyinde | 🔴 KRİTİK — Entropi sıkıştırma fazında VNS yerine ALNS-stil destroy/repair kullan. "H > H_max → problem-specific bölge kaldır, structure-aware ekle" |
| **AOEA** | Destroy/repair zaten var (atomic ops) | ✅ İYİ — Ama destroy intensity'sini adaptif yap: Erken iterasyonlarda %30-40, geç iterasyonlarda %10-15 kaldır |

**Öncelikli Aksiyon:** RDMA'ya ALNS-stil destructive interference ekle (Task ID: 4.2)

---

### DNA #3: AGRESİF VE ÇOK-KATMANLI LOKAL ARAMA

**Ne yapıyorlar?** Çözüm iyileştirmede local search'i sonuna kadar kullanıyorlar.

**LKH'nin LS Katmanları:**
```
Layer 1: 2-opt → Her kenar çifti kontrol
Layer 2: 3-opt → Her üç kenar kontrol (L-K'nın varsayılanı 5-opt'e kadar!)
Layer 3: Sequential 4-opt, 5-opt → Kademeli derinleşme
Layer 4: Node relocate, Or-opt → Tek node taşıma
Layer 5: Segment moves → Tur segmentleri arası taşıma

Sonuç: LKH bir iterasyonunda ~100K+ LS hamlesi yapar
```

**ALNS + LS Kombinasyonu:**
```
ALNS iterasyon: destroy → repair → lokal arama
Lokal arama detayı:
  1. 2-opt → İyileşme varsa devam (tipik 5-20 improve)
  2. Or-opt → İyileşme varsa devam
  3. 2-opt* (restart) → İyileşme varsa devam
  4. Swap → İyileşme varsa devam
  ... iyileşme yok olana kadar tekrarla
```

**Kritik İçgörü:** "Top kalite = global arama kalitesi × local arama derinliği"

```
İyi global search + zayıf LS = 5-10% gap
Zayıf global search + iyi LS = 3-5% gap
İyi global search + iyi LS = <1% gap ← HEDEF
```

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | "Sadece en iyi N çözüme LS uygula" | ⚠️ ORTA — LS'yi "first-improvement" yerine "best-improvement" stratejisi ile yap. Her child'e LS uygula, iyileşme oranı yüksekse derinleş |
| **EBSO** | "VNS entegrasyonu zaten mevcut" | ⚠️ ORTA — Mevcut VNS'yi çok katmanlı yap: 2-opt → Or-opt → 3-opt → swap → repeat. LS olasılığını entropi fazına bağla: Exploit fazında LS=100%, Explore fazında LS=20% |
| **AOEA** | "Olasıksal LS" | ⚠️ ORTA — LS'yi her child'e zorunlu yap ama derinlik adaptif olsun. İyi genome'lerin ürettiği child'lara derin LS, kötü genome'lerin child'lerine yüzeysel LS |

**Öncelikli Aksiyon:** Tüm algoritmalara "multi-layer LS pipeline" oluştur (Task ID: 4.3)

---

### DNA #4: ADAPTİF MEKANİZMALAR (Hangi Operator Ne Zaman Çalışıyor?)

**Ne yapıyorlar?** Sabit operatör seti yerine, problemi analiz edip en etkili operatörleri tercih ediyorlar.

**ALNS Adaptif Mekanizması (Ropke & Pisinger):**
```
Segment-based weight update:
  - Her 100 iterasyonda operatör skorlarını hesapla
  - En çok new_best üreten destroy/repair → ağırlık ARTIR
  - En az improve üreten → ağırlık AZALT
  - Roulette wheel selection ile operatör seç

  Sonuç: Shaw Removal + Regret-2 erken iterasyonlarda ağırlıklı,
         Worst Removal + Greedy geç iterasyonlarda ağırlıklı
         → Problem'ın hangi aşamada hangi operatöre ihtiyacı var?
         ALNS bunu OTOMATIK öğreniyor
```

**HGS Adaptif Çeşitlilik Yönetimi (Vidal 2012):**
```
3 farklı popülasyon arası adaptasyon:
  1. Giant tour population (Split ile decode)
  2. Route-based population (doğrudan rota temsili)
  3. Elite archive (en iyi çözümler)

  Adapte edilen:
  - Population size
  - Selection pressure (tournament size)
  - Crossover probability
  - Mutation intensity
  → Amaç: "Genetic drift'i engelle, çeşitliliği koru ama quality'yi artır"
```

**Kritik İçgörü:** Adaptif mekanizma = "algoritmanın kendi kendini tune etmesi"

```
Manuel Tuning (eski yaklaşım):
  Developer: "Shaw removal'ı %30, Random removal'ı %20 kullanayım"
  Problem: Instance tipine göre değişir → bazı instance'larda kötü

Adaptif (yeni yaklaşım):
  Algoritma: "Bu instance'da Shaw+Regret3 çok iyi çalışıyor, ağırlıklarını artırıyorum"
  Result: Her instance için optimal operatör kombinasyonu
```

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | Adaptif θ_esik var ama basit | ✅ İYİ — Rezonans eşik değerini ALNS-stil segment-based güncelle. "Son 100 iterasyonda Constructive mode ile üretilen child'lar mı daha iyi, yoksa Destructive mode mu?" → Mode ağırlıklarını adaptif yap |
| **EBSO** | Adaptif H_target(t) var | ✅ İYİ — Ama faz geçiş sınırlarını (H_min, H_max) da adaptif yap. "Bu instance'da H_min=0.3 çok düşük kalıyor, 0.4'e çıkar" → Instance-specific entropi hedefleri |
| **AOEA** | Meta-evrim zaten adaptif | ✅ EN İYİ — AOEA'nın en büyük gücü. Ama meta-evrim interval'ını adaptif yap: Erken iterasyonlarda sık (her 50 iter), geç iterasyonlarda seyrek (her 500 iter) |

**Öncelikli Aksiyon:** Tüm algoritmalara instance-adaptive parametre öğrenme ekle (Task ID: 4.4)

---

### DNA #5: SPLIT-BASED GİANT TOUR TEMSİLİ

**Ne yapıyorlar?** TSP (giant tour) üzerinde optimize ediyor, araç rotalarına bölme işini ayrı bir decodera bırakıyorlar.

**Split Decoder Mantığı:**
```
Giant Tour (TSP):
  [0, 5, 2, 8, 3, 1, 7, 6, 4, 0]
  (Tek devamlı permütasyon, depo başlangıç/bitiş)

Split Decoder (CVRPTW):
  [0, 5, 2, 8 | 3, 1 | 7, 6, 4, 0]
  Araç 1: Depot → 5 → 2 → 8 → Depot  (Toplam demand < capacity, TW OK)
  Araç 2: Depot → 3 → 1 → Depot    (Toplam demand < capacity, TW OK)
  Araç 3: Depot → 7 → 6 → 4 → Depot (Toplam demand < capacity, TW OK)

Split = Shortest path problemi (DP ile O(n²·V) çözülür)
```

**Neden bu kadar güçlü?**
```
Doğrudan Rota Temsili:
  - Crossover: "Rota 1'in node'ları ile Rota 3'ün node'larını takas et"
    → Kapasite ihlali, TW ihlali, infeasible çözüm
  - Mutation: Node rotalar arası taşı → Complex constraint kontrol
  - LS: Cross-route move → Feasibility check overhead

Giant Tour + Split:
  - Crossover: Standart TSP crossover (OX, PMX, ERX) → Her zaman FEASIBLE!
  - Mutation: Standart TSP mutation (swap, invert, scramble) → Her zaman FEASIBLE!
  - LS: Standart TSP LS (2-opt, 3-opt) → Her zaman FEASIBLE!
  - Araç sayısı + route yapısı → Split decoder otomatik optimize eder
```

**Bu, literatürdeki EN ÖNEMLİ mimari kararlardan biridir:**

| Mimari | Feasibility | Crossover Karmaşıklığı | LS Karmaşıklığı | Genel Başarı |
|--------|-------------|----------------------|-----------------|-------------|
| Direct route representation | Infeasible sık olur | O(n²) + constraint check | O(n²) + constraint check | Düşük-Orta |
| Giant tour + Split | Her zaman feasible | O(n) standart | O(n²) standart | YÜKSEK |

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | Giant tour + Split uyumlu tasarlanmış | ✅ EN İYİ — Zaten HybridSplitBaseStrategy'den türetiliyor. Rezonans crossover Giant tour üzerinde çalışıyor → doğal uyum |
| **EBSO** | Giant tour + Split uyumlu | ✅ EN İYİ — Swarm update permutation uzayında → Split decode ile araç rotalarına bölünür |
| **AOEA** | Giant tour + Split uyumlu | ✅ EN İYİ — Destroy/repair giant tour üzerinde çalışır. Regret insertion sırasında Split decode ile feasibility kontrolü yapılır |

**Durum:** Tüm 3 algoritma zaten doğru mimariyi kullanıyor ✅

---

### DNA #6: ÇOKLU BAŞLANGIÇ ÇÖZÜMÜ (Multi-Start Strategy)

**Ne yapıyorlar?** Tek başlangıç noktası yerine, farklı heuristic'lerden çoklu başlangıç çözümleri üretiyorlar.

**En Etkili Başlangıç Heuristic'leri:**
```
1. Nearest Neighbor (NN):                O(n²) — Hızlı, orta kalite
2. Clarke-Wright Savings:                O(n² log n) — İyi, araç sayısı optimize
3. Insertion (Cheapest/Regret):          O(n²·V) — İyi, TW-aware
4. Sweep Algorithm (geometrik):          O(n log n) — Kümeleme bazlı
5. Random + LS:                          O(n²) — Çeşitlilik

HGS yaklaşımı: 25-50 farklı başlangıç çözümü ile başlar
LKH yaklaşımı: 10+ farklı NN varyantı ile başlar
```

**Neden önemli?**
```
Tek başlangıç:  Local optimum X'e yakınsarsın
Çoklu başlangıç: Farklı bölgelerden X, Y, Z noktalarına yakınsarsın
                 → En iyi Z'yi bulma olasılığı çok daha yüksek

Matematiksel: P(en iyi ≥ k) = 1 - (1 - p)^k
  p = tek başlangıçla BKS'yi bulma olasılığı
  k = başlangıç çözüm sayısı

  p=0.01, k=50: P ≥ 0.39 (tekle kıyasla 39x artış)
  p=0.05, k=25: P ≥ 0.72
```

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | "NN+Random başlangıç" | ⚠️ ORTA — Başlangıç çeşitliliğini artır: NN + Clarke-Wright + Regret Insertion + Random (4 farklı popülasyon seed'i). Her seed'den popülasyonun ¼'ünü üret |
| **EBSO** | "Max entropi başlangıç" | ⚠️ ORTA — Max entropi rastgele turlar üretir ama bunların çoğu çok kötüdür. NN + Clarke-Wright ile "yapılandırılmış yüksek entropi" başlangıçları kullan |
| **AOEA** | "InitializeSolutions" | ⚠️ ORTA — Multi-start + AOEA = güçlü kombinasyon. Farklı başlangıçlardan gelen çözümler, farklı genome'lar tarafından iyileştirilir |

**Öncelikli Aksiyon:** Ortak "MultiStartInitializer" modülü oluştur (Task ID: 4.5)

---

### DNA #7: İNTELEKTÜEL KABUL KRİTERLERİ (Sophisticated Acceptance)

**Ne yapıyorlar?** Sadece en iyi çözümü kabul etmek yerine, kötü çözümleri de kontrollü kabul ediyorlar.

**Simulated Annealing (SA):**
```
T(t) = T₀ × α^t  (soğuma çizelgesi)

if ΔE < 0:  KABUL (daha iyi çözüm)
else:       p = exp(-ΔE / T(t))
            if random() < p: KABUL (daha kötü ama şans tanı)

Neden çalışıyor?
  - Yüksek T → Çok kötü çözümleri bile kabul eder → EXPLORATION
  - Düşük T → Sadece hafif kötü çözümleri kabul eder → EXPLOITATION
  - Doğal exploration → exploitation geçişi
```

**Record-to-Record Travel (RTR):**
```
threshold = best_solution_cost + deviation

if new_cost < threshold: KABUL
else:                     REDDET

deviation başlangıçta yüksek, zamanla azalır
→ SA'dan daha agresif exploitation
```

**Late Acceptance Hill Climbing (LAHC):**
```
cost_array = [tarihî maliyet değerleri]  (L boyutunda dizi)

if new_cost ≤ cost_array[current_pos % L]: KABUL
else:                                       REDDET

Neden güçlü?
  "Son L iterasyonun en kötüsünden daha iyiysem, kabul et"
  → Hafızaya dayalı, geçmiş bilgisini kullanır
  → SA'dan daha deterministik
```

**Kritik İçgörü:** Kabul kriteri, algoritmanın "cesaret seviyesi"ni belirler

```
Improving-only:  P(accept bad) = 0         → Hızlı yakınsama, yerel optimum
SA:              P(accept bad) = f(T)       → Dengeli, yaygın kullanılır
RTR:             P(accept bad) = f(deviation) → Agresif exploitation
LAHC:            P(accept bad) = f(history)  → Hafıza-bazlı, modern
```

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | "Dissonans filtresi" (sadece iyi child'lar) | 🔴 KRİTİK — Dissonans filtresi + SA ekle. Düşük rezonanslı child'lar SA ile değerlendirilsin: "Rezonans düşük ama SA kabul ettiyse, yine de popülasyona al" |
| **EBSO** | Doğrudan mevcut değil | 🔴 KRİTİK — SA veya LAHC kabul kriteri ekle. Swarm'da en iyi child doğrudan kabul edilir ama "diğer child'lar SA ile değerlendirilsin" |
| **AOEA** | Acceptance criterion evriliyor (en iyi DNA) | ✅ EN İYİ — AOEA zaten acceptance criterion'ı bir genome olarak evriltiyor. Ama başlangıç seed'lerine SA + LAHC + RTR varyantlarını ekle |

**Öncelikli Aksiyon:** RDMA'ya SA kabul kriteri, EBSO'ya LAHC ekle (Task ID: 4.6)

---

### DNA #8: ÇEŞİTLİLİK YÖNETİMİ (Explicit Diversity Control)

**Ne yapıyorlar?** Erken yakınsamayı engellemek için çeşitliliği aktif olarak yönetiyorlar.

**HGS Popülasyon Yapısı:**
```
2 popülasyon:
  S1: Giant tour population (N₁ birey)
  S2: Route-based population (N₂ birey)

  Her crossover'da:
  - Parent1 ← S1'den seç
  - Parent2 ← S2'den seç (FARKLI temsillerden!)

  Sonuç: Parent'lar structurally farklı → Child daha çeşitli
```

**ALNS Rastgelelik:**
```
Destroy/Repair seçiminde:
  - Roulette wheel → En iyi operatörler daha fazla seçilir AMA
  - Random seçim (p=0.05) → Kötü operatörler bile bazen seçilir

  Neden? "Belki şimdi kötü olan operatör, sonra iyi olacak"
  → Çeşitlilik = uzun vadeli başarı
```

**Genetik Drift Kontrolü (Vidal 2012):**
```
Distance-based diversity check:
  Her N iterasyonda:
    d_avg = ortalama popülasyon içi mesafe (edit distance veya kenar farklılığı)
    if d_avg < threshold:
      Popülasyona rastgele/taze bireyler EKLE
      (genellikle %10-30 refresh)
```

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | "Harmonic Pulse" = yapılandırılmış çeşitlilik | ✅ EN İYİ — Harmonic Pulse zaten güçlü bir çeşitlilik mekanizması. Ama "spectral clustering" yerine daha hızlı bir yöntem kullan: k-means veya baseline distance-based clustering |
| **EBSO** | "Entropi = birincil kontrol değişkeni" | ✅ EN İYİ — EBSO'nun çekirdek konsepti. Ama entropi hesabını fast approx yap: Örneğin her 10 iterasyonda tam hesapla, arada incremental update yap |
| **AOEA** | "Yeni doğan genome'ler" = çeşitlilik | ⚠️ ORTA — Yeni genome'ler tamamen rastgele. Bunu "taze genome = mevcut en iyinin mutasyona uğramış hali" olarak değiştir → Structured injection |

**Durum:** Çeşitlilik yönetimi tüm algoritmalarda var ama optimizasyon gerekiyor

---

### DNA #9: PENALTY-BASED RELAXATION (Sert Kısıtları Yumuşatma)

**Ne yapıyorlar?** CVRPTW'de zaman penceresi ve kapasite kısıtlarını cezalandırarak, infeasible bölgeleri de keşfediyorlar.

**Klasik Yaklaşım (Feasibility-First):**
```
Her zaman feasible çözüm üret:
  - TW ihlali varsa → reject
  - Kapasite ihlali varsa → reject
  - Sadece feasible child'ları kabul et

Sorun: Infeasible bölgenin hemen yanındaki FEASIBLE bölge
       çok iyi bir çözüm içerebilir ama ulaşılamaz!
```

**Penalty Yaklaşımı (SOTA):**
```
cost(solution) = total_distance
               + α_tw × tw_violation
               + α_cap × capacity_violation

α_tw ve α_cap zamanla artırılır (cezalar katılaşır):
  Başlangıç: α_tw = 10, α_cap = 5   (gevşek, infeasible kabul edilir)
  Ortaya doğru: α_tw = 100, α_cap = 50
  Son:          α_tw = 10000, α_cap = 5000  (neredeyse kesin)

Neden etkili?
  1. Infeasible bölgeden "geçiş" yaparak feasible olmayan bir bölgeye
     ulaşılabilir → daha geniş arama alanı
  2. Ceza ağırlıkları adaptif → Problem zorluğuna göre uyum sağlar
  3. Son aşamada cezalar çok yüksek → Feasible çözüm garantisi
```

**Iterated Penalty Method (Gendreau et al.):**
```
Phase 1: Serbest arama (düşük cezalar) → Global optimum bölgesini bul
Phase 2: Ceza artırma → Feasible bölgeye çek
Phase 3: Agresif ceza → Neredeyse kesin feasible çözüm

Her phase'de best solution saklanır
Final: En iyi feasible solution
```

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | TW + kapasite rezonans var ama ceza yok | 🔴 KRİTİK — Rezonans skoru sadece "benzerlik" ölçer, ceza içermiyor. TW ve kapasite ihlallerini rezonans cezası olarak ekle: `R_total = R_similarity - w1·tw_penalty - w2·cap_penalty` |
| **EBSO** | Çok-boyutlu entropi ama infeasible kabul yok | 🔴 KRİTİK — Entropi sıkıştırma fazında "sadece feasible child'ları kabul et" → Bu yanlış! Infeasible child'ları da kabul et ama cezalandır |
| **AOEA** | Penalty insertion zaten atomic op olarak var | ✅ İYİ — Ama penalty_insert'ın α değerlerini adaptif yap: Meta-evrim α parametresini de evriltsin |

**Öncelikli Aksiyon:** Tüm algoritmalara adaptive penalty relaxation ekle (Task ID: 4.7)

---

### DNA #10: NEURAL BOOSTING (Sinir Ağı ile Operatör Rehberliği)

**Ne yapıyorlar?** Sinir ağlarını doğrudan çözüm üretmek yerine, operatör seçimini ve parametre ayarını rehberlemek için kullanıyorlar.

**NeuroLKH Yaklaşımı (En Başarılı Hybrid):**
```
Phase 1: Classical LKH çalıştır → İyi (ama mükemmel olmayan) çözüm
Phase 2: Neural network mevcut çözümü analiz et
         "Hangi kenarlar optimize edilebilir?"
         "Hangi k-opt hamlesi potansiyelli?"
Phase 3: Neural rehberliğinde LKH'yi tekrar çalıştır
         → Neural network'ün önerdiği kenarları önceliklendir
Phase 4: Tekrar LS → %0 gap

Neden etkili?
  - Neural network STRUCTÜREL BİLGİ çıkarır (hangi kenarlar önemli?)
  - LKH CLASSICAL GÜÇ sağlar (k-opt, aggressive LS)
  - Hybrid = Neural insight + Classical power
```

**BOPO (ICML 2025) Yaklaşımı:**
```
Bayesian Preference Optimization:
  - Multiple construction heuristic'lerin output'unu karşılaştır
  - Preference model eğit: "Hangi construction decision daha iyi?"
  - Model'i guide olarak kullan: Construction sırasında hangi node'u seç?

  NOT: BOPO construction phase'e odaklanır
  RDMA/AOEA/EBSO improvement phase'de çalışır
  → İKİSİNİ BİRLEŞTİR = Full pipeline (construction + improvement)
```

**Kritik İçgörü:** NN'i çözüm üretici değil, OPERATÖR REHBERİ olarak kullan

```
Yanlış: NN → Doğrudan tur üret (zayıf kalite, generalizasyon sorunu)
Doğru:  NN → "Bu durumda 2-opt yapmamı öner, Or-opt değil" (hafif overhead, güçlü rehberlik)
Doğru:  NN → "Bu iterasyonda Shaw removal'ı seç, Random değil" (operatör seçim rehberliği)
```

**UniRide Algoritmalarımıza Nasıl Entegre Ederiz?**

| Algoritma | Mevcut Durum | İyileştirme |
|-----------|-------------|-------------|
| **RDMA** | Rezonans hesabı matematiksel | ⚠️ GELECEK — Rezonans ağırlıklarını (w1, w2, w3) bir lightweight NN (Decision Tree veya küçük MLP) ile öğren. Training data: benchmark sonuçları |
| **EBSO** | Entropi hedefi adaptif ama sabit formül | ⚠️ GELECEK — H_target çizelgesinin parametrelerini (H_start, H_end, γ) problem features'larından öğren |
| **AOEA** | Meta-evrim zaten operator seçiyor | ✅ UYGUN — AOEA'ya BOPO-stil preference learning ekle: Destroy/repair kararlarının kalitesini kaydet, küçük bir model ile "hangi durumda hangi operator?" öğren |

**Öncelikli Aksiyon:** Kısa vadede yapılmaz, uzun vadede (akademik makale sonrası) GBCH algoritması ile entegrasyon

---

## 5. ÖZET: 10 DNA ve Etki Seviyesi

```
DNA # | Başarı Faktörü                    | Etki    | RDMA | EBSO | AOEA | Öncelik
──────┼────────────────────────────────────┼─────────┼──────┼──────┼──────┼─────────
  1   | Problem-Structure Aware Ops        | 🔴 ÇOK  | ✅✅  | ⚠️   | ✅✅✅ | P0
  2   | Büyük Komşuluk Araması (LNS)       | 🔴 ÇOK  | ❌→✅ | ❌→✅ | ✅✅  | P0
  3   | Çok Katmanlı Lokal Arama           | 🔴 ÇOK  | ⚠️→✅ | ⚠️→✅ | ⚠️→✅ | P0
  4   | Adaptif Mekanizmalar               | 🟡 ORTA | ✅✅  | ✅✅  | ✅✅✅ | P1
  5   | Giant Tour + Split Temsil          | 🔴 ÇOK  | ✅✅✅ | ✅✅✅ | ✅✅✅ | ✅ YAPILI
  6   | Çoklu Başlangıç Çözümü             | 🟡 ORTA | ⚠️   | ⚠️   | ⚠️   | P1
  7   | İntelektüel Kabul Kriterleri        | 🔴 ÇOK  | ❌→✅ | ❌→✅ | ✅✅✅ | P0
  8   | Çeşitlilik Yönetimi                | 🟡 ORTA | ✅✅  | ✅✅  | ⚠️   | P1
  9   | Penalty-Based Relaxation            | 🔴 ÇOK  | ❌→✅ | ❌→✅ | ⚠️   | P0
 10   | Neural Boosting                    | 🟡 ORTA | ⚠️G  | ⚠️G  | ⚠️G  | P3 (Gelecek)

✅ = Mevcut, ⚠️ = Kısmen, ❌ = Eksik, G = Gelecek planı, → = İyileştirilecek
```

---

## 6. ALGORİTMA GELİŞTİRME YOL HARİTASI

### 6.1 Sıralı İyileştirme Planı

```
FAZ 0: Ortak Altyapı (Her 3 algoritma için)
├── MultiStartInitializer (NN + Clarke-Wright + Regret + Random)
├── MultiLayerLS (2-opt → Or-opt → 3-opt → Swap → Repeat)
├── PenaltyManager (adaptive α_tw, α_cap)
└── SA/LAHC AcceptanceCriterion kütüphanesi

FAZ 1: EBSO İyileştirmesi (En düşük implementasyon maliyeti)
├── DNA #2: ALNS-stil destroy/repair entegrasyonu
├── DNA #7: SA kabul kriteri
├── DNA #9: Penalty-based relaxation
└── DNA #6: Multi-start initialization
→ HEDEF: EBSO "Enhanced EBSO" (E²BSO) olarak yayınlanabilir

FAZ 2: RDMA İyileştirmesi (En dengeli profil)
├── DNA #1: Shaw-related resonance metric
├── DNA #2: ALNS-stil destructive interference
├── DNA #7: SA kabul kriteri (dissonans filtresi ile birleşik)
├── DNA #9: Penalty-based resonance
└── DNA #6: Multi-start initialization
→ HEDEF: RDMA "Enhanced RDMA" (R²DMA) olarak yayınlanabilir

FAZ 3: AOEA İyileştirmesi (En yüksek novada)
├── DNA #1: CVRPTW-specific atomic operations
├── DNA #9: Adaptive penalty parameters
├── DNA #4: Adaptive meta-evolution interval
└── DNA #8: Structured genome injection
→ HEDEF: AOEA "Production AOEA" olarak yayınlanabilir
```

### 6.2 Beklenen Performans Etkisi

```
                    Mevcut    FAZ 0+1    FAZ 0+1+2    FAZ 0+1+2+3
                    (Tahmin)  (E²BSO)    (R²DMA)      (P-AOEA)
TSPLIB Gap:         5-10%     1-3%       1-3%         1-3%
CVRPTW Gap:         15-25%    3-5%       3-5%         2-4%
Akademik Değer:     ★★★★     ★★★★★     ★★★★★       ★★★★★
```

---

## 7. EN ÖNEMLİ 3 İÇGÖRÜ

### İçgörü 1: "Generic → Problem-Aware" Geçişi
```
Tüm başarılı yöntemlerin ortak özelliği:
  "Problemin YAPISINI anlayan operatörler kullanırlar"

Bu, tüm 10 DNA'nın temelinde yatan ana fikirdir.
Her operatör, her LS move, her crossover problemi "anlamalıdır".
```

### İçgörü 2: "Search Structure > Search Intensity"
```
Aynı bütçeyle:
  100K rastgele 2-opt hamlesi  <  10K ALNS destroy/repair + LS

  AKILLI ARAMA > ÇOK ARAMA

Yapılandırılmış mahalle (Shaw + Regret), rastgele mahalleden 5-10x daha etkilidir.
```

### İçgörü 3: "Exploration-Exploitation Dengesi = Başarının %80'i"
```
%80 Başarı: Doğru exploration-exploitation dengesi
%15 Başarı: Problem-aware operatörler
%5  Başarı: Neyi optimize ettiğini bilmek (TSP vs CVRPTW)

EBSO'nun entropi mekanizması, RDMA'nın rezonans eşik mekanizması,
AOEA'nın meta-evrim mekanizması → Hepsi aynı şeye çalışıyor:
  "Ne zaman keşfet, ne zaman sömürü?"
```

---

## 8. SONRAKİ ADIM

Bu analiz, algoritmalarımızı "nasıl iyileştiririz?" sorusuna kapsamlı bir yanıt veriyor.

**Tavsiye edilen sıralama:**
1. ✅ **Önce FAZ 0'ı yap** (ortak altyapı: MultiStart, MultiLayerLS, Penalty, SA/LAHC)
2. ✅ **Sonra EBSO'yu iyileştir** (en düşük risk, en hızlı sonuç)
3. ✅ **Sonra RDMA'yi iyileştir** (en dengeli, en güçlü akademik potansiyel)
4. ⏸️ **AOEA opsiyonel** (en yüksek novada ama en yüksek implementasyon maliyeti)

**Akademik Yayın Stratejisi:**
- Makale 1: "E²BSO: Enhanced Entropy-Balanced Swarm Optimization for CVRPTW" (Hızlı sonuç)
- Makale 2: "R²DMA: Resonance-Driven Memetic Algorithm with Adaptive Large Neighborhood Search" (Güçlü contribution)
- Makale 3: "AOEA + BOPO: Operator Co-evolution with Preference Learning" (En yenilikçi)

---

> **Önceki Belge:** `05_Algorithm_Scoring_Matrix.md` — 17 algoritma puanlama
> **Sonraki Belge:** `07_Enhanced_Algorithm_Designs.md` — İyileştirilmiş algoritma tasarımları (PLAN)
