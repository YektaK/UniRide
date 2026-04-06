# UniRide CVRP Optimizasyon Sistemi
## Developer Handover Dokümanı

**Versiyon:** 3.0.0  
**Tarih:** 24 Mart 2026  
**Hazırlayan:** Z.ai Development Team

---

## İçindekiler

1. [Özet](#1-özet)
   - [1.1 Yapılan Değişiklikler](#11-yapılan-değişiklikler)
2. [Backend Değişiklikleri (Python)](#2-backend-değişiklikleri-python)
   - [2.1 Yeni Dosyalar](#21-yeni-dosyalar)
   - [2.2 Güncellenen Dosyalar](#22-güncellenen-dosyalar)
   - [2.3 Local Search Type Seçenekleri](#23-local-search-type-seçenekleri)
3. [Frontend Değişiklikleri (TypeScript/React)](#3-frontend-değişiklikleri-typescriptreact)
   - [3.1 Güncellenen Dosyalar](#31-güncellenen-dosyalar)
   - [3.2 algorithm-constants.ts Yeni Fonksiyonlar](#32-algorithm-constantsts-yeni-fonksiyonlar)
4. [API Değişiklikleri](#4-api-değişiklikleri)
   - [4.1 POST /api/v1/optimize](#41-post-apiv1optimize)
   - [4.2 Algoritma Destek Matrisi](#42-algoritma-destek-matrisi)
5. [Kurulum ve Dağıtım](#5-kurulum-ve-dağıtım)
   - [5.1 Backend Kurulumu](#51-backend-kurulumu)
   - [5.2 Frontend Kurulumu](#52-frontend-kurulumu)
6. [Test ve Doğrulama](#6-test-ve-doğrulama)
   - [6.1 Backend Testi](#61-backend-testi)
   - [6.2 Frontend Testi](#62-frontend-testi)
7. [Sonraki Adımlar ve Öneriler](#7-sonraki-adımlar-ve-öneriler)
8. [İletişim ve Destek](#8-i̇letişim-ve-destek)

---

## 1. Özet

Bu doküman, UniRide CVRP (Capacitated Vehicle Routing Problem) optimizasyon sisteminde yapılan önemli güncellemeleri belgelemektedir. Güncellemeler, backend (Python) ve frontend (TypeScript/React) katmanlarını kapsamakta olup, sistemin algoritma seçeneklerini genişletmekte ve kod kalitesini artırmaktadır.

### 1.1 Yapılan Değişiklikler

- ✅ **GWO (Grey Wolf Optimizer)** algoritması eklendi
- ✅ **HHO (Harris Hawks Optimization)** algoritması eklendi
- ✅ **Two-Opt standalone** stratejisi eklendi
- ✅ **Local Search Type** parametresi tüm meta-sezgisel algoritmalara eklendi (2-opt, 3-opt, Or-opt, Hybrid)
- ✅ 2-opt kod tekrarı merkezi `local_search` modülüne taşındı
- ✅ Frontend UI güncellendi: Yerel Arama dropdown'ı eklendi

---

## 2. Backend Değişiklikleri (Python)

### 2.1 Yeni Dosyalar

| Dosya Yolu | Açıklama |
|------------|----------|
| `optimizer_api/utils/local_search.py` | Merkezi local search modülü (2-opt, 3-opt, Or-opt, Hybrid) |
| `optimizer_api/strategies/gwo_strategy.py` | Grey Wolf Optimizer implementasyonu |
| `optimizer_api/strategies/hho_strategy.py` | Harris Hawks Optimization implementasyonu |
| `optimizer_api/strategies/two_opt_strategy.py` | Standalone Two-Opt stratejisi (multi-start desteği) |

### 2.2 Güncellenen Dosyalar

1. **`strategies/__init__.py`** - STRATEGY_REGISTRY güncellendi, GWO, HHO ve Two-Opt eklendi
2. **`strategies/ga_strategy.py`** - `local_search_type` parametresi eklendi, merkezi local_search modülü kullanımı
3. **`strategies/pso_strategy.py`** - `local_search_type` parametresi eklendi, merkezi local_search modülü kullanımı
4. **`models/schemas.py`** - `LocalSearchType` enum eklendi, GWO ve HHO config şemaları
5. **`main.py`** - API v3.0.0, GWO/HHO endpoint'leri, `compareAllAlgorithms` güncellendi

### 2.3 Local Search Type Seçenekleri

| Değer | Görünen Ad | Açıklama |
|-------|------------|----------|
| `none` | Yok | Yerel arama uygulanmaz |
| `two_opt` | 2-Opt (Klasik) | Kenar değiştirme ile iyileştirme, hızlı ve etkili |
| `three_opt` | 3-Opt (Yüksek Kalite) | 3 kenar değiştirme, daha güçlü iyileştirme |
| `or_opt` | Or-Opt (Kümeleme) | Alt tur yeniden konumlandırma, kümeleme için etkili |
| `hybrid` | Hibrit (Kombine) | 2-opt + 3-opt + Or-opt kombine, en iyi kalite |

---

## 3. Frontend Değişiklikleri (TypeScript/React)

### 3.1 Güncellenen Dosyalar

| Dosya Yolu | Değişiklik |
|------------|------------|
| `src/lib/algorithm-constants.ts` | Two-Opt algoritması, Local Search sabitleri, helper fonksiyonlar |
| `src/services/vehicle-calculator.ts` | `local_search_type` parametresi eklendi |
| `src/app/api/calculate-vehicles/route.ts` | `local_search_type` parametresi, default `genetic_algorithm` |
| `src/app/(app)/admin/route-test/page.tsx` | Yerel Arama dropdown'ı eklendi |
| `src/app/(app)/admin/vehicle-planning/page.tsx` | Yerel Arama dropdown'ı eklendi |

### 3.2 algorithm-constants.ts Yeni Fonksiyonlar

```typescript
// Algoritmanın local search destekleyip desteklemediğini kontrol eder
function algorithmSupportsLocalSearch(algorithm: string): boolean

// Local search type için görünen ad döndürür
function getLocalSearchDisplayName(type: LocalSearchType): string

// UI dropdown için hazır options array
const LOCAL_SEARCH_OPTIONS: Array<{key, label, description}>
```

**Yeni Export'lar:**
- `LOCAL_SEARCH_KEYS` - Local search type sabitleri
- `LOCAL_SEARCH_DISPLAY_NAMES` - Görünen adlar
- `LOCAL_SEARCH_DESCRIPTIONS` - Açıklamalar
- `LocalSearchType` - Type tanımı

---

## 4. API Değişiklikleri

### 4.1 POST /api/v1/optimize

**Yeni opsiyonel parametreler:**

```json
{
  "algorithm": "gwo | hho | two_opt | genetic_algorithm | pso | ...",
  "local_search_type": "none | two_opt | three_opt | or_opt | hybrid",
  
  "gwo_config": {
    "population_size": 30,
    "max_iterations": 100,
    "initial_a": 2.0,
    "exploration_rate": 0.5,
    "local_search_type": "two_opt"
  },
  
  "hho_config": {
    "population_size": 30,
    "max_iterations": 100,
    "initial_energy": 1.0,
    "jump_probability": 0.5,
    "local_search_type": "two_opt"
  },
  
  "two_opt_config": {
    "max_iterations": 1000,
    "multi_start": true,
    "num_starts": 10
  }
}
```

### 4.2 Algoritma Destek Matrisi

| Algoritma | Önerilen | Local Search | Karmaşıklık |
|-----------|----------|--------------|-------------|
| Genetik Algoritma (GA) | ✓ | ✓ | O(g×p×n²) |
| PSO | ✓ | ✓ | O(i×s×n²) |
| Gri Kurt (GWO) | ✓ | ✓ | O(i×p×n²) |
| Harris Hawks (HHO) | ✓ | ✓ | O(i×h×n²) |
| Two-Opt Local Search | — | — | O(n²) |
| Greedy | — | — | O(n²) |
| Permütasyon TSP | — | — | O(n!) |
| OR-Tools CVRP | — | — | O(n³) |

---

## 5. Kurulum ve Dağıtım

### 5.1 Backend Kurulumu

1. `optimizer_api/utils/local_search.py` dosyasını oluşturun
2. `optimizer_api/strategies/` altına `gwo_strategy.py`, `hho_strategy.py`, `two_opt_strategy.py` ekleyin
3. `strategies/__init__.py` dosyasını güncelleyin
4. `ga_strategy.py` ve `pso_strategy.py` dosyalarını güncelleyin
5. `models/schemas.py` dosyasını güncelleyin
6. `main.py` dosyasını güncelleyin
7. Python API'yi yeniden başlatın:
   ```bash
   uvicorn main:app --reload
   ```

### 5.2 Frontend Kurulumu

- `src/lib/algorithm-constants.ts` dosyasını güncelleyin
- `src/services/vehicle-calculator.ts` dosyasını güncelleyin
- `src/app/api/calculate-vehicles/route.ts` dosyasını güncelleyin
- `src/app/(app)/admin/route-test/page.tsx` dosyasını güncelleyin
- `src/app/(app)/admin/vehicle-planning/page.tsx` dosyasını güncelleyin
- Uygulamayı yeniden başlatın:
  ```bash
  npm run dev
  # veya
  npm run build && npm start
  ```

---

## 6. Test ve Doğrulama

### 6.1 Backend Testi

```bash
# Health check
curl http://localhost:8000/health

# Mevcut algoritmaları listele
curl http://localhost:8000/api/v1/strategies

# GWO ile optimizasyon
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "gwo",
    "students": [...],
    "depot": {...},
    "local_search_type": "two_opt"
  }'

# HHO ile optimizasyon
curl -X POST http://localhost:8000/api/v1/optimize \
  -H "Content-Type: application/json" \
  -d '{
    "algorithm": "hho",
    "students": [...],
    "depot": {...}
  }'

# Algoritma karşılaştırma
curl -X POST http://localhost:8000/api/v1/compare \
  -H "Content-Type: application/json" \
  -d '{
    "students": [...],
    "depot": {...},
    "algorithms": ["genetic_algorithm", "pso", "gwo", "hho"]
  }'
```

### 6.2 Frontend Testi

1. `/admin/route-test` sayfasına gidin
2. Algoritma dropdown'ından **GWO** veya **HHO** seçin
3. Yerel Arama dropdown'ından bir seçenek belirleyin
4. Noktalar seçip **"Optimize Et"** butonuna tıklayın
5. Sonuçların doğru döndüğünü doğrulayın
6. `/admin/vehicle-planning` sayfasında da aynı testleri yapın

---

## 7. Sonraki Adımlar ve Öneriler

### Önerilen İyileştirmeler

- Algoritma performans karşılaştırma dashboard'u eklenmesi
- Hyperparameter tuning için otomatik optimizasyon
- Sonuçların veritabanında saklanması ve geçmiş sorgulama
- Real-time optimizasyon ilerleme göstergesi (WebSocket)
- Daha fazla local search yöntemi (Lin-Kernighan, etc.)

### Bilinen Sorunlar

- Permütasyon algoritması 10+ nokta için çok yavaş çalışıyor (UI'da uyarı var)
- OR-Tools CVRP ekstra bağımlılık gerektiriyor (`google-ortools`)
- Hybrid local search büyük problemlerde yavaş kalabilir

---

## 8. İletişim ve Destek

Bu dokümantasyon ile ilgili sorularınız için **Z.ai Development Team** ile iletişime geçebilirsiniz. Teknik detaylar ve kod örnekleri için ilgili dosyalardaki yorum satırlarını inceleyebilirsiniz.

---

**— Doküman Sonu —**
