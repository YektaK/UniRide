# UniRide Optimizer API - GWO & HHO Güncelleme Paketi

## 📦 Paket İçeriği

Bu paket, UniRide Optimizer API'ye GWO (Grey Wolf Optimizer) ve HHO (Harris Hawks Optimization) algoritmalarını ekler ve önemli hataları düzeltir.

---

## 🔧 Düzeltilen Kritik Hatalar

### 1. Unicode Encoding Hatası (Windows)
- **Sorun:** `✓` karakteri Windows terminal'de `charmap` hatası veriyordu
- **Çözüm:** ASCII-safe logging eklendi
- **Dosya:** `optimizer_api/utils/data_loader.py`

### 2. Algoritma İsim Eşleşmemesi
- **Sorun:** UI'da `nearest-neighbor`, `two-opt` / Python'da farklı isimler
- **Çözüm:** `algorithm-constants.ts` ile tek kaynak doğrulu (single source of truth)
- **Dosya:** `nextjs/src/lib/algorithm-constants.ts`

### 3. Time Matrix Fallback Uyarısı
- **Sorun:** Matrix yüklenemediğinde sessizce sıfır matris dönülüyordu
- **Çözüm:** Uyarı logu ve durum kontrol metodları eklendi
- **Dosya:** `optimizer_api/utils/data_loader.py`

### 4. Route-Test Payload Uyumsuzluğu
- **Sorun:** `start/end/waypoints/strategy` gönderiliyor, API `students/depot/algorithm` bekliyor
- **Çözüm:** Doğru payload formatına çeviri yapıldı
- **Dosya:** `nextjs/src/app/(app)/admin/route-test/page.tsx`

---

## 📁 Dosya Yapısı ve Kurulum

### Python API Dosyaları

| Zip İçindeki Dosya | Hedef Klasör | Durum |
|--------------------|--------------|-------|
| `optimizer_api/main.py` | `optimizer_api/main.py` | ✏️ DÜZENLENDİ |
| `optimizer_api/models/schemas.py` | `optimizer_api/models/schemas.py` | ✏️ DÜZENLENDİ |
| `optimizer_api/strategies/__init__.py` | `optimizer_api/strategies/__init__.py` | ✏️ DÜZENLENDİ |
| `optimizer_api/strategies/gwo_strategy.py` | `optimizer_api/strategies/gwo_strategy.py` | ✨ YENİ |
| `optimizer_api/strategies/hho_strategy.py` | `optimizer_api/strategies/hho_strategy.py` | ✨ YENİ |
| `optimizer_api/utils/data_loader.py` | `optimizer_api/utils/data_loader.py` | ✏️ DÜZENLENDİ |

### Next.js Dosyaları (Frontend)

| Zip İçindeki Dosya | Hedef Klasör | Durum |
|--------------------|--------------|-------|
| `nextjs/src/services/optimizer-service.ts` | `src/services/optimizer-service.ts` | ✏️ DÜZENLENDİ |
| `nextjs/src/app/api/compare-algorithms/route.ts` | `src/app/api/compare-algorithms/route.ts` | ✏️ DÜZENLENDİ |
| `nextjs/src/lib/algorithm-constants.ts` | `src/lib/algorithm-constants.ts` | ✨ YENİ |
| `nextjs/src/app/(app)/admin/route-test/page.tsx` | `src/app/(app)/admin/route-test/page.tsx` | ✏️ DÜZENLENDİ |
| `nextjs/src/app/(app)/admin/vehicle-planning/page.tsx` | `src/app/(app)/admin/vehicle-planning/page.tsx` | ✏️ DÜZENLENDİ |

---

## 🚀 Kurulum Adımları

### 1. Python API Güncelleme

```bash
# Zip'i aç
cd your-project/
unzip optimizer_gwo_hho_update.zip

# Python dosyalarını kopyala
cp -r optimizer_update_package/optimizer_api/* your-project/optimizer_api/

# API'yi yeniden başlat
cd optimizer_api
uvicorn main:app --reload
```

### 2. Next.js Güncelleme

```bash
# Next.js dosyalarını kopyala
cp optimizer_update_package/nextjs/src/services/optimizer-service.ts src/services/
cp optimizer_update_package/nextjs/src/app/api/compare-algorithms/route.ts src/app/api/compare-algorithms/
cp optimizer_update_package/nextjs/src/lib/algorithm-constants.ts src/lib/
cp -r "optimizer_update_package/nextjs/src/app/(app)" src/app/

# Next.js'i yeniden başlat
npm run dev
# veya
bun dev
```

---

## ✅ Yeni Algoritmalar

| Algoritma | Kod | Açıklama |
|-----------|-----|----------|
| **GWO** | `gwo` veya `grey_wolf` | Gri Kurt Optimizasyonu - Sosyal hiyerarşi tabanlı |
| **HHO** | `hho` veya `harris_hawks` | Harris Hawks Optimizasyonu - Kaçış enerjisi tabanlı |

---

## 📊 Tüm Algoritmalar (7 Adet)

| Algoritma | Kod | Açıklama | Önerilen |
|-----------|-----|----------|----------|
| **GA** | `genetic_algorithm`, `ga` | Genetik Algoritma | ✅ |
| **PSO** | `pso` | Parçacık Sürü Optimizasyonu | ✅ |
| **GWO** | `gwo`, `grey_wolf` | Gri Kurt Optimizasyonu | ✅ |
| **HHO** | `hho`, `harris_hawks` | Harris Hawks Optimizasyonu | ✅ |
| **Greedy** | `greedy` | En Yakın Komşu | ❌ |
| **Permutation** | `permutation_tsp` | Optimal (n≤10) | ❌ |
| **OR-Tools** | `ortools_cvrp` | Google Endüstri Standardı | ❌ |

---

## 🔌 Algoritma Sabitleri Kullanımı

```typescript
import { 
    ALGORITHM_KEYS, 
    ALGORITHM_OPTIONS,
    normalizeAlgorithmName,
    getAlgorithmDisplayName 
} from "@/lib/algorithm-constants";

// Algoritma key'i al
const key = ALGORITHM_KEYS.GWO; // "gwo"

// Görünen adı al
const name = getAlgorithmDisplayName("gwo"); // "Gri Kurt Optimizasyonu"

// Eski ismi normalize et
const normalized = normalizeAlgorithmName("nearest-neighbor"); // "greedy"
```

---

## 🧪 Test

```bash
cd optimizer_api

# GWO testi
python test_gwo.py

# HHO testi
python test_hho.py

# Tüm algoritma karşılaştırması
python test_comparison.py

# Time matrix yükleme doğrulama
python -c "from utils.data_loader import DataLoader; dl = DataLoader.get_instance(); print(dl.get_status())"
```

---

## 📝 Değişiklik Günlüğü

### v2.2.0 (24.03.2026)

**Yeni Özellikler:**
- GWO (Grey Wolf Optimizer) algoritması eklendi
- HHO (Harris Hawks Optimization) algoritması eklendi
- `algorithm-constants.ts` ile merkezi algoritma yönetimi

**Hata Düzeltmeleri:**
- Unicode encoding hatası düzeltildi (Windows uyumluluğu)
- Algoritma isim eşleşme sorunları düzeltildi
- Time matrix yükleme uyarıları eklendi
- Route-test payload uyumsuzluğu düzeltildi

**İyileştirmeler:**
- `DataLoader.get_status()` metodu eklendi
- `DataLoader.is_matrix_loaded()` kontrolü eklendi
- Daha iyi fallback mekanizması

---

**Tarih:** 24.03.2026
**Versiyon:** 2.2.0
