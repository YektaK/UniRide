# 01 - UniRide SOTA Framework Architecture & Vision

> **Oluşturulma Tarihi:** 01 Nisan 2026, 15:40  
> **Sürüm:** 1.0.0  
> **Konu:** VRP (Araç Rotalama Problemi) Çözücü Motorunun Akademik "State-of-the-Art (SOTA)" Seviyesine Yükseltilmesi

## 1. Vizyon ve Amaç (Vision & Goal)
Mevcut UniRide optimizasyon motoru, kapasite kısıtlı araç rotalama problemini (CVRPTW) PSO, HHO, GWO gibi saf sürü zekası algoritmaları ve $O(N^2)$ zaman karmaşıklığına sahip standart bir Split-Decoder ile çözmektedir.

Planlanan **SOTA (State of the Art) Framework** dönüşümündeki amaç; güncel 2024-2026 VRP akademik makalelerinde kanıtlanmış "Lineer Bölme (Linear Split)", "Zaman Bükülmesi (Time-Warp)", ve "ALNS Destekli Hibrit Sürü" yaklaşımlarını sisteme entegre etmektir. Bu dönüşüm sayesinde sistem sadece rotalama yapan bir ticari yazılım olmaktan çıkacak; literatüre katkı sağlayabilecek yenilikçi (novel) bir akademik çatıya dönüşecektir.

## 2. Mimari Kararlar (Architectural Decisions)

Sistemi SOTA ilan etmemizi sağlayacak 4 temel mimari karar alınmıştır:

### A. Lineer Zamanlı ( $O(N)$ ) Split Algoritması
- **Neden?** Geleneksel Prins algoritması dev-turları (giant tours) alt rotalara bölerken $O(N^2)$ zaman harcar. Bu, 100+ öğrencilik rotalarda büyük darboğaz yaratır.
- **Karar:** Parçalama işlemi sırasında ileriye dönük durak sayısını mantıksal olarak sınırlayan (Bounded Forward Search) ve *Monotone Queue* mantığı ile işletilen $O(N)$ zamanlı bir dekoder yazılacaktır.

### B. Infeasibility Relaxation (Esnek Sınırlar ve Cezalar)
- **Neden?** Klasik algoritmalar kapasite veya zaman sınırı aşıldığında o rotayı çöpe atar. Bu, genetik çeşitliliği öldürür.
- **Karar:** Rota asla reddedilmeyecek. Bunun yerine rotaya **Time-Warp** (zamanı geriye sarma / gecikme) ve **Kapasite Taşması (Soft Capacity)** cezaları eklenecek. Çok kötü rotalar ağır ceza puanları alarak genetik havuzdan doğal seçilimle elenecek, esnek rotalar ise lokal minimumlardan kurtulmayı sağlayacaktır.

### C. ALNS Destekli Sürü (Swarm) Hibridizasyonu
- **Neden?** Sürü algoritmaları (PSO, HHO) sayısal/sürekli varyasyonlar için harikadır ama ayrık (discrete) rotalama problemlerinde ezbere çalışırlar. 
- **Karar:** Sadece sürü zekası kullanmak yerine, sürünün "Hangi onarma/yok etme operatörünün kullanılacağına" karar verdiği bir üst-yönetici (metaheuristic) hibrit model (MO-HHO-ALNS) kurulacaktır.

### D. Multi-Objective (Pareto Front) Optimizasyon
- **Neden?** Sadece "en ucuz maliyetli" rotayı dönmek modern lojistikte yetersizdir.
- **Karar:** Karar vericiye/kullanıcıya (Admin) birbiriyle çelişen amaçlar için (Minimum Araç Sayısı vs Minimum Öğrenci Gecikmesi) Non-dominated Sorting (NSGA-II) mantığıyla çoklu çözüm tepsisi (Pareto Front) sunulacaktır.

---
**Onaylar:** Mimarinin temel kodlama prensiplerinde Python Standart Kütüphaneleri ve Saf Numpy kullanılacak; performansı baltalayan şişkin dış kütüphanelerden kaçınılacaktır.

---

## 3. SOTA Baseline Çözücüler (04.04.2026 - Ekleyen: Z.ai)

### 3.1 Akademik Makale İçin Zorunlu Kıyaslama

Akademik makalede "State-of-the-Art" iddiasında bulunmak için, geliştirdiğimiz algoritmaları literatürdeki kanıtlanmış SOTA çözücüler ile kıyaslamak **ZORUNLUDUR**. Reviewer'lar bu kıyaslamayı mutlaka isteyecektir.

### 3.2 SOTA Çözücüler ve Akademik Değerleri

| Çözücü | Akademik Prestij | Makaledeki Rolü | Referans |
|--------|------------------|-----------------|----------|
| **PyVRP** | ⭐⭐⭐⭐⭐ DIMACS 2021 Birincisi | **Gold Standard Baseline** | Vidal (2022) - 1500+ atıf |
| **OR-Tools** | ⭐⭐⭐⭐ Endüstri Standardı | Pratik Referans | Google Research |
| **VROOM** | ⭐⭐⭐ Pratik/Hız | Hız Scalability Testi | Coupey (2024) |

### 3.3 Mevcut Kod Durumu (04.04.2026 - Z.ai)

**Mevcut dosyalar:**
- `optimizer_api/strategies/pyvrp_strategy.py` ✅ (505 satır, kapsamlı implementasyon)
- `optimizer_api/strategies/vroom_strategy.py` ✅ (429 satır, kapsamlı implementasyon)
- `optimizer_api/strategies/ortools_cvrp.py` ✅ (aktif kullanımda)

**Sorun:** PyVRP ve VROOM `requirements.txt`'de tanımlı DEĞİL. Bu nedenle kurulu değilse sessizce fallback yapılıyor.

### 3.4 Önerilen Entegrasyon (04.04.2026 - Z.ai)

**Gerekli Adımlar:**

1. **requirements.txt'ye ekle:**
   ```
   # SOTA Solvers (Akademik Benchmark için)
   pyvrp>=0.9.0    # DIMACS 2021 Winner - HGS
   pyvroom>=1.0.0  # Ultra-fast C++ solver
   ```

2. **Benchmark STRATEGIES listesine ekle:**
   ```python
   # SOTA Baseline Solvers
   ("PyVRP", "pyvrp", 30),      # DIMACS Winner - Gold Standard
   ("OR-Tools", "ortools", 30), # Industry Standard
   ("VROOM", "vroom", 5),       # Ultra-Fast - Scalability
   ```

### 3.5 Makale Strateji Kategorizasyonu (04.04.2026 - Z.ai)

```
┌─────────────────────────────────────────────────────────────┐
│                    STRATEGIES KATEGORİLERİ                   │
├─────────────────────────────────────────────────────────────┤
│  [A] Kendi Algoritmalarımız (Makale Konusu)                 │
│      ├── Hybrid Local Search (2-opt, 3-opt, Or-opt)        │
│      ├── ALNS (Destroy/Repair) - Planlanıyor               │
│      └── Linear Split + Metaheuristic                      │
│                                                             │
│  [B] SOTA Baseline Çözücüler (KARŞILAŞTIRMA İÇİN)          │
│      ├── PyVRP (HGS) ← DIMACS 2021 Winner - GOLD STANDARD  │
│      ├── OR-Tools (GLS) ← Endüstri Standardı               │
│      └── VROOM ← Ultra-Fast - Scalability Testi            │
│                                                             │
│  [C] Klasik Sezgiseller (Literatür Referansı)              │
│      ├── Nearest Neighbor                                   │
│      ├── Sweep Heuristic                                    │
│      └── Clarke-Wright Savings                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.6 Makale Tablosu Formatı (Önerilen)

| Instance | N | Optimal | PyVRP | OR-Tools | VROOM | **Ours** |
|----------|---|---------|-------|----------|-------|----------|
| berlin52 | 52 | 7542 | GAP% | GAP% | GAP% | GAP% |
| kroA100 | 100 | 21282 | GAP% | GAP% | GAP% | GAP% |
| d198 | 198 | 15780 | GAP% | GAP% | GAP% | GAP% |

Bu format makalenin bilimsel kabulünü önemli ölçüde artırır.
