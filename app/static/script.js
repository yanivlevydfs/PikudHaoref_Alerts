// Map Initialization
const map = L.map('map', {
    zoomControl: false // Move to bottom right later
}).setView([31.5, 34.8], 8); // Auto-center on Israel

// Move zoom controls
L.control.zoom({ position: 'bottomleft' }).addTo(map);

// Add Dark Matter CartoDB Basemap
L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
}).addTo(map);

// State variables
let currentAlertId = null;
let markersLayer = L.layerGroup().addTo(map);

// DOM Elements
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const noAlertsScreen = document.getElementById('no-alerts');
const activeAlertsScreen = document.getElementById('active-alerts');
const alertTitle = document.getElementById('alert-title');
const alertDesc = document.getElementById('alert-desc');
const locationsCount = document.getElementById('locations-count');
const lastUpdated = document.getElementById('last-updated');
const citySelect = $('#city-select'); // Use jQuery for Select2
const locationsList = document.getElementById('locations-list');

// Initialize Select2 on load
$(document).ready(function () {
    citySelect.select2({
        placeholder: "חפש אזור התרעה...",
        allowClear: true,
        dir: "rtl" // Support Right-to-Left alignment
    });

    // Listen to changes (User selects a city)
    citySelect.on('select2:select', function (e) {
        const selectedCity = e.params.data.text;
        if (selectedCity) {
            panToCity(selectedCity);
        }
    });
});

// Caching Geocoding Results to be gentle on Nominatim
const geoCache = JSON.parse(localStorage.getItem('geoCache_v3')) || {};

// Helpers
function setStatus(state, text) {
    statusDot.className = 'pulse-dot ' + state;
    statusText.innerText = text;

    const now = new Date();
    lastUpdated.innerText = now.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function updateUI(data) {
    if (!data || data.message === "No active alerts at the moment." || !data.data) {
        noAlertsScreen.classList.add('active');
        activeAlertsScreen.classList.remove('active');
        setStatus('safe', 'שגרה - אין התרעות');
        markersLayer.clearLayers();
        citySelect.empty().trigger('change'); // Clear Dropdown
        locationsList.innerHTML = '';
        currentAlertId = null;
        return;
    }

    const alertData = data.data;

    // Check if it's new data to avoid re-rendering layout/map if nothing changed
    if (currentAlertId === alertData.id) {
        setStatus('danger', 'מצב חירום פעיל');
        return;
    }

    currentAlertId = alertData.id;

    // Update DOM texts
    alertTitle.innerText = alertData.title || "התרעה פעילה!";
    alertDesc.innerText = alertData.desc || "היכנסו למרחב מוגן.";
    locationsCount.innerText = alertData.data.length;

    // Populate Select2 Dropdown and List
    citySelect.empty();
    citySelect.append(new Option('', '', false, false)); // Empty option for placeholder
    locationsList.innerHTML = '';

    alertData.data.forEach(city => {
        // Select2 Option
        const option = new Option(city, city, false, false);
        citySelect.append(option);

        // List Item
        const li = document.createElement('li');
        li.className = 'location-item';
        li.innerText = city;
        li.addEventListener('click', () => {
            panToCity(city);
        });
        locationsList.appendChild(li);
    });
    citySelect.trigger('change');

    noAlertsScreen.classList.remove('active');
    activeAlertsScreen.classList.add('active');
    setStatus('danger', 'מצב חירום פעיל');

    // Trigger Geo-cording and Mapping
    plotCitiesOnMap(alertData.data);
}

// Map Plotting Logic
async function plotCitiesOnMap(cities) {
    markersLayer.clearLayers(); // Clear old markers
    const bounds = L.latLngBounds();
    let plottedAtLeastOne = false;

    console.log(`Starting to fetch and plot polygons for ${cities.length} cities...`);

    for (let i = 0; i < cities.length; i++) {
        const city = cities[i];
        let geoData = geoCache[city]; // We now cache the full GeoJSON feature

        if (geoData === undefined || geoData === null) {
            // Clean up Oref specific zones to increase Geocoding success
            let searchCity = city.split('-')[0].trim();
            searchCity = searchCity.replace("אזור תעשייה", "").trim() || searchCity;

            // Wait 1 second before calling Nominatim to respect Usage Policy and heavy polygon requests
            await new Promise(r => setTimeout(r, 1000));
            try {
                // Fetch GeoJSON polygon for city in Israel context
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchCity + ', Israel')}&polygon_geojson=1&limit=1`);
                const json = await res.json();

                if (json && json.length > 0 && json[0].geojson) {
                    geoData = json[0].geojson;
                    geoCache[city] = geoData;
                    console.log(`[GEO-SUCCESS] Fetched Polygon for ${city}`);
                } else {
                    geoCache[city] = "NOT_FOUND"; // Cache the miss
                    console.warn(`[GEO-MISS] Could not find polygon for ${city}`);
                }

                // Be careful not to exceed localStorage quota with huge polygons
                try {
                    localStorage.setItem('geoCache_v3', JSON.stringify(geoCache));
                } catch (e) {
                    console.warn("localStorage full, continuing without saving this polygon to browser cache.");
                }

            } catch (err) {
                console.error(`[GEO-ERROR] Geocoding failed for ${city}`, err);
            }
        } else {
            console.log(`[GEO-CACHE] Loaded ${city} polygon from cache.`);
        }

        if (geoData && geoData !== "NOT_FOUND") {
            try {
                // Render the GeoJSON Polygon
                const polygonLayer = L.geoJSON(geoData, {
                    style: {
                        color: "#ff0000",
                        weight: 2,
                        opacity: 1,
                        fillColor: "#ff0000",
                        fillOpacity: 0.3
                    },
                    // If the GeoJSON is just a point (Nominatim couldn't find a polygon), draw a red circle instead of default blue marker
                    pointToLayer: function (feature, latlng) {
                        return L.circleMarker(latlng, {
                            radius: 8,
                            fillColor: "#ff0000",
                            color: "#ffffff",
                            weight: 1,
                            opacity: 1,
                            fillOpacity: 0.8
                        });
                    }
                }).addTo(markersLayer);

                polygonLayer.bindTooltip(city, { direction: 'center', className: 'custom-tooltip' });

                // Get bounds of this specific polygon to extend overall map bounds
                const layerBounds = polygonLayer.getBounds();
                bounds.extend(layerBounds);
                plottedAtLeastOne = true;

                // Periodically fit bounds so user sees progress
                if (i % 5 === 0 || i === cities.length - 1) {
                    map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
                }
            } catch (layerErr) {
                console.error(`Error rendering Layer for ${city}`, layerErr);
            }
        }
    }
}

// Map Interaction
function panToCity(cityName) {
    const geoData = geoCache[cityName];
    if (geoData && geoData !== "NOT_FOUND") {
        if (geoData.type && geoData.type.includes("Polygon")) {
            // It's a GeoJSON polygon
            const tempLayer = L.geoJSON(geoData);
            map.fitBounds(tempLayer.getBounds(), { maxZoom: 14, duration: 1.5 });
        } else if (Array.isArray(geoData)) {
            // It's a Point coordinate [lat, lon]
            map.setView(geoData, 14, { animate: true, duration: 1.5 });
        }
    }
}

// Fetch Logic
async function fetchAlerts() {
    setStatus('fetching', 'בודק מול השרת...');
    try {
        const res = await fetch('/api/alerts');
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        updateUI(data);
    } catch (err) {
        console.error("Failed to fetch alerts", err);
        setStatus('safe', 'שגיאת התחברות');
    }
}

// Init & Interval
fetchAlerts();
setInterval(fetchAlerts, 10000); // Poll every 10 seconds on the client side
