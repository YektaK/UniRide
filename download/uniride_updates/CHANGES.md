# UniRide Optimizasyon Güncellemeleri

Bu paket, 2-opt algoritması merkeziyetsizliği ve yeni meta-sezgisel algoritma stratejileri için gerekli güncellemeleri içerir.

## Değişen Dosyalar

### Backend (optimizer_api/)

#### Yeni Dosyalar

1. **utils/local_search.py** (YENİ)
   - Merkezi local search modülü
   - 2-opt, 3-opt, Or-opt ve Hybrid algoritmaları
   - Tüm meta-sezgisel stratejiler tarafından kullanılır

2. **strategies/gwo_strategy.py** (YENİ)
   - Grey Wolf Optimizer (GWO) stratejisi
   - Mirjalili et al. (2014) referansı
   - Local search entegrasyonu

3. **strategies/hho_strategy.py** (YENİ)
   - Harris Hawks Optimizer (HHO) stratejisi
   - Heidari et al. (2019) referansı
   - Lévy flight ve dört kuşatma stratejisi

4. **strategies/two_opt_strategy.py** (YENİ)
   - Bağımsız Two-Opt stratejisi
   - Multi-start optimizasyon desteği
   - Nearest neighbor başlangıç çözümü

#### Güncellenen Dosyalar

5. **strategies/__init__.py**
   - GWO, HHO ve Two-Opt stratejileri eklendi
   - Registry güncellendi

6. **strategies/ga_strategy.py**
   - Local search entegrasyonu eklendi
   - `local_search_type` parametresi eklendi

7. **strategies/pso_strategy.py**
   - Local search entegrasyonu eklendi
   - `local_search_type` parametresi eklendi

8. **models/schemas.py**
   - `LocalSearchType` enum eklendi
   - `local_search_type` parametresi eklendi
   - `gwo_config`, `hho_config`, `two_opt_config` parametreleri eklendi

9. **main.py**
   - GWO ve HHO algoritmaları eklendi
   - API dokümantasyonu güncellendi
   - Versiyon 3.0.0

### Frontend (frontend/)

10. **optimizer-service.ts**
    - `LocalSearchType` tipi eklendi
    - `local_search_type` desteği
    - Two-Opt strateji desteği
    - GWO ve HHO config tipleri güncellendi

## Kurulum

1. Backend dosyalarını kopyalayın:
   ```
   optimizer_api/utils/local_search.py      -> optimizer_api/utils/
   optimizer_api/strategies/gwo_strategy.py -> optimizer_api/strategies/
   optimizer_api/strategies/hho_strategy.py -> optimizer_api/strategies/
   optimizer_api/strategies/two_opt_strategy.py -> optimizer_api/strategies/
   optimizer_api/strategies/__init__.py     -> optimizer_api/strategies/
   optimizer_api/strategies/ga_strategy.py  -> optimizer_api/strategies/
   optimizer_api/strategies/pso_strategy.py -> optimizer_api/strategies/
   optimizer_api/models/schemas.py          -> optimizer_api/models/
   optimizer_api/main.py                    -> optimizer_api/
   ```

2. Frontend dosyasını kopyalayın:
   ```
   frontend/optimizer-service.ts -> src/services/
   ```

## Kullanım

### Local Search Konfigürasyonu

Tüm meta-sezgisel algoritmalar (GA, PSO, GWO, HHO) artık `local_search_type` parametresi ile yerel arama yöntemi seçebilir:

```python
# Python API
request = OptimizationRequest(
    algorithm="gwo",
    students=students,
    depot=depot,
    local_search_type="two_opt",  # "none", "two_opt", "three_opt", "or_opt", "hybrid"
    gwo_config={
        "population_size": 30,
        "max_iterations": 100,
    }
)
```

```typescript
// TypeScript
const result = await optimizeRoutes(students, depot, {
    algorithm: "gwo",
    local_search_type: "two_opt",
    gwo_config: {
        population_size: 30,
        max_iterations: 100,
    }
});
```

### Yeni Algoritmalar

#### Grey Wolf Optimizer (GWO)
- **Algoritma adı**: `gwo` veya `grey_wolf`
- **Parametreler**: `gwo_config`
  - `population_size`: Kurt sürüsü büyüklüğü (varsayılan: 30)
  - `max_iterations`: Maksimum iterasyon (varsayılan: 100)
  - `initial_a`: Başlangıç a parametresi (varsayılan: 2.0)
  - `exploration_rate`: Keşif oranı (varsayılan: 0.5)

#### Harris Hawks Optimizer (HHO)
- **Algoritma adı**: `hho` veya `harris_hawks`
- **Parametreler**: `hho_config`
  - `population_size`: Şahin sayısı (varsayılan: 30)
  - `max_iterations`: Maksimum iterasyon (varsayılan: 100)
  - `initial_energy`: Başlangıç enerjisi (varsayılan: 1.0)
  - `jump_probability`: Kaçış olasılığı (varsayılan: 0.5)

#### Two-Opt (Bağımsız)
- **Algoritma adı**: `two_opt` veya `2opt`
- **Parametreler**: `two_opt_config`
  - `max_iterations`: Maksimum iterasyon (varsayılan: 2000)
  - `multi_start`: Çoklu başlangıç (varsayılan: true)
  - `num_starts`: Başlangıç sayısı (varsayılan: 10)

## Referanslar

- Croes, G. (1958). A method for solving traveling salesman problems. Operations Research.
- Lin, S. (1965). Computer solutions of the traveling salesman problem. Bell System Technical Journal.
- Or, I. (1976). Traveling salesman-type combinatorial problems. Ph.D. Thesis.
- Mirjalili, S., et al. (2014). Grey wolf optimizer. Advances in Engineering Software.
- Heidari, A. A., et al. (2019). Harris hawks optimization. Future Generation Computer Systems.
