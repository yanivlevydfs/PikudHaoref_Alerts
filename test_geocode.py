import asyncio
import json
from app.services.geocode_service import GeocodeService

async def main():
    service = GeocodeService()
    await service.start()
    res = await service.get_coordinates(["תל אביב - מרכז העיר", "רמת גן"])
    with open("test_out.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False)
    await service.close()

if __name__ == "__main__":
    asyncio.run(main())
