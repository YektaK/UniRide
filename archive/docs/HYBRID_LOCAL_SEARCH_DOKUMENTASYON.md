# Hybrid Local Search Algoritması Dokümantasyonu

## 📖 Genel Bakış

**Hybrid Local Search**, birden fazla local search algoritmasını bir araya kullanarak tek bir algoritmadan daha iyi sonuçlar elde eden bir optimizasyon yaklaşımıdır. Bu yöntem, farklı algoritmaların güçlü yönlerini birleştirerek local optima'dan kaçma ve daha kaliteli çözümler bulma yeteneğine sahiptir.

---

## 🔧 Algoritma Mimarisi

### Varsayılan Çalışma Sırası

Hybrid algoritma, algoritmaları **hızdan yavaşa** doğru sıralı uygular:

```
1. Swap        (O(n²))  → Hızlı, fine-tuning için
2. 2-opt       (O(n²))  → Klasik, güvenilir
3. Or-opt      (O(n²))  → Segment relocation
4. Cross Exchange (O(n²×k²)) → CVRP için segment değişimi
5. 3-opt       (O(n³))  → Yüksek kalite, yavaş
6. Time Window Aware → CVRPTW için zaman penceresi optimizasyonu
```

### Her Iterasyonda Ne Yapılır?

```python
for iteration in range(max_iterations):
    improved_this_round = False
    
    for method in [Swap, 2-opt, Or-opt, Cross-Exchange, 3-opt, TimeWindow]:
        new_route, new_duration = method.improve(current_route, duration_func)
        
        if new_duration < current_duration:
            current_route = new_route
            current_duration = new_duration
            improved_this_round = True
    
    if not improved_this_round:
        break  # Hiçbir iyileştirme yoksa dur
```

---

## 📊 Algoritma Detayları

### 1. Swap (Yer Değiştirme)
- **Zaman Karmaşıklığı**: O(n²)
- **Ne Yapar**: İki müşteri konumunu değiştirir
- **En İyi Kullanım**: Hızlı fine-tuning, küçük pertürbasyonlar
- **Örnek**:
  ```
  Önce: A → B → C → D → E
  Swap(1,3): A → D → C → B → E
  ```

### 2. 2-opt
- **Zaman Karmaşıklığı**: O(n²)
- **Ne Yapar**: İki kenarı keser, segmenti ters çevirir
- **En İyi Kullanım**: Orta büyüklükte problemler
- **Örnek**:
  ```
  Önce: A → B → C → D → E
  2-opt(1,3): A → D → C → B → E
  ```

### 3. Or-opt
- **Zaman Karmaşıklığı**: O(n²)
- **Ne Yapar**: 1-3 ardışık müşteriyi farklı bir konuma taşır
- **En İyi Kullanım**: Kümelenmiş müşterisi olan problemler
- **Örnek**:
  ```
  Önce: A → B → C → D → E
  Or-opt (BC taşı): A → D → B → C → E
  ```

### 4. Cross Exchange
- **Zaman Karmaşıklığı**: O(n²×k²)
- **Ne Yapar**: İki segmenti değiştirir (CVRP için)
- **En İyi Kullanım**: Çok araçlı rotalama problemleri

### 5. 3-opt
- **Zaman Karmaşıklığı**: O(n³)
- **Ne Yapar**: Üç kenarı keser, 7 farklı yeniden bağlama dener
- **En İyi Kullanım**: Yüksek kalite gerektiren, zaman kritik olmayan

### 6. Time Window Aware
- **Ne Yapar**: Zaman penceresi ihlallerini minimize eder
- **En İyi Kullanım**: CVRPTW problemleri
- **Ceza Fonksiyonu**: `score = duration + penalty × tw_violation`

---

## ⚙️ Parametreler

```python
HybridLocalSearch(
    methods=None,              # Varsayılan: [Swap, 2-opt, Or-opt, Cross-Exchange, 3-opt, TW]
    max_iterations=100,        # Maksimum dış iterasyon
    use_random_order=False,    # Rastgele sıralama
    include_cross_exchange=True,  # CVRP için
    include_time_window=True   # CVRPTW için
)
```

### Iterasyon Limitleri (Her Method İçin)

| Algoritma | Max Iterasyon | Neden |
|-----------|---------------|-------|
| Swap | 30 | Hızlı, az iterasyon yeterli |
| 2-opt | 40 | Klasik, orta |
| Or-opt | 30 | Orta |
| Cross-Exchange | 20 | Yavaş |
| 3-opt | 15 | En yavaş, az iterasyon |
| Time Window | 25 | Orta |

---

## 📈 Performans Beklentisi

### Küçük Problemler (n ≤ 100)
- **Beklenen Gap**: %0-2 (optimal yakın)
- **Süre**: < 1 saniye
- **En İyi**: Hybrid veya 3-opt

### Orta Problemler (100 < n ≤ 500)
- **Beklenen Gap**: %2-5
- **Süre**: 1-10 saniye
- **En İyi**: Hybrid veya 2-opt

### Büyük Problemler (500 < n ≤ 2000)
- **Beklenen Gap**: %5-10
- **Süre**: 10-60 saniye
- **En İyi**: Hybrid veya 2-opt (3-opt çok yavaş)

---

## 🎯 Kullanım Örnekleri

### Temel Kullanım
```python
from utils.local_search import HybridLocalSearch, LocalSearchType

# Hybrid local search oluştur
hybrid = HybridLocalSearch(max_iterations=100)

# Rota iyileştir
improved_route, improved_duration = hybrid.improve(
    route=current_route,
    duration_func=calculate_duration
)
```

### CVRPTW için
```python
hybrid = HybridLocalSearch(
    max_iterations=50,
    include_time_window=True
)

improved_route, duration = hybrid.improve(
    route=route,
    duration_func=duration_func,
    time_windows=time_windows,  # Dict[str, (start, end)]
    arrival_times=arrival_times  # Dict[str, float]
)
```

### Factory Function ile
```python
from utils.local_search import apply_local_search, LocalSearchType

improved_route, duration = apply_local_search(
    route=route,
    duration_func=duration_func,
    local_search_type=LocalSearchType.HYBRID,
    max_iterations=100
)
```

---

## 🔬 Neden Hybrid Daha İyi?

1. **Local Optima'dan Kaçış**: Bir algoritma takıldığında diğer devam edebilir
2. **Farklı Komşuluk Yapıları**: Her algoritma farklı çözüm uzayını keşfeder
3. **Kombine Etki**: Ardışık uygulama sinerji yaratır
4. **Esneklik**: Problem tipine göre metodlar eklenebilir/çıkarılabilir

---

## 📝 Kaynaklar

- Croes, G. (1958). A method for solving traveling salesman problems. (2-opt)
- Lin, S. (1965). Computer solutions of the traveling salesman problem. (3-opt)
- Or, I. (1976). Traveling salesman-type combinatorial problems. (Or-opt)
- Taillard, E. (1993). Parallel iterative search methods for VRP. (Cross Exchange)

---

*Bu dokümantasyon UniRide CVRPTW projesi için hazırlanmıştır.*
*Tarih: 2026-04-04*
*Katılımcı: Super Z AI Assistant*
