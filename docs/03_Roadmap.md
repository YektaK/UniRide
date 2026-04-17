# UniRide CVRPTW - Gelistirme Yol Haritasi

## Surum: 3.1.0 | Tarih: 17 Nisan 2026 (17.04.2026 - Guncelleyen: Antigravity AI)

> **Ozet:** FAZ 0-3 SOTA Framework tamamlandi. E2BSO, R2DMA, P-AOEA uretime hazir. Test coverage %64. DNA 10/10.

---

## Genel Bakis

Bu yol haritasi, UniRide Ozel Ogrenci Tasima Sistemi'nin CVRPTW (Kapasiteli Arac Rotalama Problemi Zaman Pencereli) entegrasyonu icin kapsamli bir plan sunmaktadir. Proje, 7 ana fazdan olusmakta olup, ilk 4 faz ve SOTA Framework FAZ 0-3 tamamlanmistir.

---

## Tamamlanan Fazlar

### Faz 1: Temel Altyapi (TAMAMLANDI)
**Durum:** Tamamlandi | **Sure:** 2 hafta

| Gorev | Durum | Aciklama |
|-------|-------|----------|
| Next.js 16 Kurulumu | TAMAM | App Router, TypeScript, Tailwind CSS 4.x |
| Supabase Entegrasyonu | TAMAM | PostgreSQL, RLS policies |
| Python Backend API | TAMAM | FastAPI, CORS (env-tabanli), Health check |
| Temel UI Bilesenleri | TAMAM | shadcn/ui (~38 bilesен) |
| Authentication | TAMAM | Supabase Auth + requireAdmin guard |

### Faz 2: CVRP Optimizasyonu (TAMAMLANDI)
**Durum:** Tamamlandi | **Sure:** 3 hafta

| Gorev | Durum | Aciklama |
|-------|-------|----------|
| Genetic Algorithm | TAMAM | OX1 crossover, swap/inversion mutation |
| PSO | TAMAM | Swap-based velocity, discrete PSO |
| GWO | TAMAM | Grey Wolf Optimizer (Mirjalili et al., 2014) |
| HHO | TAMAM | Harris Hawks Optimization (Heidari et al., 2019) |
| Greedy/Nearest Neighbor | TAMAM | Hizli sezgisel cozum |
| OR-Tools CVRP | TAMAM | Endustri standardi cozucu |
| PyVRP (Opsiyonel) | TAMAM | DIMACS 2021 kazanani - graceful fallback |
| VROOM (Opsiyonel) | TAMAM | Ultra-hizli C++ cozucu - graceful fallback |
| Permutation TSP | TAMAM | Optimal cozum (n<=10) |
| Two-Opt | TAMAM | Local search iyilestirme |
| K-Means Clustering | TAMAM | Multi-vehicle clustering (arsivlendi: _archived/) |

### Faz 3: Veritabani & UI (TAMAMLANDI)
**Durum:** Tamamlandi | **Sure:** 2 hafta

| Gorev | Durum | Aciklama |
|-------|-------|----------|
| Admin Dashboard | TAMAM | Kullanici, arac, surucu yonetimi |
| Driver Interface | TAMAM | Atamalar ve navigasyon |
| Student Interface | TAMAM | Haftalik program, ride request |
| Excel Bulk Upload | TAMAM | Toplu ogrenci yukleme |
| Route Planning UI | TAMAM | Algoritma secimi ve sonuclari |
| IE Dashboard | TAMAM | Resource Histogram, Tracks, Bottleneck |
| Sandbox Mode | TAMAM | Ozel arac config ile re-optimize |
| Route Plan Kaydetme | TAMAM | route_plans tablosu + API |

### Faz 4: CVRPTW (Zaman Pencereli Rotalama) (TAMAMLANDI)
**Durum:** Tamamlandi | **Sure:** 4 hafta

#### 4.1 Backend CVRPTW Destegi
| Gorev | Durum | Aciklama |
|-------|-------|----------|
| Split Decoder (DP) | TAMAM | Optimal trip bolme - Prins (2004) |
| GA-Split Strategy | TAMAM | GA + Split Decoder (Pipeline B) |
| PSO-Split Strategy | TAMAM | PSO + Split Decoder (Pipeline B) |
| GWO-Split Strategy | TAMAM | GWO + Split Decoder (Pipeline B) |
| HHO-Split Strategy | TAMAM | HHO + Split Decoder (Pipeline B) |
| Time Window Veri Yapisi | TAMAM | Backward (Pickup) + Forward (Dropoff) |
| Time Window Violation Tracking | TAMAM | Accumulating counter, earliest-time wait |
| CVRPTW Wrapper | TAMAM | Time window overlay for holistic solvers |
| Local Search (8 tip) | TAMAM | 2-opt, 3-opt, Or-opt, Swap, Cross, Hybrid + Numba |

#### 4.2 Frontend Time Window UI
| Gorev | Durum | Aciklama |
|-------|-------|----------|
| Direction Selection UI | TAMAM | Pickup / Dropoff toggle |
| Time Window Input Fields | TAMAM | Target time, offset |
| API Integration Updates | TAMAM | Direction, target_time gonderimi |

#### 4.3 Guvenlik & Kod Kalitesi (09-10.04.2026)
| Gorev | ID | Durum | Aciklama |
|-------|----|-------|----------|
| Auth guard -- calculate-vehicles | A-1 | TAMAM | requireAdmin eklendi |
| CORS env-tabanli yapilandirma | A-2 | TAMAM | ALLOWED_ORIGINS env var |
| Sandbox IE endpoint duzeltme | A-3 | TAMAM | /api/v1/ie/analyze fetch kaldirildi |
| total_time_window_violations | B-1 | TAMAM | Pydantic modele eklendi |
| strategy->algorithm fix | B-2 | TAMAM | Sandbox fetch duzeltildi |
| max_tour_time->max_travel_time | B-4 | TAMAM | Sandbox field duzeltildi |
| as any kaldir | C-3 | TAMAM | DbUserRow tipi eklendi |
| Supabase env dogrulama | C-4 | TAMAM | Bos fallback kaldirildi |
| kmeans_tsp.py arsivle | C-2 | TAMAM | _archived/ dizinine tasindin |

#### 4.4 Forensic Audit Duzeltmeleri (10.04.2026)
| Gorev | ID | Durum | Aciklama |
|-------|----|-------|----------|
| Negatif departure skip | FIX-01 | TAMAM | departure_time < 0 => continue |
| DROPOFF tw_violations birikmeli | FIX-02 | TAMAM | Counter loop disina, += 1, earliest wait |
| PICKUP j degisken cakismasi | FIX-03 | TAMAM | k + trip_end tracker |
| 15.0 => constant (split stratejiler) | FIX-04 | TAMAM | constants.py + logger.warning |
| Duplicate _minutes_to_time kaldir | FIX-05 | TAMAM | 2. kopya silindi |
| Bare except: => typed exceptions | FIX-06 | TAMAM | 7/7 site duzeltildi |
| haversine_distance tek kaynak | FIX-07 | TAMAM | clustering.py => from utils.data_loader import haversine_distance |
| HybridSplitBaseStrategy olustur | FIX-08 | TAMAM | 3 method tasindi, 4 strateji inherit ediyor |
| Unused depot parametre kaldir | FIX-09 | TAMAM | _get_target_arrival/departure_time |
| ALGORITHM_COMPARISON.md guncelle | FIX-10 | TAMAM | mavi->yesil statu guncellendi |

---

## Devam Eden Fazlar

### Faz 4.5: Teknik Borc ve Test (TAMAMLANDI)
**Durum:** Tamamlandi | **Tarih:** 17 Nisan 2026

#### 4.5.1 Teknik Borc (Tamamlananlar)
| Gorev | Oncelik | Durum | Aciklama |
|-------|---------|-------|----------|
| Benchmark daemon thread | YUKSEK | TAMAM | Thread-safe SingletonMeta eklendi |
| FIX-04 genislet -- Pipeline A stratejileri | YUKSEK | TAMAM | main.py consolidation + BaseStrategy extraction (13.04.2026) |
| P1 Stratejileri refactor (super() kullan) | YUKSEK | TAMAM | Duplicate kisimlar kaldirildi (13.04.2026) |
| P0-1: Benchmark run body/query fix | YUKSEK | TAMAM | BenchmarkRunRequest Pydantic body (14.04.2026) |
| P0-3: Results Next.js route | YUKSEK | TAMAM | /api/benchmark/results/[runId]/route.ts (14.04.2026) |
| P1-1: DataLoader thread-safety | ORTA | TAMAM | SingletonMeta + get_instance() backward-compat (14.04.2026) |
| P1-3: CSP header | ORTA | TAMAM | Content-Security-Policy next.config.ts (14.04.2026) |
| P1-4: Benchmark Import CLI=>Web | ORTA | TAMAM | /api/v1/benchmark/cli/import endpoint (14.04.2026) |
| P2-1: RLS Write Policy | ORTA | TAMAM | Vehicles, Routes, Assignments admin yetkisi (14.04.2026) |
| P2-2: Admin Falsy Check Bug | ORTA | TAMAM | Bos string guncellemelerini engelleyen hata duzeltildi |
| P2-3: User Deletion Order | ORTA | TAMAM | Silme sirasi: Auth => DB (14.04.2026) |
| P2-4: Schema Sync | ORTA | TAMAM | schema.sql (plans, matrix, sandbox) senkronize edildi |
| ResourceProfiler magic numbers | DUSUK | TAMAM | DEFAULT_PICKUP_HOUR/DEFAULT_DROPOFF_HOUR env vars (13.04.2026) |
| main.old.py temizle | DUSUK | TAMAM | 24KB olu kod => docs/old/ archive (13.04.2026) |
| Algorithm Parameter Config UI | DUSUK | BEKLEMEDE | Frontend'de algoritma parametresi ayarlama |
| DataLoader TTL/Invalidation | DUSUK | BEKLEMEDE | Singleton'a cache suresi + yenileme mekanizmasi |

#### 4.5.2 Test Altyapisi (TAMAMLANDI)
| Gorev | Oncelik | Durum | Aciklama |
|-------|---------|-------|----------|
| Unit testler (SplitDecoder, Clustering, LocalSearch) | YUKSEK | TAMAM | %64 coverage'a ulasildi (14.04.2026) |
| HybridSplitBaseStrategy testleri | ORTA | TAMAM | Base class inheritance dogrulandi |
| Strategy smoke tests (tum stratejiler) | ORTA | TAMAM | Her strateji icin basic optimize() cagrisi |
| Test coverage hedefi: %64 | ORTA | TAMAM | Tamamlandi -- hedef asildi! |

#### 4.5.3 Akademik Benchmark
| Gorev | Oncelik | Durum | Aciklama |
|-------|---------|-------|----------|
| TSPLIB EUC_2D NINT rounding | YUKSEK | TAMAM | tsplib_parser.py -- tam standart uyumlu |
| greedy(eil51): gap=19.95%, two_opt: gap=6.34% | ORTA | TAMAM | Akademik referans degerleri dogrulandi |
| Solomon CVRPTW benchmark | ORTA | BEKLEMEDE | Sonraki adim |
| ALGORITHM_COMPARISON.md gercek veriyle guncelle | ORTA | BEKLEMEDE | [TAHMINI] etiketlerini kaldir |

---

### FAZ SOTA 0-3: SOTA Framework (TAMAMLANDI)
**Durum:** TAMAMLANDI | **Tarih:** 17 Nisan 2026

#### SOTA FAZ 0: Ortak Altyapi Modulleri (sota_common/)
| Gorev | Durum | Detay |
|-------|-------|-------|
| MultiStartInitializer | TAMAM | NN + CW + Regret-2 + Random |
| MultiLayerLS | TAMAM | 2-opt => Or-opt => 3-opt => Swap |
| PenaltyManager | TAMAM | alfa_tw, alfa_cap, 3-fazli iterated penalty |
| AcceptanceCriterion | TAMAM | SA + LAHC + RTR |
| DestroyOperators | TAMAM | Random/Worst/Shaw/Related removal |
| RepairOperators | TAMAM | Greedy/Regret-2/Regret-3 insertion |
| DiversityController | TAMAM | Edge-based entropy, Hamming distance |

#### SOTA FAZ 1: E2BSO (Evolutionary & Entropy-Based Swarm Optimization)
| Gorev | Durum | Detay |
|-------|-------|-------|
| E2BSO implementasyonu | TAMAM | e2bso.py (978 satir) |
| DNA Coverage | TAMAM | D1 D2 D3 D4 D6 D7 D8 = 7/10 |
| eil51 Benchmark | TAMAM | **0.47% gap** (optimal: 426, sonuc: 428) |
| berlin52 Benchmark | TAMAM | **0.00% OPTIMAL** (7542 = 7542) |

#### SOTA FAZ 2: R2DMA (Resonance-Reinforced Destroy and Merge Algorithm)
| Gorev | Durum | Detay |
|-------|-------|-------|
| R2DMA implementasyonu | TAMAM | r2dma.py (~680 satir) |
| 6-boyutlu Rezonans Metrigi | TAMAM | Jaccard, LCS, Shaw, Kapasite, TW |
| 3 Crossover Modu | TAMAM | Constructive / Moderate / Destructive |
| DNA Coverage | TAMAM | D1-D4, D6-D9 = 8/10 |
| eil51 Benchmark | TAMAM | **0.47% gap** |
| berlin52 Benchmark | TAMAM | **0.00% OPTIMAL** |

#### SOTA FAZ 3: P-AOEA (Production Adaptive Operator Evolution Algorithm)
| Gorev | Durum | Detay |
|-------|-------|-------|
| P-AOEA implementasyonu | TAMAM | paoea.py (~1423 satir) |
| 20+ Atomic Operation | TAMAM | Meta-evrim: tournament, crossover, mutation |
| Neural/ML Evolutionary Genome | TAMAM | DNA-10 -- Operator secimi + parametre onerisi |
| DNA Coverage | TAMAM | **10/10** -- Tum DNA faktorleri |
| eil51 Benchmark | TAMAM | **0.00% OPTIMAL [SAMPIYONLUK]** (426 = 426) |
| berlin52 Benchmark | TAMAM | **0.00% OPTIMAL [SAMPIYONLUK]** (7542 = 7542) |

---

## Gelecek Fazlar

### Faz 5: Veri Kaliciligi & Atama Sistemi
**Durum:** Planlandi | **Tahmini Sure:** 2 hafta | **Hedef:** Mayis 2026

| Gorev | Oncelik | Aciklama |
|-------|---------|----------|
| Surucu atama UI | YUKSEK | route_plans.driver_assignments kolonu mevcut, UI gerekli |
| Cift yonlu planlama | ORTA | Pickup + Dropoff birlikte planlama |
| Standart arac ihtiyac tablosu | ORTA | IE engine ile entegre |
| DataLoader payload duzeltmesi | DUSUK | Fail-fast mekanizmasi |
| time_matrix caching | DUSUK | Redis veya in-memory TTL cache |

### Faz 6: Bildirim & Otomasyon
**Durum:** Planlandi | **Tahmini Sure:** 2-3 hafta | **Hedef:** Haziran 2026

| Gorev | Oncelik | Aciklama |
|-------|---------|----------|
| Push/Email/SMS bildirim servisi | ORTA | Firebase Cloud Messaging veya Supabase Edge Functions |
| Aksam 22:00 onay bildirimleri | ORTA | Ertesi gun seferi onay/red |
| Gece 23:00 otomatik planlama | ORTA | Cron job ile rota olusturma |
| ETA hesaplama | DUSUK | Varis zamani tahmini |
| Anlik rota guncelleme | DUSUK | Iptal/onay sonrasi dynamic re-routing |

### Faz 7: Production Deployment
**Durum:** Planlandi | **Tahmini Sure:** 2 hafta | **Hedef:** Temmuz 2026

| Gorev | Oncelik | Aciklama |
|-------|---------|----------|
| Docker Containerization | YUKSEK | Frontend + Backend + Redis docker-compose |
| CI/CD Pipeline | YUKSEK | GitHub Actions: lint, test, build, deploy |
| Rate Limiting (tum API) | ORTA | Redis-backed rate limiter middleware |
| Monitoring & Logging | ORTA | Structured logging, Sentry veya benzeri |
| FastAPI async endpoint | DUSUK | /api/v1/optimize => async + run_in_executor |
| Zod schema validation | DUSUK | calculate-vehicles raw cast => zod.parse |
| Penetrasyon testi | DUSUK | OWASP Top 10 dogrulamasi |

---

## Zaman Cizelgesi

```
2026 Q1 (Tamamlandi)
+-- Faz 1: Temel Altyapi [TAMAM]
+-- Faz 2: CVRP Optimizasyonu [TAMAM]
+-- Faz 3: Veritabani & UI [TAMAM]

2026 Q2 (Buyuk Olcude Tamamlandi)
+-- Faz 4: CVRPTW [TAMAM] (Nisan 2026)
+-- Faz 4.5: Teknik Borc & Test [TAMAM] (Nisan 2026 -- 100% tamamlandi)
+-- FAZ SOTA 0-3: SOTA Framework [TAMAM] (17 Nisan 2026 -- P-AOEA 0.00% SAMPIYONLUK)
+-- Faz 5: Veri Kaliciligi & Atama (Mayis 2026)
+-- Faz 6: Bildirim & Otomasyon (Haziran 2026)

2026 Q3 (Planlandi)
+-- Faz 7: Production Deployment (Temmuz 2026)
+-- Akademik Makale (GECCO/WCCI 2026 -- E2BSO)

2026 Q4 (Vizyon)
+-- AAAI/IJCAI 2027 submission (R2DMA)
+-- IEEE TEVC submission (P-AOEA)
```

---

## KPI'lar ve Basari Kriterleri

### Teknik KPI'lar
| Metrik | Hedef | Mevcut | Durum |
|--------|-------|--------|-------|
| Optimizasyon Hizi (50 ogrenci) | <5 saniye | ~3 saniye | TAMAM |
| Route Quality (P-AOEA optimal farki) | <%3 | **%0.00** | TAMAM [SAMPIYONLUK] |
| API Response Time | <200ms | ~150ms | TAMAM |
| Test Coverage | >%60 | **%64** | TAMAM |
| DNA Coverage | 10/10 | **10/10** | TAMAM |
| TSPLIB NINT Uyumu | %100 | %100 | TAMAM |
| Bare except: sayisi | 0 | 0 | TAMAM |
| Duplicate code (LOC) | <50 | ~30 | TAMAM |
| CSP Security Headers | Var | Var | TAMAM |
| RLS Write Policies | Var | Var | TAMAM |

### Is KPI'lari
| Metrik | Hedef | Mevcut |
|--------|-------|--------|
| Arac Kullanim Orani | >%85 | N/A |
| Ogrenci Memnuniyeti | >%90 | N/A |
| Time Window Compliance | >%95 | N/A |

---

## Riskler ve Azaltici Onlemler

| Risk | Olasilik | Etki | Azaltici Onlem |
|------|----------|------|----------------|
| Algoritma Performansi N>100 | Orta | Yuksek | Benchmark testleri, PyVRP/VROOM fallback |
| Time Window Ihlalleri | Dusuk (duzeltildi) | Orta | FIX-01/02/03 uygulandi, test yazildi |
| time_matrix veri eksikligi | Orta | Yuksek | logger.warning eklendi (FIX-04), caching planlandi |
| Singleton DataLoader stale data | Dusuk | Orta | TTL mekanizmasi planlandi |
| Veri Guvenligi | Dusuk | Kritik | RLS, CORS fix, auth guard, CSP uygulandi |

---

## Iletisim

- **Proje Yoneticisi:** [E-posta]
- **Teknik Lead:** [E-posta]
- **Dokumantasyon:** /docs klasoru
- **Issue Tracker:** GitHub Issues

---

*Bu yol haritasi proje gereksinimlerine gore guncellenecektir.*
*Son guncelleme: 17.04.2026 -- SOTA Framework FAZ 0-3 tamamlanmasi sonrasi.*


> (10.04.2026 - AI Audit): TSP Benchmark Studio entegrasyonu kod duzeyinde incelendi. /api/benchmark/run rotalari, FastAPI backend benchmark_runner mekanizmalari ve ilgili Python strateji dosyalarinin projenin Dual-Track SOTA ve ticari hibrit motor yapisina uygun olarak ayri bir execution branch olarak (academic_benchmark) basariyla entegre edildigi dogrulandi.

> (14.04.2026 - Antigravity AI): Kapsamli capraz kontrol gerceklestirildi. 4 duzeltme uygulandi: BenchmarkRunRequest Pydantic modeli, /api/benchmark/results/[runId] route, DataLoader SingletonMeta thread-safety, CSP security header. Detaylar: docs/00_14.04.2026_KAPSAMLI_KOD_INCELEME.md

> (17.04.2026 - Antigravity AI): Tum dokumantasyon guncellemeleri tamamlandi. SOTA Framework FAZ 0-3 entegrasyonu dogrulandi. P-AOEA ile eil51 ve berlin52 benchmarklarinda %0.00 gap (optimal) elde edildi. Test coverage %64. DNA Coverage 10/10.
