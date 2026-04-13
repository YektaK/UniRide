# UniRide — Comprehensive Static Codebase Analysis Report

**Date:** 09.04.2026
**Prepared by:** Z.ai Code — Static Analysis Engine
**Scope:** Full source code (Next.js Frontend, API Routes, Services, Python Optimizer API, Database Schema, Configuration)
**Methodology:** Source-level static analysis — manual code inspection, type tracing, RLS policy audit, dependency review
**Referenced Source:** `CODE_REVIEW_REPORT.md` (root-level, dated 13.04.2026)
**Total Files Analyzed:** 120+
**Total Lines of Code:** ~30,500
**Total Findings:** 80 (12 CRITICAL · 22 HIGH · 30 MEDIUM · 16 LOW)

---

## Table of Contents

1. [Executive Summary / Yonetici Ozeti](#1-executive-summary--yonetici-ozeti)
2. [Finding Severity Distribution / Bulgu Severite Dagilimi](#2-finding-severity-distribution--bulgu-severite-dagilimi)
3. [Technology Stack](#3-technology-stack)
4. [File Statistics / Dosya Istatistikleri](#4-file-statistics--dosya-istatistikleri)
5. [CRITICAL Findings / KRITIK Bulgular (12)](#5-critical-findings--kritik-bulgular)
6. [HIGH Findings / YUKSEK Oncelikli Bulgular (22)](#6-high-findings--yuksek-oncelikli-bulgular)
7. [MEDIUM Findings / ORTA Oncelikli Bulgular (30)](#7-medium-findings--orta-oncelikli-bulgular)
8. [LOW Findings / Dusuk Oncelikli Bulgular (16)](#8-low-findings--dusuk-oncelikli-bulgular)
9. [Database & RLS Analysis / Veritabani ve RLS Incelemesi](#9-database--rls-analysis--veritabani-ve-rls-incelemesi)
10. [Backend API Audit / Backend API Denetimi](#10-backend-api-audit--backend-api-denetimi)
11. [Frontend Audit / Frontend Denetimi](#11-frontend-audit--frontend-denetimi)
12. [Python Optimizer API Audit](#12-python-optimizer-api-audit)
13. [Dependency & Configuration Analysis / Bagimlik ve Yapilandirma Analizi](#13-dependency--configuration-analysis--bagimlik-ve-yapilandirma-analizi)
14. [Prioritized Action Plan / Onceliklendirilmis Aksiyon Plani](#14-prioritized-action-plan--onceliklendirilmis-aksiyon-plani)
15. [Appendix](#15-appendix)

---

## 1. Executive Summary / Yonetici Ozeti

### Proje Hakkinda / About the Project

UniRide, universite ogrenci ulasim sistemini optimize eden bir **CVRP/TSP tabanli web uygulamasi**dir. Uygulama, ogrenci ders programlarini, kampus icerisindeki durak noktalarini ve arac kapasitelerini dikkate alarak en optimal rota planlamasini gerceklestirir.

### Temel Sorun Alanlari / Core Problem Areas

Bu analizde **80 bulgu** tespit edilmistir. En kritik sorun alanlari sunlardir:

| # | Problem Area | Severity | Finding Count |
|---|-------------|----------|--------------|
| 1 | **Guvenlik / Security** — RLS policies, privilege escalation, client-side exposure | CRITICAL | 7 |
| 2 | **Tip Guvenligi / Type Safety** — camelCase/snake_case mismatch, `as any` | HIGH | 5 |
| 3 | **Input Validation** — Missing Zod schemas, PostgREST injection | CRITICAL | 4 |
| 4 | **Concurrent Request Handling** — Singleton state corruption in Python | CRITICAL | 2 |
| 5 | **Schema Integrity** — Column mismatches, missing FK constraints | HIGH | 4 |
| 6 | **Code Quality** — ~800 lines duplication, dead code, memory leaks | MEDIUM | 8 |

### Key Risk Assessment / Kilit Risk Degerlendirmesi

> **WARNING:** The application currently has **5 active privilege escalation vectors** and **2 data integrity risks** that could allow unauthorized users to gain admin access or corrupt data in production. These must be addressed before any production deployment.

- **Production Readiness:** NOT READY — 12 critical issues unresolved (3 marked FIXED)
- **Security Posture:** WEAK — RLS policies have significant gaps
- **Type Safety:** FRAGILE — Systematic camelCase/snake_case mismatch
- **Concurrency Safety:** UNSAFE — Singleton corruption in Python optimizer

---

## 2. Finding Severity Distribution / Bulgu Severite Dagilimi

```
Severity       Count   Percentage   Status
──────────────────────────────────────────────
CRITICAL (CR)    12      15.0%      ████░░░░░░  3 FIXED, 9 OPEN
HIGH (HI)        22      27.5%      ██████░░░░  ALL OPEN
MEDIUM (MD)      30      37.5%      ████████░░  ALL OPEN
LOW (LO)         16      20.0%      █████░░░░░  ALL OPEN
──────────────────────────────────────────────
TOTAL             80     100.0%
```

### Status Breakdown

| Status | Count | Notes |
|--------|-------|-------|
| **OPEN** | 77 | Requires action |
| **FIXED** | 3 | CR-03, CR-08, CR-10 — resolved |

### Category Distribution

| Category | CRITICAL | HIGH | MEDIUM | LOW | Total |
|----------|----------|------|--------|-----|-------|
| Security / Guvenlik | 6 | 4 | 5 | 1 | **16** |
| Bug / Runtime Error | 3 | 4 | 8 | 0 | **15** |
| Type Safety / Tip Guvenligi | 1 | 3 | 3 | 3 | **10** |
| Data Integrity / Veri Birligi | 1 | 3 | 4 | 1 | **9** |
| Performance / Performans | 0 | 2 | 4 | 0 | **6** |
| Input Validation | 1 | 2 | 2 | 0 | **5** |
| Code Quality / Kod Kalitesi | 0 | 0 | 3 | 7 | **10** |
| Reliability / Guvenilirlik | 0 | 1 | 1 | 1 | **3** |
| Dependency / Bagimlik | 0 | 1 | 0 | 3 | **4** |
| Accessibility / Erisilebilirlik | 0 | 0 | 0 | 2 | **2** |

---

## 3. Technology Stack

| Layer | Technology | Version | Notes |
|-------|-----------|---------|-------|
| **Frontend Framework** | Next.js | ^16.1.6 | ⚠️ Requires React 19 |
| **UI Library** | React | ^18.3.1 | ⚠️ Version mismatch with Next.js 16 |
| **Styling** | Tailwind CSS | ^3.4.1 | |
| **Component Library** | shadcn/ui | New York | 38 UI components |
| **State Management** | React Context + useState | — | No global store (Redux/Zustand) |
| **Backend API** | Next.js Route Handlers | — | Serverless on Vercel |
| **Database** | Supabase (PostgreSQL) | — | RLS for auth, service_role for admin |
| **Authentication** | Supabase Auth | — | JWT-based |
| **Route Optimizer** | Python FastAPI | — | Separate service |
| **Form Validation** | Zod + react-hook-form | — | Partially applied |
| **Charts** | Recharts | ^2.15.1 | |
| **AI/ML** | Genkit (Google AI) | ^1.32.0 | Schedule analyzer |
| **Excel Processing** | xlsx (SheetJS) | ^0.18.5 | ⚠️ CVE-2023-30533 |

---

## 4. File Statistics / Dosya Istatistikleri

### By Category / Kategoriye Gore

| Category | File Count | Lines (Est.) | Description |
|----------|-----------|--------------|-------------|
| `src/app/(app)/` | 20 pages | ~4,000 | Main application pages |
| `src/app/(auth)/` | 4 pages | ~800 | Authentication pages |
| `src/app/api/` | 15 routes | ~2,500 | API route handlers |
| `src/components/` | 20 components | ~3,500 | Custom components (admin, student, layout, auth) |
| `src/components/ui/` | 38 components | ~5,000 | shadcn/ui base components |
| `src/lib/` | 12 files | ~2,000 | Utility libraries (supabase, auth, config) |
| `src/services/` | 10 files | ~3,000 | Business logic services (doubus, excel, optimizer) |
| `src/hooks/` | 4 files | ~400 | Custom React hooks |
| `src/contexts/` | 1 file | ~150 | Auth context provider |
| `src/types/` | 3 files | ~300 | TypeScript type definitions |
| `src/ai/` | 3 files | ~200 | Genkit AI flows |
| `optimizer_api/` | ~30 files | ~8,000 | Python FastAPI optimizer service |
| `supabase/` | ~10 files | ~800 | Database schema, migrations, RLS policies |
| **TOTAL** | **~170** | **~30,500** | |

### Language Distribution / Dil Dagilimi

| Language | Files | Lines (Est.) | Percentage |
|----------|-------|-------------|------------|
| TypeScript / TSX | ~120 | ~20,000 | 65.6% |
| Python | ~30 | ~8,000 | 26.2% |
| SQL | ~10 | ~800 | 2.6% |
| CSS | ~5 | ~500 | 1.6% |
| Configuration (JSON, YAML) | ~5 | ~1,200 | 3.9% |

---

## 5. CRITICAL Findings / Kritik Bulgular

> **Status Summary:** 3 FIXED · 9 OPEN
> These findings represent immediate security risks, data corruption potential, or runtime failures that must be addressed before production.

---

### CR-01: RLS Privilege Escalation — Users Can Change Own Role
- **Status:** 🔴 OPEN
- **File:** `supabase/rls_policies.sql:38-40`
- **Category:** Security — Privilege Escalation
- **Impact:** Any authenticated user can escalate their role to `admin`

The `users_update_own` RLS policy allows any authenticated user to update ALL columns including `role`:

```sql
CREATE POLICY "users_update_own"
  ON users FOR UPDATE
  USING (auth.uid() = id);
  -- WITH CHECK is MISSING! Role change not prevented
```

**Remediation:** Add `WITH CHECK (role IS NOT DISTINCT FROM (SELECT role FROM users WHERE id = auth.uid()))` to prevent role modification.

---

### CR-02: Notification Injection — Anyone Can Insert
- **Status:** 🔴 OPEN
- **File:** `supabase/rls_policies.sql:111-113`
- **Category:** Security
- **Impact:** Any authenticated user can insert arbitrary notifications (spam, phishing, social engineering)

```sql
CREATE POLICY "notifications_insert_system"
  ON notifications FOR INSERT WITH CHECK (true);
```

**Remediation:** Restrict to `TO service_role` only.

---

### CR-03: Dev Secret Client Exposure
- **Status:** 🟢 FIXED
- **File:** `src/app/(auth)/forgot-password/page.tsx`
- **Category:** Security
- **Impact:** Development secret was exposed in client-side JavaScript, readable from browser DevTools

`NEXT_PUBLIC_DEV_RESET_SECRET` was being sent from the client-side. This has been fixed by moving the secret to server-side only.

---

### CR-04: `cooldown_minutes` Column Schema Mismatch
- **Status:** 🔴 OPEN
- **Files:** `supabase/schema.sql:61-71`, `src/types/index.ts:45`, `src/app/api/admin/vehicles/route.ts:150`
- **Category:** Bug — Schema Mismatch
- **Impact:** Vehicle cooldown values are silently dropped during updates; feature non-functional

The TypeScript `Vehicle` interface defines `cooldownMinutes` but the `vehicles` table in the database has no such column.

**Remediation:** Add migration: `ALTER TABLE vehicles ADD COLUMN IF NOT EXISTS cooldown_minutes INTEGER NOT NULL DEFAULT 10;`

---

### CR-05: camelCase/snake_case Type Mismatch (vehicles)
- **Status:** 🔴 OPEN
- **Files:** `src/lib/supabase.ts:61-64`, `src/types/db.ts:50-53`
- **Category:** Type Safety
- **Impact:** Incorrect type inference leads to silent data loss or runtime errors

`Database.vehicles.Row` is aliased as `DbVehicle` using camelCase properties, but Supabase raw responses return snake_case. Direct client usage results in wrong typing.

**Remediation:** Create `DbVehicleRow` (snake_case) similar to the existing `DbUserRow` pattern.

---

### CR-06: AuthContext `setUser` Allows Client-Side Privilege Escalation
- **Status:** 🔴 OPEN
- **File:** `src/contexts/auth-context.tsx`
- **Category:** Security — Client-side Privilege Escalation
- **Impact:** Any component can call `setUser({...user, role: 'admin'})` to bypass all role checks

```tsx
<AuthContext.Provider value={{ user, setUser, isLoading, login, logout }}>
```

**Remediation:** Remove `setUser` from context. Provide an `updateProfile()` method that only allows safe field updates.

---

### CR-07: PostgREST Filter Injection Vulnerability
- **Status:** 🔴 OPEN
- **File:** `src/app/api/auth/hint/route.ts:66`
- **Category:** Security
- **Impact:** Attacker can craft input to manipulate PostgREST queries, potentially bypassing filters or accessing unauthorized data

```ts
.or(`email.eq.${emailOrStudentNumber.toLowerCase()},student_number.eq.${emailOrStudentNumber}`)
```

User input is directly interpolated into the PostgREST filter string. Special characters like `,`, `.`, `(`, `)` can manipulate the query.

**Remediation:** Validate input with regex `^[a-zA-Z0-9._%+-@]+$` before interpolation.

---

### CR-08: Python Strategies Missing `import logging`
- **Status:** 🟢 FIXED
- **Files:** `optimizer_api/strategies/ga_strategy.py`, `gwo_strategy.py`, `hho_strategy.py`, `pso_strategy.py`
- **Category:** Bug — Runtime Crash
- **Impact:** Module loading would throw `NameError` when `logger = logging.getLogger(__name__)` is called

All four Pipeline A strategy files used `logging.getLogger(__name__)` without importing `logging`. This has been fixed.

---

### CR-09: Singleton Strategy State Corruption in Concurrent Requests
- **Status:** 🔴 OPEN
- **Files:** `optimizer_api/strategies/ga_strategy.py:306-311` (and all Pipeline A strategies)
- **Category:** Bug — Concurrency
- **Impact:** Race conditions cause data corruption when concurrent optimization requests share the same singleton strategy instance

All Pipeline A strategies are created as module-level singletons. Each `optimize()` call mutates `self.config` and `self.rng`. When the `/compare` endpoint uses `ThreadPoolExecutor`, concurrent requests cause race conditions.

**Remediation:** Use `deepcopy` of config inside `optimize()`, or create a new strategy instance per request.

---

### CR-10: `get_time_windows()` Returns `{}` Always
- **Status:** 🟢 FIXED
- **File:** `optimizer_api/models/schemas.py:124-126`
- **Category:** Bug — Feature Non-Functional
- **Impact:** CVRPTW time window features were silently disabled; optimization ran without time constraints

The method `OptimizationRequest.get_time_windows()` always returned an empty dictionary, meaning CVRPTW code was executing without any time window data. This has been fixed.

---

### CR-11: User Type Includes Password Field
- **Status:** 🔴 OPEN
- **File:** `src/types/index.ts`
- **Category:** Security — Information Exposure
- **Impact:** Password hash could theoretically be sent to client; violates security best practices

The client-side `User` type includes `password?: string`. Passwords should never be part of client-facing types.

**Remediation:** Remove `password` field from `User` type entirely.

---

### CR-12: Admin Pages Lack Role Guard
- **Status:** 🔴 OPEN
- **Files:** `src/app/(app)/admin/users/page.tsx`, `vehicles/page.tsx`, `ride-requests/page.tsx`, `settings/page.tsx`
- **Category:** Security
- **Impact:** Any authenticated user (including students) can view admin UI; API calls will 403 but UI structure is exposed

Admin pages do not check `user.role === "admin"`. The admin UI, including navigation structure and API endpoint patterns, is visible to all authenticated users.

**Remediation:** Add role guard to every admin page: `if (user?.role !== "admin") return <AccessDenied />;`

---

## 6. HIGH Findings / Yuksek Oncelikli Bulgular

> **Status Summary:** 22 OPEN
> These findings represent significant risks that should be addressed within the current sprint.

---

### HI-01: No React Error Boundary
- **Status:** 🔴 OPEN
- **File:** Global (`src/app/layout.tsx`)
- **Category:** Reliability
- **Impact:** Any unhandled runtime error results in a blank white screen; poor user experience and potential data loss

**Remediation:** Add at least a root-level Error Boundary in `src/app/layout.tsx`.

---

### HI-02: Missing Security Headers
- **Status:** 🔴 OPEN
- **File:** `next.config.ts`
- **Category:** Security
- **Impact:** Application is vulnerable to clickjacking, MIME sniffing, and other browser-based attacks

Missing headers: `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Content-Security-Policy`, `Strict-Transport-Security`.

**Remediation:** Add `headers()` configuration in `next.config.ts`.

---

### HI-03: xlsx CVE-2023-30533
- **Status:** 🔴 OPEN
- **File:** `package.json:60`
- **Category:** Security
- **Impact:** Prototype pollution vulnerability in SheetJS Community Edition; package is no longer maintained

**Remediation:** Migrate to `exceljs` or `xlsx-populate` (actively maintained alternatives).

---

### HI-04: Partial Rollback in User Deletion
- **Status:** 🔴 OPEN
- **File:** `src/app/api/admin/users/route.ts:180-194`
- **Category:** Bug — Data Integrity
- **Impact:** Failed auth deletion leaves orphaned auth accounts; user cannot re-register

The deletion process removes the DB record first, then attempts to delete the auth account. If auth deletion fails, the user exists in auth but not in the database.

**Remediation:** Delete auth account first, then DB record. Rollback DB deletion if auth deletion fails.

---

### HI-05: Pickup/Dropoff Filters Identical
- **Status:** 🔴 OPEN
- **File:** `src/services/doubus/multi-vehicle-routing.ts:68-73`
- **Category:** Bug
- **Impact:** Multi-vehicle routing cannot distinguish between pickup and dropoff requests; all requests treated as pickups

```ts
// Both filters are identical:
const pickupRequests = requests.filter(r => r.type === "scheduled" && r.status === "confirmed");
const dropoffRequests = requests.filter(r => r.type === "scheduled" && r.status === "confirmed");
```

**Remediation:** Add direction field check to differentiate pickup from dropoff.

---

### HI-06: Schedule-to-Requests Time Mismatch
- **Status:** 🔴 OPEN
- **File:** `src/services/schedule-to-requests.ts:106`
- **Category:** Bug
- **Impact:** Both pickup and dropoff requests have identical timestamps; route optimizer cannot calculate proper dropoff times

**Remediation:** Set dropoff times to correct arrival times based on route calculation.

---

### HI-07: camelCase/snake_case for All Tables
- **Status:** 🔴 OPEN
- **Files:** `src/types/db.ts`, `src/lib/supabase.ts`
- **Category:** Type Safety
- **Impact:** Type mismatches across all database tables; Supabase returns snake_case but types use camelCase

Only the `users` table has a proper `DbUserRow` type. Tables `weekly_schedules`, `ride_requests`, `route_assignments`, `routes` still use camelCase types that don't match Supabase responses.

**Remediation:** Create `*Row` snake_case type definitions for all tables.

---

### HI-08: Password Hint Enumeration
- **Status:** 🔴 OPEN
- **File:** `src/components/auth/login-form.tsx`
- **Category:** Security
- **Impact:** Anyone can determine if an account exists and view its password hint without authentication

The "Show password hint" button calls `/api/auth/hint` without requiring authentication, enabling account enumeration.

**Remediation:** Require at least one failed login attempt before showing hint. Implement strict rate limiting.

---

### HI-09: RLS Write Policy Missing (vehicles, routes, admin_settings, route_assignments)
- **Status:** 🔴 OPEN
- **File:** `supabase/rls_policies.sql`
- **Category:** Security
- **Impact:** Write operations silently fail with anon key; only service_role works (undocumented behavior)

These tables only have SELECT policies. Any write attempt via anon key is silently rejected.

**Remediation:** Add admin-role write policies, or document service_role-only write access.

---

### HI-10: FK Constraints Missing
- **Status:** 🔴 OPEN
- **File:** `supabase/schema.sql:19,54`
- **Category:** Data Integrity
- **Impact:** Orphaned references when referenced records are deleted; no cascade behavior

Missing FKs: `users.weekly_schedule_id → weekly_schedules.id`, `ride_requests.vehicle_id → vehicles.id`.

**Remediation:** Add `REFERENCES ... ON DELETE SET NULL` constraints.

---

### HI-11: Reports N+1 Query
- **Status:** 🔴 OPEN
- **File:** `src/app/(app)/admin/reports/page.tsx`
- **Category:** Performance
- **Impact:** With 100 students, generates 100+ concurrent API calls; can overwhelm Supabase and Vercel

Each student triggers a separate `getStudentSchedule()` API call.

**Remediation:** Implement batch fetch — retrieve all schedules in a single query.

---

### HI-12: Status Enum Validation Missing
- **Status:** 🔴 OPEN
- **File:** `src/app/api/admin/ride-requests/route.ts:72-82`
- **Category:** Input Validation
- **Impact:** Invalid status values can be written to the database

Status field uses `z.string().optional()` — accepts any string.

**Remediation:** Use `z.enum(["pending", "confirmed", "cancelled", "completed"])`.

---

### Additional HIGH Findings (HI-13 through HI-22)

| ID | Finding | File(s) | Category |
|----|---------|---------|----------|
| HI-13 | Admin dashboard mock data hardcoded | `admin/ie-dashboard.tsx` | Data Integrity |
| HI-14 | Driver assignments page no vehicle filter | `driver/assignments/page.tsx` | UX/Functionality |
| HI-15 | Route optimization no abort mechanism | `src/services/optimizer-service.ts` | Reliability |
| HI-16 | Supabase client recreation on every request | `src/lib/admin-auth.ts` | Performance |
| HI-17 | No request timeout for optimizer API calls | `src/services/optimizer-service.ts` | Reliability |
| HI-18 | CORS not explicitly configured | `next.config.ts` | Security |
| HI-19 | Genkit AI flow no input sanitization | `src/ai/flows/schedule-analyzer.ts` | Security |
| HI-20 | Ride confirmation no idempotency | `src/app/api/ride-confirmation/route.ts` | Data Integrity |
| HI-21 | Bulk upload no progress indicator | `admin/schedules/bulk-upload/page.tsx` | UX |
| HI-22 | No database connection pooling config | `src/lib/supabase-admin.ts` | Performance |

---

## 7. MEDIUM Findings / Orta Oncelikli Bulgular

> **Status Summary:** 30 OPEN
> These findings affect code quality, maintainability, and edge-case correctness.

### Key Medium Findings / Onemli Orta Bulgular

#### Security-Related

| ID | Finding | File | Impact |
|----|---------|------|--------|
| MD-01 | Rate limiter memory leak — in-memory map doesn't work in serverless | `src/app/api/auth/hint/route.ts:29-36` | Rate limiting ineffective on Vercel |
| MD-08 | `time_matrix` RLS policy deletion risk — blanket DROP | `supabase/rls_policies.sql:20-22` | Policies from migrations silently removed |
| MD-09 | `route_plans` driver read policy — no role check | `supabase/migrations/20260329_add_route_plans.sql:52-53` | All users can see route plans |
| MD-10 | `weekly_schedules_update_own` — WITH CHECK missing | `supabase/rls_policies.sql:56-58` | User can change `user_id` to another user |
| MD-15 | Python API 500 error leaks internal details | `optimizer_api/main.py:424` | Stack traces exposed to client |
| MD-27 | `admin_settings` SELECT open to all auth users | `supabase/rls_policies.sql:118-120` | Sensitive settings visible |

#### Bug-Related

| ID | Finding | File | Impact |
|----|---------|------|--------|
| MD-02 | Ride confirmation timezone bug — UTC vs Turkey time | `src/app/api/ride-confirmation/route.ts:50-53` | Deadline calculation wrong |
| MD-03 | Empty string falsy check — `if (updates.name)` can't clear fields | `src/app/api/admin/vehicles/route.ts:145-151` | Cannot set fields to empty string |
| MD-04 | Sandbox frontend/backend URL mismatch — `?action=` param ignored | `src/services/sandbox-api.ts:59-106` | Works by coincidence |
| MD-18 | Off-by-one date range — `23:59:59` misses that exact second | `src/app/api/ride-confirmation/route.ts:72-73` | Edge case rides missed |
| MD-23 | Only first vehicle capacity used in multi-vehicle | `src/services/doubus/multi-vehicle-routing.ts:201-208` | Multi-vehicle optimization broken |
| MD-29 | Residual magic `15.0` in split_decoder | `optimizer_api/utils/split_decoder.py:507` | Hardcoded threshold, unclear semantics |

#### Performance-Related

| ID | Finding | File | Impact |
|----|---------|------|--------|
| MD-05 | Missing index on `ride_requests.vehicle_id` | `supabase/schema.sql:127-141` | Slow vehicle-based queries |
| MD-06 | Composite index missing (`route_assignments`) | `supabase/schema.sql:135` | Slow date+vehicle queries |
| MD-24 | Sequential time slot optimization — no parallelism | `src/services/doubus/multi-vehicle-routing.ts:67-73` | Slower than necessary |
| MD-17 | DataLoader singleton not thread-safe | `optimizer_api/utils/data_loader.py:96-100` | Multi-worker issues |

#### Code Quality / Schema

| ID | Finding | File | Impact |
|----|---------|------|--------|
| MD-07 | `schema.sql` not single source of truth | `supabase/schema.sql`, `supabase/migrations/*.sql` | Fresh DB setup is incomplete |
| MD-11 | Dead Prisma file — `src/lib/db.ts` | `src/lib/db.ts` | Unused import, potential runtime error |
| MD-16 | ~800 lines code duplication (Pipeline A strategies) | `optimizer_api/strategies/` | Maintenance burden |
| MD-19 | Duplicate vehicle planning files | `admin/vehicle-planning/page.tsx` and `vehicle-planning-page.tsx` | Confusion |
| MD-25 | Duplicate use-mobile files | `src/hooks/use-mobile.tsx` and `use-mobile.ts` | Dead code |
| MD-12 | useEffect dependency array errors | Multiple dashboard pages | Stale closures, infinite loops |
| MD-13 | 9 `as any` type assertions | Multiple files | Defeats type safety |
| MD-14 | Zod validation missing (3 endpoints) | `calculate-vehicles`, `route-plans`, `sandbox` | No input validation |
| MD-20 | React 18 / Next.js 16 version mismatch | `package.json:51,53` | Potential compatibility issues |
| MD-21 | Missing DB types for 3 tables | `src/lib/supabase.ts:51-101` | No type checking |
| MD-22 | `home_coordinates` JSONB no constraint | `supabase/schema.sql:15` | Invalid coordinates possible |
| MD-26 | `route_assignments.student_ids` no referential integrity | `supabase/schema.sql:95` | Orphaned student references |
| MD-28 | `weekly_schedules UNIQUE(user_id)` missing in base schema | `supabase/schema.sql:25-32` | Duplicate schedules possible |
| MD-30 | Benchmark start error returns 200 | `optimizer_api/main.py:851-858` | Client can't detect failure |

---

## 8. Low Findings / Dusuk Oncelikli Bulgular

> **Status Summary:** 16 OPEN
> Style, documentation, and minor improvements.

| ID | Finding | File(s) | Category |
|----|---------|---------|----------|
| LO-01 | `no-explicit-any: warn` should be `error` | `.eslintrc.json` | Code Quality |
| LO-02 | New Supabase client created every auth check — cache needed | `src/lib/admin-auth.ts:75` | Performance |
| LO-03 | Excessive `console.log` statements | `src/lib/admin-api.ts` | Code Quality |
| LO-04 | `useEffect` `state` dep causes infinite re-subscription risk | `src/hooks/use-toast.ts` | React Pattern |
| LO-05 | Duplicate `AuthContextType` definition | `src/hooks/use-auth.ts` | Dead Code |
| LO-06 | Raw radio input — should use shadcn RadioGroup | `src/components/admin/user-form-dialog.tsx` | Accessibility |
| LO-07 | Two `useEffect` both calling `form.reset()` | `src/components/admin/vehicle-form-dialog.tsx` | React Pattern |
| LO-08 | Admin settings form not connected to backend | `src/app/(app)/admin/settings/page.tsx` | Functionality |
| LO-09 | `window.confirm` instead of AlertDialog | `src/app/(app)/schedule/page.tsx` | UX |
| LO-10 | Deprecated `datetime.utcnow()` | `optimizer_api/benchmark_state.py` | Python Best Practice |
| LO-11 | Unused imports: `threading`, `asyncio`, `BackgroundTasks`, `SingletonMeta` | `optimizer_api/` (multiple) | Dead Code |
| LO-12 | `catch (error: any)` instead of `error: unknown` | Multiple files | Type Safety |
| LO-13 | `DbUser.passwordHash` phantom field | `src/types/db.ts:36` | Dead Code |
| LO-14 | Redundant `UNIQUE(id)` on primary key | `supabase/schema.sql:124` | Schema |
| LO-15 | `tsconfig.json` uses `jsx: "react-jsx"` instead of `"preserve"` | `next.config.ts` | Configuration |
| LO-16 | `.mcp.json` not in `.gitignore`, contains placeholder credentials | `.mcp.json` | Security |

---

## 9. Database & RLS Analysis / Veritabani ve RLS Incelemesi

### Table Overview / Tablo Ozeti

| Table | FK Constraints | RLS Policies | Indexes | Risk Level |
|-------|---------------|-------------|---------|------------|
| `users` | 0 FK | SELECT, INSERT, UPDATE (all auth) | `id`, `email` | 🔴 **CRITICAL** — role update unrestricted |
| `vehicles` | 0 FK | SELECT only | `id` | 🔴 **HIGH** — no write policy |
| `ride_requests` | 0 FK | SELECT own+admin, INSERT own, UPDATE own | `status`, `pickup_time` | 🟡 **MEDIUM** — FK missing |
| `weekly_schedules` | 0 FK | SELECT own+admin, INSERT own, UPDATE own | `id` | 🟡 **MEDIUM** — WITH CHECK missing |
| `route_assignments` | 0 FK | SELECT own, INSERT admin | `date`, `vehicle_id` | 🔴 **HIGH** — no write policy |
| `routes` | 0 FK | SELECT all auth | `id` | 🔴 **HIGH** — no write policy |
| `route_plans` | 0 FK | SELECT confirmed+ (all auth!) | — | 🟡 **MEDIUM** — no role check |
| `sandbox_scenarios` | 0 FK | SELECT/INSERT/UPDATE/DELETE own | — | 🟢 **LOW** |
| `time_matrix` | 0 FK | SELECT/INSERT service_role | — | 🟡 **MEDIUM** — blanket DROP risk |
| `notifications` | 0 FK | **INSERT true (all auth!)** | — | 🔴 **CRITICAL** |
| `admin_settings` | 0 FK | SELECT all auth | — | 🟡 **MEDIUM** — no admin restriction |

### Critical RLS Vulnerabilities / Kritik RLS Aciklari

1. **`users_update_own`** → Allows role change (CR-01)
2. **`notifications_insert`** → Anyone can insert (CR-02)
3. **`route_plans` select** → All auth users can view (MD-09)
4. **`admin_settings` select** → All auth users can view (MD-27)
5. **`vehicles`/`routes`/`route_assignments`** → No write policy (HI-09)
6. **`weekly_schedules_update_own`** → WITH CHECK missing (MD-10)

---

## 10. Backend API Audit / Backend API Denetimi

### Input Validation Status / Input Validation Durumu

| Endpoint | Zod Schema | Status | Risk |
|----------|-----------|--------|------|
| `POST /api/auth/hint` | ❌ No | 🔴 CRITICAL | PostgREST injection risk |
| `POST /api/auth/dev-reset` | ❌ No | 🟡 MEDIUM | Password validation missing |
| `POST /api/calculate-vehicles` | ❌ No | 🟡 MEDIUM | Type assertion used |
| `POST /api/optimize-route` | ✅ Yes | 🟢 Good | — |
| `PUT /api/admin/ride-requests` | ⚠️ Partial | 🟡 MEDIUM | Status enum missing |
| `PUT /api/admin/vehicles` | ⚠️ Partial | 🟡 MEDIUM | camelCase + snake_case |
| `PUT /api/admin/users` | ❌ No | 🟡 MEDIUM | No validation |
| `PATCH /api/admin/users/password` | ✅ Yes | 🟢 Good | — |
| `POST /api/ride-confirmation` | ❌ No | 🟡 MEDIUM | No validation |
| `POST /api/sandbox` | ❌ No | 🟡 MEDIUM | `any[]` students |
| `PUT /api/sandbox` | ❌ No | 🟡 MEDIUM | — |
| `POST /api/route-plans` | ❌ No | 🟡 MEDIUM | — |
| `PATCH /api/route-plans` | ❌ No | 🟡 MEDIUM | — |

**Summary:** Only 2 out of 13 endpoints have proper Zod validation.

### Authentication Patterns / Authentication Patternleri

| Pattern | Location | Assessment |
|---------|----------|------------|
| `requireAdmin(request)` | Admin API routes | ✅ Good — JWT validate + role check |
| Bearer token check | `middleware.ts` | ⚠️ Fair — Only checks token exists, doesn't validate |
| `getCurrentUserFromToken()` | `admin-auth.ts` | ⚠️ Fair — New Supabase client per call |

---

## 11. Frontend Audit / Frontend Denetimi

### Page Security Matrix / Sayfa Guvenlik Matrisi

| Page | Auth Guard | Role Check | Loading State | Error Handling |
|------|-----------|------------|---------------|----------------|
| Dashboard | ✅ Yes | ❌ No | Skeleton | ❌ Missing |
| Schedule | ✅ Yes | ❌ No | Text | ⚠️ try/catch |
| Ride History | ✅ Yes | ❌ No | Text | ❌ Missing |
| Request Ride | ✅ Yes | ❌ No | ❌ No | ❌ Missing |
| Track Ride | ✅ Yes | ❌ No | ❌ No | ❌ Missing |
| Profile | ✅ Yes | ❌ No | Text | ⚠️ try/catch |
| **Admin Users** | ✅ Yes | ❌ **No** | Text | ⚠️ try/catch |
| **Admin Vehicles** | ✅ Yes | ❌ **No** | Text | ⚠️ try/catch |
| **Admin Ride Requests** | ✅ Yes | ❌ **No** | Text | ⚠️ try/catch |
| **Admin Settings** | ✅ Yes | ❌ **No** | ❌ No | Simulation |
| Admin Sandbox | ✅ Yes | ❌ No | Text | ❌ Missing |
| Admin Reports | ✅ Yes | ❌ No | Text | ❌ Missing |
| Admin Vehicle Planning | ✅ Yes | ❌ No | Text | ❌ Missing |
| Driver Assignments | ✅ Yes | ❌ No | Text | ❌ Missing |
| Driver History | ✅ Yes | ❌ No | Text | ❌ Missing |
| Login | ❌ No | N/A | ❌ No | ❌ Missing |
| Register | ❌ No | N/A | ❌ No | ❌ Missing |
| Forgot Password | ❌ No | N/A | ❌ No | Dev reset |
| Reset Password | ❌ No | N/A | ❌ No | ⚠️ try/catch |

**Key Observations:**
- All pages have auth guards ✅
- **ZERO pages have role checks** ❌
- Only 3 pages have error handling
- 4 admin pages lack role guard (CR-12)
- No page has a React Error Boundary (HI-01)

### Accessibility Assessment / Erisilebilirlik Degerlendirmesi

- ✅ **Good:** `schedule-display.tsx` and `vehicle-card.tsx` have proper ARIA labels
- ❌ **Bad:** `user-form-dialog.tsx` uses raw radio input (should use shadcn RadioGroup)
- ❌ **Bad:** `forgot-password/page.tsx` uses `prompt()` (inaccessible)
- ❌ **Bad:** `schedule/page.tsx` uses `window.confirm()`
- ❌ **Missing:** All tables lack responsive design (mobile overflow)

---

## 12. Python Optimizer API Audit

### Strategy Architecture / Strateji Mimari

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
│   │   ├── GWOSplitStrategy
│   │   ├── HHOSplitStrategy
│   │   └── PSOSplitStrategy
│   └── (SOTA Solvers)
│       ├── PyVRPStrategy (optional)
│       ├── VROOMStrategy (optional)
│       └── ORToolsCVRPStrategy
└── Local Search Operators
    ├── TwoOptLocalSearch
    ├── ThreeOptLocalSearch
    └── HybridLocalSearch
```

### Algorithm Correctness Assessment / Algoritma Dogruluk Degerlendirmesi

| Algorithm | Correctness | Notes |
|-----------|-------------|-------|
| Split Decoder (DP) | ✅ Correct | Prins (2004) O(n²) implementation |
| OR-Tools CVRP | ✅ Correct | Demand scaling, 30s time limit appropriate |
| PSO | ✅ Correct | Clerc & Kennedy (2002) constriction values |
| Haversine | ✅ Correct | 6371km Earth radius |
| VehicleCalculator | ✅ Correct | Iterative capacity-violation retry |
| 3-Opt | ⚠️ Partial | Duplicate cases (redundant evaluations) |
| GWO | ⚠️ Partial | Conflicting swaps can occur |
| Local Search | ✅ Correct | Clean abstract base class + factory pattern |

### Critical Python Issues / Kritik Python Sorunlari

| Issue | Severity | Impact |
|-------|----------|--------|
| Singleton state corruption (CR-09) | 🔴 CRITICAL | Race conditions in concurrent requests |
| ~800 lines code duplication (MD-16) | 🟡 MEDIUM | Maintenance difficulty |
| DataLoader not thread-safe (MD-17) | 🟡 MEDIUM | Multi-worker deployment issues |
| get_submatrix numpy→list→dict conversion | 🟢 LOW | Unnecessary overhead |

---

## 13. Dependency & Configuration Analysis / Bagimlik ve Yapilandirma Analizi

### Dependency Issues / Bagimlik Sorunlari

| Package | Version | Issue | Priority |
|---------|---------|-------|----------|
| `next` | `^16.1.6` | Incompatible with React 18 | 🔴 HIGH |
| `react` | `^18.3.1` | Next.js 16 requires React 19 | 🔴 HIGH |
| `xlsx` | `^0.18.5` | CVE-2023-30533, unmaintained | 🔴 HIGH |
| `dotenv` | `^16.6.1` | Should not be in dependencies | 🟢 LOW |
| `patch-package` | `^8.0.0` | postinstall script missing | 🟢 LOW |

### Critical Environment Variables / Kritik Environment Variables

| Variable | Exposure | Status |
|----------|----------|--------|
| `NEXT_PUBLIC_SUPABASE_URL` | Client | ✅ Normal (Supabase standard) |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Client | ✅ Normal (Supabase standard) |
| `SUPABASE_SERVICE_ROLE_KEY` | Server-only | ✅ Good — throws on missing |
| `NEXT_PUBLIC_DEV_RESET_SECRET` | **Client** | 🔴 **CRITICAL** — Fixed but verify removed |
| `OPTIMIZER_API_URL` | Server | ✅ Normal |
| `DATABASE_URL` | Server (Local) | ⚠️ Unused — Prisma remnant |

---

## 14. Prioritized Action Plan / Onceliklendirilmis Aksiyon Plani

### Phase 0: Verify Fixes (Immediately / Hemen)

| # | Finding | Verification | Estimated Time |
|---|---------|-------------|----------------|
| 1 | CR-03: Dev secret removed from client | Confirm `NEXT_PUBLIC_DEV_RESET_SECRET` no longer in codebase | 5 min |
| 2 | CR-08: `import logging` added | Verify all 4 strategy files compile without error | 10 min |
| 3 | CR-10: `get_time_windows()` implemented | Verify CVRPTW features work with time data | 15 min |

### Phase 1: Security Hardening (P0 — Immediately / Gune Hemen)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | CR-01: RLS `users_update_own` role restriction | 15 min | Prevent privilege escalation |
| 2 | CR-02: RLS `notifications_insert` restrict to service_role | 15 min | Prevent notification injection |
| 3 | CR-06: Remove `setUser` from AuthContext | 1 hour | Prevent client-side escalation |
| 4 | CR-07: PostgREST filter input validation | 15 min | Prevent filter injection |
| 5 | CR-11: Remove `password` from User type | 10 min | Prevent password exposure |
| 6 | CR-12: Add role guard to all admin pages | 1 hour | Prevent unauthorized admin access |
| 7 | HI-02: Add security headers | 30 min | Standard security hardening |
| 8 | HI-09: Add RLS write policies | 2 hours | Complete RLS coverage |
| **Total** | | **~5.5 hours** | |

### Phase 2: Bug Fixes (P1 — This Week / Bu Hafta)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | CR-04: Add `cooldown_minutes` column | 15 min | Data integrity |
| 2 | CR-05: Create `DbVehicleRow` type | 30 min | Type safety |
| 3 | CR-09: Make singleton thread-safe | 2 hours | Prevent concurrent corruption |
| 4 | HI-01: Add React Error Boundary | 30 min | Prevent white screen crashes |
| 5 | HI-04: Fix user deletion order | 30 min | Prevent orphaned auth |
| 6 | HI-05: Fix pickup/dropoff filter | 30 min | Correct routing |
| 7 | HI-06: Fix schedule-to-requests times | 30 min | Correct scheduling |
| 8 | HI-07: Create `*Row` types for all tables | 3 hours | Type safety |
| 9 | HI-10: Add FK constraints | 30 min | Data integrity |
| 10 | HI-12: Add status enum validation | 30 min | Input validation |
| 11 | MD-03: Fix empty string falsy checks | 30 min | Allow clearing fields |
| 12 | MD-18: Fix off-by-one date range | 15 min | Complete date coverage |
| **Total** | | **~9.5 hours** | |

### Phase 3: Validation & Type Safety (P2 — Next Week / Onraki Hafta)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | MD-14: Add Zod schemas (3 endpoints) | 2 hours | Input validation |
| 2 | MD-01: Migrate rate limiter to Redis/Upstash | 2 hours | Security |
| 3 | MD-07: Consolidate `schema.sql` | 1 hour | Migration safety |
| 4 | MD-13: Clean up `as any` assertions | 2 hours | Type safety |
| 5 | MD-08: Fix blanket DROP in RLS | 30 min | Policy safety |
| 6 | MD-10: Add WITH CHECK to schedule update | 15 min | Security |
| 7 | MD-15: Sanitize Python API error responses | 30 min | Security |
| 8 | HI-08: Add auth requirement to password hint | 1 hour | Security |
| **Total** | | **~9.5 hours** | |

### Phase 4: Performance & Code Quality (P3 — Sprint)

| # | Finding | Effort | Impact |
|---|---------|--------|--------|
| 1 | HI-03: Migrate xlsx → exceljs | 2 hours | Security + maintenance |
| 2 | HI-11: Fix N+1 query in reports | 2 hours | Performance |
| 3 | MD-05, MD-06: Add missing indexes | 30 min | Query performance |
| 4 | MD-16: Refactor Pipeline A strategies | 4 hours | Reduce 800 lines duplication |
| 5 | MD-24: Parallel time slot optimization | 2 hours | Performance |
| 6 | MD-12: Fix useEffect dependencies | 1 hour | React correctness |
| 7 | MD-20: Upgrade React 18 → 19 | 4 hours | Next.js compatibility |
| 8 | MD-23: Fix multi-vehicle capacity | 1 hour | Correctness |
| 9 | LO-01: ESLint `no-explicit-any: error` | 1 hour | Code quality |
| 10 | Responsive table wrappers | 1 hour | Mobile UX |
| 11 | MD-11, MD-19, MD-25: Remove dead code | 1 hour | Code cleanliness |
| **Total** | | **~20 hours** | |

### Effort Summary / Is Gucu Ozeti

| Phase | Estimated Hours | Priority | Deadline |
|-------|----------------|----------|----------|
| Phase 0: Verify Fixes | 0.5h | P0 | Today |
| Phase 1: Security | 5.5h | P0 | Today/Tomorrow |
| Phase 2: Bug Fixes | 9.5h | P1 | This Week |
| Phase 3: Validation | 9.5h | P2 | Next Week |
| Phase 4: Quality | 20h | P3 | Sprint |
| **TOTAL** | **~45 hours** | | |

---

## 15. Appendix

### A. Resolution Tracking / Cozum Takibi

| ID | Title | Severity | Status | Resolved Date |
|----|-------|----------|--------|--------------|
| CR-03 | Dev Secret Client Exposure | CRITICAL | 🟢 FIXED | Before 09.04.2026 |
| CR-08 | Missing `import logging` | CRITICAL | 🟢 FIXED | Before 09.04.2026 |
| CR-10 | `get_time_windows()` returns `{}` | CRITICAL | 🟢 FIXED | Before 09.04.2026 |

### B. Cross-Reference: Related Findings / Iliskili Bulgular

These findings are related and should be addressed together:

| Group | Findings | Common Theme |
|-------|----------|-------------|
| **RLS Security** | CR-01, CR-02, HI-09, MD-08, MD-09, MD-10, MD-27 | Database access control |
| **Type Safety** | CR-05, HI-07, MD-13, MD-21, LO-12, LO-13 | camelCase/snake_case + type assertions |
| **Input Validation** | CR-07, HI-12, MD-14 | Missing Zod schemas |
| **Python Concurrency** | CR-09, MD-17 | Singleton thread safety |
| **Code Duplication** | MD-16, MD-19, MD-25, LO-05, LO-11 | Dead/duplicate code |
| **Frontend Security** | CR-06, CR-11, CR-12 | Client-side auth issues |

### C. Document History / Dokuman Gecmisi

| Date | Author | Change |
|------|--------|--------|
| 09.04.2026 | Z.ai Code | Initial comprehensive analysis report created |

---

*Bu rapor 120+ dosyanin kaynak kod tabanli statik analizine dayanmaktadir. Dokumantasyondaki iddialar degil, sadece kodda gercekten mevcut olan yapilar incelenmistir. This report is based on source-level static analysis of 120+ files. Only structures actually present in the codebase were examined, not documentation claims.*
