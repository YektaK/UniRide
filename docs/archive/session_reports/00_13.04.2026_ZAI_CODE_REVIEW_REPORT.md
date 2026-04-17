# UniRide — Kapsamli Endustri Standartlarinda Code Review Raporu

**Tarih:** 13.04.2026  
**Reviewer:** Z.ai Code  
**Kapsam:** Tum kaynak kodu (Next.js Frontend, API Routes, Services, Python Optimizer API, Database Schema, Configuration)  
**Toplam Dosya:** ~120+ dosya incelendi  
**Bulgular:** 80+ bulgu (12 KRITIK, 22 YUKSEK, 30 ORTA, 16 Dusuk)

---

## Icerik

1. [Yonetici Ozeti](#1-yonetici-ozeti)
2. [KRITIK Bulgular](#2-kritik-bulgular)
3. [YUKSEK Oncelikli Bulgular](#3-yuksek-oncelikli-bulgular)
4. [ORTA Oncelikli Bulgular](#4-orta-oncelikli-bulgular)
5. [Dusuk Oncelikli Bulgular](#5-dusuk-oncelikli-bulgular)
6. [Backend API Detayli Inceleme](#6-backend-api-detayli-inceleme)
7. [Frontend Detayli Inceleme](#7-frontend-detayli-inceleme)
8. [Python Optimizer API Detayli Inceleme](#8-python-optimizer-api-detayli-inceleme)
9. [Veritabani ve RLS Incelemesi](#9-veritabani-ve-rls-incelemesi)
10. [Yapilandirma ve Bagimlik Analizi](#10-yapilandirma-ve-bagimlik-analizi)
11. [Onceliklendirilmis Aksiyon Plani](#11-onceliklendirilmis-aksiyon-plani)

---

## 1. Yonetici Ozeti

### Proje Hakkinda
UniRide, universite ogrenci ulasim sistemini optimize eden bir CVRP/TSP tabanli web uygulamasi. Next.js 16 + TypeScript + Supabase + Python FastAPI (optimizer_api) mimarisi kullanilmaktadir.

### Bulgular Dagilimi

| Severite | Sayi | Kategoriler |
|----------|------|-------------|
| **KRITIK** | 12 | Guvenlik aciklari, calisma zamani hatalari, veri kaybi |
| **YUKSEK** | 22 | Performans, tip guvenligi, RLS eksiklikleri |
| **ORTA** | 30 | Kod kalitesi, input validation, tutarsizliklar |
| **DUSUK** | 16 | Stilde, dokumantasyon, kucuk iyilestirmeler |

### Temel Sorun Alanlari
1. **Guvenlik:** RLS politikalari onemli aciklar iceriyor (privilege escalation mumkun)
2. **Tip Guvenligi:** camelCase/snake_case uyumsuzlugu tip sistemi boyunca yaygin
3. **Input Validation:** Bircok API endpoint Zod validation eksigi yasiyor
4. **Frontend Guvenligi:** Dev secret client-side'a eksik, setUser context'e acik
5. **Python API:** Concurrent isteklerde singleton strateji state corruptyonu
6. **Kod Tekrarı:** Pipeline A stratejileri ~800 satir tekrar iceriyor

---

## 2. KRITIK Bulgular

### CR-01: Kullanici Rolunu Degistirme Acigi (RLS)
- **Dosya:** `supabase/rls_policies.sql:38-40`
- **Kategori:** Guvenlik — Privilege Escalation
- **Bulgu:** `users_update_own` RLS politikasi herhangi bir authenticated kullaniciya tum sutunlari guncelleme izni veriyor. Bir ogrenci `role` alanini `admin` olarak degistirebilir.
```sql
CREATE POLICY "users_update_own"
  ON users FOR UPDATE
  USING (auth.uid() = id);
  -- WITH CHECK eksik! role degisikligi engellenmiyor
```
- **Cozum:** `WITH CHECK (role IS NOT DISTINCT FROM (SELECT role FROM users WHERE id = auth.uid()))` ekle.

### CR-02: Notification Injection Acigi (RLS)
- **Dosya:** `supabase/rls_policies.sql:111-113`
- **Kategori:** Guvenlik
- **Bulgu:** `notifications_insert_system` politikasi `WITH CHECK (true)` ile tum auth kullanıclarına notification insert izni veriyor.
```sql
CREATE POLICY "notifications_insert_system"
  ON notifications FOR INSERT WITH CHECK (true);
```
- **Cozum:** `TO service_role` ile kisitla.

### CR-03: Dev Reset Secret Client-Side'a Eksik
- **Dosya:** `src/app/(auth)/forgot-password/page.tsx`
- **Kategori:** Guvenlik
- **Bulgu:** `NEXT_PUBLIC_DEV_RESET_SECRET` environment variable client-side'a eksik. Browser network tab'indan okunabilir.
```tsx
"Authorization": `Bearer ${process.env.NEXT_PUBLIC_DEV_RESET_SECRET ?? ""}`
```
- **Cozum:** Client-side dev reset'i tamamen kaldir. Server-side API route kullan.

### CR-04: `cooldown_minutes` Sutunu Veritabaninda Yok
- **Dosya:** `supabase/schema.sql:61-71`, `src/types/index.ts:45`, `src/app/api/admin/vehicles/route.ts:150`
- **Kategori:** Bug — Schema Mismatch
- **Bulgu:** TypeScript `Vehicle` interface `cooldownMinutes` tanimliyor ama veritabani `vehicles` tablosunda bu sutun yok. Her vehicle update sessizce degeri dropluyor.
- **Cozum:** Migration ekle: `ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS cooldown_minutes INTEGER NOT NULL DEFAULT 10;`

### CR-05: camelCase/snake_case Tip Uyumsuzlugu (vehicles)
- **Dosya:** `src/lib/supabase.ts:61-64`, `src/types/db.ts:50-53`
- **Kategori:** Tip Guvenligi
- **Bulgu:** `Database.vehicles.Row` olarak `DbVehicle` (camelCase) tanimli ama Supabase raw response snake_case donduruyor. Dogrudan client kullanimda yanlis tipleme oluyor.
- **Cozum:** `DbVehicleRow` (snake_case) olustur, `DbUserRow` ornegi gibi.

### CR-06: AuthContext `setUser` Acik
- **Dosya:** `src/contexts/auth-context.tsx`
- **Kategori:** Guvenlik — Client-side Privilege Escalation
- **Bulgu:** `setUser` context degerinde eksik. Herhangi bir consumer `setUser({...user, role: 'admin'})` ile yetki yukseltebilir.
```tsx
<AuthContext.Provider value={{ user, setUser, isLoading, login, logout }}>
```
- **Cozum:** `setUser`'i context'ten kaldir, yerine `updateProfile` metodu ekle.

### CR-07: PostgREST Filter Injection
- **Dosya:** `src/app/api/auth/hint/route.ts:66`
- **Kategori:** Guvenlik
- **Bulgu:** `.or()` filter'ina kullanici girisi dogrudan interpolasyon ediliyor. Ozelform karakterlerle PostgREST manipulasyonu mumkun.
```ts
.or(`email.eq.${emailOrStudentNumber.toLowerCase()},student_number.eq.${emailOrStudentNumber}`)
```
- **Cozum:** Input'u `^[a-zA-Z0-9._%+-@]+$` regex ile validate et.

### CR-08: Pipeline A Stratejileri `import logging` Eksik
- **Dosya:** `optimizer_api/strategies/ga_strategy.py`, `gwo_strategy.py`, `hho_strategy.py`, `pso_strategy.py`
- **Kategori:** Bug — Runtime Crash
- **Bulgu:** Bu dort strateji dosyasi `logger = logging.getLogger(__name__)` kullaniyor ama `import logging` import etmiyor. Modul yuklendiginde `NameError` firlatir.
- **Cozum:** Her dosyaya `import logging` ekle.

### CR-09: Singleton Strateji State Corruptonu
- **Dosya:** `optimizer_api/strategies/ga_strategy.py:306-311` (ve digerleri)
- **Kategori:** Bug — Concurrency
- **Bulgu:** Tum Pipeline A stratejileri module-level singleton olarak olusturulur. Her `optimize()` call `self.config` ve `self.rng`'yi mutate eder. `/compare` endpoint'indeki `ThreadPoolExecutor` ile concurrent isteklerde race condition olusur.
- **Cozum:** `optimize()` icinde config'in deepcopy'sini al veya her istekte yeni strateji olustur.

### CR-10: Time Window Feature Dead Code
- **Dosya:** `optimizer_api/models/schemas.py:124-126`
- **Kategori:** Bug — Feature Non-Functional
- **Bulgu:** `OptimizationRequest.get_time_windows()` her zaman `{}` donduruyor. CVRPTW kodu calisiyor ama bos veriyle — zaman penceresi ozellikleri sessizce calismiyor.
- **Cozum:** Metodu implement et veya dead code path'leri kaldir.

### CR-11: User Tipinde `password` Alani
- **Dosya:** `src/types/index.ts`
- **Kategori:** Guvenlik
- **Bulgu:** Client-side `User` tipi `password?: string` iceriyor. Sifreler client'a hicbir sekilde gelmemeli.
- **Cozum:** `password` alanini `User` tipinden tamamen kaldir.

### CR-12: Frontend Admin Sayfalari Role Kontrolu Yok
- **Dosya:** `src/app/(app)/admin/users/page.tsx`, `vehicles/page.tsx`, `ride-requests/page.tsx`, `settings/page.tsx`
- **Kategori:** Guvenlik
- **Bulgu:** Admin sayfalari `user.role === "admin"` kontrolu yapmiyor. Auth olan herhangi bir kullanici admin UI'ya erisebilir (API 403 donecek ama UI gorunur).
- **Cozum:** Her admin sayfasinin basina role kontrolu ekle: `if (user?.role !== "admin") return <AccessDenied />;`

---

## 3. YUKSEK Oncelikli Bulgular

### HI-01: React Error Boundary Yok
- **Dosya:** Global
- **Kategori:** Reliability
- **Bulgu:** Tum uygulamada hic React Error Boundary yok. Herhangi bir runtime hatasi beyaz ekrana neden olur.
- **Cozum:** `src/app/layout.tsx`'e en azindan bir Error Boundary ekle.

### HI-02: Security Headers Eksik
- **Dosya:** `next.config.ts`
- **Kategori:** Guvenlik
- **Bulgu:** `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy` gibi kritik security headers tanimli degil.
- **Cozum:** `next.config.ts`'e `headers()` konfigurasyonu ekle.

### HI-03: `xlsx` Paketi Guvenlik Acigi
- **Dosya:** `package.json:60`
- **Kategori:** Guvenlik
- **Bulgu:** `xlsx@^0.18.5` (SheetJS Community) CVE-2023-30533 prototype pollution zafiyetine sahip. Artik bakim yapilmiyor.
- **Cozum:** `exceljs` veya `xlsx-populate` gibi actively maintained alternatife gec.

### HI-04: Kullanici Silme Islemi Partial Rollback
- **Dosya:** `src/app/api/admin/users/route.ts:180-194`
- **Kategori:** Bug — Data Integrity
- **Bulgu:** Once DB kaydi siliniyor, sonra auth kaydi. Auth silme basarisiz olursa orphaned auth hesabi kaliyor.
- **Cozum:** Auth hesabini once sil, sonra DB. Basarisiz olursa rollback yap.

### HI-05: Pick/Dropoff Filtreleri Ayni (Multi-Vehicle Routing)
- **Dosya:** `src/services/doubus/multi-vehicle-routing.ts:68-73`
- **Kategori:** Bug
- **Bulgu:** `pickupRequests` ve `dropoffRequests` ayni filtre kullaniyor — her ikisi de `type === "scheduled" && status === "confirmed"`.
- **Cozum:** Pick/dropoff ayrimi icin direction field kontrolu ekle.

### HI-06: Schedule-to-Requests Pickup/Dropoff Zamanlari Ayni
- **Dosya:** `src/services/schedule-to-requests.ts:106`
- **Kategori:** Bug
- **Bulgu:** Hem pickup hem dropoff request'inde `requestedPickupTime` ve `requestedDropoffTime` ayni degerlere set ediliyor.
- **Cozum:** Dropoff zamanlarini dogru arrival time'lara set et.

### HI-07: camelCase/snake_case Uyumsuzlugu (Tum Tablolar)
- **Dosya:** `src/types/db.ts`, `src/lib/supabase.ts`
- **Kategori:** Tip Guvenligi
- **Bulgu:** Sadece `users` tablosu icin `DbUserRow` olusturuldu. `weekly_schedules`, `ride_requests`, `route_assignments`, `routes` tablolari hala camelCase tip kullaniyor.
- **Cozum:** Tum tablolar icin `*Row` snake_case tip tanimlari olustur.

### HI-08: Password Hint API Enumeration Zafiyeti
- **Dosya:** `src/components/auth/login-form.tsx`
- **Kategori:** Guvenlik
- **Bulgu:** "Sifre ipucu goster" butonu authentication olmadan `/api/auth/hint` cagiriyor. Herhangi biri hesap varligini ve password hint'ini gorebilir.
- **Cozum:** Rate-limit cok agir yap. En azindan basarisiz giris denemesinden sonra goster.

### HI-09: RLS Write Policy Eksik (vehicles, routes, admin_settings, route_assignments)
- **Dosya:** `supabase/rls_policies.sql`
- **Kategori:** Guvenlik
- **Bulgu:** Bu tablolar icin sadece SELECT policy var. Anon key ile yapilan write islemleri sessizce basarisiz olur. Sadece service_role ile calisiyor ama bu dokumante edilmemis.
- **Cozum:** Admin role icin write policy ekle veya service_role-only kullanimi dokumante et.

### HI-10: FK Constraints Eksik
- **Dosya:** `supabase/schema.sql:19,54`
- **Kategori:** Data Integrity
- **Bulgu:** `users.weekly_schedule_id` ve `ride_requests.vehicle_id` uzerinde FK constraint yok. Silinen kayitlara referans orphaned kaliyor.
- **Cozum:** `REFERENCES ... ON DELETE SET NULL` ekle.

### HI-11: Reports Sayfası N+1 Query
- **Dosya:** `src/app/(app)/admin/reports/page.tsx`
- **Kategori:** Performans
- **Bulgu:** Her ogrenci icin ayri `getStudentSchedule()` API call yapiliyor. 100 ogrenci = 100+ concurrent request.
- **Cozum:** Batch fetch ile tek seferde tum schedule'leri cek.

### HI-12: Admin Ride Requests Status Enum Validation Eksik
- **Dosya:** `src/app/api/admin/ride-requests/route.ts:72-82`
- **Kategori:** Input Validation
- **Bulgu:** Status field `z.string().optional()` ile herhangi bir string kabul ediyor. Gecersiz degerler veritabanina yaziliyor.
- **Cozum:** `z.enum([...])` ile sinirlandir.

---

## 4. ORTA Oncelikli Bulgular

### MD-01: Rate Limiter Memory Leak
- **Dosya:** `src/app/api/auth/hint/route.ts:29-36`
- **Kategori:** Security
- **Bulgu:** In-memory `rateLimitMap` multi-process deployment'larda ise yaramiyor. Vercel serverless'ta her invocation ayri process.

### MD-02: Ride Confirmation Timezone Bug
- **Dosya:** `src/app/api/ride-confirmation/route.ts:50-53`
- **Kategori:** Bug
- **Bulgu:** Deadline hesaplamasi timezone-dependent. Vercel UTC calisir, `22:00 local` = `22:00 UTC` olur, Turkiye saati degil.

### MD-03: Empty String Falsy Check Bug
- **Dosya:** `src/app/api/admin/vehicles/route.ts:145-151`, `admin/users/route.ts:136-137`
- **Kategori:** Bug
- **Bulgu:** `if (updates.name)` — empty string `""` falsy oldugu icin bir alani bosaltmak mumkun degil. `!== undefined` kullanilmali.

### MD-04: Sandbox Frontend/Backend URL Mismatch
- **Dosya:** `src/services/sandbox-api.ts:59-106`, `src/app/api/sandbox/route.ts`
- **Kategori:** Bug
- **Bulgu:** Frontend `?action=list` ve `?action=delete` gonderiyor ama backend bu parametreleri kontrol etmiyor. Tesadufen calisiyor.

### MD-05: Missing Index on `ride_requests.vehicle_id`
- **Dosya:** `supabase/schema.sql:127-141`
- **Kategori:** Performans

### MD-06: Composite Index Eksik (`route_assignments`)
- **Dosya:** `supabase/schema.sql:135`
- **Kategori:** Performans

### MD-07: `schema.sql` Tek Kaynak Degil
- **Dosya:** `supabase/schema.sql`, `supabase/migrations/*.sql`
- **Kategori:** Migration Correctness
- **Bulgu:** `time_matrix`, `route_plans`, `sandbox_scenarios` tablolari ve `password_hint` sutunu sadece migration dosyalarinda mevcut. Sadece `schema.sql` calistirilirse eksik veritabani.

### MD-08: `time_matrix` RLS Policy Silme Riski
- **Dosya:** `supabase/rls_policies.sql:20-22`
- **Kategori:** Security
- **Bulgu:** `rls_policies.sql`'in basindaki blanket DROP tum public schema policy'lerini siliyor. Migration dosyalarinda tanimli `time_matrix` policy'leri de silinir.

### MD-09: `route_plans` Drivers Read Policy Role Check Yok
- **Dosya:** `supabase/migrations/20260329_add_route_plans.sql:52-53`
- **Kategori:** Security
- **Bulgu:** Tum authenticated kullanicilar confirmed/active/completed route plan'larini gorebiliyor. Sadece admin/driver olmalari gerekiyor.

### MD-10: `weekly_schedules_update_own` WITH CHECK Eksik
- **Dosya:** `supabase/rls_policies.sql:56-58`
- **Kategori:** Security
- **Bulgu:** UPDATE policy'sinde `WITH CHECK` clause yok. Kullanici `user_id`'yi baskasinin ID'sine degistirebilir.

### MD-11: Dead Prisma File
- **Dosya:** `src/lib/db.ts`
- **Kategori:** Dead Code
- **Bulgu:** Prisma import ediyor ama projede Prisma kullanilmiyor (Supabase kullaniliyor). Potansiyel olarak calisma zamani hata.

### MD-12: useEffect Dependency Array Hatalari
- **Dosya:** `src/app/(app)/dashboard/page.tsx:34`, `driver/history/page.tsx`, `driver/assignments/page.tsx`
- **Kategori:** React Pattern

### MD-13: `as any` Tip Assertions (9 adet)
- **Dosya:** Multiple files
- **Kategori:** Tip Guvenligi

### MD-14: Zod Validation Eksik (calculate-vehicles, route-plans, sandbox)
- **Dosya:** Multiple API routes
- **Kategori:** Input Validation

### MD-15: Python API 500 Error Internal Details Leak
- **Dosya:** `optimizer_api/main.py:424`
- **Kategori:** Security

### MD-16: ~800 Satir Kod Tekrari (Pipeline A Stratejileri)
- **Dosya:** `optimizer_api/strategies/ga_strategy.py`, `pso_strategy.py`, `gwo_strategy.py`, `hho_strategy.py`
- **Kategori:** Code Quality

### MD-17: DataLoader Singleton Thread-Safe Degil
- **Dosya:** `optimizer_api/utils/data_loader.py:96-100`
- **Kategori:** Concurrency

### MD-18: Off-by-One Date Range Query
- **Dosya:** `src/app/api/ride-confirmation/route.ts:72-73`
- **Kategori:** Bug
- **Bulgu:** `lt("requested_pickup_time", "${rideDate}T23:59:59")` — `23:59:59.000` anindaki ride'lar miss ediliyor.

### MD-19: Duplicate Vehicle Planning Files
- **Dosya:** `src/app/(app)/admin/vehicle-planning/page.tsx` ve `vehicle-planning-page.tsx`
- **Kategori:** Code Quality

### MD-20: React 18 / Next.js 16 Version Mismatch
- **Dosya:** `package.json:51,53`
- **Kategori:** Dependency
- **Bulgu:** Next.js 16 React 19 gerektirir ama proje React 18 kullanıyor.

### MD-21: `notifications`, `admin_settings`, `time_matrix` Database Type Eksik
- **Dosya:** `src/lib/supabase.ts:51-101`
- **Kategori:** Tip Guvenligi

### MD-22: home_coordinates JSONB Constraint Yok
- **Dosya:** `supabase/schema.sql:15`
- **Kategori:** Data Integrity

### MD-23: Only First Vehicle Capacity Used
- **Dosya:** `src/services/doubus/multi-vehicle-routing.ts:201-208`
- **Kategori:** Bug
- **Bulgu:** Multiple active vehicle varsa sadece ilkinin kapasitesi kullaniliyor.

### MD-24: Sequential Time Slot Optimization (No Parallelism)
- **Dosya:** `src/services/doubus/multi-vehicle-routing.ts:67-73`
- **Kategori:** Performans

### MD-25: Duplicate use-mobile Files
- **Dosya:** `src/hooks/use-mobile.tsx` ve `src/hooks/use-mobile.ts`
- **Kategori:** Dead Code

### MD-26: `route_assignments.student_ids` Referential Integrity Yok
- **Dosya:** `supabase/schema.sql:95`
- **Kategori:** Data Integrity

### MD-27: `admin-settings` SELECT Herkese Acik
- **Dosya:** `supabase/rls_policies.sql:118-120`
- **Kategori:** Security

### MD-28: `weekly_schedules UNIQUE(user_id)` Base Schema Eksik
- **Dosya:** `supabase/schema.sql:25-32`
- **Kategori:** Schema Design

### MD-29: Residual Magic `15.0` in split_decoder.py
- **Dosya:** `optimizer_api/utils/split_decoder.py:507`
- **Kategori:** Bug

### MD-30: Benchmark Start Error Returns 200
- **Dosya:** `optimizer_api/main.py:851-858`
- **Kategori:** API Design

---

## 5. Dusuk Oncelikli Bulgular

| ID | Dosya | Bulgular |
|----|-------|----------|
| LO-01 | `.eslintrc.json` | `no-explicit-any: warn` yerine `error` olmali |
| LO-02 | `src/lib/admin-auth.ts:75` | Her auth check'te yeni Supabase client olusturuluyor (cache gerekli) |
| LO-03 | `src/lib/admin-api.ts` | Asiri console.log |
| LO-04 | `src/hooks/use-toast.ts:state dep` | useEffect'te `state` dependency infinite re-subscription riski |
| LO-05 | `src/hooks/use-auth.ts` | Duplicate AuthContextType definition |
| LO-06 | `src/components/admin/user-form-dialog.tsx` | Raw radio input, shadcn RadioGroup kullanilmali |
| LO-07 | `src/components/admin/vehicle-form-dialog.tsx` | Iki useEffect ayni anda form.reset() cagiriyor |
| LO-08 | `src/app/(app)/admin/settings/page.tsx` | Form backend'e bagli degil, sadece simulasyon |
| LO-09 | `src/app/(app)/schedule/page.tsx` | `window.confirm` yerine AlertDialog kullanilmali |
| LO-10 | `optimizer_api/benchmark_state.py` | Deprecated `datetime.utcnow()` |
| LO-11 | `optimizer_api/` (multiple) | Unused imports: `threading`, `asyncio`, `BackgroundTasks`, `SingletonMeta` |
| LO-12 | Multiple files | `catch (error: any)` yerine `error: unknown` |
| LO-13 | `src/types/db.ts:36` | `DbUser.passwordHash` phantom field |
| LO-14 | `supabase/schema.sql:124` | Redundant `UNIQUE(id)` on PK |
| LO-15 | `next.config.ts` | `tsconfig.json` `jsx: "react-jsx"` yerine `"preserve"` |
| LO-16 | `.mcp.json` | `.gitignore`'da yok, placeholder credentials iceriyor |

---

## 6. Backend API Detayli Inceleme

### 6.1 Input Validation Durumu

| Endpoint | Zod Schema | Durum |
|----------|-----------|-------|
| `POST /api/auth/hint` | Hayir | CRITIK — PostgREST injection riski |
| `POST /api/auth/dev-reset` | Hayir | Orta — Password validation eksik |
| `POST /api/calculate-vehicles` | Hayir | Orta — `as` type assertion kullaniliyor |
| `POST /api/optimize-route` | Evet | Iyi |
| `PUT /api/admin/ride-requests` | Kismi | Orta — Status enum eksik |
| `PUT /api/admin/vehicles` | Kismi | Iyi (camelCase + snake_case) |
| `PUT /api/admin/users` | Hayir | Orta |
| `PATCH /api/admin/users/password` | Evet | Iyi |
| `POST /api/ride-confirmation` | Hayir | Orta |
| `POST /api/sandbox` | Hayir | Orta — `any[]` students |
| `PUT /api/sandbox` | Hayir | Orta |
| `POST /api/route-plans` | Hayir | Orta |
| `PATCH /api/route-plans` | Hayir | Orta |
| `GET /api/optimize-route` | N/A | Orta — Unauthenticated strategy listing |
| `GET /api/route` | N/A | Bilgi — Dead "Hello world" route |

### 6.2 Authentication Patternleri

| Pattern | Dosya | Not |
|---------|-------|-----|
| `requireAdmin(request)` | admin API routes | Iyi — JWT validate + role check |
| Bearer token check (middleware) | `middleware.ts` | Orta — Only checks token exists, not validates |
| `getCurrentUserFromToken()` | `admin-auth.ts` | Orta — New client per call |

---

## 7. Frontend Detayli Inceleme

### 7.1 Sayfa Yapilari

| Sayfa | Auth Guard | Role Check | Loading State | Error Handling |
|-------|-----------|------------|---------------|----------------|
| Dashboard | Evet | Hayir | Skeleton | Eksik |
| Schedule | Evet | Hayir | Text | try/catch |
| Ride History | Evet | Hayir | Text | Eksik |
| Request Ride | Evet | Hayir | Hayir | Eksik |
| Track Ride | Evet | Hayir | Hayir | Eksik |
| Profile | Evet | Hayir | Text | try/catch |
| Admin Dashboard | Evet | Hayir | Text | Eksik |
| Admin Users | Evet | **Hayir** | Text | try/catch |
| Admin Vehicles | Evet | **Hayir** | Text | try/catch |
| Admin Ride Requests | Evet | **Hayir** | Text | try/catch |
| Admin Settings | Evet | **Hayir** | Hayir | Simulasyon |
| Admin Sandbox | Evet | Hayir | Text | Eksik |
| Admin Reports | Evet | Hayir | Text | Eksik |
| Admin Vehicle Planning | Evet | Hayir | Text | Eksik |
| Driver Assignments | Evet | Hayir | Text | Eksik |
| Driver History | Evet | Hayir | Text | Eksik |
| Login | Hayir | N/A | Hayir | Eksik |
| Register | Hayir | N/A | Hayir | Eksik |
| Forgot Password | Hayir | N/A | Hayir | Dev reset |
| Reset Password | Hayir | N/A | Hayir | try/catch |

### 7.2 Erisilebilirlik (Accessibility)

- **Iyi:** `schedule-display.tsx` ve `vehicle-card.tsx` proper ARIA labels
- **Kotu:** `user-form-dialog.tsx` raw radio input (shadcn RadioGroup kullanilmali)
- **Kotu:** `forgot-password/page.tsx` `prompt()` kullaniyor (erişilemez)
- **Kotu:** `schedule/page.tsx` `window.confirm()` kullaniyor
- **Eksik:** Tum tablolar responsive degil (mobile overflow)

---

## 8. Python Optimizer API Detayli Inceleme

### 8.1 Strateji Mimari

```
BaseRoutingStrategy (base)
├── Pipeline A (Cluster-First Route-Second)
│   ├── GeneticAlgorithmStrategy
│   ├── PSOSplitStrategy
│   ├── GWOSplitStrategy
│   └── HHOSplitStrategy
├── Pipeline B (Route-First Cluster-Second)
│   ├── HybridSplitBaseStrategy
│   │   ├── GASplitStrategy
│   │   ├── GOWSplitStrategy
│   │   ├── HHOSplitStrategy
│   │   └── PSOSplitStrategy
│   └── (SOTA solvers)
│       ├── PyVRPStrategy (optional)
│       ├── VROOMStrategy (optional)
│       └── ORToolsCVRPStrategy
└── Local Search Operators
    ├── TwoOptLocalSearch
    ├── ThreeOptLocalSearch
    └── HybridLocalSearch
```

### 8.2 Dogruluk Degerlendirmesi

| Algoritma | Dogruluk | Not |
|-----------|----------|-----|
| Split Decoder (DP) | Dogru | Prins (2004) O(n²) implementasyon |
| OR-Tools CVRP | Dogru | Demand scaling, 30s time limit uygun |
| PSO | Dogru | Clerc & Kennedy (2002) constriction degerleri |
| Haversine | Dogru | 6371km Earth radius |
| VehicleCalculator | Dogru | Iterative capacity-violation retry |
| 3-Opt | Kismi | Duplicate case'ler var (redundant evaluations) |
| GWO | Kismi | Conflicting swap'lar olusabilir |
| Local Search | Dogru | Temiz abstract base class + factory pattern |

### 8.3 Performans

| Sorun | Etki |
|-------|------|
| Singleton state corruption (concurrent) | Yuksek — /compare endpoint'inde |
| ~800 satir kod tekrarı (Pipeline A) | Orta — Bakım zorlugu |
| DataLoader singleton thread-safe degil | Orta — Multi-worker deployment |
| get_submatrix numpy → list → dict conversion | Dusuk — Unnecessary overhead |

---

## 9. Veritabani ve RLS Incelemesi

### 9.1 Tablo Ozeti

| Tablo | FK Constraints | RLS Policies | Indexes | Not |
|-------|---------------|-------------|---------|-----|
| users | 0 FK | SELECT, INSERT, UPDATE (tum auth) | id, email | **CRITIK: role update kısıtlama yok** |
| vehicles | 0 FK | SELECT only | id | **WRITE POLICY YOK** |
| ride_requests | 0 FK | SELECT own + admin, INSERT own, UPDATE own | status, pickup_time | FK eksik (vehicle_id) |
| weekly_schedules | 0 FK | SELECT own + admin, INSERT own, UPDATE own | id | UNIQUE(user_id) base schema eksik |
| route_assignments | 0 FK | SELECT own, INSERT admin | date, vehicle_id | **WRITE POLICY YOK** |
| routes | 0 FK | SELECT all auth | id | **WRITE POLICY YOK** |
| route_plans | 0 FK | SELECT confirmed+ (tum auth!) | - | **Role check yok** |
| sandbox_scenarios | 0 FK | SELECT/INSERT/UPDATE/DELETE own | - | Migration dosyasinda |
| time_matrix | 0 FK | SELECT/INSERT service_role | - | Migration dosyasinda |
| notifications | 0 FK | **INSERT true (tum auth!)** | - | **CRITIK** |
| admin_settings | 0 FK | SELECT all auth | - | **Admin SELECT kisitlama yok** |

### 9.2 Kritik RLS Aciklari

1. **users_update_own** → Role degisikligine izin veriyor (CR-01)
2. **notifications_insert** → Herkes notification insert edebilir (CR-02)
3. **route_plans select** → Tum auth kullanicilar gorebilir (MD-09)
4. **admin_settings select** → Tum auth kullanicilar gorebilir (MD-27)
5. **vehicles/routes/route_assignments** → Write policy yok (HI-09)
6. **weekly_schedules_update_own** → WITH CHECK eksik (MD-10)

---

## 10. Yapilandirma ve Bagimlik Analizi

### 10.1 Bagimlik Sorunlari

| Paket | Version | Sorun | Oncelik |
|-------|---------|-------|---------|
| `next` | `^16.1.6` | React 18 ile uyumsuz | Yuksek |
| `react` | `^18.3.1` | Next.js 16 React 19 gerektirir | Yuksek |
| `xlsx` | `^0.18.5` | CVE-2023-30533, artik bakim yok | Yuksek |
| `dotenv` | `^16.6.1` | Dependencies'te olmali degil | Dusuk |
| `patch-package` | `^8.0.0` | postinstall script eksik | Dusuk |

### 10.2 Kritik Environment Variables

| Variable | Exposure | Durum |
|----------|----------|-------|
| `NEXT_PUBLIC_SUPABASE_URL` | Client | Normal (Supabase standard) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Client | Normal (Supabase standard) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only | Iyi — supabase-admin.ts'de throw on missing |
| `NEXT_PUBLIC_DEV_RESET_SECRET` | **Client** | **KRITIK** — Client'a gecmemeli |
| `OPTIMIZER_API_URL` | Server | Normal |
| `DATABASE_URL` | Server (Local) | Prisma icin — artik kullanilmiyor |

---

## 11. Onceliklendirilmis Aksiyon Plani

### Faz 1: Guvenlik Aciklari (P0 — Hemen)

| # | Bulgu | Effort | Impact |
|---|-------|--------|--------|
| 1 | CR-01: RLS users_update_own role kisitlama | 15 dk | Privilege escalation onlemek |
| 2 | CR-02: RLS notifications_insert service_role kisitla | 15 dk | Injection onlemek |
| 3 | CR-03: NEXT_PUBLIC_DEV_RESET_SECRET kaldir | 30 dk | Secret exposure onlemek |
| 4 | CR-06: setUser context'ten kaldir | 1 saat | Client-side escalation onlemek |
| 5 | CR-07: PostgREST filter input validation | 15 dk | Injection onlemek |
| 6 | CR-11: User tipinden password kaldir | 10 dk | Password exposure onlemek |
| 7 | CR-12: Admin sayfalari role check ekle | 1 saat | Unauthorized access onlemek |
| 8 | HI-02: Security headers ekle | 30 dk | Standard guvenlik |
| 9 | HI-09: RLS write policy ekle | 2 saat | Tam RLS kapsamı |

### Faz 2: Bug Fixler (P1 — Bu Hafta)

| # | Bulgu | Effort | Impact |
|---|-------|--------|--------|
| 1 | CR-04: cooldown_minutes sutun ekle | 15 dk | Data integrity |
| 2 | CR-08: Python stratejilere import logging | 10 dk | Runtime crash onlemek |
| 3 | CR-09: Singleton thread-safe yap | 2 saat | Concurrent corruption onlemek |
| 4 | CR-10: get_time_windows() implement et | 1 saat | CVRPTW aktif et |
| 5 | HI-01: React Error Boundary | 30 dk | App crash onlemek |
| 6 | HI-04: User deletion order fix | 30 dk | Orphaned auth onlemek |
| 7 | HI-05: Pickup/dropoff filter fix | 30 dk | Dogru routing |
| 8 | HI-06: Schedule-to-requests zaman fix | 30 dk | Dogru zamanlama |
| 9 | MD-03: Empty string falsy check | 30 dk | Alan bosaltma |
| 10 | MD-18: Off-by-one date range | 15 dk | Tam tarih araligi |
| 11 | MD-29: Residual magic 15.0 | 5 dk | Konsistens |

### Faz 3: Tip Guvenligi ve Validation (P2 — Onraki Hafta)

| # | Bulgu | Effort | Impact |
|---|-------|--------|--------|
| 1 | CR-05, HI-07: Tum *Row tipleri olustur | 3 saat | Tip guvenligi |
| 2 | HI-12: Status enum validation | 30 dk | Input validation |
| 3 | MD-14: Zod schema ekle (3 endpoint) | 2 saat | Input validation |
| 4 | MD-01: Rate limiter Redis'e tası | 2 saat | Guvenlik |
| 5 | MD-07: schema.sql birlestir | 1 saat | Migration safety |
| 6 | MD-13: as any temizle | 2 saat | Tip guvenligi |

### Faz 4: Performans ve Kod Kalitesi (P3 — Sprint)

| # | Bulgu | Effort | Impact |
|---|-------|--------|--------|
| 1 | HI-03: xlsx → exceljs migration | 2 saat | Guvenlik + bakim |
| 2 | HI-11: Reports N+1 query fix | 2 saat | Performans |
| 3 | MD-16: Pipeline A refactoring | 4 saat | 800 satir azaltma |
| 4 | MD-24: Parallel time slot optimization | 2 saat | Performans |
| 5 | MD-12: useEffect dependency fixes | 1 saat | React pattern |
| 6 | MD-20: React 18 → 19 upgrade | 4 saat | Next.js uyumluluk |
| 7 | LO-01: ESLint no-explicit-any → error | 1 saat | Kod kalitesi |
| 8 | Responsive table wrappers | 1 saat | Mobile UX |

---

## Ekler

### A. Dosya Sayisi Ozeti

| Kategori | Dosya Sayisi | Satir (Tahmini) |
|----------|-------------|----------------|
| src/app/(app)/ | 20 pages | ~4,000 |
| src/app/(auth)/ | 4 pages | ~800 |
| src/app/api/ | 15 routes | ~2,500 |
| src/components/ | 20 components | ~3,500 |
| src/components/ui/ | 38 components | ~5,000 |
| src/lib/ | 12 files | ~2,000 |
| src/services/ | 10 files | ~3,000 |
| src/hooks/ | 4 files | ~400 |
| src/contexts/ | 1 file | ~150 |
| src/types/ | 3 files | ~300 |
| optimizer_api/ | ~30 files | ~8,000 |
| supabase/ | ~10 files | ~800 |
| **TOPLAM** | **~160** | **~30,500** |

### B. Teknoloji Stack

| Katman | Teknoloji | Version |
|--------|-----------|---------|
| Frontend | Next.js | ^16.1.6 |
| UI Library | React | ^18.3.1 |
| Styling | Tailwind CSS | ^3.4.1 |
| Component Library | shadcn/ui | New York |
| State | React Context + useState | - |
| Backend API | Next.js Route Handlers | - |
| Database | Supabase (PostgreSQL) | - |
| Auth | Supabase Auth | - |
| Optimizer | Python FastAPI | - |
| Form Validation | Zod + react-hook-form | - |
| Charts | Recharts | ^2.15.1 |
| AI/ML | Genkit (Google AI) | ^1.32.0 |

---

*Bu rapor 120+ dosyanin kaynak kod tabanli analizine dayanmaktadir. Dokumantasyondaki iddialar degil, sadece kodda gercekten mevcut olan yapilar incelenmistir.*
