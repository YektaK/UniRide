import requests
import json

payload = {
    "algorithm": "genetic_algorithm",
    "clustering_algorithm": "sweep",
    "students": [
        {
            "id": "student_1",
            "name": "Ahmet",
            "location_code": "Mh11",
            "disability_type": "Sw"
        },
        {
            "id": "student_2",
            "name": "Mehmet",
            "location_code": "Mh12",
            "disability_type": "So"
        },
        {
            "id": "student_3",
            "name": "Ayşe",
            "location_code": "Mh13",
            "disability_type": "So"
        }
    ],
    "depot": {"id": "D.Kampus", "lat": 40.8410, "lng": 31.1478, "type": "depot"},
    "max_travel_time": 120,
    "sw_capacity": 4,
    "so_capacity": 5
}

algorithms = ["kmeans", "fuzzy_cmeans", "k_medoids", "sweep", "clarke_wright"]

for algo in algorithms:
    print(f"Testing {algo}...")
    payload["clustering_algorithm"] = algo
    try:
        response = requests.post("http://127.0.0.1:8001/api/v1/optimize", json=payload)
        if response.status_code == 200:
            print(f"✅ {algo} SUCCESS! Vehicles: {response.json().get('total_vehicles')}")
        else:
            print(f"❌ {algo} FAILED! Status: {response.status_code}")
            try:
                print(f"Response: {response.json()}")
            except:
                print(f"Response: {response.text}")
    except Exception as e:
        print(f"❌ {algo} ERROR: {e}")
