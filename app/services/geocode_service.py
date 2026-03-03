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
        cache_file: str = CACHE_FILE,
        timeout: float = 10.0,
        max_concurrency: int = 2,
        min_delay_seconds: float = 2.0,  # Nominatim is strict; 2.0s to be extra safe
        user_agent: str = "PikudHaoref_Alerts/1.2 (contact: admin@admin.com)",
    ):
        self.cache_file = cache_file
        self.timeout = timeout
        self.user_agent = user_agent

        self.cache: Dict[str, Any] = {}
        self._in_progress: Dict[str, asyncio.Task] = {}

        self._cache_dirty: bool = False
        self._cache_lock = asyncio.Lock()  # protects cache + dirty flag + save

        self._semaphore = asyncio.Semaphore(max_concurrency)

        # Global throttling across *all* outgoing requests.
        self._rate_lock = asyncio.Lock()
        self._min_delay = float(min_delay_seconds)
        self._last_request_ts: float = 0.0

        self._client: Optional[httpx.AsyncClient] = None

        # Ensure db directory exists early
        os.makedirs(os.path.dirname(self.cache_file), exist_ok=True)
        self._load_cache()

    # ----------------------------
    # Lifecycle (recommended)
    # ----------------------------
    async def start(self) -> None:
        """Create the shared AsyncClient (connection pooling)."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
            logger.info("[GEO] httpx.AsyncClient started.")

    async def close(self) -> None:
        """Close the shared AsyncClient."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
            logger.info("[GEO] httpx.AsyncClient closed.")

    # ----------------------------
    # Cache I/O
    # ----------------------------
    def _load_cache(self) -> None:
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                
                logger.info("[GEO] Loaded %d cached coordinates from disk.", len(self.cache))
            except Exception as e:
                logger.error("[GEO] Failed to load geo cache: %s", e)
                self.cache = {}
        else:
            self.cache = {}

    def _atomic_write_json(self, path: str, data: Dict[str, Any]) -> None:
        """Atomic write to avoid corrupted cache files on crash."""
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            # Faster than pretty indent, still UTF-8 safe
            json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        os.replace(tmp_path, path)

    async def _save_cache_if_dirty(self) -> None:
        async with self._cache_lock:
            if not self._cache_dirty:
                return
            try:
                # Copy to avoid holding lock during disk write if you want; keeping it simple+safe.
                snapshot = dict(self.cache)
                self._atomic_write_json(self.cache_file, snapshot)
                self._cache_dirty = False
                logger.info("[GEO] Saved geo cache (%d entries).", len(snapshot))
            except Exception as e:
                logger.error("[GEO] Failed to save geo cache: %s", e)

    # ----------------------------
    # Public API
    # ----------------------------
    async def get_coordinates(self, cities: List[str]) -> Dict[str, Any]:
        """
        Returns a mapping: city -> GeoJSON OR "NOT_FOUND"
        Uses cache first; fetches missing entries concurrently (bounded + rate-limited).
        """
        if not cities:
            return {}

        await self.start()  # ensure client exists

        # Deduplicate while preserving order (important if callers expect stable behavior)
        cities_unique = list(dict.fromkeys(cities))

        results: Dict[str, Any] = {}
        missing: List[str] = []

        # Fast cache hits
        async with self._cache_lock:
            for city in cities_unique:
                if city in self.cache:
                    results[city] = self.cache[city]
                else:
                    missing.append(city)

        if not missing:
            return results

        # Create or reuse tasks per missing city
        fetch_pairs: List[Tuple[str, asyncio.Task]] = []
        for city in missing:
            existing = self._in_progress.get(city)
            if existing is not None:
                fetch_pairs.append((city, existing))
            else:
                task = asyncio.create_task(self._fetch_and_cache(city))
                self._in_progress[city] = task
                fetch_pairs.append((city, task))

        # Await all concurrently (not sequentially)
        tasks = [t for _, t in fetch_pairs]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for (city, _), r in zip(fetch_pairs, task_results):
            if isinstance(r, Exception):
                logger.error("[GEO] Fetch failed for %s: %s", city, r)
                results[city] = "ERROR"
            else:
                results[city] = r

        # Save once (and only if dirty)
        await self._save_cache_if_dirty()
        return results

    # ----------------------------
    # Internals
    # ----------------------------
    async def _fetch_and_cache(self, city: str) -> Any:
        """
        Fetch from Nominatim and store in cache. Always clears _in_progress entry.
        """
        try:
            geo_data = await self._fetch_from_nominatim(city)
            async with self._cache_lock:
                self.cache[city] = geo_data
                self._cache_dirty = True
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
