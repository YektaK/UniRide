# UniRide Changelog

> Bu dosya proje değişikliklerini takip eder.  
> **Son Güncelleme:** 26 Mart 2026

---

## [2.0.0] - Planlanıyor - Split Entegrasyonu

### Eklenecek (Added)
- `optimizer_api/utils/split_decoder.py` - Optimal Split Decoder modülü
- `optimizer_api/strategies/hybrid_base_strategy.py` - Hibrit strateji temel sınıfı
- `optimizer_api/strategies/pso_split_strategy.py` - PSO + Split algoritması
- `optimizer_api/strategies/hho_split_strategy.py` - HHO + Split algoritması
- `optimizer_api/strategies/gwo_split_strategy.py` - GWO + Split algoritması
- `optimizer_api/strategies/ga_split_strategy.py` - GA + Split algoritması
- `optimizer_api/utils/local_search.py` - 2-opt ve Or-opt local search
- `tests/test_split_decoder.py` - Split decoder unit testleri
- `tests/test_hybrid_strategies.py` - Hibrit strateji testleri

### Değişecek (Changed)
- `optimizer_api/strategies/__init__.py` - Yeni stratejiler registry'ye eklenecek
- `src/lib/algorithm-constants.ts` - Frontend algoritma seçenekleri güncellenecek
- Mevcut algoritmalar opsiyonel olarak korunacak

### Beklenen İyileştirmeler (Expected Improvements)
- Tek öğrencilik rota oranı: %15-20 → <%5
- Ortalama araç sayısı: %15-20 azalma
- Ortalama tur süresi: %20-25 azalma
- Feasibility rate: %100 (her zaman geçerli çözüm)

---

## [1.1.0] - 25 Mart 2026 - Algoritma Analizi

### Eklendi (Added)
- VROOM projesi analizi ve karşılaştırması
- PyVRP entegrasyon önerileri
- Akademik makale araştırması (2023-2025)
- `CVRPTW_Analiz_ve_Cozum_Onerileri.md` dokümanı

### Değişti (Changed)
- ROADMAP.md güncellendi
- Mimari kararlar tablosu genişletildi

---

## [1.0.0] - 24 Mart 2026 - İlk Stabil Sürüm

### Eklendi (Added)
- Next.js 15 frontend uygulaması
- Python FastAPI optimizer servisi
- Supabase veritabanı entegrasyonu
- K-Means clustering modülü
- Genetic Algorithm stratejisi
- PSO stratejisi
- OR-Tools CVRP entegrasyonu
- Greedy heuristic stratejisi
- Permutation TSP stratejisi
- Time matrix loader
- DataLoader singleton pattern

### Frontend Özellikleri
- Admin dashboard
- Driver dashboard
- Student dashboard
- Vehicle planning sayfası
- Route visualization
- Algorithm comparison

### Backend Özellikleri
- `/api/calculate-vehicles` endpoint
- `/api/admin/*` CRUD endpoints
- `/api/driver/*` endpoints
- Supabase RLS policies

---

## [0.9.0] - Mart 2026 - Pre-Release

### Eklendi (Added)
- Temel VRP çözümü
- K-Means kümeleme
- Basit rota optimizasyonu
- Öğrenci yönetimi
- Araç yönetimi

### Bilinen Sorunlar (Known Issues)
- K-Means katı kümeleme sorunu
- Time matrix duyarsızlığı
- Tek öğrencilik rotalar

---

## Sürüm Numaralandırma Kuralı

Bu proje **Semantic Versioning** kullanır:

- **MAJOR** (X.0.0): Breaking changes, mimari değişiklikler
- **MINOR** (0.X.0): Yeni özellikler, backward compatible
- **PATCH** (0.0.X): Bug fixes, küçük iyileştirmeler

---

## Gelecek Sürümler

### [2.1.0] - Planlanıyor
- Local search modülü (2-opt, Or-opt)
- Benchmark test sonuçları
- Performans karşılaştırma raporu

### [2.2.0] - Planlanıyor
- Faz 2: Veri kalıcılığı
- Route plans veritabanı kaydı
- Sürücü atama sistemi

### [3.0.0] - Gelecek
- Faz 3: İş akışı otomasyonu
- Faz 4: Canlı takip
- Mobil uygulama

---

## Değişiklik Kategorileri

| Kategori | Sembol | Açıklama |
|----------|--------|----------|
| Added | ✨ | Yeni özellik |
| Changed | 🔄 | Değişen özellik |
| Deprecated | ⚠️ | Kullanımdan kaldırılacak |
| Removed | ❌ | Kaldırılan özellik |
| Fixed | 🐛 | Düzeltilen hata |
| Security | 🔒 | Güvenlik düzeltmesi |

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi
