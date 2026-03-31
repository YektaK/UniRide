# Verified Code Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Integrate the advanced, verified code version from `.proposed_changes/31.03.2026` into the active `UniRide` codebase, ensuring robust migration across the Database, Python Optimizer API, and Next.js Web Application. 

**Architecture:** The migration is divided cleanly into layers. We will perform file replacements and additions task-by-task, committing each subset individually to maintain a clean git history. The flow will be Database -> Python API Backend -> Next.js Frontend -> Documentation.

**Tech Stack:** Supabase (PostgreSQL), Python (FastAPI, pytest), Next.js (TypeScript, React).

## User Review Required

> [!CAUTION]
> Applying this plan will override existing `src` and `optimizer_api` files with the versions found in `.proposed_changes/31.03.2026`. Please review the tasks to ensure you are ready to overwrite current files.

## Proposed Changes

---

### Task 1: Supabase Database Updates

**Files:**
- [NEW] `supabase/migrations/20260329_add_route_plans.sql`
- [NEW] `supabase/migrations/20260329_add_sandbox_scenarios.sql`

- [ ] **Step 1: Copy migration files**
```bash
cp UniRide/.proposed_changes/31.03.2026/supabase/migrations/20260329_add_route_plans.sql UniRide/supabase/migrations/
cp UniRide/.proposed_changes/31.03.2026/supabase/migrations/20260329_add_sandbox_scenarios.sql UniRide/supabase/migrations/
```

- [ ] **Step 2: Commit**
```bash
git add UniRide/supabase/migrations/
git commit -m "chore(db): add route plans and sandbox migrations"
```

### Task 2: Python Optimizer API

**Files:**
- [MODIFY] `optimizer_api/main.py`
- [MODIFY] `optimizer_api/models/schemas.py`
- [MODIFY] `optimizer_api/strategies/*.py`
- [MODIFY] `optimizer_api/utils/*.py`

- [ ] **Step 1: Sync Python core files**
```bash
cp -r UniRide/.proposed_changes/31.03.2026/optimizer_api/main.py UniRide/optimizer_api/
cp -r UniRide/.proposed_changes/31.03.2026/optimizer_api/models/schemas.py UniRide/optimizer_api/models/
cp -r UniRide/.proposed_changes/31.03.2026/optimizer_api/strategies/* UniRide/optimizer_api/strategies/
cp -r UniRide/.proposed_changes/31.03.2026/optimizer_api/utils/* UniRide/optimizer_api/utils/
```

- [ ] **Step 2: Commit**
```bash
git add UniRide/optimizer_api/
git commit -m "feat(api): integrate updated optimizer strategies and utilities"
```

### Task 3: Python Optimizer Tests & Config

**Files:**
- [NEW] `optimizer_api/tests/*`
- [NEW] `optimizer_api/conftest.py`
- [NEW] `optimizer_api/README_TESTS.md`
- [MODIFY] `optimizer_api/test_*.py`

- [ ] **Step 1: Sync tests**
```bash
cp -r UniRide/.proposed_changes/31.03.2026/optimizer_api/tests UniRide/optimizer_api/
cp UniRide/.proposed_changes/31.03.2026/optimizer_api/conftest.py UniRide/optimizer_api/
cp UniRide/.proposed_changes/31.03.2026/optimizer_api/README_TESTS.md UniRide/optimizer_api/
cp -r UniRide/.proposed_changes/31.03.2026/optimizer_api/test_*.py UniRide/optimizer_api/
```

- [ ] **Step 2: Run tests (optional)**
```bash
cd UniRide/optimizer_api && pytest
```

- [ ] **Step 3: Commit**
```bash
git add UniRide/optimizer_api/
git commit -m "test(api): sync optimizer test suite"
```

### Task 4: Next.js Types & Services

**Files:**
- [MODIFY] `src/types/index.ts`
- [MODIFY] `src/types/ie-resource.ts`
- [MODIFY] `src/lib/admin-api.ts`
- [MODIFY] `src/lib/algorithm-constants.ts`
- [MODIFY] `src/services/optimizer-service.ts`
- [MODIFY] `src/services/route-plans.ts`
- [MODIFY] `src/services/sandbox-api.ts`

- [ ] **Step 1: Sync types and backend services**
```bash
cp UniRide/.proposed_changes/31.03.2026/src/types/index.ts UniRide/src/types/
cp UniRide/.proposed_changes/31.03.2026/src/types/ie-resource.ts UniRide/src/types/
cp UniRide/.proposed_changes/31.03.2026/src/lib/admin-api.ts UniRide/src/lib/
cp UniRide/.proposed_changes/31.03.2026/src/lib/algorithm-constants.ts UniRide/src/lib/
cp UniRide/.proposed_changes/31.03.2026/src/services/optimizer-service.ts UniRide/src/services/
cp UniRide/.proposed_changes/31.03.2026/src/services/route-plans.ts UniRide/src/services/
cp UniRide/.proposed_changes/31.03.2026/src/services/sandbox-api.ts UniRide/src/services/
```

- [ ] **Step 2: Commit**
```bash
git add UniRide/src/types/ UniRide/src/lib/ UniRide/src/services/
git commit -m "feat(webapp): sync resource types and admin api services"
```

### Task 5: Next.js App Routes & Components

**Files:**
- [MODIFY] `src/app/api/calculate-vehicles/route.ts`
- [MODIFY] `src/app/api/optimize-route/route.ts`
- [MODIFY] `src/app/api/route-plans/route.ts`
- [MODIFY] `src/app/api/sandbox/route.ts`
- [MODIFY] `src/app/(app)/admin/compare/page.tsx`
- [MODIFY] `src/app/(app)/admin/sandbox/page.tsx`
- [MODIFY] `src/components/admin/*.tsx`

- [ ] **Step 1: Sync Next.js API Routes**
```bash
cp -r UniRide/.proposed_changes/31.03.2026/src/app/api/* UniRide/src/app/api/
```

- [ ] **Step 2: Sync Pages & Components**
```bash
cp -r "UniRide/.proposed_changes/31.03.2026/src/app/(app)/admin/*" "UniRide/src/app/(app)/admin/"
cp -r UniRide/.proposed_changes/31.03.2026/src/components/admin/* UniRide/src/components/admin/
```

- [ ] **Step 3: Commit**
```bash
git add UniRide/src/app/ UniRide/src/components/
git commit -m "feat(webapp): sync admin sandbox and routing components"
```

### Task 6: Documentation & Meta Files

**Files:**
- [NEW] `docs/CVRPTW_Database_Integration_Plan.md`
- [NEW] `docs/DEPLOYMENT_GUIDE.md`
- [MODIFY] `docs/*.md`
- [MODIFY] `IMPLEMENTATION_STATUS.md`
- [MODIFY] `.ai-handover.md`

- [ ] **Step 1: Sync Docs**
```bash
cp -r UniRide/.proposed_changes/31.03.2026/docs/* UniRide/docs/
cp UniRide/.proposed_changes/31.03.2026/IMPLEMENTATION_STATUS.md UniRide/
cp UniRide/.proposed_changes/31.03.2026/.ai-handover.md UniRide/
```

- [ ] **Step 2: Build verification (Optional)**
```bash
cd UniRide && npm run build
```

- [ ] **Step 3: Final Commit**
```bash
git add UniRide/docs/ UniRide/IMPLEMENTATION_STATUS.md UniRide/.ai-handover.md
git commit -m "docs: sync updated implementation plans and statuses"
```

---

## Open Questions
- Do you want to review the python pytest coverage before proceeding? 
- Should we branch off your current code first before overwriting, simply by running `git checkout -b feature/proposed-changes-sync`?

## Verification Plan

### Automated Tests
- Run Python optimizer API test suite (`cd UniRide/optimizer_api && pytest`).
- Verify Next.js types by compiling TypeScript (`npx tsc --noEmit`).

### Manual Verification
- Testing local environment UI locally `npm run dev`.
- Ensure new features under `/admin/sandbox` and `/admin/compare` route appropriately in your UI.
