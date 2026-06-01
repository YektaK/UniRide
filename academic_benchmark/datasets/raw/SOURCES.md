# Academic Benchmark Raw Dataset Sources

Downloaded on 2026-06-01 for UniRide academic benchmark validation.

## CVRPLIB CVRP

Source page: <https://galgos.inf.puc-rio.br/cvrplib/en/instances>

Downloaded files:
- `cvrplib_selected/*.vrp`: selected small Augerat Set A/B CVRP instances.
- `cvrplib_selected_solutions/*.sol`: matching CVRPLIB best-known route/value files from the site's `instanceSolution` endpoint.

Selected starter instances:
- `A-n32-k5`, `A-n33-k5`, `A-n33-k6`, `A-n34-k5`
- `B-n31-k5`, `B-n34-k5`, `B-n35-k5`, `B-n38-k6`

## SINTEF Solomon VRPTW 100 Customers

Source page: <https://www.sintef.no/projectweb/top/vrptw/100-customers/>

Downloaded files:
- `solomon_100/In/*.txt`: 56 Solomon 100-customer VRPTW instance definitions from SINTEF's `solomon-100.zip`.
- `solomon_100_solutions/*.txt`: detailed best-known solution files linked from the SINTEF 100-customer table.

SINTEF notes that the reported VRPTW objective is hierarchical: first minimize vehicle count, then total distance, using double precision and two-decimal rounded total distance.

## Import Command

```powershell
python -m academic_benchmark.cvrplib_manager scan academic_benchmark\datasets\raw\cvrplib_selected academic_benchmark\datasets\raw\solomon_100
python -m academic_benchmark.cvrplib_manager import academic_benchmark\datasets\raw\cvrplib_selected academic_benchmark\datasets\raw\solomon_100
```
