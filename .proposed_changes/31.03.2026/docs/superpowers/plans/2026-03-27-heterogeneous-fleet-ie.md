# Heterogeneous Fleet Implementation Plan (IE Model)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement a heterogeneous fleet support system for UniRide with Advanced IE Resource Allocation (Standard Vehicles, Directional Blocking, and Slack Time optimization).

---

### Task 1: Backend Schemas & Models
- [ ] **Step 1: Update `schemas.py` with `VehicleConfig` (inc. 15m cooldown) and `OptimizationRequest`**
- [ ] **Step 2: Update Frontend types in `src/types/index.ts`**
- [ ] **Step 3: Commit**

### Task 2: Resource Engine (IE Logic)
- [ ] **Step 1: Implement "Standard Vehicle" Benchmarking in `resource_profiler.py`**
- [ ] **Step 2: Implement Directional Blocking Logic**
- [ ] **Step 3: Implement Slack Time Demand Leveling Suggestions**
- [ ] **Step 4: Run tests: `pytest UniRide/optimizer_api/tests/test_resource_profiler.py`**
- [ ] **Step 5: Commit**

### Task 3: Solver Integration (Heterogeneous)
- [ ] **Step 1: Update `SplitDecoderV2` for per-vehicle capacities**
- [ ] **Step 2: Update VROOM and PyVRP Strategy wrappers**
- [ ] **Step 3: Verify with `test_strategies.py`**
- [ ] **Step 4: Commit**

### Task 4: Frontend IE Dashboard
- [ ] **Step 1: Implement `ResourceHistogram.tsx` (Stacked Bars + Tooltips)**
- [ ] **Step 2: Implement Aligned Resource Tracks (Gantt-like)**
- [ ] **Step 3: Commit**

### Task 5: Interactive Sandbox & Loop
- [ ] **Step 1: Implement "Add/Change Vehicle" in Sandbox UI**
- [ ] **Step 2: Implement "Shift Student" action and Re-optimization trigger**
- [ ] **Step 3: Manual Walkthrough Verification**
- [ ] **Step 4: Commit**
