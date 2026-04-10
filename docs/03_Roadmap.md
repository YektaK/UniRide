# UniRide CVRPTW - Geliştirme Yol Haritası

## Sürüm: 2.1.0 | Tarih: 09 Nisan 2026 (09.04.2026 - Ekleyen: Copilot AI)

---

## 📊 Genel Bakış

Bu yol haritası, UniRide Özel Öğrenci Taşıma Sistemi'nin CVRPTW (Kapasiteli Araç Rotalama Problemi Zaman Pencereli) entegrasyonu için kapsamlı bir plan sunmaktadır. Proje, 4 ana fazdan oluşmakta olup, her faz belirli hedeflere odaklanmaktadır.

---

## ✅ Tamamlanan Fazlar

### Faz 1: Temel Altyapı ✅
**Durum:** Tamamlandı | **Tahmini Süre:** 2 hafta

| Görev | Durum | Açıklama |
|-------|-------|----------|
| Next.js 16 Kurulumu | ✅ | App Router, TypeScript, Tailwind CSS |
| Supabase Entegrasyonu | ✅ | PostgreSQL, RLS policies |
| Python Backend API | ✅ | FastAPI, CORS, Health check |
| Temel UI Bileşenleri | ✅ | shadcn/ui components |
| Authentication | ✅ | Supabase Auth |

### Faz 2: CVRP Optimizasyonu ✅
**Durum:** Tamamlandı | **Tahmini Süre:** 3 hafta

| Görev | Durum | Açıklama |
|-------|-------|----------|
| Genetic Algorithm | ✅ | OX1 crossover, swap/inversion mutation |
| PSO | ✅ | Swap-based velocity, discrete PSO |
| Greedy/Nearest Neighbor | ✅ | Hızlı sezgisel çözüm |
| OR-Tools CVRP | ✅ | Endüstri standardı çözücü |
| Permutation TSP | ✅ | Optimal çözüm (n≤10) |
| K-Means Clustering | ✅ | Multi-vehicle clustering |

### Faz 3: Veritabanı & UI ✅
**Durum:** Tamamlandı | **Tahmini Süre:** 2 hafta

| Görev | Durum | Açıklama |
|-------|-------|----------|
| Admin Dashboard | ✅ | Kullanıcı, araç, sürücü yönetimi |
| Driver Interface | ✅ | Atamalar ve navigasyon |
| Student Interface | ✅ | Haftalık program, ride request |
| Excel Bulk Upload | ✅ | Toplu öğrenci yükleme |
| Route Planning UI | ✅ | Algoritma seçimi ve sonuçlar |

---

## 🔄 Devam Eden Fazlar

### Faz 4: CVRPTW (Zaman Pencereli Rotalama) 🔄
**Durum:** Devam Ediyor | **Tahmini Süre:** 3-4 hafta

#### 4.1 Backend CVRPTW Desteği (1-2 hafta)
| Görev | Durum | Öncelik |
|-------|-------|---------|
| GWO Strategy Implementasyonu | ✅ TAMAMLANDI (09.04.2026 - Ekleyen: Copilot AI) | Yüksek |
| HHO Strategy Implementasyonu | ✅ TAMAMLANDI (09.04.2026 - Ekleyen: Copilot AI) | Yüksek |
| Split Decoder (Pipeline B) | ✅ TAMAMLANDI | Yüksek |
| Time Window Veri Yapısı | ✅ TAMAMLANDI | Yüksek |
| Backward Scheduling (Pickup) | ✅ TAMAMLANDI | Yüksek |
| Forward Scheduling (Dropoff) | ✅ TAMAMLANDI | Yüksek |
| Time Window Violation Tracking | ✅ TAMAMLANDI | Orta |

#### 4.2 Frontend Time Window UI (1 hafta)
| Görev | Durum | Öncelik |
|-------|-------|---------|
| Direction Selection UI | ✅ TAMAMLANDI | Yüksek |
| Time Window Input Fields | ✅ TAMAMLANDI | Yüksek |
| Algorithm Parameter Config UI | ⬜ Bekliyor | Orta |
| API Integration Updates | ✅ TAMAMLANDI | Yüksek |

#### 4.3 Test & Doğrulama (1 hafta)
| Görev | Durum | Öncelik |
|-------|-------|---------|
| Unit Tests | ⬜ Bekliyor | Orta |
| Integration Tests | ⬜ Bekliyor | Orta |
| Performance Benchmarks | 🔄 Kısmi (TSPLib benchmark mevcut) | Düşük |

---

## 🔧 Faz 4.4: Kod Kalitesi ve Güvenlik Düzeltmeleri (09.04.2026 - Ekleyen: Copilot AI)
**Durum:** Devam Ediyor | **Referans:** `docs/05_Code_Quality_Roadmap.md`

| Görev | ID | Durum | Öncelik | Paralel? |
|-------|-----|-------|---------|---------|
| Auth guard — POST /api/calculate-vehicles | A-1 | ⬜ Bekliyor | 🔴 KRİTİK | ✅ |
| CORS env-tabanlı yapılandırma | A-2 | ⬜ Bekliyor | 🔴 YÜKSEK | ✅ |
| Sandbox IE endpoint düzeltme | A-3 | ⬜ Bekliyor | 🔴 YÜKSEK | ✅ |
| `total_time_window_violations` modele ekle | B-1 | ⬜ Bekliyor | 🟡 ORTA | ✅ |
| `strategy`→`algorithm` field fix (sandbox) | B-2 | ⬜ Bekliyor | 🟡 ORTA | ✅ |
| `strategy`→`algorithm` field fix (calculate-vehicles) | B-3 | ⬜ Bekliyor | 🟡 ORTA | ✅ |
| `max_tour_time`→`max_travel_time` (sandbox) | B-4 | ⬜ Bekliyor | 🟡 ORTA | ✅ |

---

## 📅 Gelecek Fazlar

### Faz 5: Bildirim Sistemi
**Durum:** Planlandı | **Tahmini Süre:** 2 hafta

| Görev | Açıklama |
|-------|----------|
| Notification Service | Push/email/SMS bildirimler |
| Evening Confirmations | Akşam 22:00 bildirimleri |
| Student Confirmation UI | Onay/Red butonları |
| Admin Notification Panel | Bildirim yönetimi |

### Faz 6: Otomatik Planlama
**Durum:** Planlandı | **Tahmini Süre:** 2 hafta

| Görev | Açıklama |
|-------|----------|
| Scheduled Jobs | Cron job entegrasyonu |
| Nightly Planning | Gece 23:00 rota planlama |
| ETA Calculation | Varış zamanı tahmini |
| Dynamic Re-routing | Anlık rota güncelleme |

### Faz 7: Production Deployment
**Durum:** Planlandı | **Tahmini Süre:** 1 hafta

| Görev | Açıklama |
|-------|----------|
| Docker Containerization | Dockerfile, docker-compose |
| CI/CD Pipeline | GitHub Actions |
| Monitoring | Logging, metrics |
| Security Audit | Penetrasyon testi |

---

## 📈 Zaman Çizelgesi

```
2026 Q1 (Tamamlandı)
├── Faz 1: Temel Altyapı ✅
├── Faz 2: CVRP Optimizasyonu ✅
└── Faz 3: Veritabanı & UI ✅

2026 Q2 (Devam Ediyor)
├── Faz 4: CVRPTW 🔄 (Nisan 2026)
├── Faz 5: Bildirim Sistemi (Mayıs 2026)
└── Faz 6: Otomatik Planlama (Haziran 2026)

2026 Q3 (Planlandı)
└── Faz 7: Production Deployment (Temmuz 2026)
```

---

## 🎯 KPI'lar ve Başarı Kriterleri

### Teknik KPI'lar
| Metrik | Hedef | Mevcut |
|--------|-------|--------|
| Optimizasyon Hızı | <5 saniye (50 öğrenci) | ~3 saniye ✅ |
| Route Quality | <10% optimal farkı | ~8% ✅ |
| API Response Time | <200ms | ~150ms ✅ |
| Test Coverage | >80% | ~40% ⚠️ |

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
| Algoritma Performansı | Orta | Yüksek | Benchmark testleri, optimizasyon |
| Time Window İhlalleri | Yüksek | Orta | Soft constraint, penalty function |
| API Entegrasyon Sorunları | Düşük | Yüksek | Fallback mekanizması |
| Veri Güvenliği | Düşük | Kritik | RLS, encryption, audit |

---

## 📞 İletişim

- **Proje Yöneticisi:** [E-posta]
- **Teknik Lead:** [E-posta]
- **Dokümantasyon:** `/docs` klasörü
- **Issue Tracker:** GitHub Issues

---

*Bu yol haritası proje gereksinimlerine göre güncellenecektir.*
