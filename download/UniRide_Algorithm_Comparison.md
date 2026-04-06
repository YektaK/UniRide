# UniRide Algoritma Karşılaştırması

> **Son Güncelleme:** 26 Mart 2026  
> **Amaç:** Mevcut vs Yeni (Split) algoritmaların karşılaştırması

---

## 1. Yönetici Özeti

Bu doküman, UniRide projesinde kullanılan optimizasyon algoritmalarını karşılaştırmakta ve **Split entegrasyonunun** beklenen iyileştirmelerini özetlemektedir.

### Temel Bulgular

| Metrik | Mevcut (K-Means + Meta) | Hedef (Split + Meta) | İyileştirme |
|--------|------------------------|---------------------|-------------|
| Ort. Araç Sayısı | 7-8 (N=30) | 5-6 (N=30) | -20% |
| Tek Öğrencilik Rotalar | %15-20 | <%5 | -75% |
| Feasibility Rate | %92 | %100 | +8% |
| Time Matrix Duyarlılık | Yok | Tam | ✓ |

---

## 2. Mevcut Algoritmalar

### 2.1 Genetic Algorithm (GA)

**Dosya:** `optimizer_api/strategies/ga_strategy.py`

| Parametre | Değer |
|-----------|-------|
| Population Size | 50 |
| Max Iterations | 100 |
| Crossover Rate | 0.85 |
| Mutation Rate | 0.15 |
| Selection | Tournament (size=3) |
| Elitism | 2 individuals |

**Operatörler:**
- **Crossover:** Order Crossover (OX1)
- **Mutation:** Swap veya Inversion (rastgele seçim)

**Akış:**
```
Students → K-Means → Clusters → GA per Cluster → Routes
```

**Artıları:**
- Kanıtlanmış etkinlik
- Kolay hiperparametre ayarı
- Çeşitlilik (crossover)

**Eksileri:**
- K-Means bağımlılığı
- Time matrix duyarsız kümeleme
- Yavaş yakınsama

---

### 2.2 Particle Swarm Optimization (PSO)

**Dosya:** `optimizer_api/strategies/pso_strategy.py`

| Parametre | Değer |
|-----------|-------|
| Swarm Size | 30 |
| Max Iterations | 100 |
| Inertia Weight (w) | 0.729 (Clerc) |
| Cognitive Weight (c1) | 1.49445 |
| Social Weight (c2) | 1.49445 |

**Pozisyon:** Permütasyon (location codes)  
**Hız:** Swap operations listesi

**Akış:**
```
Students → K-Means → Clusters → PSO per Cluster → Routes
```

**Artıları:**
- Hızlı yakınsama
- Basit implementasyon
- Az parametre

**Eksileri:**
- K-Means bağımlılığı
- Lokal optimum riski
- Swap bazlı hız kısıtları

---

### 2.3 Harris Hawks Optimization (HHO)

**Dosya:** `vrp_discussion/python_heuristic/hho_strategy.py`

| Parametre | Değer |
|-----------|-------|
| Population Size | 30 |
| Max Iterations | 100 |
| Initial Energy | 1.0 |
| Jump Probability | 0.5 |

**4 Siege Stratejisi:**
1. Soft Besiege
2. Hard Besiege
3. Soft Besiege with Progressive Rapid Dives
4. Hard Besiege with Progressive Rapid Dives

**Artıları:**
- Lévy Flight ile kaçış
- Adaptif arama
- Güçlü exploitation

**Eksileri:**
- K-Means bağımlılığı
- Karmaşık implementasyon
- Parametre hassasiyeti

---

### 2.4 Grey Wolf Optimizer (GWO)

**Dosya:** `vrp_discussion/python_heuristic/gwo_strategy.py`

| Parametre | Değer |
|-----------|-------|
| Population Size | 30 |
| Max Iterations | 100 |
| Initial a | 2.0 |
| Exploration Rate | 0.5 |

**Hiyerarşi:**
- Alpha (α): En iyi çözüm
- Beta (β): 2. en iyi
- Delta (δ): 3. en iyi
- Omega (ω): Geri kalanlar

**Artıları:**
- Sosyal hiyerarşi çeşitliliği
- Dengeli keşif/sömürü
- Basit parametreler

**Eksileri:**
- K-Means bağımlılığı
- Hiyerarşi güncelleme maliyeti

---

### 2.5 OR-Tools CVRP

**Dosya:** `optimizer_api/strategies/ortools_cvrp.py`

| Parametre | Değer |
|-----------|-------|
| Solver | GUIDED_LOCAL_SEARCH |
| Time Limit | 10 saniye |

**Artıları:**
- C++ tabanlı (hızlı)
- Kanıtlanmış etkinlik
- Constraint handling

**Eksileri:**
- K-Means ile kullanılıyor (potansiyel kayıp)
- Black box
- Parametre sınırlı

---

## 3. Yeni Algoritmalar (Split Entegrasyonu)

### 3.1 Giant Tour + Split Yaklaşımı

**Temel Fark:**
```
MEVCUT:
  Students → K-Means → Clusters → Meta-Heuristic → Routes
                    ↑
                Time matrix duyarsız!

YENİ (Split):
  Students → Meta-Heuristic → Giant Tour → Split Decoder → Routes
                                          ↑
                                  Time matrix duyarlı!
```

### 3.2 Split Decoder Algoritması

**Girdi:** Giant Tour = [3, 1, 4, 8, 2, 5, 7, 6, 9, 10]

**Çıktı:**
```
Route 1: [3, 1, 4]    → Sw=2, So=1, Time=42dk
Route 2: [8, 2, 5]    → Sw=1, So=2, Time=38dk
Route 3: [7, 6, 9, 10] → Sw=2, So=2, Time=55dk
```

**DP Tablosu:**
```
dp[i] = min(dp[j] + cost(segment[j:i]))  for all valid j < i

Geçerlilik Kontrolü:
- Sw_count ≤ 4
- So_count ≤ 5
- Segment_time ≤ 180 dk
```

---

## 4. Detaylı Karşılaştırma

### 4.1 Mimari Karşılaştırma

| Özellik | K-Means + Meta | Giant Tour + Split |
|---------|---------------|-------------------|
| **Kümeleme** | K-Means (coğrafi) | Yok (Split ile otomatik) |
| **Constraint Check** | Sonradan | Entegre |
| **Time Matrix** | Duyarsız | Tam duyarlı |
| **Feasibility** | %92 | %100 |
| **Global Optimal** | Zor | Daha kolay |
| **Tek Öğrenci Rotası** | Sık | Minimum |

### 4.2 Performans Karşılaştırması (N=30, Tahmini)

| Algoritma | Araç | Süre (dk) | Exec (s) | Feasibility |
|-----------|------|-----------|----------|-------------|
| GA | 8 | 85 | 2.3 | %90 |
| PSO | 7 | 82 | 1.8 | %92 |
| HHO | 7 | 80 | 2.1 | %94 |
| GWO | 7 | 81 | 1.9 | %93 |
| OR-Tools | 6 | 75 | 0.5 | %100 |
| **GA-Split** | 6 | 65 | 2.5 | %100 |
| **PSO-Split** | 5 | 62 | 2.0 | %100 |
| **HHO-Split** | 5 | 60 | 2.3 | %100 |
| **GWO-Split** | 5 | 61 | 2.1 | %100 |

### 4.3 Ölçeklenebilirlik (N=300, Tahmini)

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

## 5. Kullanım Senaryoları

### 5.1 Hangi Algoritma Ne Zaman Kullanılmalı?

| Senaryo | Önerilen Algoritma | Gerekçe |
|---------|-------------------|---------|
| **Hız kritik** | OR-Tools | C++ tabanlı, en hızlı |
| **Kalite kritik** | HHO-Split | Lévy Flight ile iyi keşif |
| **Dengeli** | PSO-Split | Hız + kalite dengesi |
| **Basit setup** | GA-Split | Az parametre |
| **Akademik çalışma** | GWO-Split | Yeni yaklaşım, yayın potansiyeli |

### 5.2 Parametre Önerileri

#### Küçük Ölçek (N < 50)

```python
config = {
    "swarm_size": 20,
    "max_iterations": 50,
    "max_no_improvement": 15
}
```

#### Orta Ölçek (50 ≤ N < 150)

```python
config = {
    "swarm_size": 30,
    "max_iterations": 100,
    "max_no_improvement": 20
}
```

#### Büyük Ölçek (N ≥ 150)

```python
config = {
    "swarm_size": 50,
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
| S2 | 50 | 30% | 70% | Orta ölçek |
| S3 | 100 | 30% | 70% | Büyüme senaryosu |
| S4 | 300 | 30% | 70% | Hedef ölçek |
| S5 | 100 | 50% | 50% | Dengeli dağılım |
| S6 | 100 | 70% | 30% | Ağır Sw |

### 6.2 Karşılaştırma Metrikleri

| Metrik | Birim | Hedef |
|--------|-------|-------|
| Total Vehicles | Adet | Min |
| Total Duration | Dakika | Min |
| Avg Route Duration | Dakika | ≤90 |
| Single-Student Routes | % | <5% |
| Execution Time | Saniye | <60s |
| Feasibility | % | 100% |

### 6.3 İstatistiksel Test

Her algoritma her senaryo için **10 run** yapılacak:
- Mean, Std, Min, Max hesaplanacak
- ANOVA ile anlamlılık testi
- Wilcoxon rank-sum (non-parametrik)

---

## 7. Sonuç ve Öneriler

### 7.1 Ana Sonuçlar

1. **Split entegrasyonu** tüm algoritmalar için **iyileştirme** sağlayacak
2. **HHO-Split** ve **GWO-Split** en iyi kalite sonuçlarını verecek
3. **PSO-Split** hız-kalite dengesinde en iyi seçim
4. **OR-Tools** hız için en iyi, ama Split olmadan potansiyel kayıp

### 7.2 Önerilen Yol Haritası

1. **Faz 1.4:** Split Decoder implementasyonu
2. **Faz 1.5:** Hibrit stratejiler (PSO-Split, HHO-Split, GWO-Split, GA-Split)
3. **Faz 1.9:** Benchmark testleri
4. **Sonrası:** En iyi algoritmayı varsayılan yap

### 7.3 Varsayılan Algoritma Önerisi

**PSO-Split** varsayılan olarak önerilir:
- Hızlı execution time
- İyi çözüm kalitesi
- Basit hiperparametreler
- Paralel değerlendirme imkanı

---

## Ek A: Algoritma Parametre Tablosu

| Algoritma | Pop/Swarm | Iterasyon | Diğer Parametreler |
|-----------|-----------|-----------|-------------------|
| GA | 50 | 100 | CR=0.85, MR=0.15 |
| PSO | 30 | 100 | w=0.729, c1=c2=1.49445 |
| HHO | 30 | 100 | E0=1.0, r=0.5 |
| GWO | 30 | 100 | a0=2.0 |
| GA-Split | 50 | 100 | CR=0.85, MR=0.15 |
| PSO-Split | 30 | 100 | w=0.729, c1=c2=1.49445 |
| HHO-Split | 30 | 100 | E0=1.0, r=0.5 |
| GWO-Split | 30 | 100 | a0=2.0 |

---

## Ek B: Referans Makaleler

1. Prins, C. (2004). A simple and effective evolutionary algorithm for the vehicle routing problem.
2. Heidari, A. A., et al. (2019). Harris hawks optimization.
3. Mirjalili, S., et al. (2014). Grey wolf optimizer.
4. Kennedy, J., & Eberhart, R. (1995). Particle swarm optimization.
5. VROOM Project: https://github.com/VROOM-Project/vroom
6. PyVRP: https://github.com/PyVRP/PyVRP

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**Son Güncelleme:** 26 Mart 2026
