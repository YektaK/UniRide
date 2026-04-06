# UniRide Uygulama Durumu

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi  
> **Sürüm:** 2.0  
> **Son Güncelleme:** 26 Mart 2026

---

## Genel Durum

| Bileşen | Durum | İlerleme |
|---------|-------|----------|
| Frontend (Next.js) | ✅ Aktif | 100% |
| Backend API (Next.js) | ✅ Aktif | 100% |
| Python Optimizer | ✅ Aktif | 100% |
| Database (Supabase) | ✅ Aktif | 100% |
| **Split Decoder** | 🔵 Planlanıyor | 0% |
| **Hybrid Strategies** | 🔵 Planlanıyor | 0% |
| **Benchmark Tests** | 🔵 Planlanıyor | 0% |

---

## Algoritma Durumu

### Mevcut Algoritmalar (K-Means + Meta-Heuristic)

| Algoritma | Dosya | Durum | Test |
|-----------|-------|-------|------|
| Genetic Algorithm | `ga_strategy.py` | ✅ Aktif | ✅ Var |
| PSO | `pso_strategy.py` | ✅ Aktif | ✅ Var |
| HHO | `hho_strategy.py` | ✅ Aktif | ✅ Var |
| GWO | `gwo_strategy.py` | ✅ Aktif | ✅ Var |
| OR-Tools | `ortools_cvrp.py` | ✅ Aktif | ✅ Var |
| Greedy | `greedy_heuristic.py` | ✅ Aktif | ✅ Var |
| K-Means TSP | `kmeans_tsp.py` | ✅ Aktif | ✅ Var |
| Permutation TSP | `permutation_tsp.py` | ✅ Aktif | ✅ Var |

### Yeni Algoritmalar (Giant Tour + Split)

| Algoritma | Dosya | Durum | Test |
|-----------|-------|-------|------|
| Split Decoder | `split_decoder.py` | 🔵 Planlanıyor | ⬜ Yok |
| Hybrid Base | `hybrid_base_strategy.py` | 🔵 Planlanıyor | ⬜ Yok |
| PSO-Split | `pso_split_strategy.py` | 🔵 Planlanıyor | ⬜ Yok |
| HHO-Split | `hho_split_strategy.py` | 🔵 Planlanıyor | ⬜ Yok |
| GWO-Split | `gwo_split_strategy.py` | 🔵 Planlanıyor | ⬜ Yok |
| GA-Split | `ga_split_strategy.py` | 🔵 Planlanıyor | ⬜ Yok |
| Local Search | `local_search.py` | 🔄 Mevcut/Genişletilecek | ✅ Var |

---

## Dosya Yapısı

### Mevcut Yapı

```
optimizer_api/
├── main.py                          ✅ Aktif
├── requirements.txt                 ✅ Aktif
├── models/
│   └── schemas.py                   ✅ Aktif
├── strategies/
│   ├── __init__.py                  ✅ Aktif
│   ├── base_strategy.py             ✅ Aktif
│   ├── ga_strategy.py               ✅ Aktif
│   ├── pso_strategy.py              ✅ Aktif
│   ├── hho_strategy.py              ✅ Aktif
│   ├── gwo_strategy.py              ✅ Aktif
│   ├── ortools_cvrp.py              ✅ Aktif
│   ├── greedy_heuristic.py          ✅ Aktif
│   ├── kmeans_tsp.py                ✅ Aktif
│   └── permutation_tsp.py           ✅ Aktif
└── utils/
    ├── data_loader.py               ✅ Aktif
    ├── clustering.py                ✅ Aktif
    └── local_search.py              ✅ Aktif
```

### Hedef Yapı

```
optimizer_api/
├── main.py                          ✅
├── requirements.txt                 ✅
├── models/
│   └── schemas.py                   ✅
├── strategies/
│   ├── __init__.py                  🔄 Güncellenecek
│   ├── base_strategy.py             ✅
│   ├── hybrid_base_strategy.py      🔵 YENİ
│   ├── ga_strategy.py               ✅ (opsiyonel)
│   ├── pso_strategy.py              ✅ (opsiyonel)
│   ├── hho_strategy.py              ✅ (opsiyonel)
│   ├── gwo_strategy.py              ✅ (opsiyonel)
│   ├── ga_split_strategy.py         🔵 YENİ
│   ├── pso_split_strategy.py        🔵 YENİ
│   ├── hho_split_strategy.py        🔵 YENİ
│   ├── gwo_split_strategy.py        🔵 YENİ
│   ├── ortools_cvrp.py              ✅
│   ├── greedy_heuristic.py          ✅
│   ├── kmeans_tsp.py                ✅
│   └── permutation_tsp.py           ✅
└── utils/
    ├── data_loader.py               ✅
    ├── clustering.py                ✅ (opsiyonel)
    ├── split_decoder.py             🔵 YENİ
    └── local_search.py              🔄 Genişletilecek
```

---

## Test Durumu

### Unit Tests

| Test Dosyası | Durum | Coverage |
|--------------|-------|----------|
| `test_strategies.py` | ✅ Aktif | Temel testler |
| `test_api.py` | ✅ Aktif | API testleri |
| `test_comparison.py` | ✅ Aktif | Karşılaştırma |
| `test_split_decoder.py` | 🔵 Planlanıyor | - |
| `test_hybrid_strategies.py` | 🔵 Planlanıyor | - |

### Integration Tests

| Senaryo | Durum |
|---------|-------|
| API → Python | ✅ Aktif |
| Database → Python | ✅ Aktif |
| Frontend → Backend | ✅ Aktif |
| Split Pipeline | 🔵 Planlanıyor |

### Benchmark Tests

| Senaryo | N | Durum |
|---------|---|-------|
| Small | 30 | 🔵 Planlanıyor |
| Medium | 100 | 🔵 Planlanıyor |
| Large | 300 | 🔵 Planlanıyor |
| Comparison | 30-300 | 🔵 Planlanıyor |

---

## Performans Metrikleri

### Mevcut Performans (N=30)

| Algoritma | Ort. Araç | Ort. Süre (dk) | Exec Time (s) |
|-----------|-----------|----------------|---------------|
| GA | 8 | 85 | 2.3 |
| PSO | 7 | 82 | 1.8 |
| HHO | 7 | 80 | 2.1 |
| GWO | 7 | 81 | 1.9 |
| OR-Tools | 6 | 75 | 0.5 |

### Hedef Performans (Split Sonrası)

| Algoritma | Ort. Araç | Ort. Süre (dk) | Exec Time (s) |
|-----------|-----------|----------------|---------------|
| GA-Split | 6 | 65 | 2.5 |
| PSO-Split | 5 | 62 | 2.0 |
| HHO-Split | 5 | 60 | 2.3 |
| GWO-Split | 5 | 61 | 2.1 |
| OR-Tools | 6 | 75 | 0.5 |

**İyileştirme Hedefleri:**
- Araç sayısı: %15-20 azalma
- Tur süresi: %20-25 azalma
- Tek öğrencilik rotalar: %75 azalma
- Feasibility: %100

---

## Bilinen Sorunlar

### Kritik (Split ile Çözülecek)

| Sorun | Durum | Çözüm |
|-------|-------|-------|
| K-Means katı kümeleme | 🔵 Çözümde | Split entegrasyonu |
| Time matrix duyarsızlık | 🔵 Çözümde | Split decoder |
| Tek öğrencilik rotalar | 🔵 Çözümde | Optimal split |

### Orta Öncelik

| Sorun | Durum | Açıklama |
|-------|-------|----------|
| Local search genişletme | 🔵 Planlanıyor | 2-opt, Or-opt |
| Benchmark eksik | 🔵 Planlanıyor | Performans testleri |
| Dokümantasyon | 🔄 Güncelleniyor | Bu dosyalar |

### Düşük Öncelik

| Sorun | Durum | Açıklama |
|-------|-------|----------|
| Eski stratejiler | ⬜ Bekliyor | Opsiyonel tutulacak |
| PyVRP entegrasyonu | ⬜ İleride | Alternatif çözücü |

---

## Yapılacaklar (To-Do)

### Bu Sprint

- [ ] `split_decoder.py` implementasyonu
- [ ] `hybrid_base_strategy.py` implementasyonu
- [ ] `pso_split_strategy.py` implementasyonu
- [ ] Unit testler

### Sonraki Sprint

- [ ] `hho_split_strategy.py`
- [ ] `gwo_split_strategy.py`
- [ ] `ga_split_strategy.py`
- [ ] Local search genişletme

### İleriki Sprint

- [ ] Benchmark testleri
- [ ] Frontend güncellemesi
- [ ] Dokümantasyon tamamlama

---

## Değişiklik Geçmişi

| Tarih | Değişiklik |
|-------|------------|
| 26.03.2026 | Split entegrasyonu planlaması |
| 25.03.2026 | ROADMAP.md güncellemesi |
| 24.03.2026 | Faz 1 tamamlandı |

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi  
**Son Güncelleme:** 26 Mart 2026
