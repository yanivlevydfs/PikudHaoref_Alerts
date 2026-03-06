import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx

logger = logging.getLogger("pikudhaoref_app.geocode")

CACHE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "db", "geo_cache.json")


class GeocodeService:
    """
    Production-oriented geocoding service with:
      - in-memory + persistent JSON cache
      - deduplication of concurrent requests per-city
      - connection pooling via a persistent httpx.AsyncClient
      - bounded concurrency
      - global rate limiting (polite to Nominatim)
      - atomic cache saves + save-only-when-dirty
      - no print() tracing (uses logger)
    """

    def __init__(
        self,
        timeout: float = 10.0,
        max_concurrency: int = 2,
        min_delay_seconds: float = 2.0,  # Nominatim is strict; 2.0s to be extra safe
        user_agent: str = "PikudHaoref_Alerts/1.2 (contact: admin@admin.com)",
    ):
        self.timeout = timeout
        self.user_agent = user_agent
        self.max_concurrency = max_concurrency

        self._in_progress: Dict[str, asyncio.Task] = {}
        
        # Async objects lazily initialized to safely attach to the calling thread's event loop
        self._semaphore:  Optional[asyncio.Semaphore] = None
        self._rate_lock:  Optional[asyncio.Lock] = None

        self._min_delay = float(min_delay_seconds)
        self._last_request_ts: float = 0.0

        self._client: Optional[httpx.AsyncClient] = None

    # ----------------------------
    # Lifecycle (recommended)
    # ----------------------------
    async def start(self) -> None:
        """Create the shared AsyncClient and thread-bound locks."""
        if self._rate_lock is None:
            self._rate_lock = asyncio.Lock()
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrency)

        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("[GEO] httpx.AsyncClient and EventLoop Locks started.")

    async def close(self) -> None:
        """Close the shared AsyncClient."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("[GEO] httpx.AsyncClient closed.")

    # ----------------------------
    # Public API
    # ----------------------------
    async def get_coordinates(self, cities: List[str]) -> Dict[str, Any]:
        """
        Returns a mapping: city -> GeoJSON OR "NOT_FOUND"
        Checks the SQLite database first; fetches missing entries concurrently.
        """
        if not cities:
            return {}

        await self.start()

        # Local import to avoid circular dependencies
        from app.db.database import get_geolocation_by_city

        cities_unique = list(dict.fromkeys(cities))
        results: Dict[str, Any] = {}
        missing: List[str] = []

        # Fast Database hits
        for city in cities_unique:
            db_hit = get_geolocation_by_city(city)
            if db_hit is not None:
                results[city] = db_hit
            else:
                missing.append(city)

        if not missing:
            return results

        # Create or reuse concurrent tasks per missing city
        fetch_pairs: List[Tuple[str, asyncio.Task]] = []
        for city in missing:
            existing = self._in_progress.get(city)
            if existing is not None:
                fetch_pairs.append((city, existing))
            else:
                task = asyncio.create_task(self._fetch_and_cache(city))
                self._in_progress[city] = task
                fetch_pairs.append((city, task))

        tasks = [t for _, t in fetch_pairs]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for (city, _), r in zip(fetch_pairs, task_results):
            if isinstance(r, Exception):
                logger.error("[GEO] Fetch failed for %s: %s", city, r)
                results[city] = "ERROR"
            else:
                results[city] = r

        return results

    # ----------------------------
    # Internals
    # ----------------------------
    async def _fetch_and_cache(self, city: str) -> Any:
        """
        Fetch from Nominatim and store directly in the SQLite database.
        """
        from app.db.database import save_geolocation
        
        try:
            geo_data = await self._fetch_from_nominatim(city)
            is_found = geo_data != "NOT_FOUND"
            
            # Save strictly to the DB without local state mutation
            save_geolocation(city, is_found, geo_data if is_found else None)
                
            if is_found:
                logger.info(f"[GEO BG] ✅ SUCCESS: GeoLocation found for '{city}'")
            else:
                logger.warning(f"[GEO BG] ❌ FAILED: No GeoLocation found for '{city}'")
                
            return geo_data
        finally:
            self._in_progress.pop(city, None)

    def _normalize_city(self, city: str) -> str:
        """
        Pre-process city string like the frontend did (kept from your logic, just organized).
        """
        search_city = city.split("-")[0].strip()

        if (
            "אזור תעשייה" in search_city
            or "פארק תעשיות" in search_city
            or search_city.startswith("רחוב")
        ):
            search_city = city.replace("-", " ").strip()

        search_city = (
            search_city.replace("רחוב ", "")
            .replace("פארק ", "")
            .replace('בי"ס', "")
            .strip()
        )

        # Keep specific שדרות
        if search_city.startswith("שדרות ") and not any(
            x in search_city for x in ["השביעית", "הציונות", "ירושלים"]
        ):
            search_city = search_city.replace("שדרות ", "").strip()

        return search_city

    async def _throttle(self) -> None:
        """
        Enforces a minimum delay between outgoing requests (global).
        This is more reliable than sleeping inside each task.
        """
        async with self._rate_lock:
            now = time.monotonic()
            wait = (self._last_request_ts + self._min_delay) - now
            if wait > 0:
                await asyncio.sleep(wait)
            self._last_request_ts = time.monotonic()

    async def _fetch_from_nominatim(self, city: str) -> Any:
        """
        Returns GeoJSON if found, else "NOT_FOUND".
        """
        if self._client is None:
            # Safety (start() should have created it)
            await self.start()
        assert self._client is not None

        search_city = self._normalize_city(city)

        base_url = "https://nominatim.openstreetmap.org/search"
        params = {
            "format": "json",
            "polygon_geojson": "1",
            "limit": "1",
            "countrycodes": "il",
            "accept-language": "he",
            "addressdetails": "1",
            "q": search_city,
        }
        headers = {"User-Agent": self.user_agent}

        async with self._semaphore:
            max_retries = 3
            current_delay = 1.0

            for attempt in range(max_retries):
                try:
                    # Request 1
                    await self._throttle()
                    resp = await self._client.get(base_url, params=params, headers=headers)
                    resp.raise_for_status()
                    data = resp.json()

                    # Retry with last word if complex name fails
                    if not data and len(search_city.split()) > 1:
                        last_word = search_city.split()[-1]
                        params["q"] = last_word

                        await self._throttle()
                        resp = await self._client.get(base_url, params=params, headers=headers)
                        resp.raise_for_status()
                        data = resp.json()

                    if data:
                        result = data[0]
                        geojson = result.get("geojson")
                        if geojson:
                            return geojson

                        lat = result.get("lat")
                        lon = result.get("lon")
                        if lat is not None and lon is not None:
                            try:
                                return {
                                    "type": "Point",
                                    "coordinates": [float(lon), float(lat)],
                                }
                            except ValueError:
                                pass

                    return "NOT_FOUND"

                except httpx.HTTPStatusError as e:
                    if e.response.status_code == 429 and attempt < max_retries - 1:
                        # Apply global penalty to all concurrent/future requests
                        async with self._rate_lock:
                            self._last_request_ts = time.monotonic() + 5.0
                            
                        logger.warning("[GEO] Nominatim 429 Too Many Requests for %s. Backing off for %.1f seconds...", city, current_delay)
                        await asyncio.sleep(current_delay)
                        current_delay *= 2
                        continue
                        
                    logger.error("[GEO] Nominatim HTTP error for %s: %s", city, e)
                    raise
                except httpx.RequestError as e:
                    logger.error("[GEO] Nominatim request error for %s: %s", city, e)
                    raise
                except Exception as e:
                    logger.error("[GEO] Nominatim unexpected error for %s: %s", city, e)
                    raise


# Global instance
geocode_service = GeocodeService()
