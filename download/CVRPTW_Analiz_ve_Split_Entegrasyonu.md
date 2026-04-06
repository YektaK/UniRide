# CVRPTW Analiz ve Split Entegrasyonu

> **Doküman Sürümü:** 2.0  
> **Son Güncelleme:** 26 Mart 2026  
> **Durum:** Split Entegrasyonu Planlanıyor

---

## 1. Problem Tanımı

### 1.1 CVRPTW (Capacitated Vehicle Routing Problem with Time Windows)

UniRide projesi, fiziksel engelli (Sw - tekerlekli sandalye) ve engeli bulunmayan (So - diğer) üniversite öğrencilerinin belirli zaman dilimlerinde kampüs içi ve dışı noktalara taşınmasını amaçlamaktadır. Bu problem, literatürde **CVRPTW** (Capacitated Vehicle Routing Problem with Time Windows) olarak bilinmektedir.

**Problem Ölçeği:**
- Mevcut öğrenci sayısı: N ≈ 30
- Hedeflenen ölçek: N ≥ 300
- Lokasyon sayısı: 100+ (Sw ve So kodları)

### 1.2 Kısıtlar (Constraints)

| Kısıt | Açıklama | Değer |
|-------|----------|-------|
| **Sw Kapasitesi** | Tekerlekli sandalyeli öğrenci kapasitesi | max 4 |
| **So Kapasitesi** | Normal koltuk kapasitesi | max 5 |
| **Toplam Kapasite** | Araç başına toplam kapasite | max 9 |
| **Tur Süresi** | Bir aracın toplam tur süresi | max 180 dk |
| **Öğrenci Süresi** | Öğrencinin araçta geçireceği max süre | max 120 dk |
| **Time Matrix** | Asimetrik seyahat süreleri | Gerçek trafik verisi |

### 1.3 Problemin NP-Hard Doğası

CVRPTW, NP-Hard bir problemdir. N öğrenci için olası permütasyon sayısı N! kadardır:
- N = 30 için: 2.65 × 10³² permütasyon
- N = 300 için: Astronomik sayıda permütasyon

Bu nedenle, **sezgisel (heuristic)** ve **meta-sezgisel (meta-heuristic)** algoritmalar kullanılması zorunludur.

---

## 2. Mevcut Mimari Analizi

### 2.1 Cluster-First, Route-Second Yaklaşımı

Mevcut sistem, "Cluster-First, Route-Second" prensibini benimsemiştir:

```
Students (N=300)
      ↓
┌─────────────────┐
│   K-Means       │  ← Coğrafi kümeleme
│   Clustering    │
└─────────────────┘
      ↓
Cluster 1, Cluster 2, ..., Cluster K
      ↓
┌─────────────────┐
│   GA / PSO /    │  ← Her küme için ayrı TSP çözümü
│   HHO / GWO     │
└─────────────────┘
      ↓
Route 1, Route 2, ..., Route K
```

### 2.2 Tespit Edilen Sorunlar

#### Sorun 1: K-Means'in Time Matrix Duyarsızlığı

K-Means algoritması sadece coğrafi mesafeye (Euclidean/Haversine) göre kümeleme yapar. Ancak gerçek seyahat süreleri:
- Trafik yoğunluğuna
- Yol yapısına
- Tek yönlü yollara
- Kavşak gecikmelerine

bağlı olarak coğrafi mesafeden farklılık gösterir.

**Örnek:**
```
K-Means sonucu:
  Cluster A: [Öğrenci1, Öğrenci2, Öğrenci3]
  
Gerçek time_matrix:
  Öğrenci1 → Öğrenci2: 45 dakika (kötü yol)
  Öğrenci2 → Öğrenci3: 30 dakika
  Toplam: 75 dakika > 45 dk limit!
  
Sonuç: Küme reddediliyor, yeni araç açılıyor.
```

#### Sorun 2: Katı Küme Sınırları

Mevcut `VehicleCalculator.calculate()` fonksiyonunda (clustering.py, satır 296-346):

```python
for attempt in range(max_attempts):
    clusters = self.cluster_students(points, num_vehicles)
    # ...
    if route_duration > self.max_tour_time:
        valid = False
        break  # ← KÜME REDDEDİLİYOR!
    
    num_vehicles += 1  # ← Yeni araç açılıyor
```

Bu yaklaşım:
- Sadece 2 dakika aşım için bile yeni araç açılmasına
- **Tek öğrencilik verimsiz rotalar** oluşmasına
- Araç kullanım oranının düşmesine neden olur.

#### Sorun 3: Global Optimal'den Uzaklık

Her küme bağımsız optimize edildiği için:
- Küme A'dan 1 öğrenci küme B'ye geçse daha iyi olabilir
- Ama bu geçiş K-Means tarafından engelleniyor
- Local optimum'a takılma riski yüksek

### 2.3 Mevcut Algoritmalar

| Algoritma | Dosya | Temel Yaklaşım |
|-----------|-------|----------------|
| GA | `ga_strategy.py` | Order Crossover + Swap/Inversion Mutation |
| PSO | `pso_strategy.py` | Swap Operation + Clerc Constriction |
| HHO | `hho_strategy.py` | 4 Farklı Siege Stratejisi + Lévy Flight |
| GWO | `gwo_strategy.py` | Alpha-Beta-Delta Hiyerarşisi |
| OR-Tools | `ortools_cvrp.py` | Guided Local Search |

**Ortak Sorun:** Tümü K-Means clustering'e bağımlı!

---

## 3. Önerilen Çözüm: Split Entegrasyonu

### 3.1 Giant Tour Representation

Split entegrasyonu ile yeni yaklaşım:

```
Students (N=300)
      ↓
┌─────────────────────────────────────────┐
│        META-SEZGİSEL OPTİMİZASYON        │
│                                         │
│   Population/Swarm/Hawks/Wolves         │
│              ↓                          │
│   Giant Tour: [3,1,4,8,2,5,7,6,9,...]  │
│   ↑ Tüm öğrenciler TEK permütasyon      │
└─────────────────────────────────────────┘
      ↓
┌─────────────────────────────────────────┐
│           OPTIMAL SPLIT DECODER          │
│                                         │
│   Giant Tour → Tüm olası bölünmeleri    │
│   dene → DP ile EN İYİ bölünme          │
│              ↓                          │
│   Route 1: [3,1,4]  (42 dk)             │
│   Route 2: [8,2,5]  (38 dk)             │
│   Route 3: [7,6,9,10] (55 dk)           │
└─────────────────────────────────────────┘
```

### 3.2 Split Algoritması Nasıl Çalışır?

**Prins & Lacomme Split (2004):**

```python
def optimal_split(giant_tour, constraints):
    n = len(giant_tour)
    dp = [∞] * (n + 1)
    dp[0] = 0
    
    for i in range(n):
        sw_count = 0
        so_count = 0
        duration = 0
        
        for j in range(i, n):
            # Capacity kontrolü
            sw_count, so_count += update_capacity(tour[j])
            if sw_count > 4 or so_count > 5:
                break  # ← Kapasite aşıldı, bu segment geçersiz
            
            # Süre hesabı
            duration += time_matrix[tour[j-1]][tour[j]]
            if duration > 180:
                break  # ← Süre aşıldı, bu segment geçersiz
            
            # DP güncelleme
            if dp[i] + duration < dp[j+1]:
                dp[j+1] = dp[i] + duration
    
    return backtrack(dp)
```

**Önemli:** Split, TÜM olası bölünmeleri değerlendirir:
- `[1,2,3] + [4,5,6] + [7,8,9]`
- `[1,2] + [3,4,5] + [6,7,8,9]`
- `[1,4,8] + [2,3,5,6,7,9]` ← Sizin örneğiniz
- ... (binlerce kombinasyon)

### 3.3 Split'in Avantajları

| Özellik | K-Means + Meta | Giant Tour + Split |
|---------|---------------|-------------------|
| **Constraint Handling** | Sonradan kontrol | Split içinde entegre |
| **Feasibility** | Sık infeasible | **Her zaman feasible** |
| **Time Matrix** | Duyarsız | **Tam duyarlı** |
| **Tek öğrencilik rotalar** | Sık oluşur | **Minimum** |
| **Global Optimal** | Zor | **Daha yakın** |
| **Kümeleme Hatası** | Yaygın | **Yok** |

---

## 4. Hibrit Algoritmalar

### 4.1 PSO-Split

```
Particle Position = Giant Tour (Tüm öğrenciler)
Fitness Evaluation = Split Decoder → Total Cost
Velocity = Swap Operations
```

**Avantajlar:**
- Hızlı yakınsama
- Basit implementasyon
- Paralel değerlendirme imkanı

### 4.2 HHO-Split

```
Hawk Position = Giant Tour
Prey (Best Solution) = En düşük maliyetli tur
Escape Energy = Exploration/Exploitation dengesi
```

**Avantajlar:**
- Lévy Flight ile lokal optimum kaçış
- 4 farklı siege stratejisi
- Adaptif arama

### 4.3 GWO-Split

```
Wolf Position = Giant Tour
Alpha, Beta, Delta = İlk 3 en iyi çözüm
Position Update = Leaders'a doğru hareket
```

**Avantajlar:**
- Sosyal hiyerarşi ile çeşitlilik
- Dengeli keşif/sömürü
- Basit parametreler

### 4.4 GA-Split

```
Chromosome = Giant Tour
Crossover = Order Crossover (OX1)
Mutation = Swap/Inversion
Selection = Tournament + Elitism
```

**Avantajlar:**
- Kanıtlanmış etkinlik
- Çaprazlama ile çeşitlilik
- Kolay hiperparametre ayarı

---

## 5. Implementasyon Planı

### 5.1 Yeni Dosya Yapısı

```
optimizer_api/
├── utils/
│   ├── split_decoder.py          ← YENİ: Optimal Split
│   ├── local_search.py           ← YENİ: 2-opt, or-opt
│   ├── data_loader.py            ← Mevcut
│   └── clustering.py             ← Mevcut (opsiyonel)
├── strategies/
│   ├── base_strategy.py          ← Mevcut
│   ├── hybrid_base_strategy.py   ← YENİ: Split tabanlı base
│   ├── pso_split_strategy.py     ← YENİ
│   ├── hho_split_strategy.py     ← YENİ
│   ├── gwo_split_strategy.py     ← YENİ
│   └── ga_split_strategy.py      ← YENİ
└── main.py
```

### 5.2 Geliştirme Aşamaları

| Aşama | Görev | Süre | Öncelik |
|-------|-------|------|---------|
| 1 | `split_decoder.py` | 2-3 saat | 🔴 Kritik |
| 2 | `hybrid_base_strategy.py` | 1 saat | 🔴 Kritik |
| 3 | `pso_split_strategy.py` | 2 saat | 🟡 Yüksek |
| 4 | `hho_split_strategy.py` | 2 saat | 🟡 Yüksek |
| 5 | `gwo_split_strategy.py` | 2 saat | 🟡 Yüksek |
| 6 | `ga_split_strategy.py` | 2 saat | 🟡 Yüksek |
| 7 | `local_search.py` | 1-2 saat | 🟢 Orta |
| 8 | Test & Benchmark | 3-4 saat | 🟢 Orta |

**Toplam Tahmini Süre:** 16-18 saat

---

## 6. Beklenen İyileştirmeler

### 6.1 Kantitatif Hedefler

| Metrik | Mevcut | Hedef | İyileştirme |
|--------|--------|-------|-------------|
| Ortalama araç sayısı (N=100) | ~18 | ~14 | -22% |
| Tek öğrencilik rotalar | %15-20 | <%5 | -75% |
| Ortalama tur süresi | 85 dk | 65 dk | -24% |
| İnfeasible çözüm oranı | %8 | %0 | -100% |

### 6.2 Niteliksel İyileştirmeler

1. **Daha Adil Dağılım:** Öğrenciler time_matrix'e göre optimal gruplandırılacak
2. **Daha Az Araç:** Kümeleme hataları nedeniyle açılan gereksiz araçlar önlenecek
3. **Daha Hızlı Süreç:** K-Means iterasyonu kalkacak, direkt optimizasyon
4. **Daha İyi Debug:** Giant tour → Split süreci daha izlenebilir

---

## 7. Akademik Yayın Potansiyeli

### 7.1 Yenilik Değeri

| Katkı | Açıklama | Değer |
|-------|----------|-------|
| **Heterojen Kapasite** | Sw/So ayrı kapasite modellemesi | Yüksek |
| **Gerçek Dünya Uygulaması** | İstanbul verisi, gerçek time_matrix | Yüksek |
| **Hibrit Yaklaşım** | PSO/HHO/GWO + Split kombinasyonu | Orta-Yüksek |
| **Karşılaştırmalı Çalışma** | 4 algoritmanın Split ile karşılaştırması | Orta |

### 7.2 Hedef Dergiler

| Dergi | Impact Factor | Tür |
|-------|--------------|-----|
| Expert Systems with Applications | 8.5 | Q1 |
| Computers & Operations Research | 4.5 | Q1 |
| European Journal of Operational Research | 6.4 | Q1 |
| Applied Soft Computing | 8.7 | Q1 |

### 7.3 Önerilen Makale Başlığı

> "Hybrid Meta-Heuristic Algorithms with Optimal Split for Heterogeneous CVRPTW: A Case Study on Disabled Student Transportation"

---

## 8. Referanslar

1. Prins, C. (2004). A simple and effective evolutionary algorithm for the vehicle routing problem. *Computers & Operations Research*, 31(12), 1985-2002.

2. Lacomme, P., Prins, C., & Ramdane-Chérif, W. (2004). Competitive memetic algorithms for arc routing problems. *Annals of Operations Research*, 131(1), 159-185.

3. Heidari, A. A., et al. (2019). Harris hawks optimization: Algorithm and applications. *Future Generation Computer Systems*, 97, 849-872.

4. Mirjalili, S., et al. (2014). Grey wolf optimizer. *Advances in Engineering Software*, 69, 46-61.

5. Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization. *IEEE ICNN*, 1942-1948.

---

## 9. Ek A: Mevcut Kod Analizi

### clustering.py Sorunlu Satırlar

```python
# SATIR 296-346: VehicleCalculator.calculate()
def calculate(self, students: List[Dict], route_optimizer=None) -> Dict:
    # ...
    for attempt in range(max_attempts):
        clusters = self.cluster_students(points, num_vehicles)
        # ...
        for i, cluster in enumerate(clusters):
            # ...
            if route_duration > self.max_tour_time:
                valid = False
                break  # ← SORUN: Küme reddediliyor
        
        if valid:
            return result
        
        num_vehicles += 1  # ← SORUN: Gereksiz araç artışı
```

### pso_strategy.py Mevcut Yapı

```python
# SATIR 323-443: PSOStrategy.optimize()
def optimize(self, request: OptimizationRequest) -> OptimizationResponse:
    # ...
    # SORUN: VehicleCalculator kullanılıyor
    calculator = VehicleCalculator(
        sw_capacity=request.sw_capacity,
        so_capacity=request.so_capacity,
        max_tour_time=request.max_travel_time
    )
    # ...
    result = calculator.calculate(student_dicts, route_optimizer)
```

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**İletişim:** [Proje Repository]
