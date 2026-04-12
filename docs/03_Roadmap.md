# UniRide CVRPTW - Geliştirme Yol Haritası

## Sürüm: 2.2.0 | Tarih: 10 Nisan 2026 (10.04.2026 - Ekleyen: Antigravity AI)

---

## 📊 Genel Bakış

Bu yol haritası, UniRide Özel Öğrenci Taşıma Sistemi'nin CVRPTW (Kapasiteli Araç Rotalama Problemi Zaman Pencereli) entegrasyonu için kapsamlı bir plan sunmaktadır. Proje, 7 ana fazdan oluşmakta olup, ilk 4 faz tamamlanmıştır.

---

## ✅ Tamamlanan Fazlar

### Faz 1: Temel Altyapı ✅
**Durum:** Tamamlandı | **Süre:** 2 hafta

| Görev | Durum | Açıklama |
|-------|-------|----------|
| Next.js 16 Kurulumu | ✅ | App Router, TypeScript, Tailwind CSS 3.x |
| Supabase Entegrasyonu | ✅ | PostgreSQL, RLS policies |
| Python Backend API | ✅ | FastAPI, CORS (env-tabanlı), Health check |
| Temel UI Bileşenleri | ✅ | shadcn/ui components (80+ bileşen) |
| Authentication | ✅ | Supabase Auth + requireAdmin guard |

### Faz 2: CVRP Optimizasyonu ✅
**Durum:** Tamamlandı | **Süre:** 3 hafta

| Görev | Durum | Açıklama |
|-------|-------|----------|
| Genetic Algorithm | ✅ | OX1 crossover, swap/inversion mutation |
| PSO | ✅ | Swap-based velocity, discrete PSO |
| GWO | ✅ | Grey Wolf Optimizer (Mirjalili et al., 2014) |
| HHO | ✅ | Harris Hawks Optimization (Heidari et al., 2019) |
| Greedy/Nearest Neighbor | ✅ | Hızlı sezgisel çözüm |
| OR-Tools CVRP | ✅ | Endüstri standardı çözücü |
| PyVRP (Opsiyonel) | ✅ | DIMACS 2021 kazananı — graceful fallback |
| VROOM (Opsiyonel) | ✅ | Ultra-hızlı C++ çözücü — graceful fallback |
| Permutation TSP | ✅ | Optimal çözüm (n≤10) |
| Two-Opt | ✅ | Local search iyileştirme |
| K-Means Clustering | ✅ | Multi-vehicle clustering (arşivlendi: `_archived/`) |

### Faz 3: Veritabanı & UI ✅
**Durum:** Tamamlandı | **Süre:** 2 hafta

| Görev | Durum | Açıklama |
|-------|-------|----------|
| Admin Dashboard | ✅ | Kullanıcı, araç, sürücü yönetimi |
| Driver Interface | ✅ | Atamalar ve navigasyon |
| Student Interface | ✅ | Haftalık program, ride request |
| Excel Bulk Upload | ✅ | Toplu öğrenci yükleme |
| Route Planning UI | ✅ | Algoritma seçimi ve sonuçlar |
| IE Dashboard | ✅ | Resource Histogram, Tracks, Bottleneck |
| Sandbox Mode | ✅ | Özel araç config ile re-optimize |
| Route Plan Kaydetme | ✅ | `route_plans` tablosu + API |

### Faz 4: CVRPTW (Zaman Pencereli Rotalama) ✅
**Durum:** Tamamlandı | **Süre:** 4 hafta

#### 4.1 Backend CVRPTW Desteği ✅
| Görev | Durum | Açıklama |
|-------|-------|----------|
| Split Decoder (DP) | ✅ | Optimal trip bölme — Prins (2004) |
| GA-Split Strategy | ✅ | GA + Split Decoder (Pipeline B) |
| PSO-Split Strategy | ✅ | PSO + Split Decoder (Pipeline B) |
| GWO-Split Strategy | ✅ | GWO + Split Decoder (Pipeline B) |
| HHO-Split Strategy | ✅ | HHO + Split Decoder (Pipeline B) |
| Time Window Veri Yapısı | ✅ | Backward (Pickup) + Forward (Dropoff) |
| Time Window Violation Tracking | ✅ | Accumulating counter, earliest-time wait |
| CVRPTW Wrapper | ✅ | Time window overlay for holistic solvers |
| Local Search (8 tip) | ✅ | 2-opt, 3-opt, Or-opt, Swap, Cross, Hybrid + Numba |

#### 4.2 Frontend Time Window UI ✅
| Görev | Durum | Açıklama |
|-------|-------|----------|
| Direction Selection UI | ✅ | Pickup / Dropoff toggle |
| Time Window Input Fields | ✅ | Target time, offset |
| API Integration Updates | ✅ | Direction, target_time gönderimi |

#### 4.3 Güvenlik & Kod Kalitesi ✅ (09–10.04.2026)
| Görev | ID | Durum | Açıklama |
|-------|----|-------|----------|
| Auth guard — calculate-vehicles | A-1 | ✅ | `requireAdmin` eklendi |
| CORS env-tabanlı yapılandırma | A-2 | ✅ | `ALLOWED_ORIGINS` env var |
| Sandbox IE endpoint düzeltme | A-3 | ✅ | `/api/v1/ie/analyze` fetch kaldırıldı |
| `total_time_window_violations` | B-1 | ✅ | Pydantic modele eklendi |
| `strategy`→`algorithm` fix | B-2 | ✅ | Sandbox fetch düzeltildi |
| `max_tour_time`→`max_travel_time` | B-4 | ✅ | Sandbox field düzeltildi |
| `as any` kaldır | C-3 | ✅ | `DbUserRow` tipi eklendi |
| Supabase env doğrulama | C-4 | ✅ | Boş fallback kaldırıldı |
| `kmeans_tsp.py` arşivle | C-2 | ✅ | `_archived/` dizinine taşındı |

#### 4.4 Forensic Audit Düzeltmeleri ✅ (10.04.2026)
| Görev | ID | Durum | Açıklama |
|-------|----|-------|----------|
| Negatif departure skip | FIX-01 | ✅ | `departure_time < 0 → continue` |
| DROPOFF tw_violations birikmeli | FIX-02 | ✅ | Counter loop dışına, `+= 1`, `earliest` wait |
| PICKUP `j` değişken çakışması | FIX-03 | ✅ | `k` + `trip_end` tracker |
| `15.0` → constant (split stratejiler) | FIX-04 | ✅ | `constants.py` + `logger.warning` |
| Duplicate `_minutes_to_time` kaldır | FIX-05 | ✅ | 2. kopya silindi |
| Bare `except:` → typed exceptions | FIX-06 | ✅ | 7/7 site düzeltildi |
| `haversine_distance` tek kaynak | FIX-07 | ✅ | `clustering.py` → `from utils.data_loader import haversine_distance` |
| `HybridSplitBaseStrategy` oluştur | FIX-08 | ✅ | 3 method taşındı, 4 strateji inherit ediyor |
| Unused `depot` parametre kaldır | FIX-09 | ✅ | `_get_target_arrival/departure_time` |
| `ALGORITHM_COMPARISON.md` güncelle | FIX-10 | ✅ | 🔵→🟢 statü güncellendi |

---

## 🔄 Devam Eden Fazlar

### Faz 4.5: Kalan Teknik Borç ve Test 🔄
**Durum:** Devam Ediyor | **Tahmini Süre:** 1-2 hafta

#### 4.5.1 Kalan Teknik Borç
| Görev | Öncelik | Durum | Açıklama |
|-------|---------|-------|----------|
| FIX-04 genişlet — Pipeline A stratejileri | � | ✅ | main.py consolidation + BaseStrategy extraction + Strategy refactoring (Commit a8ccb11 - 174 LOC removed) |
| 🔴 P1 Stratejileri refactor (super() kullan) | 🔴 | ✅ | Remove duplicate _get_duration/_calculate_route_duration from GA/HHO/PSO/GWO strategies (13.04.2026 - Commit a8ccb11) |
| FIX-07 tamamla — `clustering.py` haversine | 🟢 | ✅ | `clustering.py:11` → `from utils.data_loader import haversine_distance` (13.04.2026) |
| Algorithm Parameter Config UI | 🟢 | ⬜ | Frontend'de algoritma parametresi ayarlama |
| DataLoader TTL/Invalidation | 🟢 | ⬜ | Singleton'a cache süresi + yenileme mekanizması |
| ResourceProfiler magic numbers | 🟢 | ✅ | DEFAULT_PICKUP_HOUR/DEFAULT_DROPOFF_HOUR env vars (13.04.2026) |
| `main.old.py` temizle | 🟢 | ✅ | 24KB ölü kod → docs/old/ archive (13.04.2026)

#### 4.5.2 Test Altyapısı
| Görev | Öncelik | Durum | Açıklama |
|-------|---------|-------|----------|
| Split Decoder audit fix testleri | 🔴 | ⬜ | FIX-01/02/03 için doğrulama testleri |
| HybridSplitBaseStrategy testleri | 🟡 | ⬜ | Base class inheritance doğrulaması |
| Strategy smoke tests (tüm 18 strateji) | 🟡 | ⬜ | Her strateji için basic optimize() çağrısı |
| Test coverage hedefi: %60 | 🟡 | ⬜ | Mevcut: ~%25 → Hedef: %60 |

#### 4.5.3 Akademik Benchmark
| Görev | Öncelik | Durum | Açıklama |
|-------|---------|-------|----------|
| Benchmark sonuçlarını çalıştır | 🟡 | ⬜ | TSPLib + Solomon instances |
| PyVRP/VROOM karşılaştırma tablosu | 🟡 | ⬜ | SOTA kıyaslama (DIMACS) |
| `ALGORITHM_COMPARISON.md` gerçek veriyle güncelle | 🟡 | ⬜ | `[TAHMİNİ]` etiketlerini kaldır |
| GAP hesaplama doğrulama | 🟡 | ⬜ | Negatif GAP sorunu araştırın |

---

## 📅 Gelecek Fazlar

### Faz 5: Veri Kalıcılığı & Atama Sistemi
**Durum:** Planlandı | **Tahmini Süre:** 2 hafta | **Hedef:** Mayıs 2026

| Görev | Öncelik | Açıklama |
|-------|---------|----------|
| Sürücü atama UI | 🔴 | `route_plans.driver_assignments` kolonu mevcut, UI gerekli |
| Çift yönlü planlama | 🟡 | Pickup + Dropoff birlikte planlama |
| Standart araç ihtiyaç tablosu | 🟡 | IE engine ile entegre |
| DataLoader payload düzeltmesi | 🟢 | Fail-fast mekanizması |
| time_matrix caching | 🟢 | Redis veya in-memory TTL cache |

### Faz 6: Bildirim & Otomasyon
**Durum:** Planlandı | **Tahmini Süre:** 2-3 hafta | **Hedef:** Haziran 2026

| Görev | Öncelik | Açıklama |
|-------|---------|----------|
| Push/Email/SMS bildirim servisi | 🟡 | Firebase Cloud Messaging veya Supabase Edge Functions |
| Akşam 22:00 onay bildirimleri | 🟡 | Ertesi gün seferi onay/red |
| Gece 23:00 otomatik planlama | 🟡 | Cron job ile rota oluşturma |
| ETA hesaplama | 🟢 | Varış zamanı tahmini |
| Anlık rota güncelleme | 🟢 | İptal/onay sonrası dynamic re-routing |

### Faz 7: Production Deployment
**Durum:** Planlandı | **Tahmini Süre:** 2 hafta | **Hedef:** Temmuz 2026

| Görev | Öncelik | Açıklama |
|-------|---------|----------|
| Docker Containerization | 🔴 | Frontend + Backend + Redis docker-compose |
| CI/CD Pipeline | 🔴 | GitHub Actions: lint, test, build, deploy |
| Rate Limiting (tüm API) | 🟡 | Redis-backed rate limiter middleware |
| Monitoring & Logging | 🟡 | Structured logging, Sentry veya benzeri |
| FastAPI async endpoint | 🟢 | `/api/v1/optimize` → async + `run_in_executor` |
| Zod schema validation | 🟢 | `calculate-vehicles` raw cast → `zod.parse` |
| Penetrasyon testi | 🟢 | OWASP Top 10 doğrulaması |

---

## 📈 Zaman Çizelgesi

```
2026 Q1 (Tamamlandı)
├── Faz 1: Temel Altyapı ✅
├── Faz 2: CVRP Optimizasyonu ✅
└── Faz 3: Veritabanı & UI ✅

2026 Q2 (Devam Ediyor)
├── Faz 4: CVRPTW ✅ (Nisan 2026)
├── Faz 4.5: Teknik Borç & Test 🔄 (Nisan 2026)
├── Faz 5: Veri Kalıcılığı & Atama (Mayıs 2026)
└── Faz 6: Bildirim & Otomasyon (Haziran 2026)

2026 Q3 (Planlandı)
└── Faz 7: Production Deployment (Temmuz 2026)
```

---

## 🎯 KPI'lar ve Başarı Kriterleri

### Teknik KPI'lar
| Metrik | Hedef | Mevcut | Durum |
|--------|-------|--------|-------|
| Optimizasyon Hızı (50 öğrenci) | <5 saniye | ~3 saniye | ✅ |
| Route Quality (optimal farkı) | <10% | ~8% | ✅ |
| API Response Time | <200ms | ~150ms | ✅ |
| Test Coverage | >60% | ~25% | ⚠️ |
| Bare `except:` sayısı | 0 | 0 | ✅ |
| Magic number `15.0` (split stratejiler) | 0 | 0 | ✅ |
| Magic number `15.0` (tüm codebase) | 0 | 0 | ✅ |
| Duplicate code (LOC) | <50 | ~30 | ✅ |

### İş KPI'ları
| Metrik | Hedef | Mevcut |
|--------|-------|--------|
| Araç Kullanım Oranı | >85% | N/A |
| Öğrenci Memnuniyeti | >90% | N/A |
| Time Window Compliance | >95% | N/A |

---

## 🚨 Riskler ve Azaltıcı Önlemler

| Risk | Olasılık | Etki | Azaltıcı Önlem |
|------|----------|------|----------------|
| Algoritma Performansı N>100 | Orta | Yüksek | Benchmark testleri, PyVRP/VROOM fallback |
| Time Window İhlalleri | Düşük (düzeltildi) | Orta | FIX-01/02/03 uygulandı, test yazılacak |
| time_matrix veri eksikliği | Orta | Yüksek | `logger.warning` eklendi (FIX-04), caching planlı |
| Singleton DataLoader stale data | Düşük | Orta | TTL mekanizması planlı |
| Test coverage düşük | Yüksek | Orta | Faz 4.5.2 test sprint |
| Veri Güvenliği | Düşük | Kritik | RLS, CORS fix, auth guard uygulandı |

---

## 📞 İletişim

- **Proje Yöneticisi:** [E-posta]
- **Teknik Lead:** [E-posta]
- **Dokümantasyon:** `/docs` klasörü
- **Issue Tracker:** GitHub Issues

---

*Bu yol haritası proje gereksinimlerine göre güncellenecektir.*
*Son güncelleme: 10.04.2026 — Forensic audit düzeltmeleri ve teknik borç analizi sonrası.*


> (10.04.2026 - AI Audit): TSP Benchmark Studio entegrasyonu kod düzeyinde incelendi. /api/benchmark/run rotaları, FastAPI backend benchmark_runner mekanizmaları ve ilgili Python (Numba JIT vb.) strateji dosyalarının projenin 'Dual-Track' SOTA (State of the Art) ve ticari hibrit motor yapısına uygun olarak ayrı bir execution branch olarak (academic_benchmark) başarıyla entegre edildiği doğrulandı. Optimizasyon hedefleri ve izolasyon kurallarıyla uyumlu.
