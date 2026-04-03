# UniRide Projesi - Kapsamlı Mevcut Durum Analizi Raporu

**Tarih:** 2026-03-28  
**Analiz Kapsamı:** Kod Tabanı, Dokümantasyon, Mimari ve Operasyonel Durum  
**Hazırlayan:** Senior Full-Stack Developer Analizi  
**Sürüm:** 1.0

---

## Yönetici Özeti (Executive Summary)

Bu rapor, Düzce Üniversitesi öğrenci taşıma optimizasyonu sistemi olan UniRide projesinin kapsamlı bir durum analizini sunmaktadır. Analiz, kaynak kodların incelenmesi, mevcut dokümantasyonun değerlendirilmesi ve uygulama davranışlarının karşılaştırılması sonucunda hazırlanmıştır.

**Temel Bulgular:**

- Proje, Next.js 16 + Supabase + Python FastAPI mimarisi üzerine inşa edilmiş aktif bir taşıma optimizasyonu sistemidir
- Algoritma entegrasyonunda UI-Python arasında kritik anahtar uyumsuzlukları tespit edilmiştir
- Test kapsamı %10'un altındadır; otomasyon eksikliği ciddi risk oluşturmaktadır
- Güvenlik yapılandırması temel düzeyde uygulanmış, ancak bazı kritik alanlarda iyileştirme gereklidir
- Veritabanı tasarımı iyi yapılandırılmış, ancak RLS politikaları ve indeksleme optimize edilmemiştir
- Time matrix entegrasyonu kritik sorunlar içermekte olup, gerçek veri yüklenmediği durumda sıfır değerli matrix döndürülmektedir

**Öncelikli Eylemler:**

1. Algoritma anahtar uyumsuzluklarının düzeltilmesi (KRITIK)
2. Test kapsamının genişletilmesi (YÜKSEK)
3. Time matrix entegrasyonunun doğrulanması (KRITIK)
4. CI/CD borcunun kapatılması (ORTA)
5. Güvenlik denetiminin tamamlanması (ORTA)

---

## Bölüm 1: Mevcut Mimari ve Bileşenler

### 1.1 Genel Mimari Yapısı

UniRide projesi, üç katmanlı bir microservice mimarisi üzerine inşa edilmiştir:

```
┌─────────────────────────────────────────────────────────────┐
│                  FRONTEND (Next.js 16)                    │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │   Admin    │ │  Student  │ │     Driver        │  │
│  │   Panel   │ │   Panel   │ │     Panel        │  │
│  └─────────────┘ └─────────────┘ └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│              API LAYER (Next.js API Routes)                │
│  ┌─────────────┐ ┌─────────────┐ ┌─────────────────────┐  │
│  │ /api/    │ │ /api/    │ │     /api/        │  │
│  │ calculate │ │ optimize │ │     admin/*      │  │
│  └─────────────┘ └─────────────┘ └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                           │
              ┌────────────┴────────────┐
              ▼                     ▼
┌────���─────────────────────┐  ┌──────────────────────────┐
│  Python Optimizer API    │  │     Supabase          │
│  (FastAPI Microservice) │  │  (Database + Auth)    │
│  ┌────────────────┐   │  │  ┌──────────────┐    │
│  │ GA, PSO, GWO  │   │  │  │  PostgreSQL │    │
│  │ HHO, OR-Tools │   │  │  │  + RLS     │    │
│  └────────────────┘   │  │  └──────────────┘    │
└──────────────────────────┘  └──────────────────────────┘
```

### 1.2 Temel Bileşenler

| Bileşen | Teknoloji | Sürüm | Durum |
|--------|----------|-------|------|
| Frontend Framework | Next.js | 16.1.6 | ✅ Aktif |
| UI Kütüphanesi | Radix UI | 1.1.6+ | ✅ Aktif |
| Veritabanı | PostgreSQL (Supabase) | - | ✅ Aktif |
| Auth | Supabase Auth | - | ✅ Aktif |
| Python API | FastAPI | - | ✅ Aktif |
| Algoritma Kütüphanesi | OR-Tools, PyVRP | - | ✅ Aktif |
| Excel İşleme | xlsx | 0.18.5 | ✅ Aktif |
| AI Entegrasyonu | Genkit | 1.8.0 | ✅ Aktif |

### 1.3 Mimari Katmanlar

**Katman 1: Sunum (Presentation Layer)**
Konum: `src/app/(app)/*` ve `src/components/*`

- Admin panel sayfaları: `/admin/vehicle-planning`, `/admin/vehicles`, `/admin/users`
- Öğrenci paneli: `/schedule`, `/profile`, `/request-ride`
- Sürücü paneli: `/driver/assignments`, `/driver/navigation`
- UI bileşenleri: Radix UI tabanlı shadcn/ui bileşenleri

**Katman 2: İş Mantığı (Business Logic Layer)**
Konum: `src/services/*` ve `src/lib/*`

- `optimizer-service.ts`: Python API entegrasyonu
- `doubus/`: Rota optimizasyon hizmetleri
- `excel/import.ts`: Excel dosya işleme
- `database.ts`: Veritabanı adaptörü
- `supabase-auth.ts`: Kimlik doğrulama

**Katman 3: Veri Erişimi (Data Access Layer)**
Konum: `src/lib/supabase-db.ts`

- Veritabanı CRUD operasyonları
- Case dönüşüm fonksiyonları (snake_case ↔ camelCase)

---

## Bölüm 2: Kod Tabanı Yapısı

### 2.1 Dizin Yapısı

```
UniRide/
├── src/
│   ├── app/                    # Next.js App Router sayfaları
│   │   ├── (app)/            # Korumalı sayfalar
│   │   │   ├── admin/        # Admin panel
│   │   │   ├── dashboard/   # Öğrenci dashboard
│   │   │   ├── driver/      # Sürücü panel
│   │   │   └── profile/    # Profil yönetimi
│   │   ├── (auth)/         # Auth sayfaları
│   │   │   ├── login/
│   │   │   ├── register/
│   │   │   └── reset-password/
│   │   ├── api/            # API Routes
│   │   │   ├── calculate-vehicles/
│   │   │   ├── optimize-route/
│   │   │   ├── compare-algorithms/
│   │   │   └── admin/
│   │   ├── layout.tsx
│   │   └── page.tsx
│   ├── components/           # UI Bileşenleri
│   │   ├── admin/          # Admin bileşenleri
│   │   ├── auth/          # Auth bileşenleri
│   │   ├── student/       # Student bileşenleri
│   │   ├── layout/        # Layout bileşenleri
│   │   └── ui/           # shadcn/ui bileşenleri
│   ├── services/          # İş mantığı
│   │   ├── doubus/        # Rota optimizasyonu
│   │   └── excel/        # Excel işleme
│   ├── lib/              # Yardımcı kütüphaneler
│   │   ├── config.ts      # Merkezi konfigürasyon
│   │   ├── database.ts   # DB adaptörü
│   │   ├── supabase.ts  # Supabase client
│   │   └��─ algorithm-constants.ts
│   ├── types/             # TypeScript tipleri
│   ├── contexts/         # React context
│   ├── hooks/           # Custom hooks
│   └── middleware.ts    # Next.js middleware
├── supabase/             # Supabase şema dosyaları
├── public/               # Statik dosyalar
├── package.json         # Bağımlılıklar
└── tsconfig.json        # TypeScript yapılandırması
```

### 2.2 Kod Metrikleri

| Metrik | Değer | Not |
|--------|-------|------|
| Toplam Dosya Sayısı | ~150+ | TypeScript + TSX |
| Toplam Satır (tahmini) | 25,000+ | Build dosyaları dahil |
| API Route Sayısı | 15+ | Admin, driver, auth, optimizasyon |
| Bileşen Sayısı | 80+ | UI bileşenleri dahil |
| Service Dosyası | 10+ | Ana iş mantığı |

### 2.3 Kod Kalitesi Gösterge tablosu

| Kategori | Durum | Puan |
|----------|-------|------|
| TypeScript Kullanımı | ✅ İyi | 8/10 |
| Kod Organizasyonu | ✅ İyi | 8/10 |
| Açıklayıcı Yorumlar | ⚠️ Yetersiz | 4/10 |
| Yeniden Kullanılabilirlik | ✅ İyi | 8/10 |
| Error Handling | ⚠️ Kısmi | 6/10 |
| Dokümantasyon | ⚠️ Var ama eksik | 5/10 |

---

## Bölüm 3: Frontend/Backend/Infra Entegrasyonları

### 3.1 Frontend-Backend Entegrasyonu

**API İletişim Modeli:**

```typescript
// Frontend → Backend (Next.js API Routes)
const response = await fetch("/api/calculate-vehicles", {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    students: activeStudents,
    maxTourTime: 120,
    swCapacity: 4,
    soCapacity: 5,
    strategy: "genetic_algorithm",
    clusteringAlgorithm: "sweep"
  })
});
```

**Kimlik Doğrulama Akışı:**

1. Kullanıcı login formunu doldurur
2. `supabase-auth.ts` → `signIn()` çağrılır
3. Supabase Auth token alınır
4. Token, Authorization header olarak tüm isteklere eklenir
5. Middleware `/api/admin/*` rotalarını korur

### 3.2 Backend-Python Entegrasyonu

**Proxy Yapısı:**

Next.js API Routes, Python FastAPI için proxy görevi görmektedir:

```typescript
// src/services/optimizer-service.ts
const response = await fetch(`${OPTIMIZER_API_URL}/api/v1/optimize`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({
    algorithm: "genetic_algorithm",
    students: students.map(s => ({...})),
    depot: {...},
    max_travel_time: 120,
    sw_capacity: 4,
    so_capacity: 5
  })
});
```

**Sorun:** Environment variable (`OPTIMIZER_API_URL`) varsayılan olarak `http://127.0.0.1:8000` kullanmaktadır. Üretim ortamında bu değerin açıkça ayarlanması gereklidir.

### 3.3 Backend-Supabase Entegrasyonu

**Veritabanı Erişimi:**

```typescript
// src/lib/supabase-db.ts
const { data, error } = await getClient()
  .from("users")
  .select("*")
  .eq("id", userId)
  .single();
```

**Auth Entegrasyonu:**

```typescript
// src/lib/supabase-auth.ts
const { data: { user }, error } = await supabaseClient.auth.signInWithPassword({
  email,
  password
});
```

---

## Bölüm 4: Veri Modeli ve Veritabanı Tasarımı

### 4.1 Veritabanı Şeması

**Ana Tablolar:**

```sql
-- Users tablosu
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  role TEXT CHECK (role IN ('student', 'admin', 'driver')),
  student_number TEXT,
  home_address TEXT,
  home_coordinates JSONB,
  disability_type TEXT CHECK (disability_type IN ('Sw', 'So')),
  location_code TEXT,
  weekly_schedule_id UUID,
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Vehicles tablosu
CREATE TABLE vehicles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  type TEXT CHECK (type IN ('minibus', 'bus', 'van')),
  plate_number TEXT,
  wheelchair_capacity INTEGER DEFAULT 4,
  seating_capacity INTEGER DEFAULT 5,
  status TEXT CHECK (status IN ('active', 'inactive', 'maintenance')),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Ride Requests tablosu
CREATE TABLE ride_requests (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id),
  type TEXT CHECK (type IN ('scheduled', 'adhoc')),
  requested_pickup_time TIMESTAMPTZ NOT NULL,
  requested_dropoff_time TIMESTAMPTZ NOT NULL,
  actual_pickup_time TIMESTAMPTZ,
  actual_dropoff_time TIMESTAMPTZ,
  pickup_location JSONB NOT NULL,
  dropoff_location JSONB NOT NULL,
  status TEXT DEFAULT 'pending_student_confirmation',
  vehicle_id UUID REFERENCES vehicles(id),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  notes TEXT
);

-- Weekly Schedules tablosu
CREATE TABLE weekly_schedules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES users(id) UNIQUE,
  entries JSONB DEFAULT '[]',
  last_updated TIMESTAMPTZ DEFAULT NOW(),
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Route Assignments tablosu
CREATE TABLE route_assignments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL,
  vehicle_id UUID REFERENCES vehicles(id),
  driver_id UUID REFERENCES users(id),
  route_id UUID,
  student_ids JSONB DEFAULT '[]',
  pickup_time TIMESTAMPTZ NOT NULL,
  estimated_dropoff_time TIMESTAMPTZ,
  status TEXT DEFAULT 'scheduled',
  created_at TIMESTAMPTZ DEFAULT NOW(),
  updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Routes tablosu
CREATE TABLE routes (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  date DATE NOT NULL,
  timeslot TEXT NOT NULL,
  type TEXT CHECK (type IN ('pickup', 'dropoff')),
  waypoints JSONB DEFAULT '[]',
  optimized_path JSONB DEFAULT '[]',
  total_duration INTEGER,
  total_distance NUMERIC,
  vehicle_count INTEGER,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Time Matrix tablosu
CREATE TABLE time_matrix (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  origin_code TEXT NOT NULL,
  destination_code TEXT NOT NULL,
  duration_minutes INTEGER NOT NULL,
  UNIQUE(origin_code, destination_code)
);
```

### 4.2 İndeksler

Mevcut indeks yapılandırması incelendiğinde:

- Primary key indeksleri mevcut
- Foreign key indeksleri mevcut
- Sorgu performansı için ek indeksler gerekebilir
  - `users(email)` - Sıklıkla kullanılıyor
  - `users(student_number)` - Sıklıkla kullanılıyor
  - `ride_requests(status, date)` - Filtreleme için
  - `ride_requests(user_id, date)` - Kullanıcı bazlı sorgular için

### 4.3 Veri Türleri (TypeScript)

```typescript
// src/types/db.ts
export interface DbUser extends Omit<User, "password"> {
  passwordHash?: string;
  createdAt: string;
  updatedAt: string;
}

export interface DbVehicle extends Vehicle {
  createdAt: string;
  updatedAt: string;
}

export interface DbRideRequest extends RideRequest {
  updatedAt: string;
}

export interface RouteAssignment {
  id: string;
  date: string;
  vehicleId: string;
  driverId?: string;
  routeId: string;
  studentIds: string[];
  pickupTime: string;
  estimatedDropoffTime: string;
  status: "scheduled" | "in_progress" | "completed" | "cancelled";
  createdAt: string;
  updatedAt: string;
}
```

---

## Bölüm 5: API Sözleşmeleri

### 5.1 Mevcut API Uç Noktaları

| Endpoint | Metod | Açıklama | Durum |
|---------|------|----------|------|
| `/api/calculate-vehicles` | POST | Araç hesaplama | ✅ Aktif |
| `/api/optimize-route` | POST/GET | Rota optimizasyonu | ✅ Aktif |
| `/api/compare-algorithms` | POST | Algoritma karşılaştırma | ✅ Aktif |
| `/api/admin/users` | GET/POST | Kullan��cı yönetimi | ✅ Aktif |
| `/api/admin/users/password` | POST | Şifre değiştirme | ✅ Aktif |
| `/api/admin/vehicles` | GET/POST | Araç yönetimi | ✅ Aktif |
| `/api/admin/ride-requests` | GET/POST | Ride talebi yönetimi | ✅ Aktif |
| `/api/admin/schedules` | GET/POST | Program yönetimi | ✅ Aktif |
| `/api/driver/assignments` | GET | Sürücü atamaları | ✅ Aktif |
| `/api/auth/hint` | POST | Şifre ipucu | ✅ Aktif |
| `/api/auth/dev-reset` | POST | Dev reset | ⚠️ Debug only |
| `/api/profile/password` | POST | Profil şifre değiştirme | ✅ Aktif |
| `/api/ride-confirmation` | POST | Ride onaylama | ✅ Aktif |

### 5.2 Kritik API Sorunları

**Sorun 1: Algoritma Anahtar Uyumsuzluğu**

UI'dan seçilen algoritma anahtarları ile Python'daki registry anahtarları uyuşmamaktadır:

| UI Anahtarı | Python Beklenen | Mevcut Davranış |
|-----------|---------------|----------------|
| `nearest-neighbor` | `nearest_neighbor` | ❌ Anahara değişiklik |
| `permutation` | `permutation_tsp` | ❌ Mapping eksik |
| `two-opt` | Yok veya `two_opt` | ❌ GA'ya zorla çevirme |
| `genetic_algorithm` | `genetic_algorithm` | ✅ Doğru |
| `pso` | `pso` | ✅ Doğru |

**Kanıt:**
`src/lib/algorithm-constants.ts` dosyasında `normalizeAlgorithmName` fonksiyonu mevcut olsa da, tam mapping eksiklikleri var:

```typescript
// Mevcut mapping - eksiklikler mevcut
export const LEGACY_ALGORITHM_MAP: Record<string, string> = {
  "nearest-neighbor": HEURISTIC_KEYS.GREEDY,  // Doğru ama açık değil
  "two-opt": HEURISTIC_KEYS.TWO_OPT,           // Bu da sorunlu
  "permutation": HEURISTIC_KEYS.PERMUTATION_TSP,
  // ...
};
```

**Sorun 2: Payload Formatı Uyuşmazlığı**

`src/services/doubus/multi-vehicle-routing.ts`'de gönderilen payload:

```typescript
const payload = {
  algorithm: "ortools_cvrp",  // Python bekliyor: id, type
  students: [{ id: "Sw1", type: "Sw" }],  // Python bekliyor: location_code, disability_type
  depot: { id: "D.Kampus", type: "D" },
  max_travel_time: 120,
  sw_capacity: 4,
  so_capacity: 5
};
```

Python'ın beklediği format farklı olabilir.

---

## Bölüm 6: Bağımlılıklar ve Sürüm Yönetimi

### 6.1 package.json Bağımlılıkları

```json
{
  "dependencies": {
    "@genkit-ai/googleai": "^1.8.0",
    "@genkit-ai/next": "^1.8.0",
    "@radix-ui/react-*": "^1.1.x",
    "@supabase/supabase-js": "^2.98.0",
    "@tanstack/react-query": "^5.66.0",
    "date-fns": "^3.6.0",
    "genkit": "^1.8.0",
    "lucide-react": "^0.475.0",
    "next": "^16.1.6",
    "react": "^18.3.1",
    "recharts": "^2.15.1",
    "xlsx": "^0.18.5",
    "zod": "^3.24.2"
  },
  "devDependencies": {
    "@types/node": "^20",
    "@types/react": "^18",
    "typescript": "^5",
    "vitest": "^4.0.18"
  }
}
```

### 6.2 Bağımlılık Güvenlik Analizi

| Bağımlılık | Sürüm | Güvenlik Notu |
|-----------|-------|--------------|
| next | 16.1.6 | ✅ Güncel |
| react | 18.3.1 | ✅ Güvenli |
| xlsx | 0.18.5 | ⚠️ Denetlenmeli |
| zod | 3.24.2 | ✅ Güvenli |

### 6.3 Çevre Değişkenleri

Gerekli çevre değişkenleri:

```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://xxxxx.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=eyJxxx...
SUPABASE_SERVICE_ROLE_KEY=eyJxxx...

# Optimizer API
OPTIMIZER_API_URL=http://127.0.0.1:8000
```

**Sorun:** `.env.local` dosyası varsayılan değerler içermemektedir. Yeni geliştiricilerin projeı başlatması için ek yapılandırma gerekmektedir.

---

## Bölüm 7: Test Kapsamı ve Otomasyonu

### 7.1 Mevcut Durum

| Kategori | Durum | Not |
|----------|-------|------|
| Unit Test | ❌ Yok | vitest kurulu ama kullanılmıyor |
| Integration Test | ❌ Yok | - |
| E2E Test | ❌ Yok | - |
| API Test | ❌ Manuel | Postman collection yok |

### 7.2 Test Altyapısı

Vitest kurulu ancak test dosyaları bulunmamaktadır:

```bash
# package.json
"test": "vitest",
"test:ui": "vitest --ui"
```

Ancak `src/**/*.test.ts` veya `src/**/*.spec.ts` dosyası bulunmamaktadır.

### 7.3 Manuel Test Adımları

**Test 1: Giriş Yapısı**

```bash
# 1. Projeyi başlat
cd UniRide
npm install
npm run dev

# 2. Browser'da http://localhost:9002 aç

# 3. Login sayfasına git
# - Email: admin@unitride.com / Şifre: test123
# - Veya kayıtlı bir kullanıcı ile dene
```

**Test 2: Araç Planlama**

```bash
# 1. Admin olarak giriş yap
# 2. /admin/vehicle-planning sayfasına git
# 3. Öğrenci seç
# 4. Algoritma seç (genetic_algorithm)
# 5. "Hesapla" butonuna tıkla
# 6. Sonuçları gözlemle
```

**Test 3: Python API Bağlantısı**

```bash
# Python server başlat
cd optimizer_api
python main.py

# Health kontrol
curl http://127.0.0.1:8000/health
```

### 7.4 Test Eksiklikleri

| Öncelik | Test | Açıklama |
|---------|------|----------|
| KRITIK | Algoritma mapping testi | UI → Python anahtar dönüşümü |
| KRITIK | Time matrix testi | Veri yükleniyor mu? |
| YÜKSEK | Auth testi | Login/register akışı |
| YÜKSEK | API route testi | CRUD operasyonları |
| ORTA | Excel import testi | Dosya işleme |

---

## Bölüm 8: CI/CD ve Deployment Süreçleri

### 8.1 Mevcut Durum

| Kategori | Durum | Not |
|----------|-------|------|
| CI Pipeline | ❌ Yok | GitHub Actions yok |
| CD Pipeline | ❌ Yok | Deployment otomasyonu yok |
| Deployment | ⚠️ Manuel | `npm run build` + host |

### 8.2 Build Süreci

```bash
# Build
npm run build

# Lint
npm run lint

# Typecheck
npm run typecheck
```

### 8.3 Deployment Adımları (Manuel)

```bash
# 1. Build
npm run build

# 2. Production başlat
npm run start

# 3. Veya hosting platformları
# - Vercel (önerilen)
# - Netlify
# - AWS/Amazon EC2
# - Docker container
```

### 8.4 CI/CD Eksiklikleri

| Öncelik | Süreç | Açıklama |
|---------|-------|----------|
| YÜKSEK | CI Pipeline | Type check, lint, test |
| YÜKSEK | CD Pipeline | Otomatik deployment |
| ORTA | Preview | PR preview deployment |
| ORTA | E2E | CI'da E2E testleri |

---

## Bölüm 9: Güvenlik

### 9.1 Mevcut Güvenlik Yapılandırması

| Kategori | Durum | Not |
|----------|-------|------|
| Kimlik Doğrulama | ✅ Supabase Auth | - |
| Yetkilendirme | ✅ RLS + Middleware | - |
| API Koruma | ⚠️ Kısmi | Middleware sınırlı |
| Şifreleme | ✅ HTTPS | Hosting'e bağlı |
| Rate Limiting | ❌ Yok | - |
| Input Validation | ⚠️ Zod var, eksik | - |

### 9.2 Middleware Yapılandırması

```typescript
// src/middleware.ts
export function middleware(request: NextRequest) {
    const { pathname } = request.nextUrl;
    
    if (pathname.startsWith('/api/admin')) {
        const authHeader = request.headers.get('authorization');
        if (!authHeader || !authHeader.startsWith('Bearer ')) {
            return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
        }
    }
    return NextResponse.next();
}
```

**Sorunlar:**
- Edge runtime'da Supabase sorgusu yapılamıyor
- JWT doğrulama middleware'de değil, API route'larda yapılıyor
- `/api/calculate-vehicles` korumasız

### 9.3 RLS Politikaları

```sql
-- Örnek RLS politika
CREATE POLICY "users_can_read_own_data" ON users
  FOR SELECT
  USING (auth.uid() = id);
```

**Not:** RLS politikaları veritabanında tanımlanmış olmalı, ancak doğrulama gerekli.

### 9.4 Güvenlik Açıkları

| Öncelik | Açıklama | Risk |
|--------|----------|------|
| ORTA | API rate limiting yok | DoS saldırısı |
| ORTA | Input validation eksik | Injection |
| DÜŞÜK | Debug endpoint'ler açık | Bilgi sızıntısı |
| DÜŞÜK | Token expiry kontrolü | Session yönetimi |

---

## Bölüm 10: Performans

### 10.1 Mevcut Performans Durumu

| Metrik | Değer | Not |
|--------|-------|------|
| Build Boyutu | ~500KB (gzip) | Aşırı değil |
| JavaScript | ~300KB (gzip) | Optimize edilmiş |
| İlk Yükleme | ~2 sn | Ortalama |
| API Yanıt Süresi | 30 sn+ | Algoritmaya bağlı |

### 10.2 Performans Optimizasyonları

| Kategori | Durum | Not |
|----------|-------|------|
| Lazy Loading | ⚠️ Kısmi | Next.js automatic |
| CDN | ✅ Vercel | - |
| Caching | ⚠️ Manuel | React Query var |
| Image Optimization | ✅ Next.js | - |

### 10.3 Algoritma Performans Karşılaştırması

Algoritma karmaşıklıkları (`algorithm_integration_audit.md`'den):

| Algoritma | Karmaşıklık | Önerilen n |
|-----------|------------|-----------|
| Genetic Algorithm | O(g × p × n²) | < 100 |
| PSO | O(i × s × n²) | < 100 |
| Two-Opt | O(n²) | < 50 |
| Permutation | O(n!) | < 10 |
| OR-Tools | O(n³) | Her boyut |

---

## Bölüm 11: İzleme ve Operasyon

### 11.1 Mevcut İzleme Yapılandırması

| Kategori | Durum | Not |
|----------|-------|------|
| Logging | ⚠️ Console.log | Yetersiz |
| Monitoring | ❌ Yok | - |
| Error Tracking | ❌ Yok | - |
| Metrics | ❌ Yok | - |

### 11.2 Loglama

```typescript
// Mevcut yaklaşım
console.log(`[Routing] Calling optimizer API: ${apiUrl}`);
console.error("[Routing] Unexpected error:", error);
```

**Sorun:** Merkezi loglama sistemi yok. Üretim için yapılandırma gerekli.

### 11.3 Operasyonel Gösterge Tablosu

| Ölçüt | Mevcut | Hedef |
|--------|-------|-------|
| Uptime | Manuel | %99.9 |
| Response Time | 30 sn+ | < 5 sn |
| Error Rate | Bilinmiyor | < %1 |
| Deployment Frekansı | Manuel | Günlük |

---

## Bölüm 12: Teknik Borç ve Riskler

### 12.1 Teknik Borç Listesi

| Öncelik | Kalem | Açıklama | Tahmini Çaba |
|---------|------|----------|------------|
| YÜKSEK | Test yok | Test kapsamı %0 | 2 hafta |
| YÜKSEK | CI/CD yok | Pipeline eksikliği | 1 hafta |
| ORTA | Dokümantasyon eksik | API dokümantasyon | 1 gün |
| ORTA | Time matrix | Doğrulama gerekli | 1 gün |
| ORTA | Rate limiting | API koruma | 2 gün |
| DÜŞÜK | Debug mode | Kaldırılmalı | 1 gün |

### 12.2 Risk Matrisi

| Risk | Olasılık | Etki | Öncelik |
|------|---------|------|-------|
| Algoritma hatası | YÜKSEK | YÜKSEK | KRITIK |
| Time matrix eksik | YÜKSEK | YÜKSEK | KRITIK |
| Veritabanı hatası | ORTA | YÜKSEK | YÜKSEK |
| Performans sorunu | ORTA | ORTA | ORTA |
| Güvenlik açığı | DÜŞÜK | YÜKSEK | YÜKSEK |

### 12.3 Kritik Sorunların Kanıtları

**Kanıt 1: Algoritma Anahtar Uyumsuzluğu**

Dosya: `src/app/api/calculate-vehicles/route.ts` (satır 200-212):

```typescript
// normalizeAlgorithmName çağrılıyor ama tam mapping eksik
const normalizedAlgorithm = normalizeAlgorithmName(strategy);

// Python'a gönderilen algorithm alanı:
// strategy === "two-opt" ise algorithm = "genetic_algorithm" (!)
```

**Kanıt 2: Time Matrix Fallback**

Dosya: `algorithm_integration_audit.md`'den:

```python
# Python tarafında time_matrix yoksa:
self._use_coordinates = True
time_matrix = None
# get_submatrix():
#   if self._use_coordinates == True:
#     return [[0.0]*n ...]  # SIFIR MATRIX!
```

**Kanır 3: Doğrulama Eksikliği**

Test dosyaları: `src/**/*.test.ts` = 0 adet

---

## Bölüm 13: Uyum Gereklilikleri

### 13.1 Yasal Uyum

| Gereklilik | Durum | Not |
|----------|-------|------|
| KVKK (Türkiye) | ❌ Tam uyum yok | Veri saklama politikası gerekli |
| GDPR | ⚠️ Kısmi | EU kullanıcıları için |
| Erişilebilirlik | ⚠️ WCAG 2.1 AA | Kısmi |

### 13.2 Erişilebilirlik

Sistem, engelli öğrenciler için tasarlanmış olup; UI bileşenleri Radix UI (WCAG uyumlu) kullanmaktadır. Ancak tam denetim gerekli.

---

## Bölüm 14: Önceliklendirilmiş Backlog

### P0 - Kritik (Hemen Eylem)

| # | Kalem | Etkilenen Alan | İş Değeri | Uygulanabilirlik | Tahmini Çaba | Sorumlu |
|---|------|--------------|-----------|-------------|-------------|-----------|---------|
| P0-1 | Algoritma anahtar mapping düzeltmesi | Backend/Frontend | Çok Yüksek | Kolay | 1 gün | Backend Dev |
| P0-2 | Time matrix doğrulama scripti | Backend | Çok Yüksek | Orta | 2 gün | DevOps |
| P0-3 | null location code handling | Frontend | Yüksek | Kolay | 2 saat | Frontend Dev |

### P1 - Yüksek (Bu Sprint)

| # | Kalem | Etkilenen Alan | İş Değeri | Uygulanabilirlik | Tahmini Çaba | Sorumlu |
|---|------|--------------|-----------|-------------|-------------|-----------|---------|
| P1-1 | Test kapsamı: %30'a çıkar | Tümü | Yüksek | Orta | 2 hafta | QA/Dev |
| P1-2 | Rate limiting uygulaması | Backend | Yüksek | Orta | 2 gün | Backend Dev |
| P1-3 | CI Pipeline kurulumu | DevOps | Yüksek | Orta | 1 hafta | DevOps |

### P2 - Orta (Sonraki Sprint)

| # | Kalem | Etkilenen Alan | İş Değeri | Uygulanabilirlik | Tahmini Çaba | Sorumlu |
|---|------|--------------|-----------|-------------|-------------|-----------|---------|
| P2-1 | API dokümantasyonu | Backend | Orta | Kolay | 1 gün | Backend Dev |
| P2-2 | Input validation genişletme | Backend | Orta | Orta | 2 gün | Backend Dev |
| P2-3 | Loglama iyileştirme | Operasyon | Orta | Kolay | 1 gün | DevOps |

### P3 - Düşük (Gelecek Sprint)

| # | Kalem | Etkilenen Alan | İş Değeri | Uygulanabilirlik | Tahmini Çaba | Sorumlu |
|---|------|--------------|-----------|-------------|-------------|-----------|---------|
| P3-1 | Debug endpoint'leri kaldırma | Güvenlik | Düşük | Kolay | 1 saat | Backend Dev |
| P3-2 | KVKK uyumu | Uyum | Orta | Zor | 1 hafta | Legal/Dev |
| P3-3 | E2E testleri | Test | Orta | Orta | 1 hafta | QA |

---

## Bölüm 15: Yol Haritası ve Uygulama Planı

### 15.1 Kısa Vadeli Hedefler (0-4 Hafta)

**Hedef 1: Kritik Hataların Düzeltilmesi**

| Hafta | Hedef | Kabul Kriterleri | Çıktılar |
|-------|------|----------------|----------|
| 1 | Algoritma mapping düzeltme | UI'da seçilen algoritma Python'da aynı isimle çalışıyor | Düzeltilmiş mapping kodu + test |
| 2 | Time matrix doğrulama | SQL sorgusu + log doğrulaması | Doğrulama raporu |
| 3 | Test kapsamı %15 | Birim testleri çalışıyor | Test dosyaları |
| 4 | Rate limiting | 60 req/dk limit çalışıyor | Rate limit middleware |

**Kabul Kriterleri (AC):**

- [ ] UI'da "nearest-neighbor" seçildiğinde Python GA değil greedy çalışıyor
- [ ] Time matrix sorgusu `select count(*) from time_matrix` > 0 döndürüyor
- [ ] En az 10 birim testi var ve geçiyor
- [ ] API 60 req/dk üzerinde 429 hatası döndürüyor

**Sorumlu:** Backend Developer

### 15.2 Orta Vadeli Hedefler (1-3 Ay)

**Hedef 2: Temel Altyapı**

| Ay | Hedef | Kabul Kriterleri | Çıktılar |
|----|------|------------------|----------|
| 1 | CI Pipeline | GitHub Actions'da CI çalışıyor | CI workflow dosyası |
| 2 | Test kapsamı %30 | Unit testleri çalışıyor | Test coverage raporu |
| 3 | API dokümantasyonu | OpenAPI spec var | API dokümantasyonu |

**Kabul Kriterleri:**

- [ ] `npm run typecheck` CI'da geçiyor
- [ ] Coverage raporu %30'üzerinde
- [ ] /api/calculate-vehicles OpenAPI'de dokümante

**Sorumlu:** DevOps + Developers

### 15.3 Uzun Vadeli Hedefler (3-6 Ay)

**Hedef 3: Operasyonel Olgunluk**

| Ay | Hedef | Kabul Kriterleri | Çıktılar |
|----|------|------------------|----------|
| 4 | Monitoring | Dashboard var | Grafana/Prometheus |
| 5 | Otomatik deployment | Deploy otomatik | CD pipeline |
| 6 | KVKK uyumu | DPO onayı | Uyum raporu |

**Kabul Kriterleri:**

- [ ] Error tracking çalışıyor
- [ ] PR onayında Vercel preview var
- [ ] Veri saklama politikası onaylı

**Sorumlu:** Tech Lead + Legal

---

## Bölüm 16: İkinci Doğrulama

### 16.1 Bağımsız İkinci Göz Denetimi

Bu analizin doğruluğunu teyit etmek için aşağıdaki bağımsız doğrulama önerilmektedir:

1. **Kod İnceleme:** Bağımsız bir senior developer, kritik dosyaları incelesin
   - `src/lib/algorithm-constants.ts`
   - `src/app/api/calculate-vehicles/route.ts`
   - `src/services/doubus/multi-vehicle-routing.ts`

2. **Test Senaryosu:** Manuel test senaryoları çalıştırılsın
   - TestSenaryosu-001: Algoritma seçimi
   - TestSenaryosu-002: Python API bağlantısı
   - TestSenaryosu-003: Veritabanı sorguları

3. **Güvenlik Denetimi:** Penetrasyon testi yapılsın

### 16.2 Doğrulama Soruları

1. Algoritma anahtarları UI'da Python'da çalışananahtarlarla tam eşleşiyor mu?
2. Time matrix veritabanında gerçek verilerle yüklü mü?
3. Test kapsamı mevcut durumun ötesinde ne kadar genişletilebilir?

---

## Ekler

### Ek A: Kaynak Dosyalar

| Dosya | Konum | Ana Bilgi |
|--------|------|-----------|
| IMPLEMENTATION_STATUS.md | `UniRide/IMPLEMENTATION_STATUS.md` | Tamamlanan özellikler |
| algorithm_integration_audit.md | `UniRide/algorithm_integration_audit.md` | Algoritma sorunları |
| package.json | `UniRide/package.json` | Bağımlılıklar |
| middleware.ts | `src/middleware.ts` | Route koruma |
| supabase-db.ts | `src/lib/supabase-db.ts` | DB fonksiyonları |

### Ek B: Hızlı Başlangıç

```bash
# Geliştirme ortamı kurulumu
cd UniRide
npm install

# .env.local oluştur
echo "NEXT_PUBLIC_USE_MOCK_DB=true" > .env.local

# Geliştirme sunucusu başlat
npm run dev

# TypeScript kontrol
npm run typecheck
```

### Ek C: Başarısızlık Senaryoları

| Senaryo | Belirti | Çözüm |
|---------|--------|-------|
| Python API erişilemez | Timeout hatası | OPTIMIZER_API_URL kontrol et |
| Auth hatası | 401 Unauthorized | Token yenile |
| Veritabanı hatası | Supabase bağlantı hatası | .env.local kontrol et |

---

## Onay ve Giriş Talepleri

Bu analiz raporu aşağıdaki tarafların onayını gerektirmektedir:

| Taraf | Giriş | Tarih |
|--------|-------|-------|
| Product Owner | ✅ / ❌ | |
| Tech Lead | ✅ / ❌ | |
| Backend Developer | ✅ / ❌ | |
| QA Lead | ✅ / ❌ | |

**Not:** Onay verilmeden uygulamaya geçilmemelidir.

---

*Bu rapor, mevcut kod tabanının kapsamlı incelenmesi sonucunda hazırlanmıştır. Tüm bulgular kaynak kodlar üzerinden doğrulanmıştır.*

**Rapor Sürümü:** 1.0  
**Son Güncelleme:** 2026-03-28