# UniRide Değişiklik Günlüğü

> **Proje:** UniRide - Engelli Öğrenci Taşımacılık Sistemi  
> **Son Güncelleme:** 26 Mart 2026

---

## [2.0.0] - Planlanıyor

### Eklenecek (Added)

- `optimizer_api/utils/split_decoder.py`
  - Optimal Split Decoder modülü
  - Dinamik programlama tabanlı rota bölme
  - Heterojen kapasite desteği (Sw/So)
  - Time matrix entegrasyonu

- `optimizer_api/strategies/hybrid_base_strategy.py`
  - Hibrit strateji temel sınıfı
  - Split decoder entegrasyonu
  - Ortak yardımcı metotlar

- `optimizer_api/strategies/pso_split_strategy.py`
  - PSO + Split algoritması
  - Giant tour optimizasyonu
  - Swap operation tabanlı hız

- `optimizer_api/strategies/hho_split_strategy.py`
  - HHO + Split algoritması
  - Lévy Flight ile lokal optimum kaçışı
  - 4 siege stratejisi

- `optimizer_api/strategies/gwo_split_strategy.py`
  - GWO + Split algoritması
  - Alpha-Beta-Delta hiyerarşisi

- `optimizer_api/strategies/ga_split_strategy.py`
  - GA + Split algoritması
  - Order Crossover + Mutation

- `tests/test_split_decoder.py`
  - Split decoder unit testleri

- `tests/test_hybrid_strategies.py`
  - Hibrit strateji testleri

### Değişecek (Changed)

- `optimizer_api/strategies/__init__.py`
  - Strategy registry güncellemesi
  - Yeni algoritma eklemeleri

- `src/lib/algorithm-constants.ts`
  - Frontend algoritma seçenekleri
  - Varsayılan algoritma değişikliği

### Beklenen İyileştirmeler

| Metrik | Önce | Sonra |
|--------|------|-------|
| Tek öğrencilik rota | %15-20 | <%5 |
| Ortalama araç sayısı | - | -20% |
| Ortalama tur süresi | - | -25% |
| Feasibility rate | %92 | %100 |

---

## [1.1.0] - 25 Mart 2026

### Eklendi (Added)

- VROOM projesi analizi
  - C++20 tabanlı yüksek performans
  - OSRM entegrasyonu
  - REST API desteği

- PyVRP entegrasyon önerileri
  - HGS (Hybrid Genetic Search)
  - Modern Python implementasyonu

- Akademik makale araştırması (2023-2025)
  - CVRPTW güncel yaklaşımlar
  - Performans karşılaştırmaları

- `CVRPTW_Analiz_ve_Cozum_Onerileri.md`
  - Detaylı problem analizi
  - Çözüm alternatifleri

### Değişti (Changed)

- ROADMAP.md güncellemesi
- Mimari kararlar tablosu genişletildi

---

## [1.0.0] - 24 Mart 2026

### Eklendi (Added)

#### Frontend (Next.js 15)

- Admin Dashboard
  - Kullanıcı yönetimi
  - Araç yönetimi
  - Rota planlama
  - Raporlar

- Driver Dashboard
  - Günlük atamalar
  - Navigasyon
  - Sefer geçmişi

- Student Dashboard
  - Sefer takibi
  - Talep oluşturma
  - Geçmiş seferler

#### Backend API (Next.js)

- `/api/calculate-vehicles` - Rota optimizasyonu
- `/api/admin/*` - Admin işlemleri
- `/api/driver/*` - Sürücü işlemleri
- `/api/auth/*` - Kimlik doğrulama

#### Python Optimizer (FastAPI)

- Algoritma stratejileri
  - Genetic Algorithm
  - Particle Swarm Optimization
  - Harris Hawks Optimization
  - Grey Wolf Optimizer
  - OR-Tools CVRP
  - Greedy Heuristic
  - K-Means TSP
  - Permutation TSP

- Utility modülleri
  - DataLoader (Singleton)
  - K-Means Clustering
  - Local Search (2-opt)

#### Database (Supabase)

- `users` - Kullanıcı tablosu
- `vehicles` - Araç tablosu
- `time_matrix` - Seyahat süresi matrisi
- `weekly_schedules` - Haftalık programlar
- `ride_requests` - Sefer talepleri

---

## [0.9.0] - Mart 2026

### Eklendi (Added)

- Temel VRP çözümü
- K-Means kümeleme
- Basit rota optimizasyonu
- Öğrenci yönetimi
- Araç yönetimi

### Bilinen Sorunlar

- K-Means katı kümeleme
- Time matrix duyarsızlığı
- Tek öğrencilik rotalar

---

## Sürüm Numaralandırma

Bu proje **Semantic Versioning** kullanır:

| Seviye | Format | Açıklama |
|--------|--------|----------|
| MAJOR | X.0.0 | Breaking changes |
| MINOR | 0.X.0 | Yeni özellikler |
| PATCH | 0.0.X | Bug fixes |

---

## Gelecek Sürümler

### [2.1.0] - Planlanıyor

- Local search genişletme (Or-opt)
- Benchmark sonuçları
- Performans raporu

### [2.2.0] - Planlanıyor

- Faz 2: Veri kalıcılığı
- Route plans kayıt sistemi
- Sürücü atama

### [3.0.0] - İleriki

- Faz 3: İş akışı otomasyonu
- Faz 4: Canlı takip
- Mobil uygulama

---

## Kategori Sembolleri

| Sembol | Anlam |
|--------|-------|
| ✨ | Yeni özellik (Added) |
| 🔄 | Değişiklik (Changed) |
| ⚠️ | Kullanımdan kaldırılacak (Deprecated) |
| ❌ | Kaldırılan (Removed) |
| 🐛 | Hata düzeltmesi (Fixed) |
| 🔒 | Güvenlik (Security) |

---

**Doküman Sahibi:** UniRide Geliştirme Ekibi
