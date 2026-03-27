# 🚐 UniRide VRP Optimizasyon — Geliştirici Tartışma Paketi

> **Son Güncelleme:** 26 Mart 2026  
> **Proje:** Engelli Öğrenci Kampüs Taşımacılığı (CVRPTW)  
> **Amaç:** Bu paketi inceleyen geliştiricilerin mevcut mimariyi anlaması ve Faz 1.5 implementasyonuna katkı sağlaması

---

## 📋 İçindekiler

```
dev_discussion_package/
├── README.md                          ← Bu dosya
├── docs/
│   ├── ARCHITECTURE.md                ← Çift pipeline mimarisi, kısıt tablosu
│   ├── ALGORITHM_COMPARISON.md        ← Tüm algoritmaların karşılaştırması
│   └── ANALYSIS.md                    ← Mevcut durum analizi, tespit edilen sorunlar
└── code/
    ├── strategies/
    │   ├── __init__.py                ← Strategy Registry (mevcut)
    │   ├── base_strategy.py           ← Abstract base class (tüm algoritmalar bunu türetir)
    │   ├── ga_strategy.py             ← Genetik Algoritma (Pipeline A örneği)
    │   ├── pso_strategy.py            ← PSO (Pipeline A örneği)
    │   ├── hho_strategy.py            ← Harris Hawks (Pipeline A örneği)
    │   ├── gwo_strategy.py            ← Grey Wolf (Pipeline A örneği)
    │   └── ortools_cvrp.py            ← OR-Tools (bağımsız çözücü örneği)
    ├── models/
    │   └── schemas.py                 ← Pydantic request/response modelleri
    └── utils/
        ├── clustering.py              ← ⚠️ SORUNLU K-Means kümeleme (değiştirilecek)
        ├── data_loader.py             ← Supabase time_matrix yükleme
        └── local_search.py            ← 2-opt, 3-opt, Or-opt
```

---

## 🎯 Problem Tanımı

**Heterojen CVRPTW** (Capacitated Vehicle Routing Problem with Time Windows):
- **N** engelli öğrenci kampüse taşınacak
- Her araç: Sw (tekerlekli sandalye) ≤ 4, So (diğer) ≤ 5, toplam ≤ 9
- Her rota süresi ≤ 120 dakika
- Gerçek yol süreleri `time_matrix` tablosundan (812 edge, 29 node)
- **Hedef:** Minimum araç sayısı + minimum toplam süre

### Mevcut Sorun

Mevcut sistem K-Means ile kümeleme yapıp, süre kısıtı aşıldığında araç sayısını +1 artırarak **%15-20 oranında tek öğrencilik verimsiz rotalar** oluşturuyor:

```python
# clustering.py - SORUNLU BÖLÜM
for attempt in range(max_attempts):
    clusters = self.cluster_students(points, num_vehicles)
    if route_duration > self.max_tour_time:
        valid = False
        break                   # ← KÜMEYİ TAMAMEN REDDEDİYOR!
    num_vehicles += 1           # ← +1 ARAÇ AÇIYOR! (genellikle 1 öğrencilik)
```

---

## 🏗️ Önerilen Çift Pipeline Mimarisi

### Pipeline A: Cluster-First, Route-Second
```
Öğrenciler → Sweep / Clarke-Wright → Akıllı Kümeler → GA/PSO/HHO (küme-içi TSP) → Rotalar
```
- K-Means yerine **time matrix duyarlı** kümeleme (Sweep/Clarke-Wright)
- Her küme küçük olduğu için sezgisel hızlı çalışır
- **N > 50** senaryoları için önerilir

### Pipeline B: Route-First, Cluster-Second
```
Öğrenciler → GA/PSO/HHO (Giant Tour) → Split Decoder (DP) → Rotalar
```
- Prins (2004) referansı
- Dinamik Programlama ile %100 feasible bölme
- **N ≤ 50** senaryoları için önerilir

### Bağımsız Çözücüler
| Çözücü | Motor | Avantaj |
|--------|-------|---------|
| OR-Tools | C++ (Google) | Endüstri standardı |
| **PyVRP** | C++ + Python (HGS) | DIMACS 2021 birincisi, heterojen fleet |
| **VROOM** | C++ (pyvroom) | Ultra-hızlı, 1000+ nokta < 5s |

---

## 🔧 Kodlama Kuralları

### Yeni Algoritma Ekleme (3 Adım)

```
1. optimizer_api/strategies/ altına yeni_strategy.py oluştur
   → BaseRoutingStrategy'den türet (base_strategy.py'ye bak)
   → optimize(request) metodunu implement et

2. optimizer_api/strategies/__init__.py → STRATEGY_REGISTRY'ye kaydet

3. src/lib/algorithm-constants.ts → ALGORITHM_OPTIONS'a ekle
   (Bu dosya bu pakette yok, UI tarafıdır)
```

### Kısıt Referans Tablosu

| Kısıt | Değişken | Varsayılan |
|-------|----------|-----------|
| Sw Kapasitesi | `sw_capacity` | **4** |
| So Kapasitesi | `so_capacity` | **5** |
| Toplam Kapasite | `sw + so` | **≤ 9** |
| Max Tur Süresi | `max_tour_time` | **120 dk** |

### DP Formülasyonu Uyarısı

Split Decoder yazarken **Sw ve So kısıtları AND olarak kontrol edilmelidir:**
```python
if sw_count > SW_CAP or so_count > SO_CAP or (sw_count + so_count) > 9:
    break  # Bu alt rota geçersiz
```

---

## 📊 İmplementasyon Durumu

| Görev | Durum | Dosya |
|-------|-------|-------|
| Split Decoder (DP) | ⬜ Bekliyor | `utils/split_decoder.py` |
| Hybrid Base Strategy | ⬜ Bekliyor | `strategies/hybrid_base_strategy.py` |
| PSO-Split | ⬜ Bekliyor | `strategies/pso_split_strategy.py` |
| HHO-Split | ⬜ Bekliyor | `strategies/hho_split_strategy.py` |
| GWO-Split | ⬜ Bekliyor | `strategies/gwo_split_strategy.py` |
| GA-Split | ⬜ Bekliyor | `strategies/ga_split_strategy.py` |
| PyVRP Entegrasyonu | ⬜ Bekliyor | `strategies/pyvrp_strategy.py` |
| VROOM Entegrasyonu | ⬜ Bekliyor | `strategies/vroom_strategy.py` |
| Kümelemeyi Sweep/CW'ye çevir | ⬜ Bekliyor | `utils/clustering.py` |
| Benchmark Testleri | ⬜ Bekliyor | `tests/benchmark_split.py` |

---

## 📖 Detaylı Dokümanlar

- **[ARCHITECTURE.md](./docs/ARCHITECTURE.md)** — Çift pipeline diyagramları, kısıt tablosu, dosya haritası
- **[ALGORITHM_COMPARISON.md](./docs/ALGORITHM_COMPARISON.md)** — Performans karşılaştırması, öneriler  
- **[ANALYSIS.md](./docs/ANALYSIS.md)** — Mevcut durum, sorunlar, ölçeklenebilirlik

---

## 📚 Akademik Referanslar

1. Prins, C. (2004). A simple and effective evolutionary algorithm for VRP.
2. Vidal, T. (2022). Hybrid genetic search for the CVRP — PyVRP.
3. Heidari, A. A., et al. (2019). Harris hawks optimization.
4. Mirjalili, S., et al. (2014). Grey wolf optimizer.
5. Kennedy, J., & Eberhart, R. (1995). PSO.

---

## ❓ Tartışma Soruları

1. **Split Decoder:** DP formülasyonunda heterojen kapasite (Sw ≠ So) nasıl optimize edilmeli?
2. **Pipeline Seçimi:** N=50-100 arası hangi pipeline daha iyi sonuç verir?
3. **PyVRP vs VROOM:** Hangisi bizim problem yapımıza (heterojen fleet + TW) daha uygun?
4. **Ölçeklenebilirlik:** N=300+ için ek optimizasyonlar neler olabilir?
5. **Local Search:** Split sonrası her alt rotaya 2-opt mu, Or-opt mu daha etkili?

---

> ⚠️ **Güvenlik Notu:** Bu paket yalnızca optimizasyon algoritmaları ve ilgili yapıları içerir. Veritabanı bağlantıları, kullanıcı bilgileri, API anahtarları veya proje genelindeki diğer dosyalar dahil edilmemiştir.
