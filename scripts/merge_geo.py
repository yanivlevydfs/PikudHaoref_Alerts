import json
import os

def merge_geo_data():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(current_dir)
    cities_path = os.path.join(project_root, "app", "resources", "cities.json")
    polygons_path = os.path.join(project_root, "app", "resources", "polygons.json")
    output_path = os.path.join(project_root, "app", "static", "locations_polygons.json")

    print(f"Project root: {project_root}")
    print(f"Reading {cities_path}...")
    with open(cities_path, "r", encoding="utf-8") as f:
        cities = json.load(f)

    print(f"Reading {polygons_path}...")
    with open(polygons_path, "r", encoding="utf-8") as f:
        polygons = json.load(f)

    # Simplified mapping: Hebrew Name -> Coordinates array
    # Note: polygons.json has coordinates as [lat, lng]. 
    # Leaflet GeoJSON expects [lng, lat] for coordinates, but we can also handle it in JS.
    # Let's check the format in polygons.json again. 
    # Example: "4":[[29.5721,34.9776],...] -> [Lat, Lng]
    
    mapping = {}
    for city in cities:
        city_name = city.get("name")
        city_id = str(city.get("id"))
        
        if city_id in polygons:
            # Store it
            # We'll normalize to [Lng, Lat] for GeoJSON compatibility if needed, 
            # OR keep it as is and handle it in script.js. 
            # I'll keep it as is [Lat, Lng] but mark it.
            mapping[city_name] = {
                "id": city_id,
                "polygon": polygons[city_id]
            }

    print(f"Mapped {len(mapping)} cities.")
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(mapping, f, ensure_ascii=False)
    
    print(f"Saved to {output_path}")

if __name__ == "__main__":
    merge_geo_data()
