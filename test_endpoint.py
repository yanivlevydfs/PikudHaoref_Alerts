from fastapi.testclient import TestClient
from app.main import app
import json

def test_geocode_endpoint():
    with TestClient(app) as client:
        cities = ["שמואל", "חוות נווה צוף", "חוות נוף אב\"י", "צוף"]
        response = client.post("/api/geocode", json={"cities": cities})
        with open("test_endpoint_out.txt", "w", encoding="utf-8") as f:
            f.write(f"Status Code: {response.status_code}\n")
            f.write(json.dumps(response.json(), ensure_ascii=False, indent=2))

if __name__ == "__main__":
    test_geocode_endpoint()
