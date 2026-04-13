import requests
import json

url = "http://127.0.0.1:8000/api/v1/optimize"

payload = {
  "algorithm": "ortools_cvrp",
  "students": [
    {"id": "Sw1", "lat": 40.825, "lng": 29.331, "type": "Sw"},
    {"id": "Sw2", "lat": 40.953, "lng": 29.105, "type": "Sw"},
    {"id": "So2", "lat": 40.999, "lng": 29.066, "type": "So"}
  ],
  "depot": {"id": "D.Kampus", "lat": 41.001, "lng": 29.177, "type": "D"},
  "max_travel_time": 120,
  "sw_capacity": 4,
  "so_capacity": 5
}

headers = {"Content-Type": "application/json"}

print(f"Sending OR-Tools Full-Parity request to {url}...")
try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(json.dumps(response.json(), indent=2))
except Exception as e:
    print(f"Error: {e}")
