from staticmap import StaticMap, CircleMarker, Line
import sys

def create_static_map():
    # Initialize map
    m = StaticMap(1000, 600, url_template='https://tile.openstreetmap.org/{z}/{x}/{y}.png')
    
    # Coordinates (Lon, Lat for staticmap - opposite of Leaflet)
    # D.Kampus: [41.001167, 29.177333] -> Lon, Lat = 29.177333, 41.001167
    nodes = {
        "D.Kampus": {"coords": (29.177333, 41.001167), "color": "red", "size": 12},
        "Sw1": {"coords": (29.331389, 40.825833), "color": "blue", "size": 8},
        "Sw2": {"coords": (29.105583, 40.953694), "color": "blue", "size": 8},
        "Sw7": {"coords": (29.109806, 40.948944), "color": "blue", "size": 8},
        "Sw6": {"coords": (29.066861, 40.999944), "color": "blue", "size": 8}
    }
    
    # Route sequence
    route_names = ["D.Kampus", "Sw1", "Sw2", "Sw7", "Sw6", "D.Kampus"]
    route_coords = [nodes[n]["coords"] for n in route_names]
    
    # Add Polyline
    m.add_line(Line(route_coords, 'blue', 3))
    
    # Add Markers
    for name, data in nodes.items():
        marker = CircleMarker(data["coords"], data["color"], data["size"])
        m.add_marker(marker)
        
    try:
        # Render image
        image = m.render()
        image.save('c:/Users/yektakayman/Desktop/AiCode/FirebaseUniRide/UniRide/Fig3c_StaticGeographicMap.jpg')
        print("Successfully generated Fig3c_StaticGeographicMap.jpg")
    except Exception as e:
        print(f"Error generating map: {e}")
        sys.exit(1)

if __name__ == "__main__":
    create_static_map()
