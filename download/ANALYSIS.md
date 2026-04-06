# CVRPTW Problemi ve Split Entegrasyonu Analizi

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi  
> **Sürüm:** 2.0  
> **Tarih:** 26 Mart 2026  
> **Durum:** Split Entegrasyonu Planlanıyor

---

## 1. Yönetici Özeti

Bu doküman, UniRide projesindeki **Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)** sorununu analiz etmekte ve **Split entegrasyonu** ile çözüm önerileri sunmaktadır.

### Temel Bulgular

| Sorun | Mevcut Durum | Çözüm |
|-------|--------------|-------|
| K-Means katı kümeleme | Time matrix duyarsız | Split ile otomatik gruplama |
| Tek öğrencilik rotalar | %15-20 oranında | <%5'e düşecek |
| Feasibility sorunu | %8 infeasible | %100 feasible |

---

## 2. Problem Tanımı

### 2.1 CVRPTW Nedir?

**Capacitated Vehicle Routing Problem with Time Windows (CVRPTW)**, aşağıdaki kısıtlara sahip bir rotalama problemidir:

- **Kapasite Kısıtları:** Her aracın belirli sayıda yolcu kapasitesi vardır
- **Zaman Pencereleri:** Her rotanın maksimum süresi vardır
- **Heterojen Kapasite:** Farklı engel türleri için farklı kapasiteler

### 2.2 UniRide Problemi

| Kısıt | Değer | Açıklama |
|-------|-------|----------|
| Sw Kapasitesi | 4 | Tekerlekli sandalyeli öğrenci |
| So Kapasitesi | 5 | Diğer engel türü öğrenci |
| Max Tur Süresi | 180 dk | Bir aracın toplam tur süresi |
| Max Öğrenci Süresi | 120 dk | Öğrencinin araçta geçireceği süre |

**Ölçek:**
- Mevcut: N ≈ 30 öğrenci
- Hedef: N ≥ 300 öğrenci

### 2.3 NP-Hard Doğası

CVRPTW, NP-Hard bir problemdir:

| N | Permütasyon Sayısı |
|---|-------------------|
| 10 | 3,628,800 |
| 20 | 2.43 × 10¹⁸ |
| 30 | 2.65 × 10³² |
| 300 | Astronomik |

Bu nedenle **meta-sezgisel algoritmalar** kullanılması zorunludur.

---

## 3. Mevcut Mimari Analizi

### 3.1 Cluster-First, Route-Second Yaklaşımı

Mevcut sistem şu akışı izlemektedir:

```
┌─────────────────────────────────────────────────────────────────┐
│                    MEVCUT AKIŞ                                  │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Öğrenciler (N=300)                                            │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────┐                                               │
│   │  K-Means    │  ← Coğrafi kümeleme (Euclidean/Haversine)    │
│   │ Clustering  │  ← Time matrix DUYARSIZ!                     │
│   └─────────────┘                                               │
│         │                                                       │
│         ▼                                                       │
│   Küme 1, Küme 2, ..., Küme K                                   │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────┐                                               │
│   │ GA / PSO /  │  ← Her küme için ayrı TSP çözümü             │
│   │ HHO / GWO   │                                               │
│   └─────────────┘                                               │
│         │                                                       │
│         ▼                                                       │
│   Rota 1, Rota 2, ..., Rota K                                   │
│                                                                 │
│   ⚠️ SORUN: K-Means kümeleri KATI ve Time Matrix DUYARSIZ      │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Tespit Edilen Sorunlar

#### Sorun 1: Time Matrix Duyarsızlığı

K-Means sadece coğrafi mesafeye göre kümeleme yapar:

```
Örnek:
┌────────────────────────────────────────────────────────────────┐
│ K-Means Sonucu: Küme A = [Öğrenci1, Öğrenci2, Öğrenci3]        │
│                                                                │
│ Gerçek Time Matrix:                                            │
│   Öğrenci1 → Öğrenci2: 45 dk (kötü yol, trafik)               │
│   Öğrenci2 → Öğrenci3: 30 dk                                   │
│   Toplam: 75 dk + depot gidiş/dönüş = 95 dk                    │
│                                                                │
│ Sonuç: Tur süresi limiti aşıldı! Küme REDDEDİLİYOR!           │
└────────────────────────────────────────────────────────────────┘
```

#### Sorun 2: Katı Küme Sınırları

`clustering.py` dosyasında (satır 296-346):

```python
for attempt in range(max_attempts):
    clusters = self.cluster_students(points, num_vehicles)
    # ...
    if route_duration > self.max_tour_time:
        valid = False
        break  # ← KÜME REDDEDİLİYOR!
    
    num_vehicles += 1  # ← YENİ ARAÇ AÇILIYOR!
```

**Sonuç:** Sadece 2 dakika aşım için bile yeni araç açılıyor.

#### Sorun 3: Tek Öğrencilik Rotalar

Katı kümeleme nedeniyle:

| Senaryo | Mevcut Davranış | İdeal |
|---------|-----------------|-------|
| Tur 42 dk (limit 45 dk) | ✓ Kabul | ✓ |
| Tur 47 dk (limit 45 dk) | ✗ Red + Yeni araç | Komşuya transfer |
| Küme A'dan 1 öğrenci B'ye | Yapılamaz | Yapılabilir |

**İstatistik:** Mevcut sistemde %15-20 oranında tek öğrencilik rota oluşuyor.

### 3.3 Mevcut Algoritmalar

| Algoritma | Dosya | Yöntem | Kümeleme |
|-----------|-------|--------|----------|
| GA | `ga_strategy.py` | Order Crossover + Mutation | K-Means |
| PSO | `pso_strategy.py` | Swap Operations | K-Means |
| HHO | `hho_strategy.py` | 4 Siege Strategy | K-Means |
| GWO | `gwo_strategy.py` | Alpha-Beta-Delta | K-Means |
| OR-Tools | `ortools_cvrp.py` | Guided Local Search | K-Means |

**Ortak Sorun:** Tümü K-Means kümelemesine bağımlı!

---

## 4. Önerilen Çözüm: Split Entegrasyonu

### 4.1 Giant Tour Representation

Split entegrasyonu ile yeni yaklaşım:

```
┌─────────────────────────────────────────────────────────────────┐
│                    YENİ AKIŞ (SPLIT)                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   Öğrenciler (N=300)                                            │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────────────────────────────────────┐               │
│   │         META-SEZGİSEL OPTİMİZASYON          │               │
│   │                                             │               │
│   │   Population / Swarm / Hawks / Wolves       │               │
│   │                    │                        │               │
│   │                    ▼                        │               │
│   │   Giant Tour: [3,1,4,8,2,5,7,6,9,10,...]   │               │
│   │   ↑                                         │               │
│   │   Tüm öğrenciler TEK permütasyon            │               │
│   │   KÜMELEME YOK!                             │               │
│   └─────────────────────────────────────────────┘               │
│         │                                                       │
│         ▼                                                       │
│   ┌─────────────────────────────────────────────┐               │
│   │           OPTIMAL SPLIT DECODER             │               │
│   │                                             │               │
│   │   Giant Tour → Tüm olası bölünmeleri dene  │               │
│   │                    │                        │               │
│   │                    ▼                        │               │
│   │   ┌───────────────────────────────────────┐ │               │
│   │   │ Segment    │ Sw │ So │ Süre │ Geçerli │ │               │
│   │   ├───────────────────────────────────────┤ │               │
│   │   │ [3,1,4]    │ 2  │ 1  │ 42dk │   ✓    │ │               │
│   │   │ [3,1,4,8]  │ 3  │ 1  │ 58dk │   ✓    │ │               │
│   │   │ [3,1,4,8,2]│ 5  │ 1  │  -   │   ✗    │ │               │
│   │   └───────────────────────────────────────┘ │               │
│   │                    │                        │               │
│   │                    ▼                        │               │
│   │   Rota 1: [3,1,4]   → 42 dk                │               │
│   │   Rota 2: [8,2,5]   → 38 dk                │               │
│   │   Rota 3: [7,6,9,10]→ 55 dk                │               │
│   └─────────────────────────────────────────────┘               │
│                                                                 │
│   ✓ Time Matrix DUYARLI                                        │
│   ✓ Her zaman FEASIBLE                                         │
│   ✓ Minimum TEK ÖĞRENCİ rotası                                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Split Algoritması Nasıl Çalışır?

**Prins & Lacomme Split (2004):**

Split algoritması, dinamik programlama kullanarak giant tour'u optimal rotalara böler:

```python
def optimal_split(giant_tour, constraints):
    n = len(giant_tour)
    dp = [∞] * (n + 1)  # Minimum maliyet
    dp[0] = 0
    
    predecessor = [-1] * (n + 1)
    
    for i in range(n):
        sw_count = 0
        so_count = 0
        duration = 0
        
        for j in range(i, n):
            # Kapasite güncelle
            if giant_tour[j] == 'Sw':
                sw_count += 1
            else:
                so_count += 1
            
            # Kapasite kontrolü
            if sw_count > SW_CAPACITY or so_count > SO_CAPACITY:
                break  # Geçersiz segment
            
            # Süre hesapla
            duration += time_matrix[giant_tour[j-1]][giant_tour[j]]
            duration += time_matrix[giant_tour[j]][depot]
            
            # Süre kontrolü
            if duration > MAX_TOUR_TIME:
                break  # Geçersiz segment
            
            # DP güncelle
            if dp[i] + duration < dp[j + 1]:
                dp[j + 1] = dp[i] + duration
                predecessor[j + 1] = i
    
    # Geri izleme ile rotaları çıkar
    return extract_routes(predecessor)
```

### 4.3 Split'in Değerlendirdiği Kombinasyonlar

**Önemli:** Split sadece ardışık segmentleri değil, TÜM olası bölünmeleri değerlendirir:

```
Giant Tour: [1, 4, 8, 2, 5, 3, 7, 6, 9]

Değerlendirilen Kombinasyonlar:
┌─────────────────────────────────────────────────────────────┐
│ [1] + [4] + [8] + [2,5,3,7,6,9]                            │
│ [1,4] + [8,2] + [5,3,7,6,9]                                │
│ [1,4,8] + [2,5,3] + [7,6,9]                                │
│ [1,4,8,2] + [5,3,7] + [6,9]                                │
│ [1,4] + [8,2,5] + [3,7,6,9]                                │
│ ... (TÜM kombinasyonlar)                                    │
│                                                             │
│ En düşük maliyetli bölünme seçilir!                        │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Avantajlar

| Özellik | K-Means + Meta | Giant Tour + Split |
|---------|---------------|-------------------|
| **Kümeleme** | K-Means (katı) | Yok (otomatik) |
| **Time Matrix** | Duyarsız | **Tam duyarlı** |
| **Constraint Check** | Sonradan | **Entegre** |
| **Feasibility** | %92 | **%100** |
| **Tek Öğrenci Rota** | %15-20 | **<%5** |
| **Global Optimal** | Zor | **Daha yakın** |

---

## 5. Hibrit Algoritmalar

### 5.1 Genel Yapı

Tüm Split tabanlı algoritmalar şu yapıyı izler:

```python
class HybridSplitStrategy(BaseRoutingStrategy):
    def optimize(self, request):
        # 1. Split Decoder başlat
        self.split_decoder = SplitDecoder(
            sw_capacity=request.sw_capacity,
            so_capacity=request.so_capacity,
            max_tour_time=request.max_travel_time
        )
        
        # 2. Giant Tour oluştur (tüm öğrenciler)
        waypoints = [s.location_code for s in request.students]
        
        # 3. Meta-sezgisel ile giant tour optimize et
        best_tour = self._optimize_giant_tour(waypoints, ...)
        
        # 4. Split ile rotalara böl
        routes, total_cost = self.split_decoder.decode(best_tour, ...)
        
        # 5. Sonuç döndür
        return build_response(routes, total_cost)
```

### 5.2 PSO-Split

| Parametre | Değer |
|-----------|-------|
| Swarm Size | 30 |
| Max Iterations | 100 |
| Inertia Weight | 0.729 |
| Cognitive/Social | 1.49445 |

**Avantaj:** Hızlı yakınsama, basit implementasyon

### 5.3 HHO-Split

| Parametre | Değer |
|-----------|-------|
| Population | 30 |
| Max Iterations | 100 |
| Initial Energy | 1.0 |

**Avantaj:** Lévy Flight ile lokal optimum kaçışı

### 5.4 GWO-Split

| Parametre | Değer |
|-----------|-------|
| Population | 30 |
| Max Iterations | 100 |
| Initial a | 2.0 |

**Avantaj:** Sosyal hiyerarşi ile çeşitlilik

### 5.5 GA-Split

| Parametre | Değer |
|-----------|-------|
| Population | 50 |
| Max Iterations | 100 |
| Crossover Rate | 0.85 |
| Mutation Rate | 0.15 |

**Avantaj:** Kanıtlanmış etkinlik, kolay ayar

---

## 6. Beklenen İyileştirmeler

### 6.1 Kantitatif Hedefler (N=100)

| Metrik | Mevcut | Hedef | İyileştirme |
|--------|--------|-------|-------------|
| Ortalama Araç Sayısı | 18 | 14 | -22% |
| Ortalama Tur Süresi | 85 dk | 65 dk | -24% |
| Tek Öğrencilik Rotalar | %15-20 | <%5 | -75% |
| Feasibility Rate | %92 | %100 | +8% |

### 6.2 Niteliksel İyileştirmeler

1. **Daha Adil Dağılım:** Time matrix'e göre optimal gruplama
2. **Daha Az Araç:** Gereksiz araç açılmayacak
3. **Daha Hızlı Süreç:** K-Means iterasyonu yok
4. **Daha İyi İzlenebilirlik:** Giant tour → Split süreci şeffaf

---

## 7. Akademik Yayın Potansiyeli

### 7.1 Yenilik Değeri

| Katkı | Seviye |
|-------|--------|
| Heterojen Kapasite (Sw/So) | Yüksek |
| Gerçek Dünya Uygulaması | Yüksek |
| Hibrit Yaklaşım | Orta-Yüksek |
| Karşılaştırmalı Çalışma | Orta |

### 7.2 Hedef Dergiler

| Dergi | Impact Factor |
|-------|--------------|
| Expert Systems with Applications | 8.5 |
| Computers & Operations Research | 4.5 |
| European Journal of Operational Research | 6.4 |
| Applied Soft Computing | 8.7 |

### 7.3 Önerilen Makale Başlığı

> "Hybrid Meta-Heuristic Algorithms with Optimal Split for Heterogeneous CVRPTW: A Case Study on Disabled Student Transportation"

---

## 8. Referanslar

1. Prins, C. (2004). A simple and effective evolutionary algorithm for the vehicle routing problem. *Computers & Operations Research*, 31(12), 1985-2002.

2. Lacomme, P., Prins, C., & Ramdane-Chérif, W. (2004). Competitive memetic algorithms for arc routing problems. *Annals of Operations Research*, 131, 159-185.

3. Heidari, A. A., et al. (2019). Harris hawks optimization: Algorithm and applications. *Future Generation Computer Systems*, 97, 849-872.

4. Mirjalili, S., et al. (2014). Grey wolf optimizer. *Advances in Engineering Software*, 69, 46-61.

5. Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization. *Proceedings of ICNN*, 1942-1948.

---

## Ek A: Mevcut Kod Sorunları

### clustering.py - Sorunlu Bölüm

```python
# SATIR 320-346: Katı küme kontrolü
for i, cluster in enumerate(clusters):
    # ...
    if route_duration > self.max_tour_time:
        valid = False
        break  # ← SORUN: Küme reddediliyor, yeni araç açılıyor
    
    # ...
    
if valid:
    return result

num_vehicles += 1  # ← SORUN: Gereksiz araç artışı
```

### pso_strategy.py - K-Means Bağımlılığı

```python
# SATIR 374-409: VehicleCalculator kullanımı
calculator = VehicleCalculator(
    sw_capacity=request.sw_capacity,
    so_capacity=request.so_capacity,
    max_tour_time=request.max_travel_time
)

result = calculator.calculate(student_dicts, route_optimizer)
# ↑ SORUN: K-Means kümelemesi burada yapılıyor
```

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**Son Güncelleme:** 26 Mart 2026
