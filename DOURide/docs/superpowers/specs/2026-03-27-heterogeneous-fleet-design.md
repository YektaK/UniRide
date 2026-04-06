# Design Doc: Heterogeneous Fleet & Holistic Routing Support

**Date:** 2026-03-27
**Status:** Approved
**Topic:** Scaling UniRide to support mixed vehicle types with daily holistic optimization and ad-hoc request handling.

## 1. Executive Summary
The UniRide VRP system currently assumes a homogeneous fleet with fixed capacities. To support real-world operation where vehicle types (minibus, bus, van) vary, we are introducing a dynamic fleet model. This design also addresses "peak hour scarcity" through a holistic daily planning approach and supports dynamic ad-hoc requests via a re-optimization window.

## 2. Goals & IE Principles
- **Goal**: Optimize route assignments using a mixed fleet from Supabase.
- **Goal**: **Resource Leveling**: Minimize peak hour vehicle requirements using Slack Time.
- **Goal**: **Standard Vehicle Benchmarking**: Determine fleet needs in "Standard Units" (4 Sw + 5 So).
- **Constraint**: **Directional Blocking**: Vehicles are blocked for the duration of a trip (e.g. 10:00 Pickup blocks the vehicle for an 11:00 Return).
- **Constraint**: **Slack Window**: Students can be shifted (e.g. ±60 mins) to improve efficiency.

## 3. Architecture & Data Flow

### 3.1. Data Models
- **Vehicles (Supabase)**: Use existing `wheelchair_capacity` and `seating_capacity`.
- **Ride Requests (Supabase)**: Use `type` (scheduled/adhoc) and `slack_allowance`.
- **OptimizationRequest (API)**: Expand schema to accept `vehicles: List[VehicleConfig]` and `allow_time_shift: bool`.

### 3.2. Advanced Resource Allocation (The IE Engine)
The system operates in two modes:
1.  **Ideal (Benchmark) Mode**:
    - Ignores available vehicles.
    - Uses "Standard Units" to find the theoretical minimum fleet for each slot.
    - Generates a **Resource Histogram** showing Sw/So demand breakdown.
2.  **Fine-tune (Sandbox) Mode**:
    - Admin provides specific available vehicles.
    - Admin manually shifts "High Cost" students or adds "Temporary Resource Blocks".
    - System re-optimizes routes based on these manual constraints.

### 3.3. Directional Flow Logic
- **Pickup Trips**: 
    - Event: Arrival at school at Time T.
    - Resource Block: [T - Max_Tour_Duration, T].
- **Return Trips**:
    - Event: Departure from school at Time T.
    - Resource Block: [T, T + Max_Tour_Duration].
- **Conflict Rule**: A physical vehicle cannot occupy two overlapping blocks.

## 4. UI/UX: The IE Dashboard
- **Aligned Histogram**: Stacked bars (Pickup/Return) aligned with Resource Gantt tracks.
- **Sensitivity Data**: Tooltips showing Sw vs So counts per hour.
- **Bottleneck Indicators**: Visual flags for "Infeasible" or "Low Efficiency" slots.

### 4.1. Local API Changes (`schemas.py`)
Add `VehicleConfig` model and update `OptimizationRequest`.

### 4.2. Strategy Updates
- **VROOM/PyVRP**: Loop through the `vehicles` list in the request to define multiple vehicle types in the solver engine.
- **Genetic/Meta-heuristic**: Update `SplitDecoder` calls to use the heterogeneous vehicle assignment logic.

### 4.3. Frontend Updates
- **Vehicle Planning Page**: Update to fetch available vehicles from Supabase and pass them to the `calculate-vehicles` API.
- **Ad-hoc List**: Add a view for "Pending Ad-hoc Requests" for the current day.

## 5. Success Criteria
- [ ] System successfully assigns a mix of vehicle types to a single optimization result.
- [ ] Large vehicles are reserved for peak hours based on daily demand profiling.
- [ ] Ad-hoc requests are successfully integrated into routes 2 hours before departure.
- [ ] Sw and So capacities are strictly enforced.

## 6. Future Considerations
- Real-time driver GPS integration for even more dynamic (minutes-before) adjustments.
- Cost-based optimization (Fuel, Worker hours) alongside distance minimization.
