import json
FAST = dict(K=10, Lmax=100, use_or3=True)          # chosen on pr299/d493/u724 (not benchmark instances)
MAIN = ["rd100", "eil101", "lin105", "pr136", "pr152", "a280", "lin318", "pr439", "rat783", "pr1002"]
SEEDS = [0, 1, 2, 3, 4]
main = []
for inst in MAIN:
    for s in SEEDS:
        main.append(dict(arm="ils_fast", inst=inst, seed=s, T=30, params=FAST))
        if inst not in ("rat783", "pr1002"):   # repo LS cannot return a local optimum within budget there
            main.append(dict(arm="repo_ils", inst=inst, seed=s, T=30, params={}))
        main.append(dict(arm="lkh", inst=inst, seed=s, T=0, params=dict(runs=10)))
json.dump(main, open("tasks_main.json", "w"), indent=0)

atsp = [dict(arm="ils_fast", inst="ft53", seed=s, T=10, params=FAST) for s in range(10)]
atsp += [dict(arm="lkh_atsp_native", inst="ft53", seed=s, T=0, params=dict(runs=10)) for s in range(3)]
atsp += [dict(arm="lkh_atsp_2n", inst="ft53", seed=0, T=0, params=dict(runs=10))]
json.dump(atsp, open("tasks_atsp.json", "w"), indent=0)

PX = dict(FAST, m=8)
gpx = []
for inst in ["pr439", "rat783", "pr1002", "pcb1173"]:
    for s in SEEDS:
        gpx.append(dict(arm="px_on", inst=inst, seed=s, T=30, params=PX))
        gpx.append(dict(arm="px_off", inst=inst, seed=s, T=30, params=PX))
        gpx.append(dict(arm="ils_fast", inst=inst, seed=s, T=30, params=FAST))
json.dump(gpx, open("tasks_gpx.json", "w"), indent=0)
print(len(main), len(atsp), len(gpx))
