# UniRide — Code Quality & Security Fix Roadmap

> **Son Güncelleme:** Haziran 2025
> **Kaynak:** `CODE_REVIEW_REPORT.md` — 80+ tespit edilen issue üzerinden önceliklendirilmiş yol haritası
> **Sahip:** Backend & Frontend takımları

---

## İçindekiler

1. [P0 — Acil Güvenlik Düzeltmeleri](#p0--acil-güvenlik-düzeltmeleri)
2. [P1 — Bug Fix'ler](#p1--bug-fixler)
3. [P2 — Type Safety & Validation](#p2--type-safety--validation)
4. [P3 — Performance & Code Quality](#p3--performance--code-quality)
5. [Parallel Work Guidance](#parallel-work-guidance--eşzamanlı-çalışma-planı)
6. [Tracking & Metrics](#tracking--metrics)
7. [Sprint Allocation Summary](#sprint-allocation-summary)

---

## P0 — Acil Güvenlik Düzeltmeleri

> **Hedef:** İlk sprint (Hafta 1–2) içinde tamamlanması zorunlu.
> **Kural:** Hiçbir P0 item sprint planlamasından çıkarılamaz; production'a merge edilmeden önce mutlaka resolve edilmeli.

| ID | Finding | File | Severity | Status |
|----|---------|------|----------|--------|
| CR-01 | RLS `users_update_own` policy allows role escalation — user kendi rolünü değiştirebiliyor | `supabase/rls_policies.sql` | 🔴 Critical | ⬜ |
| CR-02 | `notifications_insert` WITH CHECK (true) — herhangi bir kullanıcı herhangi bir notification insert edebiliyor | `supabase/rls_policies.sql` | 🔴 Critical | ⬜ |
| CR-03 | `NEXT_PUBLIC_DEV_RESET_SECRET` client-side exposure | `forgot-password/page.tsx` | 🔴 Critical | ✅ Fixed |
| CR-06 | `AuthContext.setUser()` ile auth state açıkça override edilebiliyor | `auth-context.tsx` | 🔴 Critical | ⬜ |
| CR-07 | PostgREST filter injection — user input doğrudan query filter olarak kullanılıyor | `auth/hint/route.ts` | 🔴 Critical | ⬜ |
| CR-11 | User type'da `password` field暴露 — client'a password hash sızıntısı riski | `types/index.ts` | 🟠 High | ⬜ |
| CR-12 | Admin page'lerde role check yok — authenticated herkes admin panel'e erişebiliyor | `admin/*/page.tsx` | 🟠 High | ⬜ |
| HI-02 | Security headers eksik (CSP, HSTS, X-Frame-Options vb.) | `next.config.ts` | 🟠 High | ⬜ |
| HI-09 | RLS write policy eksik — tablolarda yazma işlemi policy olmadan açık | `rls_policies.sql` | 🟠 High | ⬜ |

### P0 Detaylı Aksiyon Planı

#### CR-01 & CR-02 & HI-09 — RLS Policy Overhaul
```sql
-- CR-01 FIX: users_update_own policy'den role column exclude et
CREATE POLICY users_update_own ON users
  FOR UPDATE USING (auth.uid() = id)
  WITH CHECK (
    auth.uid() = id
    AND (role IS NOT DISTINCT FROM (SELECT role FROM users WHERE id = auth.uid()))
  );

-- CR-02 FIX: notifications_insert'a proper CHECK ekle
CREATE POLICY notifications_insert ON notifications
  FOR INSERT WITH CHECK (
    recipient_id = auth.uid()
    OR EXISTS (SELECT 1 FROM users WHERE id = auth.uid() AND role = 'admin')
  );

-- HI-09 FIX: Missing write policies for each table
-- (Her tablo için tek tek WITH CHECK clause eklenecek)
```

#### CR-06 — AuthContext.setUser() Koruması
```tsx
// auth-context.tsx — setUser'ı private yap, server-only setter ekle
const setUser = (user: User) => { /* internal only */ };
// Public API: sadece login/signup callback'leri üzerinden indirect erişim
```

#### CR-07 — PostgREST Filter Injection
```ts
// auth/hint/route.ts — input validation ekle
const safeEmail = email.replace(/[^a-zA-Z0-9@._-]/g, '');
if (safeEmail !== email) throw new Error('Invalid email format');
```

#### CR-12 — Admin Page Middleware Guard
```ts
// middleware.ts veya layout.tsx level'da role check
if (pathname.startsWith('/admin') && user.role !== 'admin') {
  redirect('/unauthorized');
}
```

#### HI-02 — Security Headers
```ts
// next.config.ts
const securityHeaders = [
  { key: 'X-Frame-Options', value: 'DENY' },
  { key: 'X-Content-Type-Options', value: 'nosniff' },
  { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
  { key: 'Content-Security-Policy', value: "default-src 'self'; ..." },
  { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
];
```

---

## P1 — Bug Fix'ler

> **Hedef:** Sprint 2–3 (Hafta 3–6)
> **Öncelik:** Core functionality'yi etkileyen bug'lar önce; edge case'ler sonra.

| ID | Finding | Severity | Status | Est. Effort |
|----|---------|----------|--------|-------------|
| CR-04 | `cooldown_minutes` column missing — DB migration eksik | 🟠 High | ⬜ | 1h |
| CR-08 | Python strategies'da `import logging` yapılmış ama kullanılmamış | 🟡 Low | ✅ Fixed | — |
| CR-09 | Singleton state corruption — concurrent request'lerde state bozulması | 🟠 High | ⬜ | 4h |
| CR-10 | `get_time_windows()` dead code — unused function kaldırılmış | 🟡 Low | ✅ Fixed | — |
| HI-01 | React Error Boundary eksik — hata durumunda beyaz ekran | 🟠 High | ⬜ | 2h |
| HI-04 | User deletion order — cascade delete eksik, orphan record riski | 🟠 High | ⬜ | 2h |
| HI-05 | Pickup/dropoff filter aynı parametre kullanıyor — yanlış filtreleme | 🟠 High | ⬜ | 1h |
| HI-06 | Schedule → requests time conversion hatası — timezone/saát kayması | 🟠 High | ⬜ | 3h |
| HI-10 | Foreign key constraints missing — data integrity riski | 🟠 High | ⬜ | 3h |
| MD-03 | Empty string falsy check — `""` değer `false` olarak değerlendiriliyor | 🟡 Medium | ⬜ | 1h |
| MD-18 | Off-by-one date range bug — tarih aralığı bir gün eksik/ fazla | 🟡 Medium | ⬜ | 1h |
| MD-29 | Residual magic `15.0` value — anlamsız sabit değer | 🟡 Medium | ⬜ | 30m |

### P1 Detaylı Notlar

#### CR-09 — Singleton State Corruption
```
Problem: Global singleton instance'lar server-side concurrent request'lerde
         shared state tutuyor. Serverless/edge runtime'da bu race condition'a yol açar.
Fix:     Request-scoped dependency injection veya factory pattern uygula.
         Her request için yeni instance oluştur.
```

#### HI-10 — Missing FK Constraints
```sql
-- Eksik foreign key'ler eklenecek:
ALTER TABLE ride_requests ADD CONSTRAINT fk_ride_requests_driver
  FOREIGN KEY (driver_id) REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE ride_requests ADD CONSTRAINT fk_ride_requests_rider
  FOREIGN KEY (rider_id) REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE ride_requests ADD CONSTRAINT fk_ride_requests_route
  FOREIGN KEY (route_id) REFERENCES routes(id) ON DELETE CASCADE;
-- (+ diğer eksik constraint'ler)
```

#### HI-06 — Schedule-to-Requests Time Bug
```
Problem: Schedule'daki saat bilgisi request oluşturulurken UTC conversion
         yapılmadan direkt kullanılıyor. Timezone offset nedeniyle ±3 saat kayma.
Fix:     Tüm datetime işlemlerinde UTC normalize et; client-side'da local time display yap.
```

---

## P2 — Type Safety & Validation

> **Hedef:** Sprint 3–5 (Hafta 5–10)
> **Öncelik:** Runtime crash riski olanlar önce, DX (developer experience) iyileştirmeleri sonra.

| ID | Finding | Severity | Status | Est. Effort |
|----|---------|----------|--------|-------------|
| CR-05 | `*Row` snake_case type'lar eksik — sadece `users` table için yapılmış | 🟡 Medium | 🟡 Partial | 4h |
| HI-07 | Status enum validation — string literal yerine union type kullanılmamış | 🟡 Medium | ⬜ | 2h |
| HI-12 | Status enum validation (DB ↔ App sync) | 🟡 Medium | ⬜ | 2h |
| MD-14 | Zod schema missing — 3 endpoint'te input validation yok | 🟠 High | ⬜ | 3h |
| MD-01 | Rate limiter Redis migration — in-memory rate limiting production'da unreliable | 🟡 Medium | ⬜ | 5h |
| MD-07 | `schema.sql` consolidation — dağınık migration dosyaları | 🟡 Medium | ⬜ | 3h |
| MD-13 | `as any` cleanup — 11 yerden 10'a düşürüldü, kalanlar temizlenecek | 🟡 Medium | 🟡 Partial | 2h |

### P2 Detaylı Notlar

#### CR-05 & HI-07 — Row Types & Status Enum
```ts
// types/index.ts — eksik row type'lar eklenecek
export type RouteRow = {
  id: string;
  driver_id: string;
  origin: string;
  destination: string;
  departure_time: string;
  available_seats: number;
  created_at: string;
  // ...
};

// Status union type
export type RideStatus = 'pending' | 'accepted' | 'in_progress' | 'completed' | 'cancelled';
export type NotificationStatus = 'unread' | 'read';

// Runtime validation helper
export function assertRideStatus(status: string): RideStatus {
  const valid: RideStatus[] = ['pending', 'accepted', 'in_progress', 'completed', 'cancelled'];
  if (!valid.includes(status as RideStatus)) {
    throw new Error(`Invalid ride status: ${status}`);
  }
  return status as RideStatus;
}
```

#### MD-14 — Zod Schema for Missing Endpoints
```ts
// lib/validations/ride-request.ts
import { z } from 'zod';

export const createRideRequestSchema = z.object({
  route_id: z.string().uuid(),
  pickup_location: z.string().min(1).max(200),
  dropoff_location: z.string().min(1).max(200),
  message: z.string().max(500).optional(),
});

export const updateRideStatusSchema = z.object({
  status: z.enum(['accepted', 'rejected', 'cancelled']),
});
```

#### MD-01 — Redis Rate Limiter Migration
```
Current:  In-memory Map-based rate limiter (server restart'ta sıfırlanır)
Target:   Upstash Redis-based sliding window rate limiter
Why:      Multi-instance deployment'da rate limiting tutarsız olur

Steps:
1. @upstash/ratelimit paketini ekle
2. Redis connection config'ini environment variable'dan al
3. Mevcut rate limiter'ı yeni implementation ile değiştir
4. Integration test ile doğrula
```

---

## P3 — Performance & Code Quality

> **Hedef:** Sprint 5–8 (Hafta 9–16)
> **Öncelik:** Kullanıcı-visible performance improvement'lar önce, internal refactoring sonra.

| ID | Finding | Severity | Status | Est. Effort |
|----|---------|----------|--------|-------------|
| HI-03 | `xlsx` → `exceljs` migration — bundle size ve security improvement | 🟡 Medium | ⬜ | 3h |
| HI-11 | Reports N+1 query fix — her satır için ayrı DB sorgusu | 🟠 High | ⬜ | 4h |
| MD-16 | Pipeline A refactoring — ~800 line monolitik fonksiyon | 🟡 Medium | ⬜ | 8h |
| MD-20 | React 18 → 19 upgrade | 🟡 Medium | ⬜ | 6h |
| LO-01 | ESLint `no-explicit-any` → `error` seviyesine çek | 🟡 Low | ⬜ | 2h |

### P3 Detaylı Notlar

#### HI-11 — N+1 Query Fix
```
Current:  for (const row of rows) { const user = await getUser(row.user_id); }
Fix:      const userIds = rows.map(r => r.user_id);
          const users = await getUsersByIds(userIds);  // single batch query
Impact:   Report generation 5-10x hızlanması bekleniyor
```

#### MD-16 — Pipeline A Refactoring Plan
```
Current:  ~800 line tek fonksiyon — maintenance nightmare
Target:   Modular pipeline pattern

Proposed Structure:
  pipeline-a/
    index.ts          # Main orchestrator
    stages/
      01-fetch.ts     # Data fetching
      02-validate.ts  # Validation
      03-transform.ts # Data transformation
      04-filter.ts    # Filtering logic
      05-enrich.ts    # Data enrichment
      06-output.ts    # Result formatting
    types.ts          # Pipeline-specific types
    utils.ts          # Shared helpers
    constants.ts      # Constants (magic values buraya)
```

#### MD-20 — React 19 Upgrade Checklist
- [ ] `react` ve `react-dom` 19.x'e upgrade
- [ ] Breaking change'leri review et (ref callbacks, form actions)
- [ ] `next` compatible version kontrolü
- [ ] Unit test'leri çalıştır, regressions'ı kontrol et
- [ ] E2E test'leri ile doğrula
- [ ] Canary deployment ile production'a al

---

## Parallel Work Guidance — Eşzamanlı Çalışma Planı

> Aşağıdaki tablo hangi task'ların aynı anda farklı developer'lar tarafından yapılıbileceğini gösterir.
> **⚠️ P0 items hiçbir durumda paralel çalışılmamalı — sıralı olarak tek kişi tarafından yapılmalı.**

### Wave 1 — Sprint 1–2 (P0 + Critical P1)

```
┌─────────────────────────────────────────────────────────┐
│                    WAVE 1 — SECURITY                     │
│                                                         │
│  Dev A (Backend/DB):         Dev B (Frontend):          │
│  ├─ CR-01 RLS fix           ├─ CR-12 Admin guard       │
│  ├─ CR-02 notifications     ├─ HI-02 Security headers  │
│  ├─ CR-06 AuthContext       ├─ CR-11 Password field    │
│  ├─ CR-07 Filter injection  └─ HI-01 Error Boundary    │
│  └─ HI-09 Write policies                               │
│                                                         │
│  ⚠️  CR-01 → CR-02 → HI-09 sıralı çalışılmalı          │
└─────────────────────────────────────────────────────────┘
```

### Wave 2 — Sprint 2–4 (P1 Core Bugs)

```
┌─────────────────────────────────────────────────────────┐
│                  WAVE 2 — BUG FIXES                      │
│                                                         │
│  Dev A (Backend):            Dev B (Backend):           │
│  ├─ CR-04 cooldown column    ├─ CR-09 Singleton fix    │
│  ├─ HI-10 FK constraints     ├─ HI-06 Time conversion  │
│  ├─ HI-04 Deletion order     ├─ HI-05 Filter fix       │
│  └─ MD-03 Empty string       └─ MD-18 Off-by-one       │
│                                                         │
│  Dev C (Fullstack):                                     │
│  └─ MD-29 Magic 15.0 cleanup                            │
│                                                         │
│  ⚠️  HI-10 → HI-04 sıralı (FK constraint önce)        │
└─────────────────────────────────────────────────────────┘
```

### Wave 3 — Sprint 3–6 (P2 Type Safety)

```
┌─────────────────────────────────────────────────────────┐
│               WAVE 3 — TYPE SAFETY                       │
│                                                         │
│  Dev A (Types):               Dev B (Infra):            │
│  ├─ CR-05 Row types           ├─ MD-01 Redis migration │
│  ├─ HI-07 Status enum         └─ MD-07 Schema consol.  │
│  ├─ HI-12 Status validation                             │
│  ├─ MD-14 Zod schemas                                    │
│  └─ MD-13 as any cleanup                                 │
│                                                         │
│  ✅  Tüm task'lar paralel yapılabilir                   │
└─────────────────────────────────────────────────────────┘
```

### Wave 4 — Sprint 5–8 (P3 Performance)

```
┌─────────────────────────────────────────────────────────┐
│              WAVE 4 — PERFORMANCE & DX                   │
│                                                         │
│  Dev A (Backend):            Dev B (Frontend):          │
│  ├─ HI-11 N+1 query fix      ├─ HI-03 xlsx→exceljs    │
│  ├─ MD-16 Pipeline refactor  ├─ MD-20 React 19         │
│  └─ LO-01 ESLint strict      └─ LO-01 (cont.)         │
│                                                         │
│  ⚠️  MD-20 React 19 — en son yapılmalı (diğer task'lar │
│      tamamlandıktan sonra, conflict riski yüksek)        │
└─────────────────────────────────────────────────────────┘
```

### Dependency Graph (Critical Path)

```
CR-01 ──► CR-02 ──► HI-09 ──► HI-10 ──► HI-04
  │                                      │
  ▼                                      ▼
CR-06 ──► CR-07 ──► CR-11 ──► CR-12      │
  │                                      │
  ▼                                      ▼
HI-02 ──► HI-01 ◄────────────────────────┘
  │
  ▼
HI-05 ──► HI-06 ──► MD-03 ──► MD-18
  │
  ▼
MD-29 ──► MD-13 ──► LO-01
                    │
  CR-05 ──► HI-07 ─┤
                    ▼
              HI-12 ──► MD-14 ──► MD-01
                                │
                                ▼
                          MD-07 ──► HI-03
                                      │
                                      ▼
                                HI-11 ──► MD-16
                                            │
                                            ▼
                                        MD-20
```

---

## Tracking & Metrics

### Issue Summary

| Priority | Total | Done | Partial | Remaining |
|----------|-------|------|---------|-----------|
| P0 (Security) | 9 | 1 | 0 | **8** |
| P1 (Bugs) | 12 | 2 | 0 | **10** |
| P2 (Type Safety) | 7 | 0 | 2 | **5** |
| P3 (Performance) | 5 | 0 | 0 | **5** |
| **Toplam** | **33** | **3** | **2** | **28** |

### Estimated Effort

| Priority | Estimated Hours | Sprint Allocation |
|----------|----------------|-------------------|
| P0 | ~16h | Sprint 1–2 |
| P1 | ~20h | Sprint 2–4 |
| P2 | ~21h | Sprint 3–6 |
| P3 | ~23h | Sprint 5–8 |
| **Toplam** | **~80h** | **8 sprint** |

### Quality Gates

Her sprint sonunda aşağıdaki kriterler kontrol edilecek:

- [ ] **P0 Gate:** Tüm P0 item'lar resolved ve production'da verified
- [ ] **Test Coverage:** Her fix için en az 1 unit test; P0 için additional integration test
- [ ] **Code Review:** 2 reviewer onaylı PR (security fix'ler için zorunlu)
- [ ] **Regression:** Mevcut test suite %100 pass rate
- [ ] **Documentation:** Breaking change'ler için CHANGELOG entry

---

## Sprint Allocation Summary

| Sprint | Focus | Key Deliverables | Success Metric |
|--------|-------|------------------|----------------|
| Sprint 1–2 | **P0 Security** | RLS policies, auth guards, headers | 0 critical security findings |
| Sprint 3–4 | **P1 Core Bugs** | DB constraints, time bugs, filters | 0 P1 runtime bugs |
| Sprint 5–6 | **P2 Type Safety** | Zod schemas, row types, enum validation | TypeScript strict mode, 0 `as any` |
| Sprint 7–8 | **P3 Performance** | N+1 fix, pipeline refactor, React 19 | Report gen <2s, bundle size -15% |

---

> **Not:** Bu roadmap `CODE_REVIEW_REPORT.md` baz alınarak hazırlanmıştır. Yeni tespit edilen issue'lar ilgili priority'ye eklenir. Sprint planning'de capacity'e göre sıralama güncellenebilir ancak P0 item'ların önceliği değişmez.
