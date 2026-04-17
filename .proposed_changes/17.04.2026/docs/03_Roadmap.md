# UniRide — Kapsamli Gelistirme Yol Haritasi (Roadmap) v4

**Tarih:** 15.04.2026  
**Yazar:** Z.ai Code  
**Proje:** UniRide — Universite Ogrenci Ulasim Sistemi  
**Odak:** TSP / VRP / CVRPTW Esnek Mimari + Benchmark Suite + Cekirdek Mimari Duzeltmeleri + Akademik SOTA  
**Prensip:** Kod uzerinden teyit edilmis bilgiler esas alinmistir. Hicbir zaman random/placeholder veri KULLANILMAZ.

---

## Icerik

1. [Yonetici Ozeti ve Genel Durum](#1-yonetici-ozeti-ve-genel-durum)
2. [Faz Tamamlanma Ozeti](#2-faz-tamamlanma-ozeti)
3. [Problem Tipleri ve Desteklenen Siniflandirma](#3-problem-tipleri-ve-desteklenen-siniflandirma)
4. [Dual-Track Vizyon: Ticari + Akademik](#4-dual-track-vizyon-ticari--akademik)
5. [Faz 1: Python Optimizer — Kritik Bug Fixleri [TAMAMLANDI]](#5--faz-1-python-optimizer--kritik-bug-fixleri-tamamlandi)
6. [Faz 2: Web Benchmark Suite [TAMAMLANDI]](#6--faz-2-web-benchmark-suite-tamamlandi)
7. [Faz 3: Cekirdek Mimari Duzeltmeleri [DEVAM EDIYOR]](#7--faz-3-cekirdek-mimari-duzeltmeleri-devam-ediyor)
8. [Faz 4: Input Validation ve Tip Guvenligi](#8--faz-4-input-validation-ve-tip-guvenligi)
9. [Faz 5: Performans ve Kod Kalitesi](#9--faz-5-performans-ve-kod-kalitesi)
10. [Faz 6: Akademik SOTA ve Yayin Hazirlik](#10--faz-6-akademik-sota-ve-yayin-hazirlik)
11. [Milestone Takip Tablosu](#11-milestone-takip-tablosu)
12. [Zaman Cizelgesi ve Tahminler](#12-zaman-cizelgesi-ve-tahminler)
13. [Teknoloji Stack Referansi](#13-teknoloji-stack-referansi)
14. [Ekler: Strateji Agaci ve Benchmark Sonuclari](#14-ekler-strateji-agaci-ve-benchmark-sonuclari)

---

## 1. Yonetici Ozeti ve Genel Durum

UniRide projesi universite ogrenci ulasim sistemini optimize eden bir CVRP/TSP tabanli web uygulamasi olarak gelistirilmektedir. Proje **ticari urun** ve **akademik arastirma** olmak uzere iki paralel izde ilerlemektedir.

### Genel Progres

| Kategori | Toplam | Tamamlandi | Devam Ediyor | Bekliyor |
|----------|--------|------------|--------------|----------|
| **Fazlar** | 6 | 2 | 1 | 3 |
| **Milestone'lar** | 7 | 3 | 0 | 4 |
| **Toplam Gorev** | ~65+ | ~30 | 14 | ~21 |

### Temel Teknoloji Mimari

```
[Browser] → [Next.js 16 (TypeScript)] → [Supabase (PostgreSQL + Auth + RLS)]
                     ↕
              [Python FastAPI Optimizer (Port 8099)]
                     ↕
              [TSPLIB Benchmark Engine]
                     ↕
              [OR-Tools / PyVRP / VROOM SOTA Solvers]
```

### Code Review Ozeti

13.04.2026 tarihinde gerceklestirilen kapsamli code review'da 120+ dosya incelenmis, 80+ bulgu tespit edilmistir:

| Severite | Sayi | Temel Kategoriler |
|----------|------|-------------------|
| **KRITIK** | 12 | Guvenlik aciklari (RLS privilege escalation, secret exposure), calisma zamani hatalari, veri kaybi |
| **YUKSEK** | 22 | Performans, tip guvenligi, RLS eksiklikleri, N+1 query'ler |
| **ORTA** | 30 | Kod kalitesi, input validation, tutarsizliklar, missing indexes |
| **DUSUK** | 16 | Stil, dokumantasyon, kucuk iyilestirmeler |

> Detayli rapor: `CODE_REVIEW_REPORT.md`  
> Gelistirme gecmisi: `worklog.md`  
> Ozet roadmap: `ROADMAP.md` (root)

---

## 2. Faz Tamamlanma Ozeti

```
Faz 1 ████████████████████ 100%  (Python Optimizer — Kritik Bug Fixleri)
Faz 2 ████████████████████ 100%  (Web Benchmark Suite)
Faz 3 ███░░░░░░░░░░░░░░░░░  14%  (Cekirdek Mimari Duzeltmeleri)  ← AKTIF
Faz 4 ░░░░░░░░░░░░░░░░░░░░   0%  (Input Validation & Tip Guvenligi)
Faz 5 ░░░░░░░░░░░░░░░░░░░░   0%  (Performans & Kod Kalitesi)
Faz 6 ░░░░░░░░░░░░░░░░░░░░   0%  (Akademik SOTA & Yayin)
```

### Fazlarin Birbirine Bagimliligi

```
Faz 1 (Optimizer Stable)
  └──→ Faz 2 (Benchmark Suite)
        └──→ Faz 3 (Core Architecture)
              ├──→ Faz 4 (Validation & Types)
              │     └──→ Faz 5 (Performance & Quality)
              └──→ Faz 6 (Academic SOTA) [parallel with 4-5]
```

---

## 3. Problem Tipleri ve Desteklenen Siniflandirma

Bu platform 3 problem tipini destekleyecek esnek bir mimariye sahiptir:

| Problem Tipi | Aciklama | Standart Veri Seti | Mevcut Durum |
|-------------|----------|--------------------|-------------|
| **Standard TSP** | Simetrik Traveling Salesman Problem (EUC_2D) | TSPLIB (46 problem: eil51 → pr2392) | ✅ Tam calisan |
| **CVRP** | Kapasite kisitli Arac Rotalama (Capacitated VRP) | Pipeline A/B stratejileri | ✅ Tam calisan |
| **CVRPTW** | Kapasite + Zaman Pencere kisitli (Time Windows) | `get_time_windows()` implement edildi | ⚠️ Altyapi hazir, data aktarilacak |

**Kilit Prensip:** Mevcut benchmark yapisi Standard TSPLIB problemlerini cozmek uzere kurgulanmistir. CVRPTW altyapisi hazirdir — `pickup_time`/`dropoff_time` parse ediliyor, `CVRPTWDecoder` implement edilmistir. Veri akisi tam olarak baglandiginda aktif hale gelecektir.

### TSPLIB Dogrulama Sonuclari (NINT Rounded, EUC_2D Standard)

| Algoritma | Problem | Tour Length | Optimal | Gap |
|-----------|---------|-------------|---------|-----|
| greedy (NN) | eil51 | 511 | 426 | 19.95% |
| two_opt | eil51 | 453 | 426 | 6.34% |

> Akademik referans: Prins (2004), Clerc & Kennedy (2002), Helsgaun (2000)

---

## 4. Dual-Track Vizyon: Ticari + Akademik

UniRide iki paralel hedefe hizmet eder:

### Track A: Ticari Urun (Commercial Product)

| Bilesen | Aciklama | Hedef |
|---------|----------|-------|
| **Ogrenci Paneli** | Ders programı girisi, ride talebi, takip | Universite ogrencileri |
| **Surucu Paneli** | Rotalari gor, navigasyon, assignment | Suruculer |
| **Admin Paneli** | User management, vehicle planning, reports | Isletme yoneticileri |
| **Rota Optimizer** | Multi-vehicle routing, time windows | Gercek dunya optimizasyonu |
| **Sandbox** | Simulasyon ortami, scenario test | Isletme karar destegi |
| **Bulk Upload** | Excel ile toplu ders programi yukleme | Admin verimliligi |

### Track B: Akademik Arastirma (Academic Research)

| Bilesen | Aciklama | Hedef |
|---------|----------|-------|
| **Benchmark Suite** | TSPLIB/CVRPLIB problemleri uzerinde algoritma testi | Akademik karsilastirma |
| **Algorithm Comparison** | Pipeline A (Cluster-First) vs Pipeline B (Route-First) | Yontem karsilastirmasi |
| **SOTA Integration** | PyVRP, VROOM, OR-Tools solver entegrasyonu | Basari tablosu |
| **CVRPTW Decoder** | Prins (2004) Split-based decoding | Akademik yayin |
| **ALNS Operators** | Adaptive Large Neighborhood Search | State-of-the-art |
| **Performance Paper** | Kararlastirilmis karsilastirma sonuclari | Konferans yayini |

### Paper Publication Goals

| Yil | Hedef | Konferans / Dergi | Konu |
|-----|-------|-------------------|------|
| **2026 H2** | Draft hazirla | Internal review | Hybrid meta-heuristic + SOTA karsilastirmasi |
| **2027 Q1** | Submit | IEEE ICTI / TRB | University transit routing optimization |
| **2027 Q3** | Submit | EJOR / CIE | ALNS + meta-heuristic hybrid approach |

---

## 5. ✅ FAZ 1: Python Optimizer — Kritik Bug Fixleri [TAMAMLANDI]

**Hedef:** Optimizer'in dogru ve guvenilir calismasini saglamak  
**Tarih araligi:** Tamamlandi  
**Sorumlu:** Z.ai Code  
**Toplam gorev:** 8 ana gorev + 4 TSPLIB dogruluk gorevi = **12 gorev**

### 5.1 Ana Gorevler

| # | Gorev | Detay | Dosya(lar) | Durum |
|---|-------|-------|-----------|-------|
| 1.1 | `import logging` ekle | 16 strateji dosyasina `import logging` + logger tanimi | `strategies/*.py` | ✅ |
| 1.2 | `get_time_windows()` implement et | `schemas.py:124-160` — StudentNode'lardaki pickup_time/dropoff_time parse edip TimeWindow dict olustur | `models/schemas.py` | ✅ |
| 1.3 | Random fallback kaldir | benchmark_runner.py — Hata durumunda proper error report, `float('nan')` donusumu | `benchmark_runner.py` | ✅ |
| 1.4 | TSPLIB problem endpoint'leri | Python API: `/api/v1/benchmark/problems`, `/problems/{name}`, `/download/{name}` | `main.py` | ✅ |
| 1.5 | Benchmark /run endpoint fix | Problem name → BenchmarkProblem cevirisi + TSPLIB parser + optimal score lookup + euclidean distance | `main.py`, `benchmark_runner.py` | ✅ |
| 1.6 | Deprecated datetime.utcnow() | `benchmark_state.py` — `datetime.now(timezone.utc)` kullaniliyor | `benchmark_state.py` | ✅ |
| 1.7 | Singleton thread-safety | `patterns.py` — Double-checked locking ile thread-safe SingletonMeta | `utils/patterns.py` | ✅ |
| 1.8 | Stale yorumlari temizle | `main.py` — Temiz ve guncel dokumanlar | `main.py` | ✅ |

### 5.2 TSPLIB Benchmark Dogruluk Gorevleri (D1-D4)

| # | Gorev | Aciklama | Dosya(lar) | Durum |
|---|-------|----------|-----------|-------|
| D1 | BenchmarkRunner tour_length | `_compute_tsplib_tour_distance()` — TSPLIB koordinatlarindan NINT-rounded euclidean distance | `benchmark_runner.py` | ✅ |
| D2 | DataLoader euclidean fallback | Supabase yokken `build_euclidean_matrix()` ile gercek mesafe matrisi. 16/16 strategy coordinates geciriyor | `data_loader.py`, 16 strategy files | ✅ |
| D3 | distance=0.0 kaldirma | PyVRP + VROOM stratejilerinde `distance=0.0` yerine `_dist()` helper ile gercek mesafe | `pyvrp_strategy.py`, `vroom_strategy.py` | ✅ |
| D4 | Auto-download .tsp | `download_tsplib_problem()` ve `ensure_tsplib_problems()` fonksiyonlari mevcut | `tsplib_parser.py` | ✅ |

### 5.3 Ek Duzeltmeler

| Gorev | Aciklama | Durum |
|-------|----------|-------|
| TSPLIB EUC_2D NINT Rounding | `tsplib_euc_2d_distance()` — per-edge `int(d+0.5)` rounding (TSPLIB standard) | ✅ |
| cvrptw_wrapper.py logging | Eksik `import logging` eklendi | ✅ |
| Port 8000 → 8099 | Optimizer API portu frontend ile eslestirildi | ✅ |
| CLI → Web Import Bridge | 3 yeni endpoint: `/cli/files`, `/cli/import`, `/cli/preview` | ✅ |

### Faz 1 Dogrulama

- `greedy(eil51)`: tour=511, gap=19.95% ✅
- `two_opt(eil51)`: tour=453, gap=6.34% ✅
- Benchmark Suite UI: 3-sekmeli arayuz calisiyor ✅
- TypeScript: `src/` dizininde 0 hata ✅

---

## 6. ✅ FAZ 2: Web Benchmark Suite [TAMAMLANDI]

**Hedef:** Web arayuzunden TSPLIB problemlerini sec, calistir, sonuclari gorsellestir  
**Tarih araligi:** Tamamlandi  
**Sorumlu:** Z.ai Code  
**Toplam gorev:** 5 ana gorev + 3 CLI import gorevi = **8 gorev**

### 6.1 Ana Gorevler

| # | Gorev | Detay | Dosya(lar) | Durum |
|---|-------|-------|-----------|-------|
| 2.1 | Next.js API Routes | 4 API route: `/api/benchmark/run`, `/api/benchmark/status`, `/api/benchmark/stop`, `/api/benchmark/problems` | `src/app/api/benchmark/*/route.ts` | ✅ |
| 2.2 | Benchmark Service | `benchmark-service.ts` — TypeScript tipleri + fetch wrapper + polling mekanizmasi | `src/services/benchmark-service.ts` | ✅ |
| 2.3 | Benchmark Sayfasi | 3 sekmeli UI (1352 satir): (a) Yapilandirma, (b) Calisma/Progress, (c) Sonuclar/Gorsellestirme — Recharts | `src/app/(app)/admin/benchmark/page.tsx` | ✅ |
| 2.4 | Sidebar Menu | Admin altinda "Benchmark Suite" linki mevcut | `src/components/layout/app-sidebar.tsx` | ✅ |
| 2.5 | Sonuc Gorsellestirme | Recharts: gap analizi, performans tablosu, algoritma karsilastirma, JSON export | `page.tsx` | ✅ |

### 6.2 CLI → Web Import Bridge

| # | Gorev | Detay | Endpoint | Durum |
|---|-------|-------|----------|-------|
| 2.6 | CLI dosya listesi | Mevcut CLI JSON dosyalarini listeler | `GET /api/v1/benchmark/cli/files` | ✅ |
| 2.7 | CLI import | CLI JSON → Web format donusumu | `POST /api/v1/benchmark/cli/import` | ✅ |
| 2.8 | CLI preview | Import oncesi format donusumu onizle | `GET /api/v1/benchmark/cli/preview` | ✅ |

### Benchmark Sayfasi Ozellikleri

- **Sekme 1 — Yapilandirma:**
  - 46 TSPLIB problemi secimi (kategori filtreleme, toplu secim)
  - Algoritma secimi (Pipeline A/B gruplama, recommended badge)
  - Ayarlar paneli (n_runs, seed, deney sayisi ozeti)
- **Sekme 2 — Calisma:**
  - Gercek zamanli ilerleme gosterimi (2s polling)
  - Her deney icin status ve mesafe gosterimi
- **Sekme 3 — Sonuclar:**
  - Bar chart gorsellestirme (Recharts)
  - Algoritma karsilastirma tablosu
  - Problem bazli karsilastirma tablosu
  - JSON export
  - Hizli test: eil51 + greedy otomatik secim

---

## 7. 🔄 FAZ 3: Cekirdek Mimari Duzeltmeleri [DEVAM EDIYOR]

**Hedef:** Guvenlik aciklarini kapatmak, data integrity'yi saglamak, uygulama stabilitesini artirmak  
**Tarih araligi:** Aktif  
**Sorumlu:** Z.ai Code  
**Toplam gorev:** 15 gorev  
**Mevcut ilerleme:** 1/15 tamamlandi

### 7.1 P0 — Kritik Guvenlik (Hemen Yapilmasi Gereken)

| # | Gorev | Aciklama | Kaynak Bulgu | Effort | Durum |
|---|-------|----------|-------------|--------|-------|
| **3.1** | RLS users_update_own role kisitlama | `WITH CHECK (role IS NOT DISTINCT FROM ...)` ile rol degisikligini engelle. Privilege escalation onlemek icin kritik. | CR-01 | 15 dk | ⬜ |
| **3.2** | RLS notifications_insert service_role | `WITH CHECK (true)` kaldir, sadece `TO service_role` ile kisitla. Herkes notification insert edebiliyor. | CR-02 | 15 dk | ⬜ |
| **3.3** | NEXT_PUBLIC_DEV_RESET_SECRET kaldir | Client-side dev reset Authorization header'dan kaldirildi. Server-side 3 kat guvenlik mevcut. | CR-03 | ✅ DONE | ✅ |
| **3.4** | AuthContext setUser kaldir | `setUser` context'ten cikart, `updateProfile` metodu ekle. Client-side privilege escalation riski. | CR-06 | 1 saat | ⬜ |
| **3.5** | Admin sayfalari role guard | 4 admin sayfasina `if (user?.role !== "admin") return <AccessDenied />;` ekle. | CR-12 | 1 saat | ⬜ |

### 7.2 P1 — Yuksek Oncelikli Duzeltmeler

| # | Gorev | Aciklama | Kaynak Bulgu | Effort | Durum |
|---|-------|----------|-------------|--------|-------|
| **3.6** | React Error Boundary | Tum uygulamada Error Boundary yok. Beyaz ekrani onlemek icin `layout.tsx`'e ekle. | HI-01 | 30 dk | ⬜ |
| **3.7** | Security headers ekle | `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy` | HI-02 | 30 dk | ⬜ |
| **3.8** | RLS write policies | `vehicles`, `routes`, `route_assignments`, `admin_settings` icin admin write policy ekle | HI-09 | 2 saat | ⬜ |
| **3.9** | cooldown_minutes column migration | `ALTER TABLE vehicles ADD COLUMN cooldown_minutes INTEGER NOT NULL DEFAULT 10;` | CR-04 | 15 dk | ⬜ |
| **3.10** | Singleton thread-safe strategy instances | Concurrent isteklerde `self.config` ve `self.rng` mutate ediyor. Her istekte yeni instance veya deepcopy. | CR-09 | 2 saat | ⬜ |
| **3.11** | User deletion order fix | Auth hesabini once sil, sonra DB. Basarisiz olursa rollback. Orphaned auth riski. | HI-04 | 30 dk | ⬜ |
| **3.12** | Pickup/dropoff filter fix | `pickupRequests` ve `dropoffRequests` ayni filtre kullaniyor. Direction field kontrolu ekle. | HI-05 | 30 dk | ⬜ |
| **3.13** | Schedule-to-requests time fix | Pickup ve dropoff zamanlari ayni degerlere set ediliyor. Dropoff zamanlarini dogru arrival time'lara set et. | HI-06 | 30 dk | ⬜ |
| **3.14** | Empty string falsy check | `if (updates.name)` — empty string `""` falsy. `!== undefined` kullanilmali. | MD-03 | 30 dk | ⬜ |
| **3.15** | Off-by-one date range | `lt("requested_pickup_time", "${rideDate}T23:59:59")` — `23:59:59.000` miss ediyor. | MD-18 | 15 dk | ⬜ |

### 7.3 Faz 3 Ek Bulgular (Code Review Report'tan)

Bu bulgular Faz 3 kapsaminda ele alinabilir veya Faz 4'e devredilebilir:

| # | Gorev | Aciklama | Kaynak | Oncelik |
|---|-------|----------|--------|---------|
| 3.E1 | PostgREST filter validation | `.or()` filter'ina regex validation ekle | CR-07 | P0 |
| 3.E2 | User tipinden password kaldir | Client-side `User` tipi `password?: string` iceriyor | CR-11 | P0 |
| 3.E3 | weekly_schedules_update_own WITH CHECK | `user_id` baskasinin ID'sine degistirilebiliyor | MD-10 | P1 |
| 3.E4 | route_plans drivers role check | Tum auth kullanicilar gorebiliyor, sadece admin/driver olmali | MD-09 | P1 |
| 3.E5 | FK constraints ekle | `users.weekly_schedule_id`, `ride_requests.vehicle_id` uzerinde FK yok | HI-10 | P1 |
| 3.E6 | admin_settings SELECT kisitla | Tum auth kullanicilar gorebiliyor | MD-27 | P1 |
| 3.E7 | Dead Prisma file kaldir | `src/lib/db.ts` — Prisma import ediyor ama kullanilmiyor | MD-11 | P2 |
| 3.E8 | Duplicate use-mobile files | `.ts` ve `.tsx` duplicate | MD-25 | P2 |
| 3.E9 | Duplicate vehicle-planning files | `page.tsx` ve `vehicle-planning-page.tsx` | MD-19 | P2 |
| 3.E10 | Password hint enumeration riski | Rate-limit cok agir yap | HI-08 | P1 |

### Faz 3 Checklist

```
[✅] 3.3 NEXT_PUBLIC_DEV_RESET_SECRET kaldirildi
[ ] 3.1 RLS users_update_own role restriction
[ ] 3.2 RLS notifications_insert service_role
[ ] 3.4 AuthContext setUser removed
[ ] 3.5 Admin page role guards (4 sayfa)
[ ] 3.6 React Error Boundary
[ ] 3.7 Security headers
[ ] 3.8 RLS write policies (4 tablo)
[ ] 3.9 cooldown_minutes migration
[ ] 3.10 Singleton thread-safe instances
[ ] 3.11 User deletion order
[ ] 3.12 Pickup/dropoff filter
[ ] 3.13 Schedule-to-requests time
[ ] 3.14 Empty string falsy check
[ ] 3.15 Off-by-one date range
```

---

## 8. ⬜ FAZ 4: Input Validation ve Tip Guvenligi

**Hedef:** Tum API endpoint'lerini Zod validation ile korumak, tip guvenligini saglamak  
**Tahmini surec:** 1-2 hafta  
**Bagimlilik:** Faz 3 tamamlanmali

### 8.1 Zod Schema Ekleme

| # | Gorev | Endpoint | Mevcut Durum | Hedef |
|---|-------|----------|-------------|-------|
| 4.1 | POST /api/auth/hint | Regex validation ekle (`^[a-zA-Z0-9._%+-@]+$`) | Hayir | ✅ |
| 4.2 | POST /api/auth/dev-reset | Password validation | Hayir | ✅ |
| 4.3 | POST /api/calculate-vehicles | `as` type assertion yerine Zod | Hayir | ✅ |
| 4.4 | POST /api/ride-confirmation | Zod schema | Hayir | ✅ |
| 4.5 | POST /api/sandbox | `any[]` students → Zod array | Hayir | ✅ |
| 4.6 | PUT /api/sandbox | Zod schema | Hayir | ✅ |
| 4.7 | POST /api/route-plans | Zod schema | Hayir | ✅ |
| 4.8 | PATCH /api/route-plans | Zod schema | Hayir | ✅ |
| 4.9 | PUT /api/admin/ride-requests | Status `z.enum([...])` ekle | Kismi | ✅ |
| 4.10 | PUT /api/admin/users | Zod schema | Hayir | ✅ |

### 8.2 Tip Guvenligi

| # | Gorev | Aciklama | Kaynak | Effort |
|---|-------|----------|--------|--------|
| 4.11 | Tum `*Row` snake_case tipleri | `DbVehicleRow`, `DbScheduleRow`, `DbRideRequestRow`, `DbRouteAssignmentRow`, `DbRouteRow` olustur | CR-05, HI-07 | 3 saat |
| 4.12 | `as any` cleanup (9 adet) | Tip assertions temizle | MD-13 | 2 saat |
| 4.13 | Status enum validation | `ride_requests.status`, `route_assignments.status` icin union type | HI-12 | 30 dk |
| 4.14 | `DbUser.passwordHash` kaldir | Phantom field | LO-13 | 10 dk |
| 4.15 | Database type tanimlari | `notifications`, `admin_settings`, `time_matrix` icin tipler | MD-21 | 1 saat |

### 8.3 Rate Limiter

| # | Gorev | Aciklama | Kaynak | Effort |
|---|-------|----------|--------|--------|
| 4.16 | Rate limiter Redis'e tasi | In-memory map Vercel serverless'ta ise yaramiyor | MD-01 | 2 saat |
| 4.17 | Password hint rate limit | Basarisiz giris denemesinden sonra goster | HI-08 | 1 saat |

---

## 9. ⬜ FAZ 5: Performans ve Kod Kalitesi

**Hedef:** Uygulama performansini artirmak, kod kalitesini iyilestirmek, teknoloji stack'ini guncellemek  
**Tahmini surec:** 2-3 hafta (1 sprint)  
**Bagimlilik:** Faz 4 tamamlanmali

### 9.1 Guvenlik Paketi Gecisi

| # | Gorev | Aciklama | Kaynak | Effort |
|---|-------|----------|--------|--------|
| **5.1** | xlsx → exceljs migration | `xlsx@^0.18.5` CVE-2023-30533 prototype pollution zafiyeti. Actively maintained alternatife gec. | HI-03 | 2 saat |

### 9.2 Performans Iyilestirmeleri

| # | Gorev | Aciklama | Kaynak | Effort |
|---|-------|----------|--------|--------|
| **5.2** | Reports N+1 query fix | Her ogrenci icin ayri API call → batch fetch ile tek seferde cek | HI-11 | 2 saat |
| **5.3** | Missing index ekle | `ride_requests.vehicle_id` index'i | MD-05 | 15 dk |
| **5.4** | Composite index (route_assignments) | `date, vehicle_id` composite index | MD-06 | 15 dk |
| **5.5** | Parallel time slot optimization | Sequential time slot → parallel execution | MD-24 | 2 saat |
| **5.6** | Only first vehicle capacity fix | Multiple active vehicle varsa sadece ilkinin kapasitesi kullaniliyor | MD-23 | 1 saat |

### 9.3 Kod Kalitesi

| # | Gorev | Aciklama | Kaynak | Effort |
|---|-------|----------|--------|--------|
| **5.7** | Pipeline A refactoring | ~800 satir kod tekrari (4 strateji). Base class veya mixin ile refactor et. | MD-16 | 4 saat |
| **5.8** | ESLint strict mode | `no-explicit-any: warn` → `error` | LO-01 | 1 saat |
| **5.9** | useEffect dependency fixes | 3+ sayfada hatali dependency array | MD-12 | 1 saat |
| **5.10** | console.log temizle | `src/lib/admin-api.ts` asiri loglama | LO-03 | 30 dk |
| **5.11** | Unused imports temizle | `threading`, `asyncio`, `BackgroundTasks`, `SingletonMeta` | LO-11 | 30 dk |

### 9.4 Framework Guncelleme

| # | Gorev | Aciklama | Kaynak | Effort |
|---|-------|----------|--------|--------|
| **5.12** | React 18 → 19 upgrade | Next.js 16 React 19 gerektirir. Breaking changes kontrol et. | MD-20 | 4 saat |

### 9.5 Frontend Iyilestirmeleri

| # | Gorev | Aciklama | Kaynak | Effort |
|---|-------|----------|--------|--------|
| **5.13** | Responsive table wrappers | Tum tablolara mobile overflow wrapper | LO-15 | 1 saat |
| **5.14** | window.confirm → AlertDialog | `schedule/page.tsx` native confirm kaldir | LO-09 | 30 dk |
| **5.15** | Raw radio → shadcn RadioGroup | `user-form-dialog.tsx` erisilebilirlik | LO-06 | 30 dk |
| **5.16** | Loading state iyilestirmesi | 10+ sayfada `Text` loading → Skeleton component | - | 2 saat |

### 9.6 Database

| # | Gorev | Aciklama | Kaynak | Effort |
|---|-------|----------|--------|--------|
| **5.17** | schema.sql birlestir | Migration dosyalarindaki tablolari ana schema'ya ekle | MD-07 | 1 saat |
| **5.18** | UNIQUE(user_id) base schema ekle | `weekly_schedules` tablosu | MD-28 | 15 dk |
| **5.19** | home_coordinates JSONB constraint | Structured JSON validation | MD-22 | 30 dk |

---

## 10. ⬜ FAZ 6: Akademik SOTA ve Yayin Hazirlik

**Hedef:** State-of-the-art solver entegrasyonu, akademik benchmark, paper hazirligi  
**Tahmini surec:** 4-6 hafta  
**Bagimlilik:** Faz 1-2 tamamlandi (parallel ilerleyebilir)

### 10.1 ALNS (Adaptive Large Neighborhood Search) Operators

| # | Gorev | Aciklama | Effort |
|---|-------|----------|--------|
| **6.1** | ALNS destroy operators | Random removal, worst removal, related removal, route removal implementasyonu | 4 saat |
| **6.2** | ALNS repair operators | Greedy insertion, regret-2 insertion, regret-3 insertion | 4 saat |
| **6.3** | Adaptive mechanism | Simulated annealing based operator selection with score tracking | 3 saat |
| **6.4** | ALNS integration | Mevcut Pipeline B mimarisine ALNS operator entegrasyonu | 2 saat |

### 10.2 LinearSplit Optimizasyon

| # | Gorev | Aciklama | Effort |
|---|-------|----------|--------|
| **6.5** | LinearSplit decoder analizi | Mevcut `split_decoder.py` performans profili | 2 saat |
| **6.6** | Residual magic number temizle | `split_decoder.py:507` — residual `15.0` degeri | 5 dk |
| **6.7** | Numba optimization | Hesaplama yogun bolumler icin Numba JIT | 3 saat |

### 10.3 SOTA Solver Benchmark Integration

| # | Gorev | Aciklama | Effort |
|---|-------|----------|--------|
| **6.8** | PyVRP tam entegrasyon | CVRPTW instance'lar uzerinde PyVRP solver calisma | 2 saat |
| **6.9** | VROOM tam entegrasyon | VROOM API/engine ile CVRPTW cozumu | 2 saat |
| **6.10** | OR-Tools genisletme | Mevcut OR-Tools CVRP'yi CVRPTW'ye genislet | 3 saat |
| **6.11** | Standard benchmark set | CVRPLIB Solomon instances (100 customer problems) | 2 saat |
| **6.12** | Benchmark otomasyon | Tum solver'lar icin otomatik benchmark script'i | 3 saat |

### 10.4 Performance Comparison Paper Hazirligi

| # | Gorev | Aciklama | Effort |
|---|-------|----------|--------|
| **6.13** | Experiment design | Problem seti, parametre araligi, repeat sayisi | 2 saat |
| **6.14** | Data toplama ve analiz | Tum solver'lar icin karsilastirma sonuclari | 4 saat |
| **6.15** | Gap analizi ve istatistiksel test | Wilcoxon signed-rank test, Friedman test | 2 saat |
| **6.16** | Paper draft | Abstract, Introduction, Methodology, Experiments, Conclusion | 8 saat |
| **6.17** | Tables ve figures | LaTeX formatinda tablolar, gap图表 | 3 saat |
| **6.18** | Related work survey | CVRP/CVRPTW literature (son 5 yil) | 4 saat |

---

## 11. Milestone Takip Tablosu

| Milestone | Faz | Gosterge | Kriterler | Durum |
|-----------|-----|---------|-----------|-------|
| **M1: Optimizer Stabil** | 1.1-1.3 | import logging, get_time_windows, no random fallback | 3/3 gorev tamamlandi | ✅ |
| **M2: Benchmark API Tam** | 1.4-1.5, D1-D4 | TSPLIB endpoint, /run resolution, NINT distance, euclidean fallback | 7/7 gorev tamamlandi | ✅ |
| **M3: Benchmark UI Canli** | 2.1-2.5, 2.6-2.8 | Web'den sec, calistir, gorsellestir, CLI import | 8/8 gorev tamamlandi | ✅ |
| **M4: Guvenlik Duzeltme** | 3.1-3.5 | Kritik guvenlik aciklari kapatildi (P0 tasklar) | 1/5 tamamlandi | ⬜ |
| **M5: Stable Core** | 3.6-3.15 + Faz 4 | Bug fixler, validation, tip guvenligi | 0/25+ tamamlandi | ⬜ |
| **M6: Clean Architecture** | Faz 5 | Performans, kod kalitesi, React 19 | 0/19 tamamlandi | ⬜ |
| **M7: SOTA Ready** | Faz 6 | ALNS, SOTA benchmark, paper draft | 0/18 tamamlandi | ⬜ |

### Milestone Dependency Graph

```
M1 ✅ ──→ M2 ✅ ──→ M3 ✅ ──→ M4 ⬜ ──→ M5 ⬜ ──→ M6 ⬜
                                                ↗
                                        M7 ⬜ ──→ (parallel with M5-M6)
```

---

## 12. Zaman Cizelgesi ve Tahminler

### Sprint Planlama

| Sprint | Tarih | Faz | Hedef Milestone | Tahmini Effort |
|--------|-------|-----|----------------|----------------|
| **Sprint 1** | 15.04 - 21.04.2026 | Faz 3 (P0) | M4: Guvenlik Duzeltme | ~4 saat |
| **Sprint 2** | 22.04 - 28.04.2026 | Faz 3 (P1) + Faz 4 | M5 baslangici | ~20 saat |
| **Sprint 3** | 29.04 - 12.05.2026 | Faz 4 + Faz 5 | M5: Stable Core | ~25 saat |
| **Sprint 4** | 13.05 - 26.05.2026 | Faz 5 devam | M6: Clean Architecture | ~20 saat |
| **Sprint 5** | 27.05 - 23.06.2026 | Faz 6 | M7: SOTA Ready | ~40 saat |
| **Paper Phase** | 24.06 - 30.09.2026 | Faz 6 devam | Draft → Submit | ~20 saat |

### Faz Bazli Toplam Effort Tahminleri

| Faz | Toplam Gorev | Tahmini Surec | Kritik Yol |
|-----|-------------|---------------|-----------|
| Faz 3 | 15 + 10 ek | 1-2 hafta | 3.1, 3.2 (RLS fixes) |
| Faz 4 | 17 | 1-2 hafta | 4.11 (Tip tipleri) |
| Faz 5 | 19 | 2-3 hafta | 5.12 (React 19 upgrade) |
| Faz 6 | 18 | 4-6 hafta | 6.16 (Paper draft) |
| **TOPLAM** | **~79** | **~10-15 hafta** | — |

---

## 13. Teknoloji Stack Referansi

| Katman | Teknoloji | Version | Not |
|--------|-----------|---------|-----|
| **Frontend** | Next.js | ^16.1.6 | App Router, Route Handlers |
| **UI Library** | React | ^18.3.1 | 19'a upgrade planlanıyor |
| **Styling** | Tailwind CSS | ^3.4.1 | Utility-first |
| **Component Library** | shadcn/ui | New York | Radix + Tailwind |
| **State** | React Context + useState | — | Simple global state |
| **Form Validation** | Zod + react-hook-form | — | Client-side |
| **Charts** | Recharts | ^2.15.1 | Benchmark visualization |
| **AI/ML** | Genkit (Google AI) | ^1.32.0 | Schedule analyzer |
| **Backend API** | Next.js Route Handlers | — | Server-side |
| **Database** | Supabase (PostgreSQL) | — | RLS, Auth, Storage |
| **Auth** | Supabase Auth | — | JWT + RLS policies |
| **Optimizer** | Python FastAPI | — | Port 8099 |
| **SOTA Solvers** | OR-Tools, PyVRP, VROOM | — | Benchmark comparison |
| **Python ML** | NumPy, Numba | — | Performance optimization |

### Bagimlik Riskleri

| Paket | Risk | Mitigasyon |
|-------|------|-----------|
| `xlsx@^0.18.5` | CVE-2023-30533, bakim yok | Faz 5.1: exceljs migration |
| `next@^16.1.6` + `react@^18.3.1` | Version mismatch | Faz 5.12: React 19 upgrade |
| `dotenv@^16.6.1` | Production gereksiz | Kaldir, Next.js env kullan |
| `.mcp.json` | `.gitignore`'da yok, credentials | Kaldir veya gitignore ekle |

---

## 14. Ekler

### Ek A: Strateji Agaci (Python Optimizer)

```
BaseRoutingStrategy (base_strategy.py)
├── Pipeline A — Cluster-First, Route-Second
│   ├── GeneticAlgorithmStrategy      (ga_strategy.py)
│   ├── PSOSplitStrategy              (pso_strategy.py)
│   ├── GWOSplitStrategy              (gwo_strategy.py)
│   └── HHOSplitStrategy              (hho_strategy.py)
├── Pipeline B — Route-First, Cluster-Second
│   ├── HybridSplitBaseStrategy       (hybrid_base_strategy.py)
│   │   ├── GASplitStrategy           (ga_split_strategy.py)
│   │   ├── GOWSplitStrategy          (gwo_split_strategy.py)
│   │   ├── HHOSplitStrategy          (hho_split_strategy.py)
│   │   └── PSOSplitStrategy          (pso_split_strategy.py)
│   └── SOTA Solvers
│       ├── PyVRPStrategy             (pyvrp_strategy.py)
│       ├── PyVRPAlternativeStrategy  (pyvrp_strategy.py)
│       ├── VROOMStrategy             (vroom_strategy.py)
│       ├── VROOMFallbackStrategy     (vroom_strategy.py)
│       └── ORToolsCVRPStrategy       (ortools_cvrp.py)
├── Heuristics
│   ├── GreedyHeuristic               (greedy_heuristic.py)
│   ├── PermutationTSP                (permutation_tsp.py)
│   └── TwoOptLocalSearch             (two_opt_strategy.py)
└── Wrappers
    └── CVRPTWWrapper                 (cvrptw_wrapper.py)
```

### Ek B: Benchmark Dogrulama Sonuclari

| Algoritma | Problem | Dimension | Optimal | Tour Length | Gap | Sure (ms) |
|-----------|---------|-----------|---------|-------------|-----|-----------|
| greedy (NN) | eil51 | 51 | 426 | 511 | 19.95% | — |
| two_opt | eil51 | 51 | 426 | 453 | 6.34% | — |

### Ek C: Code Review Bulgulari Ozet Tablosu

**KRITIK (12 bulgu):**

| ID | Kategori | Aciklama | Faz |
|----|----------|----------|-----|
| CR-01 | RLS | users_update_own role restriction eksik | 3.1 |
| CR-02 | RLS | notifications_insert herkese acik | 3.2 |
| CR-03 | Guvenlik | NEXT_PUBLIC_DEV_RESET_SECRET client exposure | 3.3 ✅ |
| CR-04 | Schema | cooldown_minutes sutunu DB'de yok | 3.9 |
| CR-05 | Tip | camelCase/snake_case uyumsuzlugu (vehicles) | 4.11 |
| CR-06 | Guvenlik | AuthContext setUser acik | 3.4 |
| CR-07 | Guvenlik | PostgREST filter injection | 3.E1 |
| CR-08 | Bug | import logging eksik (4 strateji) | 1.1 ✅ |
| CR-09 | Concurrency | Singleton state corruption | 3.10 |
| CR-10 | Feature | get_time_windows() dead code | 1.2 ✅ |
| CR-11 | Guvenlik | User tipinde password alani | 3.E2 |
| CR-12 | Guvenlik | Admin sayfalari role check yok | 3.5 |

**YUKSEK (12 of 22 selected):**

| ID | Kategori | Aciklama | Faz |
|----|----------|----------|-----|
| HI-01 | Reliability | React Error Boundary yok | 3.6 |
| HI-02 | Guvenlik | Security headers eksik | 3.7 |
| HI-03 | Guvenlik | xlsx CVE zafiyeti | 5.1 |
| HI-04 | Data | User deletion partial rollback | 3.11 |
| HI-05 | Bug | Pickup/dropoff ayni filtre | 3.12 |
| HI-06 | Bug | Schedule-to-requests ayni zaman | 3.13 |
| HI-07 | Tip | Tum tablolarda camelCase/snake_case | 4.11 |
| HI-08 | Guvenlik | Password hint enumeration | 3.E10 |
| HI-09 | RLS | Write policy eksik (4 tablo) | 3.8 |
| HI-10 | Data | FK constraints eksik | 3.E5 |
| HI-11 | Performans | Reports N+1 query | 5.2 |
| HI-12 | Validation | Status enum eksik | 4.13 |

---

## Referanslar

- [ROADMAP.md](../ROADMAP.md) — Ozet roadmap (root level)
- [CODE_REVIEW_REPORT.md](../CODE_REVIEW_REPORT.md) — Kapsamli code review (80+ bulgu)
- [worklog.md](../worklog.md) — Gelistirme gecmisi (7 task, detayli log)
- [supabase/schema.sql](../supabase/schema.sql) — Veritabani semasi
- [supabase/rls_policies.sql](../supabase/rls_policies.sql) — RLS politikaları

---

*Kesin kural: Random/placeholder veri ASLA kullanilmaz. Tum sonuclar gercek TSPLIB/optimizer verilerinden elde edilir.*  
*Son guncelleme: 15.04.2026 — v4*
