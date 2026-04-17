# UniRide - Mimari Dokümantasyonu (Architecture Documentation)

> **Tarih:** 13 Temmuz 2025  
> **Sürüm:** 3.1.0  
> **Durum:** Aktif Geliştirme  
> **Yazar:** UniRide Geliştirme Ekibi

---

## İçindekiler

1. [Genel Bakış](#1-genel-bakış)
2. [Teknoloji Yığını](#2-teknoloji-yığını)
3. [Diz Yapısı](#3-diz-yapısı)
4. [Mimari Diyagramlar](#4-mimari-diyagramlar)
5. [Strateji Mimarisi](#5-strateji-mimarisi)
6. [Benchmark Mimarisi](#6-benchmark-mimarisi)
7. [API Sözleşmeleri](#7-api-sözleşmeleri)
8. [Veritabanı Şeması](#8-veritabanı-şeması)
9. [Dosya Sorumluluk Haritası](#9-dosya-sorumluluk-haritası)
10. [Tasarım İlkeleri](#10-tasarım-ilkeleri)
11. [Deployment ve Port Yapılandırması](#11-deployment-ve-port-yapılandırması)

---

## 1. Genel Bakış

### 1.1 Proje Tanımı

UniRide, üniversite öğrencileri için **CVRP** (Capacitated Vehicle Routing Problem), **TSP** (Traveling Salesman Problem) ve **VRP** (Vehicle Routing Problem) optimizasyonu sağlayan bir platformdur. Proje iki ana paralel hatta (dual-track) çalışır:

| Track | Açıklama | Hedef Kitle |
|-------|----------|-------------|
| **Commercial Product** | Stable Hybrid algoritmalar ile üretim routing | İşletmeler, üniversiteler |
| **Academic Research** | SOTA algoritma test ve benchmarking | Akademik yayın, makale |

### 1.2 Sistem Mimarisi (High-Level)

```
┌─────────────────────────────────────────────────────────────────┐
│                    Browser (Client)                             │
│                 Next.js SSR + Client Components                 │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│              Next.js App (Port 3000)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐  │
│  │ App Router   │  │ API Routes   │  │ Server Components    │  │
│  │ (Pages)      │  │ (BFF Layer)  │  │ (RSC)               │  │
│  └──────────────┘  └──────┬───────┘  └──────────────────────┘  │
└─────────────────────────┬┴─────────────────────────────────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
┌──────────────────────┐  ┌──────────────────────────────────────┐
│   Supabase (Cloud)   │  │   Python FastAPI (Port 8099)         │
│   ┌────────────┐     │  │   ┌────────────────────────────────┐ │
│   │ PostgreSQL │     │  │   │ 16 Optimization Strategies     │ │
│   │ Database   │     │  │   │ (GA, PSO, GWO, HHO, Split...)  │ │
│   ├────────────┤     │  │   ├────────────────────────────────┤ │
│   │ Auth       │     │  │   │ BenchmarkRunner (Daemon Thread) │ │
│   │ Service    │     │  │   ├────────────────────────────────┤ │
│   ├────────────┤     │  │   │ TSPLIB Parser (46+ Problems)   │ │
│   │ Storage    │     │  │   └────────────────────────────────┘ │
│   └────────────┘     │  └──────────────────────────────────────┘
└──────────────────────┘
```

### 1.3 İletişim Akışı

```
Frontend → Next.js API Route → Python FastAPI (via XTransformPort)
                                    │
                                    ├── Supabase (data loader fallback)
                                    └── TSPLIB (benchmark problems)
```

> **Not:** Frontend, relative path'ler ve `XTransformPort` query parametresi kullanır. Bu, port 3000 üzerinden tüm isteklerin tek noktadan yönetilmesini sağlar.

---

## 2. Teknoloji Yığını

### 2.1 Frontend

| Teknoloji | Sürüm | Kullanım Amacı |
|-----------|-------|----------------|
| Next.js | 16 | App Router, SSR, RSC |
| TypeScript | 5.x | Tip güvenliği |
| Tailwind CSS | 4 | Utility-first styling |
| shadcn/ui | New York style | UI component library (~38 bileşen) |
| React Hook Form | latest | Form state management |
| Zod | latest | Runtime type validation |
| Recharts | latest | Grafik ve chart'lar |
| Lucide React | latest | İkon seti |
| Genkit (Google AI) | latest | AI/ML iş akışları |

### 2.2 Backend

| Teknoloji | Sürüm | Kullanım Amacı |
|-----------|-------|----------------|
| Next.js Route Handlers | 16 | API endpoint'leri (BFF) |
| Python FastAPI | 3.1.0 | Optimizasyon microservice |
| Uvicorn | latest | ASGI server |
| Pydantic | latest | Request/response validation |
| ThreadPoolExecutor | stdlib | Paralel algoritma çalıştırma |
| Numba | optional | JIT derleme (local search) |

### 2.3 Veritabanı ve Auth

| Teknoloji | Kullanım Amacı |
|-----------|----------------|
| Supabase PostgreSQL | Ana veritabanı |
| Supabase Auth | Kullanıcı kimlik doğrulama |
| NextAuth.js v4 | Session management |
| Row Level Security (RLS) | Veri izolasyonu |

### 2.4 Python Optimizer Dependencies

| Kütüphane | Kullanım Amacı |
|-----------|----------------|
| numpy | Matematiksel işlemler |
| OR-Tools | Google CVRP çözücüsü |
| PyVRP (optional) | DIMACS 2021 HGS kazananı |
| VROOM (optional) | Ultra hızlı C++ solver |
| Numba (optional) | JIT local search |
| TSPLIB95 (optional) | Benchmark problem parsing |

---

## 3. Diz Yapısı

```
/home/z/my-project/
│
├── src/                                   # ─── NEXT.JS FRONTEND ───
│   ├── app/                               # App Router sayfaları
│   │   ├── page.tsx                       # Benchmark Suite (ana sayfa)
│   │   ├── layout.tsx                     # Root layout
│   │   ├── globals.css                    # Global stiller
│   │   ├── favicon.ico
│   │   │
│   │   ├── (app)/                         # [Auth Required] Uygulama sayfaları
│   │   │   ├── layout.tsx                 # Authenticated layout
│   │   │   ├── dashboard/page.tsx         # Kullanıcı dashboard
│   │   │   ├── schedule/page.tsx          # Haftalık program
│   │   │   ├── request-ride/page.tsx      # Biniş talebi
│   │   │   ├── track-ride/page.tsx        # Takip ekranı
│   │   │   ├── ride-history/page.tsx      # Geçmiş binmeler
│   │   │   ├── profile/page.tsx           # Profil yönetimi
│   │   │   │
│   │   │   ├── driver/                    # Sürücü modülü
│   │   │   │   ├── assignments/page.tsx   # Rota atamaları
│   │   │   │   ├── navigation/page.tsx    # Navigasyon
│   │   │   │   └── history/page.tsx       # Geçmiş rotalar
│   │   │   │
│   │   │   └── admin/                     # Yönetici paneli
│   │   │       ├── benchmark/page.tsx     # Benchmark Suite
│   │   │       ├── sandbox/page.tsx       # IE Sandbox
│   │   │       ├── compare/page.tsx       # Algoritma karşılaştırma
│   │   │       ├── route-test/page.tsx    # Rota test aracı
│   │   │       ├── vehicle-planning/      # Araç planlama
│   │   │       ├── users/page.tsx         # Kullanıcı yönetimi
│   │   │       ├── vehicles/page.tsx      # Araç yönetimi
│   │   │       ├── schedules/             # Program yönetimi
│   │   │       ├── ride-requests/page.tsx # Biniş talepleri
│   │   │       ├── drivers/page.tsx       # Sürücü yönetimi
│   │   │       ├── reports/page.tsx       # Raporlar
│   │   │       └── settings/page.tsx      # Ayarlar
│   │   │
│   │   ├── (auth)/                        # [Public] Auth sayfaları
│   │   │   ├── login/page.tsx             # Giriş
│   │   │   ├── register/page.tsx          # Kayıt
│   │   │   ├── forgot-password/page.tsx   # Şifre sıfırlama
│   │   │   └── reset-password/page.tsx    # Yeni şifre
│   │   │
│   │   └── api/                           # API Route Handlers (BFF)
│   │       ├── route.ts                   # Health check / default
│   │       ├── benchmark/                 # Benchmark endpoints
│   │       │   ├── run/route.ts           # POST: Benchmark başlat
│   │       │   ├── status/route.ts        # GET: Benchmark durumu
│   │       │   ├── stop/route.ts          # POST: Benchmark durdur
│   │       │   └── problems/route.ts      # GET: TSPLIB problemleri
│   │       ├── sandbox/route.ts           # POST: Sandbox optimizasyon
│   │       ├── optimize-route/route.ts    # POST: Rota optimizasyon
│   │       ├── compare-algorithms/        # POST: Algoritma karşılaştırma
│   │       │   └── route.ts
│   │       ├── calculate-vehicles/        # POST: Araç hesaplama
│   │       │   └── route.ts
│   │       ├── ride-confirmation/         # POST: Biniş onayı
│   │       │   └── route.ts
│   │       ├── route-plans/               # GET/POST: Rota planları
│   │       │   └── route.ts
│   │       ├── driver/assignments/        # GET: Sürücü atamaları
│   │       │   └── route.ts
│   │       ├── admin/                     # Admin API endpoints
│   │       │   ├── users/route.ts         # GET/POST: Kullanıcı CRUD
│   │       │   ├── users/password/        # PATCH: Şifre değiştir
│   │       │   │   └── route.ts
│   │       │   ├── vehicles/route.ts      # GET/POST: Araç CRUD
│   │       │   └── ride-requests/route.ts # GET: Biniş talepleri
│   │       ├── profile/password/          # PATCH: Profil şifre
│   │       │   └── route.ts
│   │       └── auth/                      # Auth helper endpoints
│   │           ├── dev-reset/route.ts     # Dev: Auth reset
│   │           └── hint/route.ts          # Auth hint (rate limited)
│   │
│   ├── components/                        # React bileşenleri
│   │   ├── ui/                            # shadcn/ui (~38 dosya)
│   │   │   ├── button.tsx, card.tsx, dialog.tsx, table.tsx, form.tsx
│   │   │   ├── select.tsx, tabs.tsx, sidebar.tsx, chart.tsx, ...
│   │   │   └── (38+ UI component)
│   │   ├── layout/                        # Uygulama layout
│   │   │   ├── app-header.tsx             # Üst menü
│   │   │   └── app-sidebar.tsx            # Yan menü
│   │   ├── admin/                         # Admin bileşenleri
│   │   │   ├── ie-dashboard.tsx           # IE Kaynak analizi
│   │   │   ├── vehicle-card.tsx           # Araç kartı
│   │   │   ├── vehicle-form-dialog.tsx    # Araç form
│   │   │   ├── user-form-dialog.tsx       # Kullanıcı form
│   │   │   ├── add-user-dialog.tsx        # Kullanıcı ekleme
│   │   │   ├── resource-tracks.tsx        # Kaynak grafikleri
│   │   │   ├── resource-histogram.tsx     # Histogram
│   │   │   └── bottleneck-indicator.tsx   # Darboğaz göstergesi
│   │   ├── auth/                          # Auth bileşenleri
│   │   │   ├── login-form.tsx
│   │   │   └── register-form.tsx
│   │   └── student/                       # Öğrenci bileşenleri
│   │       ├── schedule-display.tsx       # Program görüntüleme
│   │       ├── schedule-form-dialog.tsx   # Program form
│   │       ├── schedule-confirmation-card.tsx
│   │       ├── adhoc-ride-form.tsx        # Anlık biniş formu
│   │       └── profile-form.tsx           # Profil formu
│   │
│   ├── services/                          # Frontend servis katmanı
│   │   ├── optimizer-service.ts           # Python API iletişim (ana)
│   │   ├── benchmark-service.ts           # Benchmark servis
│   │   ├── sandbox-api.ts                 # Sandbox API
│   │   ├── route-plans.ts                 # Rota planları
│   │   ├── schedule-to-requests.ts        # Program → talep dönüşümü
│   │   ├── doubus/                        # Multi-vehicle routing
│   │   │   ├── index.ts                   # Public API
│   │   │   ├── route.ts                   # Rota hesaplama
│   │   │   ├── route-optimizer.ts         # Rota optimizasyon
│   │   │   ├── location-mapper.ts         # Konum eşleme
│   │   │   ├── vehicle-assignment.ts      # Araç atama
│   │   │   └── multi-vehicle-routing.ts   # Çoklu araç routing
│   │   └── excel/                         # Excel import/export
│   │       ├── import.ts                  # Excel import
│   │       └── driver-export.ts           # Sürücü export
│   │
│   ├── lib/                               # Yardımcı modüller
│   │   ├── config.ts                      # Merkezi konfigürasyon
│   │   ├── algorithm-constants.ts         # Algoritma sabitleri (SSOT)
│   │   ├── supabase.ts                    # Supabase client
│   │   ├── supabase-admin.ts              # Supabase admin client
│   │   ├── supabase-auth.ts              # Auth utilities
│   │   ├── supabase-db.ts                 # DB sorgu yardımcıları
│   │   ├── admin-auth.ts                 # Admin auth
│   │   ├── admin-api.ts                  # Admin API client
│   │   ├── database.ts                    # DB utilities
│   │   ├── db.ts                          # DB connection
│   │   ├── coordinates.ts                 # Koordinat hesaplama
│   │   └── utils.ts                       # Genel yardımcılar (cn, etc.)
│   │
│   ├── hooks/                             # Custom React hooks
│   │   ├── use-auth.ts                    # Auth hook
│   │   ├── use-mobile.ts / .tsx           # Responsive hook
│   │   └── use-toast.ts                   # Toast hook
│   │
│   ├── contexts/                          # React Contexts
│   │   └── auth-context.tsx               # Auth context provider
│   │
│   ├── types/                             # TypeScript tip tanımları
│   │   ├── index.ts                       # Genel tipler
│   │   ├── db.ts                          # Veritabanı tipleri
│   │   └── ie-resource.ts                 # IE kaynak analizi tipleri
│   │
│   ├── ai/                                # AI/ML entegrasyonu
│   │   ├── genkit.ts                      # Genkit yapılandırma
│   │   ├── dev.ts                         # Geliştirme ortamı
│   │   └── flows/                         # AI iş akışları
│   │       └── schedule-analyzer.ts       # Program analizi
│   │
│   └── middleware.ts                      # Next.js middleware (auth)
│
├── optimizer_api/                         # ─── PYTHON MICROSERVICE ───
│   ├── main.py                            # FastAPI uygulama (v3.1.0)
│   ├── benchmark_runner.py                # Benchmark çalıştırıcı
│   ├── benchmark_state.py                 # Thread-safe durum yönetimi
│   │
│   ├── models/
│   │   └── schemas.py                     # Pydantic modelleri
│   │
│   ├── strategies/                        # Optimizasyon stratejileri (16)
│   │   ├── __init__.py                    # Strategy Registry (SSOT)
│   │   ├── base_strategy.py               # BaseRoutingStrategy
│   │   │
│   │   ├── # Pipeline A: Cluster-First, Route-Second
│   │   ├── ga_strategy.py                 # Genetic Algorithm
│   │   ├── pso_strategy.py                # Particle Swarm Optimization
│   │   ├── gwo_strategy.py                # Grey Wolf Optimizer
│   │   ├── hho_strategy.py                # Harris Hawks Optimizer
│   │   │
│   │   ├── # Pipeline B: Route-First, Cluster-Second
│   │   ├── hybrid_base_strategy.py        # HybridSplitBaseStrategy
│   │   ├── ga_split_strategy.py           # GA + Optimal Split
│   │   ├── pso_split_strategy.py          # PSO + Optimal Split
│   │   ├── gwo_split_strategy.py          # GWO + Optimal Split
│   │   ├── hho_split_strategy.py          # HHO + Optimal Split
│   │   │
│   │   ├── # Holistic Solvers (Native CVRP)
│   │   ├── ortools_cvrp.py                # Google OR-Tools
│   │   ├── pyvrp_strategy.py              # PyVRP HGS (DIMACS 2021)
│   │   ├── vroom_strategy.py              # VROOM C++ solver
│   │   │
│   │   ├── # Heuristics & Local Search
│   │   ├── greedy_heuristic.py            # Greedy / Nearest Neighbor
│   │   ├── two_opt_strategy.py            # Two-Opt Local Search
│   │   ├── permutation_tsp.py             # Exact (n <= 10)
│   │   │
│   │   └── _archived/                     # Kaldırılmış stratejiler
│   │       └── kmeans_tsp.py
│   │
│   ├── utils/                             # Yardımcı modüller
│   │   ├── tsplib_parser.py               # TSPLIB dosya ayrıştırıcı + EUC_2D NINT
│   │   ├── data_loader.py                 # Supabase veri yükleyici (euclidean fallback)
│   │   ├── split_decoder.py               # Prins (2004) Split Decoder
│   │   ├── linear_split_decoder.py        # Lineer Split alternatifi
│   │   ├── clustering.py                  # K-Means kümeleme
│   │   ├── clustering_strategies/         # Gelişmiş kümeleme
│   │   │   ├── __init__.py
│   │   │   ├── base.py                    # Base clustering
│   │   │   ├── kmeans.py                  # K-Means
│   │   │   ├── k_medoids.py               # K-Medoids
│   │   │   ├── fuzzy_cmeans.py            # Fuzzy C-Means
│   │   │   ├── fuzzy_cmeans_enhanced.py   # Enhanced FCM
│   │   │   ├── hierarchical_fcm.py        # Hierarchical FCM
│   │   │   ├── sweep.py                   # Sweep algoritması
│   │   │   └── clarke_wright.py           # Clarke-Wright (CW)
│   │   ├── local_search.py                # 2-opt, 3-opt, hybrid local search
│   │   ├── local_search_numba.py          # Numba JIT local search
│   │   ├── resource_profiler.py           # IE kaynak analizi
│   │   ├── time_window_extractor.py       # Zaman penceresi çıkarma
│   │   ├── time_window_violation_tracker.py # Zaman penceresi ihlali
│   │   ├── constants.py                   # Sabitler
│   │   └── patterns.py                    # Singleton, tasarım örüntüleri
│   │
│   └── tests/                             # CLI benchmark araçları
│       ├── run_smart_benchmark_numba.py   # Akıllı benchmark (Numba)
│       ├── run_interactive_benchmark_v2_numba.py  # İnteraktif benchmark
│       ├── run_interactive_benchmark_v2.py
│       ├── run_interactive_benchmark.py
│       ├── run_interactive_benchmark.py
│       ├── test_all_strategies_smoke.py   # Smoke test
│       ├── test_algorithm_comparison.py   # Algoritma karşılaştırma
│       ├── test_split_decoder_audit.py    # Split decoder denetim
│       ├── test_resource_profiler.py      # Resource profiler test
│       ├── test_local_search.py           # Local search test
│       ├── dataset_loader.py              # Veri seti yükleyici
│       ├── utils_benchmark.py             # Benchmark yardımcıları
│       ├── benchmark_hierarchical_threshold.py
│       │
│       ├── benchmark_results/             # CLI çıktı dosyaları
│       │   ├── *.csv                      # İlerleme raporları
│       │   └── *.json                     # Sonuç raporları
│       │
│       └── tsplib_data/                   # TSPLIB problem dosyaları (~46)
│           ├── eil51.tsp, eil76.tsp, eil101.tsp
│           ├── berlin52.tsp, st70.tsp
│           ├── kroA100.tsp, kroB100.tsp, kroC100.tsp, kroD100.tsp
│           ├── kroA150.tsp, kroB150.tsp, kroA200.tsp, kroB200.tsp
│           ├── lin105.tsp, lin318.tsp
│           ├── pr1002.tsp, pr107.tsp, ...
│           └── (46+ .tsp dosyası)
│
├── supabase/                              # ─── VERİTABANI ───
│   ├── schema.sql                         # Ana şema
│   ├── fix_schema.sql                     # Şema düzeltme
│   ├── rls_policies.sql                   # Row Level Security
│   └── migrations/                        # SQL migration'lar
│       ├── 20260305_add_missing_user_columns.sql
│       ├── 20260305_add_time_matrix.sql
│       ├── 20260329_add_route_plans.sql
│       ├── 20260329_add_sandbox_scenarios.sql
│       └── add_disability_type.sql
│
├── docs/                                  # ─── DOKÜMANLAR ───
│   └── 02_Architecture.md                 # Bu dosya
│
├── skills/                                # AI Skill modülleri
├── public/                                # Statik dosyalar
│   ├── logo.svg
│   └── robots.txt
│
├── .ai-rules                              # AI asistan kuralları
├── .ai-handover.md                        # Session handover raporu
├── ROADMAP.md                             # Geliştirme yol haritası
├── CODE_REVIEW_REPORT.md                  # Kod inceleme raporu
├── package.json                           # Node.js bağımlılıkları
├── next.config.ts                         # Next.js yapılandırma
├── tailwind.config.ts                     # Tailwind yapılandırma
├── tsconfig.json                          # TypeScript yapılandırma
├── components.json                        # shadcn/ui yapılandırma
└── worklog.md                             # Çalışma günlüğü
```

---

## 4. Mimari Diyagramlar

### 4.1 Sistem Bileşenleri

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PRESENTATION LAYER                           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌───────────┐  │
│  │  Dashboard   │ │  Benchmark   │ │  Admin Panel │ │  Student  │  │
│  │  (page.tsx)  │ │  Suite       │ │  Pages       │ │  Pages    │  │
│  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘ └─────┬─────┘  │
│         │                │                │               │         │
│  ┌──────┴────────────────┴────────────────┴───────────────┴──────┐  │
│  │              React Context (auth-context.tsx)                   │  │
│  └──────────────────────────┬────────────────────────────────────┘  │
└─────────────────────────────┼───────────────────────────────────────┘
                              │
┌─────────────────────────────┼───────────────────────────────────────┐
│                     SERVICE LAYER                                  │
│  ┌──────────────────────────┴────────────────────────────────────┐  │
│  │                   Services Layer                              │  │
│  │  ┌─────────────────┐ ┌────────────────┐ ┌─────────────────┐  │  │
│  │  │ optimizer-       │ │ benchmark-     │ │ sandbox-        │  │  │
│  │  │ service.ts       │ │ service.ts     │ │ api.ts          │  │  │
│  │  │ (Python API)     │ │ (Benchmark)    │ │ (Sandbox)       │  │  │
│  │  └────────┬────────┘ └───────┬────────┘ └───────┬─────────┘  │  │
│  └───────────┼──────────────────┼──────────────────┼────────────┘  │
└──────────────┼──────────────────┼──────────────────┼───────────────┘
               │                  │                  │
┌──────────────┼──────────────────┼──────────────────┼───────────────┐
│              │            API ROUTE LAYER (BFF)                     │
│  ┌───────────┴──────────────────┴──────────────────┴────────────┐  │
│  │                    Next.js Route Handlers                     │  │
│  │  ┌────────────┐  ┌─────────────┐  ┌──────────┐  ┌────────┐  │  │
│  │  │ /api/      │  │ /api/       │  │ /api/    │  │ /api/  │  │  │
│  │  │ optimize-  │  │ benchmark/* │  │ sandbox  │  │ admin/*│  │  │
│  │  │ route      │  │             │  │          │  │        │  │  │
│  │  └─────┬──────┘  └──────┬──────┘  └────┬─────┘  └───┬────┘  │  │
│  └────────┼────────────────┼───────────────┼────────────┼────────┘  │
└───────────┼────────────────┼───────────────┼────────────┼──────────┘
            │                │               │            │
            ▼                ▼               ▼            ▼
┌───────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                 │
│  ┌────────────────────┐         ┌──────────────────────────────┐  │
│  │  Supabase          │         │  Python FastAPI (8099)        │  │
│  │  ┌──────────────┐  │         │  ┌────────────────────────┐  │  │
│  │  │  PostgreSQL   │  │         │  │  Strategy Registry     │  │  │
│  │  │  + RLS        │  │         │  │  (16 Algorithms)       │  │  │
│  │  ├──────────────┤  │         │  ├────────────────────────┤  │  │
│  │  │  Auth         │  │         │  │  BenchmarkRunner       │  │  │
│  │  │  (JWT)        │  │         │  │  (Daemon Thread)       │  │  │
│  │  └──────────────┘  │         │  ├────────────────────────┤  │  │
│  └────────────────────┘         │  │  TSPLIB Parser         │  │  │
│                                  │  │  (46+ Problems)        │  │  │
│                                  │  └────────────────────────┘  │  │
│                                  └──────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────┘
```

### 4.2 Auth Akışı

```
┌─────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Browser │───▶│  Supabase    │───▶│  NextAuth.js │───▶│  Middleware   │
│         │    │  Auth        │    │  v4          │    │  (redirect)  │
└─────────┘    └──────────────┘    └──────────────┘    └──────────────┘
     │                                    │
     │            JWT Token               │
     └────────────────────────────────────┘
                        │
              ┌─────────┴──────────┐
              │  Supabase Client   │
              │  (server-side)     │
              │  + RLS Policies    │
              └────────────────────┘
```

---

## 5. Strateji Mimarisi

### 5.1 Strategy Hierarchy

```
BaseRoutingStrategy (base_strategy.py)
│   Abstract methods: optimize(), name, display_name
│
├── Pipeline A: Cluster-First, Route-Second
│   │   Mantık: Önce coğrafi kümeleme (Sweep/CW), sonra her küme için TSP
│   │
│   ├── GeneticAlgorithmStrategy (ga_strategy.py)
│   │   └── Population-based: crossover, mutation, selection
│   │
│   ├── PSOStrategy (pso_strategy.py)
│   │   └── Swarm intelligence: velocity, position update
│   │
│   ├── GreyWolfOptimizerStrategy (gwo_strategy.py)
│   │   └── Social hierarchy: alpha, beta, delta, omega
│   │
│   └── HarrisHawksOptimizerStrategy (hho_strategy.py)
│       └── Hunting behavior: exploration, exploitation, escape energy
│
├── Pipeline B: Route-First, Cluster-Second
│   │   Mantık: Önce Giant Tour (TSP), sonra optimal Split (Prins 2004)
│   │
│   ├── HybridSplitBaseStrategy (hybrid_base_strategy.py)
│   │   └── Common split logic: Numba-compatible giant tour → routes
│   │
│   ├── GASplitStrategy (ga_split_strategy.py)      ★ Recommended
│   │   └── GA + Optimal Split = En iyi kalite
│   │
│   ├── PSOSplitStrategy (pso_split_strategy.py)     ★ Hızlı
│   │   └── PSO + Optimal Split = Hızlı ve kaliteli
│   │
│   ├── GWOSplitStrategy (gwo_split_strategy.py)     ★ Balanced
│   │   └── GWO + Optimal Split = Güçlü keşif-sömürü
│   │
│   └── HHOSplitStrategy (hho_split_strategy.py)     ★ Adaptive
│       └── HHO + Optimal Split = Adaptif, kaçış enerjisi
│
├── Holistic Solvers (Native CVRP)
│   │   Mantık: Doğrudan CVRP çözümü, üçüncü parti kütüphaneler
│   │
│   ├── ORToolsCVRPStrategy (ortools_cvrp.py)
│   │   └── Google OR-Tools - Industry standard
│   │
│   ├── PyVRPStrategy (pyvrp_strategy.py) [Optional]
│   │   └── PyVRP HGS - DIMACS 2021 Winner ★
│   │
│   └── VROOMStrategy (vroom_strategy.py) [Optional]
│       └── VROOM C++ - Ultra hızlı (1000+ nokta < 5sn) ⚡
│
└── Heuristics & Local Search
    │   Mantık: Basit, hızlı, küçük ölçekli problemler
    │
    ├── GreedyHeuristicStrategy (greedy_heuristic.py)
    │   └── Nearest Neighbor - O(n²)
    │
    ├── TwoOptStrategy (two_opt_strategy.py)
    │   └── 2-opt edge exchange - O(n²)
    │
    └── PermutationTSPStrategy (permutation_tsp.py)
        └── Complete search - O(n!) - Optimal for n ≤ 10
```

### 5.2 Local Search Operatörleri

Tüm meta-sezgisel algoritmalar (Pipeline A) yapılandırılabilir local search destekler:

```
LocalSearchType (Enum)
├── none      → Local search yok
├── two_opt   → Kenar değiştirme (classic 2-opt)
├── three_opt → 3 kenar değiştirme (yüksek kalite)
├── or_opt    → Alt tur yeniden konumlandırma (kümeleme)
└── hybrid    → 2-opt + 3-opt + Or-opt kombine
```

**Numba JIT Support:** `local_search_numba.py` dosyası, Numba ile derlenmiş versiyonlar sunar. Büyük problem boyutlarında belirgin hız artışı sağlar.

### 5.3 Strategy Registry

`optimizer_api/strategies/__init__.py` dosyası tüm stratejileri yönetir:

```python
STRATEGY_REGISTRY = {
    # Pipeline A (4 ana + alias'lar)
    "genetic_algorithm": GeneticAlgorithmStrategy(),
    "pso": PSOStrategy(),
    "gwo": GreyWolfOptimizerStrategy(),
    "hho": HarrisHawksOptimizerStrategy(),

    # Pipeline B (4 ana + alias'lar)
    "ga_split": GASplitStrategy(),
    "pso_split": PSOSplitStrategy(),
    "gwo_split": GWOSplitStrategy(),
    "hho_split": HHOSplitStrategy(),

    # Holistic (optional fallback)
    "ortools_cvrp": ORToolsCVRPStrategy(),
    "pyvrp": _pyvrp_strategy or ORToolsCVRPStrategy(),  # Graceful fallback
    "vroom": _vroom_strategy or ORToolsCVRPStrategy(),  # Graceful fallback

    # Heuristics (3 ana + alias'lar)
    "two_opt": TwoOptStrategy(),
    "greedy": GreedyHeuristicStrategy(),
    "permutation_tsp": PermutationTSPStrategy(),
}
```

> **Önemli:** PyVRP ve VROOM opsiyoneldir. Kurulu değilse otomatik olarak OR-Tools'a fallback yapılır.

### 5.4 Algoritma Seçim Rehberi

| Öğrenci Sayısı | Öncelik: Hız | Öncelik: Kalite | Öncelik: Dengeli |
|-----------------|-------------|-----------------|------------------|
| N ≤ 30          | `pso_split` | `ga_split` ★    | `pso_split`      |
| 30 < N ≤ 100    | `pso`       | `pyvrp`         | `hho_split`      |
| N > 100         | `vroom` ⚡  | `pyvrp`         | `ortools_cvrp`   |

---

## 6. Benchmark Mimarisi

### 6.1 Benchmark Execution Flow

```
┌─────────────────────────────────────────────────────────────────────┐
│  HTTP Request (Uvicorn Worker)                                      │
│                                                                     │
│  POST /api/v1/benchmark/run                                         │
│  ├─ can_start_run() check                                           │
│  │   └─ running_count < MAX_CONCURRENT_BENCHMARKS (3)               │
│  │       └─ 429 Too Many Requests if limit exceeded                 │
│  ├─ create_run() → BenchmarkRunState (thread-safe with Lock)        │
│  ├─ spawn daemon thread → run_benchmark_task()                      │
│  └─ return 200 OK (IMMEDIATELY) ← İstemci beklemez                  │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Daemon Thread (Background Execution)                               │
│                                                                     │
│  run_benchmark_task()                                               │
│  ├─ Resolve problem names → BenchmarkProblem objects                │
│  │   └─ load_problem_coordinates() from TSPLIB parser               │
│  ├─ Resolve algorithm configs → AlgorithmConfig                     │
│  ├─ Create BenchmarkRunner(                                         │
│  │       strategies_registry=STRATEGY_REGISTRY,                     │
│  │       state_manager=benchmark_state_manager,                     │
│  │       run_id=run_id                                              │
│  │   )                                                             │
│  ├─ runner.run(                                                     │
│  │       problems=[...],                                            │
│  │       algorithms=[...],                                          │
│  │       n_runs=3,                                                  │
│  │       seed=42                                                    │
│  │   )                                                             │
│  │   ├─ For each (problem × algorithm × run):                       │
│  │   │   ├─ Dispatch to real strategy.optimize()                    │
│  │   │   ├─ Record: tour_length, elapsed_ms, gap_percent            │
│  │   │   └─ update_progress() every N experiments (with Lock)       │
│  │   └─ complete_run() when done (with Lock)                        │
│  └─ fail_run() on exception (with Lock)                             │
│                                                                     │
├─────────────────────────────────────────────────────────────────────┤
│  Polling (Frontend)                                                 │
│                                                                     │
│  GET /api/v1/benchmark/status?run_id=xxx  (her 1 saniye)           │
│  └─ Returns: {                                                      │
│        run_id, status, total_experiments,                           │
│        completed_experiments, progress_percent,                     │
│        results_count, message, start_time, end_time                 │
│      }                                                              │
└─────────────────────────────────────────────────────────────────────┘
```

### 6.2 Thread Safety Model

```
┌──────────────────────────────────────────────────────┐
│  BenchmarkStateManager (Singleton)                    │
│  ┌──────────────────────────────────────────────────┐ │
│  │  _lock: threading.Lock()                         │ │
│  │  _runs: Dict[str, BenchmarkRunState]             │ │
│  │                                                  │ │
│  │  Write Operations (protected by _lock):           │ │
│  │  ├─ create_run()       → Lock acquire            │ │
│  │  ├─ update_progress()  → Lock acquire            │ │
│  │  ├─ add_result()       → Lock acquire            │ │
│  │  ├─ complete_run()     → Lock acquire            │ │
│  │  ├─ fail_run()         → Lock acquire            │ │
│  │  └─ stop_run()         → Lock acquire            │ │
│  │                                                  │ │
│  │  Read Operations (protected by _lock):            │ │
│  │  ├─ get_run()          → Lock acquire            │ │
│  │  ├─ can_start_run()    → Lock acquire            │ │
│  │  └─ list_runs()        → Lock acquire            │ │
│  └──────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────┘
```

### 6.3 Benchmark State Lifecycle

```
  RUNNING ──────▶ COMPLETED
     │                  ▲
     │                  │
     ├──▶ FAILED ───────┘
     │
     └──▶ STOPPED
```

### 6.4 Concurrent Limit

```python
MAX_CONCURRENT_BENCHMARKS = 3  # Soft limit
# Returns HTTP 429 when exceeded:
# {
#   "error": "Maximum 3 concurrent benchmarks reached",
#   "error_code": "CONCURRENT_LIMIT_EXCEEDED",
#   "message": "Bekleyen taklada. Diğer benchmarklar tamamlanana kadar bekleyin.",
#   "max_concurrent": 3
# }
```

---

## 7. API Sözleşmeleri

### 7.1 Port Yapılandırması

| Servis | Port | URL |
|--------|------|-----|
| Next.js (Frontend + BFF) | 3000 | `http://localhost:3000` |
| Python FastAPI (Optimizer) | 8099 | `http://127.0.0.1:8099` |
| Supabase | Cloud | `https://*.supabase.co` |

### 7.2 Next.js API Routes (BFF Layer)

#### Benchmark Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| `POST` | `/api/benchmark/run` | Yeni benchmark başlat (non-blocking) |
| `GET` | `/api/benchmark/status` | Benchmark ilerleme durumu (polling) |
| `POST` | `/api/benchmark/stop` | Çalışan benchmark'u durdur |
| `GET` | `/api/benchmark/problems` | TSPLIB problem listesi |

#### Optimization Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| `POST` | `/api/optimize-route` | Tek algoritma ile rota optimizasyonu |
| `POST` | `/api/compare-algorithms` | Tüm algoritmaları karşılaştır |
| `POST` | `/api/calculate-vehicles` | Araç gereksinim hesaplama |
| `POST` | `/api/sandbox` | Sandbox modda optimizasyon |
| `POST` | `/api/ride-confirmation` | Biniş onayı |
| `GET/POST` | `/api/route-plans` | Rota planları |

#### Admin Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| `GET/POST` | `/api/admin/users` | Kullanıcı CRUD |
| `PATCH` | `/api/admin/users/password` | Kullanıcı şifre değiştir |
| `GET/POST` | `/api/admin/vehicles` | Araç CRUD |
| `GET` | `/api/admin/ride-requests` | Biniş talepleri listele |

#### Driver Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| `GET` | `/api/driver/assignments` | Sürücü rota atamaları |

#### Auth Endpoints

| Method | Path | Açıklama |
|--------|------|----------|
| `PATCH` | `/api/profile/password` | Profil şifre değiştir |
| `POST` | `/api/auth/dev-reset` | Dev: Auth sıfırlama |
| `POST` | `/api/auth/hint` | Auth ipucu (rate limited) |

### 7.3 Python FastAPI Endpoints (Optimizer API)

> **Base URL:** `http://127.0.0.1:8099`

| Method | Path | Açıklama | Request | Response |
|--------|------|----------|---------|----------|
| `GET` | `/health` | Sağlık kontrolü | — | `{ status, version, features, algorithms }` |
| `GET` | `/api/v1/strategies` | Strateji listesi | — | `List[StrategyInfo]` |
| `POST` | `/api/v1/optimize` | Rota optimizasyonu | `OptimizationRequest` | `OptimizationResponse` |
| `POST` | `/api/v1/compare` | Algoritma karşılaştırma | `CompareRequest` | `CompareResponse` |
| `POST` | `/api/v1/vehicle-calculator` | Araç hesaplama | `OptimizationRequest` | `OptimizationResponse` |
| `POST` | `/api/v1/extract-time-windows` | Zaman penceresi çıkarma | `List[WeeklyScheduleEntry]` | `Dict[str, TimeWindow]` |
| `POST` | `/api/v1/schedule-to-students` | Program → öğrenci dönüşüm | `List[WeeklyScheduleEntry]` | `List[StudentNode]` |
| `GET` | `/api/v1/benchmark/problems` | TSPLIB problem listesi | `?category=` | `List[Dict]` |
| `GET` | `/api/v1/benchmark/problems/{name}` | Problem detayı | — | `Dict` (coordinates dahil) |
| `POST` | `/api/v1/benchmark/run` | Benchmark başlat | `{ run_id, algorithms, problems, settings }` | `{ run_id, status, total_experiments }` |
| `GET` | `/api/v1/benchmark/status` | Benchmark durumu | `?run_id=` | `{ status, progress_percent, ... }` |
| `POST` | `/api/v1/benchmark/stop` | Benchmark durdur | `?run_id=` | `{ run_id, status, results_collected }` |
| `GET` | `/api/v1/benchmark/results/{run_id}` | Benchmark sonuçları | — | `{ run_id, status, results[] }` |
| `POST` | `/api/v1/benchmark/download/{name}` | TSPLIB indirme | — | `{ status, file_path }` |

### 7.4 OptimizationRequest Schema

```typescript
{
  algorithm: string;              // "ga_split", "pso_split", "ortools_cvrp", etc.
  students: StudentNode[];        // Öğrenci listesi
  depot: Depot;                   // Başlangıç/Bitiş noktası
  max_travel_time: number;        // Maks tur süresi (dakika), default: 120
  sw_capacity: number;            // Tekerlekli sandalye kapasitesi, default: 4
  so_capacity: number;            // Oturma kapasitesi, default: 5
  local_search_type: string;      // "none" | "two_opt" | "three_opt" | "or_opt" | "hybrid"
  clustering_algorithm: string;   // "sweep" | "kmeans" | "clarke_wright"
  
  // CVRPTW Support (v3.1.0)
  direction: "pickup" | "dropoff";
  use_time_windows: boolean;
  target_time?: string;           // "09:00" (HH:MM)
  time_window_size?: number;      // 30 (dakika)
  offset_minutes?: number;        // 10 (sürücü bildirim buffer)
  
  // Algorithm-specific configs
  ga_config?: { population_size?, max_iterations?, crossover_rate?, mutation_rate? };
  pso_config?: { swarm_size?, max_iterations?, inertia_weight? };
  gwo_config?: { population_size?, max_iterations?, initial_a? };
  hho_config?: { population_size?, max_iterations?, initial_energy? };
  
  // IE Sandbox
  vehicles?: VehicleConfig[];
}
```

### 7.5 OptimizationResponse Schema

```typescript
{
  success: boolean;
  algorithm_used: string;
  routes: VehicleRoute[];         // Optimize edilmiş rotalar
  total_vehicles: number;
  total_duration_minutes: number;
  execution_time_seconds: number;
  error_message?: string;
  
  // CVRPTW
  direction?: "pickup" | "dropoff";
  time_windows_used?: boolean;
  
  // IE Resource Analysis
  ie_data?: {
    standard_vehicles_needed: number;
    hourly_demand: Record<number, { pickup: { Sw, So }, dropoff: { Sw, So } }>;
    bottlenecks: BottleneckInfo[];
    time_shift_suggestions: TimeShiftSuggestion[];
  };
}
```

---

## 8. Veritabanı Şeması

### 8.1 Tablo Özeti

| Tablo | Açıklama | Primary Key | Foreign Keys |
|-------|----------|-------------|--------------|
| `users` | Kullanıcı bilgileri | `id (UUID)` | — |
| `weekly_schedules` | Haftalık programlar | `id (UUID)` | `user_id → users` |
| `ride_requests` | Biniş talepleri | `id (UUID)` | `user_id → users`, `vehicle_id → vehicles` |
| `vehicles` | Araç bilgileri | `id (UUID)` | — |
| `routes` | Rotalar | `id (UUID)` | — |
| `route_assignments` | Rota atamaları | `id (UUID)` | `vehicle_id → vehicles`, `driver_id → users`, `route_id → routes` |
| `notifications` | Bildirimler | `id (UUID)` | `user_id → users`, `related_request_id → ride_requests` |
| `admin_settings` | Yönetici ayarları | `id (UUID)` | — |
| `sandbox_scenarios` | Sandbox senaryoları | `id (UUID)` | — |
| `route_plans` | Rota planları | `id (UUID)` | — |
| `time_matrix` | Zaman matrisi | — | — |

### 8.2 users Tablosu

```sql
CREATE TABLE users (
  id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  email           TEXT UNIQUE NOT NULL,
  name            TEXT NOT NULL,
  role            TEXT NOT NULL CHECK (role IN ('student', 'admin', 'driver')),
  student_number  TEXT UNIQUE,
  home_address    TEXT,
  home_coordinates JSONB,
  accessibility_needs TEXT[],
  disability_type TEXT CHECK (disability_type IN ('Sw', 'So')),
  location_code   TEXT,
  weekly_schedule_id UUID,
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW()
);
```

**Roller:**
- `student` — Öğrenci (binis talebi, program yönetimi)
- `admin` — Yönetici (tüm CRUD işlemleri, benchmark, sandbox)
- `driver` — Sürücü (rota görüntüleme, navigasyon)

**Disability Types:**
- `Sw` — Tekerlekli Sandalye (wheelchair) — özel araç gerektirir
- `So` — Sedye (stretcher) — standart araç

### 8.3 vehicles Tablosu

```sql
CREATE TABLE vehicles (
  id                 UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  name               TEXT NOT NULL,
  type               TEXT NOT NULL CHECK (type IN ('minibus', 'bus', 'van')),
  plate_number       TEXT,
  wheelchair_capacity INTEGER NOT NULL DEFAULT 0,
  seating_capacity   INTEGER NOT NULL DEFAULT 0,
  status             TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'maintenance')),
  created_at         TIMESTAMPTZ DEFAULT NOW(),
  updated_at         TIMESTAMPTZ DEFAULT NOW()
);
```

### 8.4 ride_requests Tablosu

```sql
CREATE TABLE ride_requests (
  id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id                 UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  type                    TEXT NOT NULL CHECK (type IN ('scheduled', 'adhoc')),
  requested_pickup_time   TIMESTAMPTZ NOT NULL,
  requested_dropoff_time  TIMESTAMPTZ NOT NULL,
  actual_pickup_time      TIMESTAMPTZ,
  actual_dropoff_time     TIMESTAMPTZ,
  pickup_location         JSONB NOT NULL,
  dropoff_location        JSONB NOT NULL,
  status                  TEXT NOT NULL CHECK (status IN (
    'pending_student_confirmation',
    'confirmed',
    'cancelled_by_student',
    'cancelled_by_admin',
    'in_progress',
    'completed',
    'pending_admin_approval'
  )),
  vehicle_id              UUID,
  notes                   TEXT,
  created_at              TIMESTAMPTZ DEFAULT NOW(),
  updated_at              TIMESTAMPTZ DEFAULT NOW()
);
```

### 8.5 Index'ler

| Index | Tablo | Kolon |
|-------|-------|-------|
| `idx_users_email` | users | email |
| `idx_users_student_number` | users | student_number |
| `idx_users_role` | users | role |
| `idx_weekly_schedules_user_id` | weekly_schedules | user_id |
| `idx_ride_requests_user_id` | ride_requests | user_id |
| `idx_ride_requests_status` | ride_requests | status |
| `idx_ride_requests_pickup_time` | ride_requests | requested_pickup_time |
| `idx_route_assignments_date` | route_assignments | date |
| `idx_route_assignments_vehicle_id` | route_assignments | vehicle_id |
| `idx_route_assignments_driver_id` | route_assignments | driver_id |
| `idx_routes_date` | routes | date |
| `idx_notifications_user_id` | notifications | user_id |
| `idx_notifications_read` | notifications | read |

### 8.6 Row Level Security (RLS)

Tüm tablolarda RLS aktiftir. Politikalar `supabase/rls_policies.sql` dosyasında tanımlıdır:

- **users**: Admin tüm kayıtları okuyabilir, herkes kendi kaydını güncelleyebilir
- **weekly_schedules**: Herkes kendi programını okuyabilir/güncelleyebilir
- **ride_requests**: Admin tüm talepleri görebilir, öğrenci sadece kendi taleplerini
- **vehicles**: Admin CRUD, sürücü read-only
- **notifications**: Herkes kendi bildirimlerini okuyabilir
- **admin_settings**: Sadece admin erişebilir

### 8.7 updated_at Trigger

Tüm tablolarda otomatik `updated_at` güncellemesi için trigger mekanizması:

```sql
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';
```

---

## 9. Dosya Sorumluluk Haritası

### 9.1 Frontend Core Dosyaları

| Dosya | Sorumluluk | Bağımlılıklar |
|-------|-----------|---------------|
| `src/lib/config.ts` | Merkezi konfigürasyon, `OPTIMIZER_API_URL` | `process.env` |
| `src/lib/algorithm-constants.ts` | Algoritma isimleri SSOT (Single Source of Truth) | — |
| `src/lib/supabase.ts` | Supabase client oluşturma | `@supabase/supabase-js` |
| `src/lib/supabase-admin.ts` | Admin Supabase client | `SUPABASE_SERVICE_ROLE_KEY` |
| `src/contexts/auth-context.tsx` | Auth state yönetimi | Supabase Auth, NextAuth |
| `src/middleware.ts` | Route protection, auth redirect | Auth context |
| `src/services/optimizer-service.ts` | Python API iletişim katmanı | `config.ts`, `fetch` |
| `src/services/benchmark-service.ts` | Benchmark servis katmanı | `fetch` |
| `src/services/sandbox-api.ts` | Sandbox optimizasyon API | `fetch` |

### 9.2 Python Core Dosyaları

| Dosya | Sorumluluk | Satır Sayısı |
|-------|-----------|-------------|
| `optimizer_api/main.py` | FastAPI uygulama, tüm endpoint'ler | ~1100+ |
| `optimizer_api/strategies/__init__.py` | Strategy Registry, SSOT | ~376 |
| `optimizer_api/strategies/base_strategy.py` | Abstract base class | — |
| `optimizer_api/benchmark_runner.py` | Benchmark execution engine | — |
| `optimizer_api/benchmark_state.py` | Thread-safe state management | ~162 |
| `optimizer_api/models/schemas.py` | Pydantic request/response modelleri | — |
| `optimizer_api/utils/tsplib_parser.py` | TSPLIB parsing + EUC_2D NINT rounding | — |
| `optimizer_api/utils/data_loader.py` | Supabase veri yükleme + euclidean fallback | — |
| `optimizer_api/utils/split_decoder.py` | Prins (2004) Optimal Split | — |
| `optimizer_api/utils/local_search.py` | 2-opt, 3-opt, hybrid local search | — |
| `optimizer_api/utils/local_search_numba.py` | Numba JIT derlenmiş local search | — |
| `optimizer_api/utils/resource_profiler.py` | IE kaynak analizi | — |
| `optimizer_api/utils/clustering.py` | K-Means kümeleme | — |
| `optimizer_api/utils/time_window_extractor.py` | Zaman penceresi çıkarma | — |
| `optimizer_api/utils/patterns.py` | Singleton ve tasarım örüntüleri | — |

### 9.3 shadcn/ui Component'ler (~38 dosya)

```
alert, alert-dialog, accordion, aspect-ratio, avatar, badge, breadcrumb,
button, calendar, card, carousel, checkbox, collapsible, command, context-menu,
dialog, drawer, dropdown-menu, form, hover-card, input, input-otp, label,
menubar, navigation-menu, pagination, popover, progress, radio-group,
resizable, scroll-area, select, separator, sheet, sidebar, skeleton, slider,
sonner, switch, table, tabs, toast, toaster, toggle, toggle-group, tooltip
```

---

## 10. Tasarım İlkeleri

### 10.1 Temel İlkeler

| # | İlke | Açıklama |
|---|------|----------|
| 1 | **Gerçek Veri Mıknatısı** | Rastgele/placeholder veri kullanılmaz. Tüm sonuçlar gerçek optimizer çalıştırmasından gelir. |
| 2 | **Akademik Doğruluk** | TSPLIB `EUC_2D NINT` rounding kullanılır. Akademik yayın uyumluluğu sağlanır. |
| 3 | **Dual-Track Mimari** | Commercial (Hybrid, stable) + Academic (SOTA/ALNS, experimental) ayrımı. |
| 4 | **Thread-Safe Singleton** | Strategy registry'de singleton pattern, benchmark state'te Lock ile thread safety. |
| 5 | **Euclidean Fallback** | Supabase unavailable olduğunda euclidean mesafe hesaplama ile çalışmaya devam eder. |
| 6 | **Graceful Degradation** | PyVRP/VROOM kurulu değilse OR-Tools'a fallback. API down olursa local calculation. |
| 7 | **SSOT (Single Source of Truth)** | `algorithm-constants.ts` (frontend) ve `strategies/__init__.py` (backend) senkronize. |
| 8 | **Non-Blocking Benchmark** | Benchmark'lar daemon thread'de çalışır. HTTP endpoint hemen 200 döner. |

### 10.2 Frontend İlkeleri

| İlke | Uygulama |
|------|----------|
| **Server Components First** | Varsayılan olarak RSC. Client component sadece interaktivite gerektiğinde. |
| **Colocation** | Component, service ve type dosyaları bir arada. |
| **Route Grouping** | `(app)` authenticated, `(auth)` public route groups. |
| **BFF Pattern** | Next.js API Routes backend proxy olarak çalışır. Frontend doğrudan Python API'ye çağrı yapmaz. |
| **Type Safety** | Zod + TypeScript end-to-end type safety. Runtime validation. |

### 10.3 Backend İlkeleri

| İlke | Uygulama |
|------|----------|
| **Strategy Pattern** | Her algoritma `BaseRoutingStrategy`'den türetilir. Registry ile yönetilir. |
| **Pydantic Validation** | Tüm request/response'lar Pydantic modelleri ile validate edilir. |
| **Daemon Thread Pattern** | Uzun süreli işlemler (benchmark) arka planda daemon thread'de çalışır. |
| **Concurrent Limit** | Aynı anda max 3 benchmark çalışabilir (soft limit, HTTP 429). |
| **CORS Configuration** | `ALLOWED_ORIGINS` env variable ile yönetilir. |

### 10.4 Veritabanı İlkeleri

| İlke | Uygulama |
|------|----------|
| **RLS First** | Tüm tablolarda Row Level Security aktif. |
| **Soft Delete Avoidance** | Hard delete + CASCADE kullanılır. |
| **UUID Primary Keys** | Tüm tablolarda UUID v4. |
| **Auto Timestamps** | `created_at` ve `updated_at` otomatik (trigger + default). |
| **Index Strategy** | Sık sorgulanan kolonlarda B-tree index. |

---

## 11. Deployment ve Port Yapılandırması

### 11.1 Geliştirme Ortamı

```bash
# Next.js Development Server
npm run dev          # → http://localhost:3000

# Python FastAPI Optimizer
cd optimizer_api
uvicorn main:app --port 8099 --reload
# → http://127.0.0.1:8099

# Health Check
curl http://127.0.0.1:8099/health
```

### 11.2 Environment Variables

**Frontend (.env.local):**
```env
NEXT_PUBLIC_SUPABASE_URL=https://xxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# Optimizer API URL (defaults to http://127.0.0.1:8099)
OPTIMIZER_API_URL=http://127.0.0.1:8099
```

**Backend (optimizer_api/.env):**
```env
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:9002
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_SERVICE_ROLE_KEY=eyJ...
```

### 11.3 CORS Configuration

FastAPI CORS middleware, `ALLOWED_ORIGINS` environment variable'dan konfigüre edilir:

```python
_allowed_origins = [
    o.strip()
    for o in os.getenv("ALLOWED_ORIGINS", 
        "http://localhost:9002,http://127.0.0.1:9002,http://localhost:3000,http://127.0.0.1:3000"
    ).split(",")
]
```

### 11.4 API Communication Pattern

```
Frontend Browser
    │
    │ fetch('/api/optimize-route?_xTransformPort=8099')
    ▼
Next.js API Route (port 3000)
    │
    │ fetch('http://127.0.0.1:8099/api/v1/optimize', { ... })
    ▼
Python FastAPI (port 8099)
    │
    ├── Strategy.optimize() → Routes
    ├── ResourceProfiler → IE Analysis
    └── Supabase (optional) → Data
```

> **XTransformPort:** Frontend'deki relative URL'ler `XTransformPort` query parametresi ile port yönlendirmesi yapar. Bu sayede frontend doğrudan farklı porta istek yapabilir.

---

## Ekler

### A. Algoritma Karşılaştırma Tablosu

| Algoritma | Pipeline | Tip | Karmaşıklık | En İyi For | Local Search |
|-----------|----------|-----|-------------|------------|--------------|
| `genetic_algorithm` | A | Meta-heuristic | O(g × p × n²) | Genel amaç | ✓ Configurable |
| `pso` | A | Swarm | O(i × s × n²) | Hızlı yakınsama | ✓ Configurable |
| `gwo` | A | Hierarchy | O(i × p × n²) | Keşif-sömürü | ✓ Configurable |
| `hho` | A | Hunting | O(i × h × n²) | Adaptif arama | ✓ Configurable |
| `ga_split` | B | Meta+Split | O(g × p × n²) + O(n²) | Küçük (N≤30) ★ | Built-in |
| `pso_split` | B | Swarm+Split | O(i × s × n²) + O(n²) | Orta (N≤100) ★ | Built-in |
| `gwo_split` | B | Hierarchy+Split | O(i × p × n²) + O(n²) | Dengeli ★ | Built-in |
| `hho_split` | B | Hunting+Split | O(i × h × n²) + O(n²) | Adaptif ★ | Built-in |
| `ortools_cvrp` | Holistic | Solver | O(n³) | Büyük (N>100) | — |
| `pyvrp` | Holistic | HGS Solver | O(n² log n) | En yüksek kalite | — |
| `vroom` | Holistic | C++ Solver | O(n²) | Ultra hızlı | — |
| `two_opt` | Heuristic | Local Search | O(n²) | Küçük-orta | — |
| `greedy` | Heuristic | Constructive | O(n²) | Hızlı baseline | — |
| `permutation_tsp` | Heuristic | Exact | O(n!) | N ≤ 10 optimal | — |

### B. Status Lifecycle - Ride Request

```
pending_student_confirmation → confirmed → in_progress → completed
        │                       │
        └── cancelled_by_student┘
        │                       │
        └── cancelled_by_admin──┘

pending_admin_approval → confirmed → in_progress → completed
```

### C. Bildirim Tipleri

| Tip | Açıklama |
|-----|----------|
| `ride_confirmation` | Biniş onayı bekleniyor |
| `ride_reminder` | Biniş hatırlatma |
| `route_update` | Rota güncellemesi |
| `system` | Sistem bildirimi |

---

> **Son Güncelleme:** 13 Temmuz 2025  
> **Belge Sürümü:** 2.0  
> **İlgili Dosyalar:** `.ai-rules`, `ROADMAP.md`, `CODE_REVIEW_REPORT.md`
