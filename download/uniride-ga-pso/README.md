# GA ve PSO Rota Optimizasyonu - UniRide

Bu modül, UniRide projesi için literatür tabanlı **Genetik Algoritma (GA)** ve **Parçacık Sürü Optimizasyonu (PSO)** implementasyonlarını içerir.

## 📚 Literatür Referansları

### Genetik Algoritma (GA)
- **Holland, J. H. (1975)**. *Adaptation in Natural and Artificial Systems*. University of Michigan Press.
- **Goldberg, D. E. (1989)**. *Genetic Algorithms in Search, Optimization and Machine Learning*. Addison-Wesley.
- **Davis, L. (1985)**. "Applying Adaptive Algorithms to Epistatic Domains". *IJCAI*.

### Parçacık Sürü Optimizasyonu (PSO)
- **Kennedy, J., & Eberhart, R. (1995)**. "Particle Swarm Optimization". *IEEE ICNN*.
- **Clerc, M., & Kennedy, J. (2002)**. "The particle swarm-explosion, stability, and convergence". *IEEE Transactions on Evolutionary Computation*.
- **Wang, K. P., et al. (2003)**. "Particle Swarm Optimization for Traveling Salesman Problem". *ICMLC*.

---

## 🔧 Algoritma Detayları

### Genetik Algoritma (GA)

| Bileşen | Yöntem | Açıklama |
|---------|--------|----------|
| **Kodlama** | Permütasyon | Her birey bir rota sıralaması |
| **Fitness** | 1/toplam_süre | Süre minimizasyonu |
| **Seçilim** | Turnuva (k=5) | k rastgele bireyden en iyi |
| **Çaprazlama** | Order Crossover (OX1) | TSP için özel, geçerli tur korur |
| **Mutasyon** | Swap + Inversion | %50 swap, %50 inversiyon |
| **Elitism** | %10 | En iyi bireyler korunur |

**Varsayılan Parametreler:**
```typescript
{
  populationSize: 100,
  eliteCount: 10,
  crossoverRate: 0.85,
  mutationRate: 0.15,
  tournamentSize: 5,
  maxIterations: 500,
  maxNoImprovement: 100
}
```

### Parçacık Sürü Optimizasyonu (PSO)

| Bileşen | Yöntem | Açıklama |
|---------|--------|----------|
| **Pozisyon** | Permütasyon | Her parçacık bir rota |
| **Hız** | Swap Operatörleri | Pozisyon değişiklikleri |
| **Atalet (w)** | 0.729 | Clerc kısıtlama faktörü |
| **Bilişsel (c1)** | 1.49445 | Kişisel en iyiye çekim |
| **Sosyal (c2)** | 1.49445 | Global en iyiye çekim |

**Varsayılan Parametreler:**
```typescript
{
  swarmSize: 50,
  inertiaWeight: 0.729,
  cognitiveWeight: 1.49445,
  socialWeight: 1.49445,
  velocityClamp: 6,
  maxIterations: 300,
  maxNoImprovement: 80
}
```

---

## 🧪 Doğrulama Yöntemleri

### 1. Brute Force Karşılaştırması
Küçük problemler (n ≤ 8) için brute force ile optimal çözüm hesaplanır ve algoritma sonuçları ile karşılaştırılır.

### 2. Test Senaryoları

| Kategori | Waypoint Sayısı | Amaç |
|----------|-----------------|------|
| Trivial | 0-2 | Temel doğruluk |
| Small | 3-5 | Optimalite kontrolü |
| Medium | 6-10 | Gerçek senaryolar |
| Large | 11-20 | Stres testi |

### 3. Performans Metrikleri

```typescript
interface BenchmarkResult {
  totalDuration: number;       // Toplam rota süresi
  executionTimeMs: number;     // Çalışma süresi
  isOptimal: boolean | null;   // Optimal mi?
  deviationFromOptimal: number;// Sapma yüzdesi
}
```

---

## 📖 Kullanım

### Temel Kullanım

```typescript
import { GeneticAlgorithmStrategy, PSOStrategy } from './route-strategies';

const ga = new GeneticAlgorithmStrategy();
const pso = new PSOStrategy();

// GA ile rota optimizasyonu
const result = await ga.calculateOptimalRoute(
  "D.Kampus",           // Başlangıç
  "D.Kampus",           // Bitiş
  ["Sw1", "Sw2", "So1"], // Waypoints
  calculateDistance      // Mesafe fonksiyonu
);

console.log(result.totalDuration);    // Toplam süre
console.log(result.routeDetails);     // Rota detayları
```

### Özel Parametreler

```typescript
import { GeneticAlgorithmStrategy, GAConfig } from './route-strategies';

const customConfig: Partial<GAConfig> = {
  populationSize: 200,
  maxIterations: 1000,
  mutationRate: 0.2,
  seed: 42 // Tekrarlanabilir sonuçlar için
};

const ga = new GeneticAlgorithmStrategy(customConfig);
```

### Benchmark Çalıştırma

```typescript
import { runBenchmark, quickValidation } from './route-strategies/__tests__/strategy-benchmark';

// Hızlı doğrulama
const isValid = await quickValidation();

// Tam benchmark
const { results, stats, summary } = await runBenchmark();
console.log(summary);
```

---

## 📊 Beklenen Sonuçlar

### Küçük Problemler (n ≤ 5)
- **GA**: %100 optimal çözüm
- **PSO**: %95+ optimal çözüm

### Orta Problemler (5 < n ≤ 10)
- **GA**: Optimalin %2-5 üstünde
- **PSO**: Optimalin %3-7 üstünde

### Büyük Problemler (n > 10)
- **GA**: Nearest Neighbor'dan %10-20 daha iyi
- **PSO**: Nearest Neighbor'dan %8-15 daha iyi

### Çalışma Süreleri
- n=5: ~5-10ms
- n=10: ~50-100ms
- n=15: ~200-500ms

---

## 🔬 Algoritma Doğruluğunu Test Etme

### Yöntem 1: Brute Force ile Karşılaştırma
```typescript
// n ≤ 8 için geçerli
const optimalDuration = bruteForceOptimal(waypoints, start, end, getDistance);
const algorithmResult = await strategy.calculateOptimalRoute(...);
const deviation = (algorithmResult.totalDuration - optimalDuration) / optimalDuration * 100;
```

### Yöntem 2: Bilinen TSP Instanceları
TSPLIB gibi standart benchmark setleri ile test.

### Yöntem 3: Çoklu Çalıştırma
Algoritmayı aynı problem üzerinde birden fazla kez çalıştırıp tutarlılığı kontrol et.

---

## 📁 Dosya Yapısı

```
src/services/doubus/route-strategies/
├── types.ts                    # Ortak tipler ve konfigürasyon
├── ga-strategy.ts             # Genetik Algoritma implementasyonu
├── pso-strategy.ts            # PSO implementasyonu
├── index.ts                   # Strateji kayıt ve export
└── __tests__/
    └── strategy-benchmark.ts  # Benchmark ve test suite
```

---

## 🚀 Entegrasyon

Mevcut UniRide projesine entegrasyon için:

1. Dosyaları `src/services/doubus/route-strategies/` altına kopyalayın
2. `index.ts` dosyasını güncelleyin
3. Mevcut `types.ts` ile yeni tipleri birleştirin

```typescript
// Kullanım
import { getStrategy } from './route-strategies';

const strategy = getStrategy('genetic-algorithm');
const result = await strategy.calculateOptimalRoute(...);
```

---

## 📝 Notlar

1. **Tohum (Seed)**: Tekrarlanabilir sonuçlar için `seed` parametresi kullanın
2. **Paralelleştirme**: Büyük popülasyonlar için Web Workers kullanılabilir
3. **Hibrit Yaklaşım**: GA + 2-Opt kombinasyonu daha iyi sonuçlar verebilir
4. **Adaptif Parametreler**: İterasyon sayısına göre parametre ayarlaması yapılabilir
