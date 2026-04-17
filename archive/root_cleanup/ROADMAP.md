# UniRide — Gelistirme Yol Haritasi (Roadmap) v3

**Tarih:** 15.04.2026 (Guncellendi)  
**Odak:** TSP/VRP/CVRPTW Esnek Yapı + Benchmark Suite Web Arayuzu + Cekirdek Mimari  
**Prensip:** Kod uzerinden teyit edilmis bilgiler esas alinmistir. Hicbir zaman random/placeholder veri KULLANILMAZ.

---

## Problem Tipleri

Bu platform 3 problem tipini destekleyecek esnek bir mimariye sahiptir:

| Problem Tipi | Aciklama | Mevcut Durum |
|-------------|----------|-------------|
| **Standard TSP** | TSPLIB benchmark problemleri (EUC_2D) | ✅ Mevcut — TSPLIB veri seti indirilebilir |
| **CVRP** | Kapasite kisitli araç rotalama | ✅ Mevcut — Pipeline A/B stratejileri |
| **CVRPTW** | Kapasite + zaman pencere kisitli | ✅ `get_time_windows()` implement edildi |

**Kilit Prensip:** Mevcut benchmark yapısı Standard TSPLIB problemlerini cozmek uzere kurgulanmistir. CVRPTW altyapisi hazir, pickup_time/dropoff_time parse ediliyor.

---

## ✅ FAZ 1: Python Optimizer — Kritik Bug Fixleri [TAMAMLANDI]
**Hedef:** Optimizer'in dogru ve guvenilir calismasini saglamak

| # | Gorev | Detay | Durum |
|---|-------|-------|-------|
| 1.1 | `import logging` ekle | 16 strateji dosyasina `import logging` + logger tanimi | ✅ |
| 1.2 | `get_time_windows()` implement et | `schemas.py:124-160` — StudentNode'lardaki pickup_time/dropoff_time parse edip TimeWindow dict olustur | ✅ |
| 1.3 | Random fallback kaldir | benchmark_runner.py — Hata durumunda proper error report, NaN donusumu | ✅ |
| 1.4 | TSPLIB problem endpoint'leri | Python API: `/api/v1/benchmark/problems`, `/api/v1/benchmark/problems/{name}`, `/api/v1/benchmark/download/{name}` | ✅ |
| 1.5 | Benchmark /run endpoint fix | Problem name → BenchmarkProblem cevirisi + TSPLIB parser + optimal score lookup + euclidean distance | ✅ |
| 1.6 | Deprecated datetime.utcnow() | `benchmark_state.py` — `datetime.now(timezone.utc)` kullaniliyor | ✅ |
| 1.7 | Singleton thread-safety | `patterns.py` — Double-checked locking ile thread-safe SingletonMeta | ✅ |
| 1.8 | Stale yorumlari temizle | `main.py` — Temiz ve guncel dokumanlar | ✅ |

**Faz 1 Dogrulama:**
- greedy(eil51): tour=513.61, gap=20.57%
- two_opt(eil51): tour=452.71, gap=6.27%
- Benchmark Suite UI: 3-sekmeli arayuz calisiyor

---

## ✅ FAZ 2: Web Benchmark Suite — Sec, Calistir, Gor [TAMAMLANDI]
**Hedef:** Web arayuzunden TSPLIB problemlerini sec, calistir, sonuclari gorsellestir

| # | Gorev | Detay | Durum |
|---|-------|-------|-------|
| 2.1 | Next.js API Routes | 4 API route: `/api/benchmark/run`, `/api/benchmark/status`, `/api/benchmark/stop`, `/api/benchmark/problems` | ✅ |
| 2.2 | Benchmark Service | `src/services/benchmark-service.ts` — TypeScript tipleri + fetch wrapper + polling | ✅ |
| 2.3 | Benchmark Sayfasi | 3 sekmeli UI: (a) Yapilandirma, (b) Calisma/Progress, (c) Sonuclar/Gorsellestirme — Recharts | ✅ |
| 2.4 | Sidebar Menu | Admin altinda "Benchmark Suite" linki mevcut | ✅ |
| 2.5 | Sonuc Gorsellestirme | Recharts: gap analizi, performans tablosu, algoritma karsilastirma, JSON export | ✅ |

---

## FAZ 3: Cekirdek Mimari Duzeltmeler (Sonraki)

| # | Gorev | Oncelik |
|---|-------|---------|
| 3.1 | RLS users_update_own role kisitlama | P0 |
| 3.2 | RLS notifications_insert service_role | P0 |
| 3.3 | NEXT_PUBLIC_DEV_RESET_SECRET kaldir | P0 |
| 3.4 | AuthContext setUser kaldir | P0 |
| 3.5 | Admin sayfalari role guard | P0 |
| 3.6-3.15 | Diger core fixes (bkz. CODE_REVIEW_REPORT.md) | P1-P2 |

## Milestone'lar

| Milestone | Faz | Gosterge | Durum |
|-----------|-----|---------|-------|
| **M1: Optimizer Stabil** | 1.1-1.3 | import logging, get_time_windows, no random fallback | ✅ |
| **M2: Benchmark API Tam** | 1.4-1.5 | TSPLIB endpoint, /run resolution, euclidean distance | ✅ |
| **M3: Benchmark UI Canli** | 2.1-2.5 | Web'den sec, calistir, gorsellestir | ✅ |
| **M4: Guvenlik Duzeltme** | 3.1-3.5 | Kritik guvenlik aciklari kapatildi | ⬜ |

---

*Kesin kural: Random/placeholder veri ASLA kullanilmaz. Tum sonuclar gercek TSPLIB/optimizer verilerinden elde edilir.*
