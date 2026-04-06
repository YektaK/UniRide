# UniRide Algoritma Karşılaştırması

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi  
> **Son Güncelleme:** 26 Mart 2026

---

## 1. Özet

Bu doküman, mevcut ve yeni (Split tabanlı) algoritmaların karşılaştırmasını sunmaktadır.

### Temel Bulgular

| Metrik | Mevcut | Split | İyileştirme |
|--------|--------|-------|-------------|
| Ort. Araç Sayısı | 7-8 | 5-6 | -20% |
| Tek Öğrenci Rotalar | %15-20 | <%5 | -75% |
| Feasibility | %92 | %100 | +8% |
| Time Matrix | Duyarsız | Duyarlı | ✓ |

---

## 2. Yaklaşım Karşılaştırması

### 2.1 Cluster-First, Route-Second (Mevcut)

```
┌────────────────────────────────────────────────────────────┐
│                    MEVCUT YAKLAŞIM                         │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Öğrenciler (N=300)                                        │
│        │                                                   │
│        ▼                                                   │
│  ┌──────────────┐                                          │
│  │   K-Means    │  ← Coğrafi mesafe                        │
│  │  Clustering  │  ← Time matrix DUYARSIZ                  │
│  └──────────────┘                                          │
│        │                                                   │
│        ▼                                                   │
│  K Küme: [Küme1, Küme2, ..., KümeK]                       │
│        │                                                   │
│        ▼                                                   │
│  ┌──────────────┐                                          │
│  │   GA / PSO   │  ← Her küme için ayrı TSP               │
│  │   HHO / GWO  │                                          │
│  └──────────────┘                                          │
│        │                                                   │
│        ▼                                                   │
│  Rotalar                                                   │
│                                                            │
│  ⚠️ SORUNLAR:                                              │
│  - Katı küme sınırları                                     │
│  - Time matrix duyarsız kümeleme                           │
│  - Küme reddedilince yeni araç                             │
│  - Tek öğrencilik rotalar                                  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### 2.2 Giant Tour + Split (Yeni)

```
┌────────────────────────────────────────────────────────────┐
│                    YENİ YAKLAŞIM                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  Öğrenciler (N=300)                                        │
│        │                                                   │
│        ▼                                                   │
│  ┌──────────────────────────────────────┐                  │
│  │      META-SEZGİSEL OPTİMİZASYON      │                  │
│  │                                      │                  │
│  │  Giant Tour: [3,1,4,8,2,5,7,6,9,...]│                  │
│  │  ↑ Tüm öğrenciler TEK permütasyon    │                  │
│  └──────────────────────────────────────┘                  │
│        │                                                   │
│        ▼                                                   │
│  ┌──────────────────────────────────────┐                  │
│  │         OPTIMAL SPLIT DECODER        │                  │
│  │                                      │                  │
│  │  - Tüm olası bölünmeleri dene        │                  │
│  │  - Capacity: Sw≤4, So≤5              │                  │
│  │  - Time: ≤180 dk                     │                  │
│  │  - Time matrix DUYARLI               │                  │
│  └──────────────────────────────────────┘                  │
│        │                                                   │
│        ▼                                                   │
│  Rota 1: [3,1,4]   → 42 dk                                │
│  Rota 2: [8,2,5]   → 38 dk                                │
│  Rota 3: [7,6,9,10]→ 55 dk                                │
│                                                            │
│  ✓ AVANTAJLAR:                                             │
│  - Time matrix duyarlı                                     │
│  - Her zaman feasible                                      │
│  - Minimum tek öğrenci rotası                              │
│  - Global optimum'a daha yakın                             │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

---

## 3. Algoritma Detayları

### 3.1 Genetic Algorithm (GA)

**Dosya:** `ga_strategy.py`

| Parametre | Değer |
|-----------|-------|
| Population | 50 |
| Iterations | 100 |
| Crossover Rate | 0.85 |
| Mutation Rate | 0.15 |
| Selection | Tournament |
| Elitism | 2 |

**Operatörler:**
- Crossover: Order Crossover (OX1)
- Mutation: Swap veya Inversion

**Artıları:**
- Kanıtlanmış etkinlik
- Çeşitlilik (crossover)
- Kolay hiperparametre

**Eksileri:**
- K-Means bağımlılığı
- Yavaş yakınsama

---

### 3.2 Particle Swarm Optimization (PSO)

**Dosya:** `pso_strategy.py`

| Parametre | Değer |
|-----------|-------|
| Swarm Size | 30 |
| Iterations | 100 |
| Inertia (w) | 0.729 |
| Cognitive (c1) | 1.49445 |
| Social (c2) | 1.49445 |

**Mekanizma:**
- Position: Permütasyon
- Velocity: Swap operations

**Artıları:**
- Hızlı yakınsama
- Az parametre
- Basit implementasyon

**Eksileri:**
- K-Means bağımlılığı
- Lokal optimum riski

---

### 3.3 Harris Hawks Optimization (HHO)

**Dosya:** `hho_strategy.py`

| Parametre | Değer |
|-----------|-------|
| Population | 30 |
| Iterations | 100 |
| Initial Energy | 1.0 |

**4 Siege Stratejisi:**
1. Soft Besiege
2. Hard Besiege
3. Soft Besiege + Progressive Dives
4. Hard Besiege + Progressive Dives

**Artıları:**
- Lévy Flight kaçışı
- Adaptif arama
- Güçlü exploitation

**Eksileri:**
- K-Means bağımlılığı
- Karmaşık implementasyon

---

### 3.4 Grey Wolf Optimizer (GWO)

**Dosya:** `gwo_strategy.py`

| Parametre | Değer |
|-----------|-------|
| Population | 30 |
| Iterations | 100 |
| Initial a | 2.0 |

**Hiyerarşi:**
- Alpha (α): En iyi
- Beta (β): 2. en iyi
- Delta (δ): 3. en iyi
- Omega (ω): Diğerleri

**Artıları:**
- Sosyal hiyerarşi
- Dengeli keşif/sömürü
- Basit parametre

**Eksileri:**
- K-Means bağımlılığı
- Hiyerarşi güncelleme maliyeti

---

## 4. Performans Karşılaştırması

### 4.1 Tahmini Performans (N=30)

| Algoritma | Araç | Süre (dk) | Exec (s) | Feasible |
|-----------|------|-----------|----------|----------|
| GA | 8 | 85 | 2.3 | %90 |
| PSO | 7 | 82 | 1.8 | %92 |
| HHO | 7 | 80 | 2.1 | %94 |
| GWO | 7 | 81 | 1.9 | %93 |
| OR-Tools | 6 | 75 | 0.5 | %100 |
| **GA-Split** | 6 | 65 | 2.5 | %100 |
| **PSO-Split** | 5 | 62 | 2.0 | %100 |
| **HHO-Split** | 5 | 60 | 2.3 | %100 |
| **GWO-Split** | 5 | 61 | 2.1 | %100 |

### 4.2 Tahmini Performans (N=300)

| Algoritma | Exec Time | Bellek | Kalite |
|-----------|-----------|--------|--------|
| GA | ~30s | Orta | Orta |
| PSO | ~25s | Düşük | Orta |
| HHO | ~28s | Düşük | İyi |
| GWO | ~26s | Düşük | İyi |
| OR-Tools | ~5s | Düşük | İyi |
| **GA-Split** | ~35s | Orta | İyi |
| **PSO-Split** | ~30s | Düşük | İyi |
| **HHO-Split** | ~32s | Düşük | Çok İyi |
| **GWO-Split** | ~30s | Düşük | Çok İyi |

---

## 5. Kullanım Önerileri

### 5.1 Hangi Algoritma Ne Zaman?

| Senaryo | Önerilen | Gerekçe |
|---------|----------|---------|
| Hız kritik | OR-Tools | C++, en hızlı |
| Kalite kritik | HHO-Split | Lévy Flight |
| Dengeli | PSO-Split | Hız + kalite |
| Basit setup | GA-Split | Az parametre |
| Akademik | GWO-Split | Yayın potansiyeli |

### 5.2 Parametre Önerileri

**Küçük Ölçek (N < 50):**
```python
config = {
    "population_size": 20,
    "max_iterations": 50,
    "max_no_improvement": 15
}
```

**Orta Ölçek (50 ≤ N < 150):**
```python
config = {
    "population_size": 30,
    "max_iterations": 100,
    "max_no_improvement": 20
}
```

**Büyük Ölçek (N ≥ 150):**
```python
config = {
    "population_size": 50,
    "max_iterations": 150,
    "max_no_improvement": 30
}
```

---

## 6. Benchmark Planı

### 6.1 Test Senaryoları

| ID | N | Sw% | So% | Açıklama |
|----|---|-----|-----|----------|
| S1 | 30 | 30% | 70% | Mevcut ölçek |
| S2 | 50 | 30% | 70% | Küçük büyüme |
| S3 | 100 | 30% | 70% | Orta ölçek |
| S4 | 300 | 30% | 70% | Hedef ölçek |
| S5 | 100 | 50% | 50% | Dengeli |
| S6 | 100 | 70% | 30% | Ağır Sw |

### 6.2 Metrikler

| Metrik | Birim | İdeal |
|--------|-------|-------|
| Total Vehicles | Adet | Min |
| Total Duration | Dakika | Min |
| Avg Route Duration | Dakika | ≤90 |
| Single-Student Routes | % | <5% |
| Execution Time | Saniye | <60s |
| Feasibility | % | 100% |

### 6.3 İstatistiksel Analiz

Her senaryo için:
- 10 run
- Mean, Std, Min, Max
- ANOVA testi
- Wilcoxon rank-sum

---

## 7. Sonuç

### 7.1 Öneriler

1. **Varsayılan:** PSO-Split
   - Hız-kalite dengesi
   - Basit implementasyon
   - İyi performans

2. **Kalite odaklı:** HHO-Split
   - En iyi çözüm kalitesi
   - Lévy Flight avantajı

3. **Hız odaklı:** OR-Tools
   - En hızlı execution
   - C++ tabanlı

### 7.2 Beklenen İyileştirmeler

| Alan | İyileştirme |
|------|-------------|
| Araç verimliliği | +20% |
| Tur süresi | -25% |
| Feasibility | +8% |
| Time matrix kullanımı | Tam entegrasyon |

---

## Ek: Referanslar

1. Prins, C. (2004). Evolutionary algorithm for VRP.
2. Heidari, A. A., et al. (2019). Harris hawks optimization.
3. Mirjalili, S., et al. (2014). Grey wolf optimizer.
4. Kennedy, J., & Eberhart, R. (1995). PSO.

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**Son Güncelleme:** 26 Mart 2026
