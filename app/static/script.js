// Map Initialization
const israelBounds = L.latLngBounds([29.4533796, 34.267333], [33.335345, 35.894829]);

const map = L.map('map', {
    zoomControl: false, // Move to bottom right later
    maxBounds: israelBounds, // Lock panning to Israel
    maxBoundsViscosity: 0.8, // Bouncy effect when hitting borders
    minZoom: 7 // Don't allow zooming out to the whole world
}).fitBounds(israelBounds); // Fit initially based on screen boundaries

// Move zoom controls
L.control.zoom({ position: 'bottomleft' }).addTo(map);

// Custom Reset Zoom/Bounds Button
const resetZoomControl = L.control({ position: 'bottomleft' });
resetZoomControl.onAdd = function (map) {
    const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
    const button = L.DomUtil.create('a', 'leaflet-control-reset-zoom', container);
    button.innerHTML = '⟲';
    button.href = '#';
    button.title = 'אפס תצוגת מפה'; // "Reset Map View" in Hebrew
    button.style.fontSize = '1.2rem';
    button.style.fontWeight = 'bold';
    button.style.display = 'flex';
    button.style.alignItems = 'center';
    button.style.justifyContent = 'center';

    L.DomEvent.on(button, 'click', function (e) {
        L.DomEvent.stopPropagation(e);
        L.DomEvent.preventDefault(e);
        map.fitBounds(israelBounds);
    });

    return container;
};
resetZoomControl.addTo(map);

// Define Map Themes
const darkTileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
});

const lightTileLayer = L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
    subdomains: 'abcd',
    maxZoom: 20
});

// Load preferred theme
let currentMapTheme = localStorage.getItem('setting_map_theme') || 'dark';
if (currentMapTheme === 'light') {
    lightTileLayer.addTo(map);
} else {
    darkTileLayer.addTo(map);
}

// Custom Map Theme Toggle Button
const themeToggleControl = L.control({ position: 'bottomleft' });
themeToggleControl.onAdd = function (map) {
    const container = L.DomUtil.create('div', 'leaflet-bar leaflet-control');
    const button = L.DomUtil.create('a', 'leaflet-control-theme-toggle', container);
    button.innerHTML = currentMapTheme === 'dark' ? '☀️' : '🌙';
    button.href = '#';
    button.title = 'שנה תצוגת מפה (בהיר/כהה)'; // "Toggle Map Theme" in Hebrew
    button.style.fontSize = '1.2rem';
    button.style.fontWeight = 'bold';
    button.style.display = 'flex';
    button.style.alignItems = 'center';
    button.style.justifyContent = 'center';

    L.DomEvent.on(button, 'click', function (e) {
        L.DomEvent.stopPropagation(e);
        L.DomEvent.preventDefault(e);

        if (currentMapTheme === 'dark') {
            map.removeLayer(darkTileLayer);
            lightTileLayer.addTo(map);
            currentMapTheme = 'light';
            button.innerHTML = '🌙';
        } else {
            map.removeLayer(lightTileLayer);
            darkTileLayer.addTo(map);
            currentMapTheme = 'dark';
            button.innerHTML = '☀️';
        }
        localStorage.setItem('setting_map_theme', currentMapTheme);
    });

    return container;
};
themeToggleControl.addTo(map);

// State variables
let currentAlertId = null;
let currentCitiesHash = ""; // Track hash of cities to avoid redundant plotting
let plottedCities = new Set(); // Track cities currently shown on map
let markersLayer = L.layerGroup().addTo(map);
let localGeoData = {}; // High-performance local polygons mapping

// DOM Elements
const statusDot = document.getElementById('status-dot');
const statusText = document.getElementById('status-text');
const noAlertsScreen = document.getElementById('no-alerts');
const activeAlertsScreen = document.getElementById('active-alerts');
const offlineBanner = document.getElementById('offline-banner');
const alertTitle = document.getElementById('alert-title');
const alertDesc = document.getElementById('alert-desc');
const locationsCount = document.getElementById('locations-count');
const lastUpdated = document.getElementById('last-updated');

// Mobile Bottom Sheet Elements
const sidebarSheet = document.getElementById('sidebar-sheet');
const sheetHandle = document.querySelector('.sheet-handle');
const citySelect = $('#city-select'); // Use jQuery for Select2
const locationsList = document.getElementById('locations-list');

// Settings Elements
const voiceToggle = document.getElementById('voice-toggle');
const soundToggle = document.getElementById('sound-toggle');
const soundSelect = document.getElementById('sound-select');
const desktopToggle = document.getElementById('desktop-toggle');
const testSoundBtn = document.getElementById('test-sound-btn');
const historyContent = document.getElementById('history-content');

// Load Settings from LocalStorage
voiceToggle.checked = localStorage.getItem('setting_voice') === 'true';
soundToggle.checked = localStorage.getItem('setting_sound') === 'true';
soundSelect.value = localStorage.getItem('setting_sound_type') || 'bell';
desktopToggle.checked = localStorage.getItem('setting_desktop') === 'true';

// Save Settings Event Listeners
voiceToggle.addEventListener('change', (e) => localStorage.setItem('setting_voice', e.target.checked));
soundToggle.addEventListener('change', (e) => localStorage.setItem('setting_sound', e.target.checked));
soundSelect.addEventListener('change', (e) => localStorage.setItem('setting_sound_type', e.target.value));

desktopToggle.addEventListener('change', (e) => {
    localStorage.setItem('setting_desktop', e.target.checked);
    if (e.target.checked && Notification.permission !== "granted") {
        Notification.requestPermission();
    }
});

testSoundBtn.addEventListener('click', () => {
    playAlertAudio(true); // Force play for testing
});

// --- Bottom Sheet Interaction Logic ---
let isSheetExpanded = false;

function toggleSheet(expand) {
    if (expand === undefined) expand = !isSheetExpanded;
    isSheetExpanded = expand;

    if (isSheetExpanded) {
        sidebarSheet.classList.add('active');
    } else {
        sidebarSheet.classList.remove('active');
    }
}

// Tap handle to toggle
if (sheetHandle) {
    sheetHandle.addEventListener('click', () => toggleSheet());
}

// Simple Swipe Detection for Mobile
let touchStartY = 0;
sidebarSheet.addEventListener('touchstart', (e) => {
    touchStartY = e.touches[0].clientY;
}, { passive: true });

sidebarSheet.addEventListener('touchend', (e) => {
    const touchEndY = e.changedTouches[0].clientY;
    const diff = touchStartY - touchEndY;

    if (Math.abs(diff) > 50) { // Threshold
        if (diff > 0) toggleSheet(true);  // Swipe Up
        else toggleSheet(false);          // Swipe Down
    }
}, { passive: true });

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
            if (window.innerWidth <= 768) toggleSheet(false);
        }
    });

    // Load High-Performance Local Polygons
    fetch('/static/locations_polygons.json')
        .then(res => res.json())
        .then(data => {
            localGeoData = data;
            console.log(`[GEO] Loaded ${Object.keys(localGeoData).length} local polygons.`);
        })
        .catch(err => console.error("[GEO] Failed to load local polygons:", err));
});

// Caching Geocoding Results to be gentle on Nominatim
const geoCache = JSON.parse(localStorage.getItem('geoCache_v5')) || {};

// Helpers
function setStatus(state, text) {
    statusDot.className = 'pulse-dot ' + state;
    statusText.innerText = text;

    const now = new Date();
    lastUpdated.innerText = now.toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function updateUI(data) {
    // System Online/Offline logic
    if (data && data.is_online === false) {
        offlineBanner.style.display = 'block';
        setStatus('danger', 'מערכת לא זמינה');

        // Update the "No Alerts" screen to show offline status if visible
        const noAlertsTitle = noAlertsScreen.querySelector('h2');
        if (noAlertsTitle) noAlertsTitle.innerText = 'מערכת לא זמינה';
    } else {
        offlineBanner.style.display = 'none';
        const noAlertsTitle = noAlertsScreen.querySelector('h2');
        if (noAlertsTitle) noAlertsTitle.innerText = 'שגרה';
    }

    if (!data || data.message === "No active alerts at the moment." || !data.data) {
        noAlertsScreen.classList.add('active');
        activeAlertsScreen.classList.remove('active');

        if (data && data.is_online === false) {
            setStatus('danger', 'מערכת לא זמינה');
        } else {
            setStatus('safe', 'שגרה - אין התרעות');
        }

        markersLayer.clearLayers();
        plottedCities.clear();
        citySelect.empty().trigger('change'); // Clear Dropdown
        locationsList.innerHTML = '';
        currentAlertId = null;
        currentCitiesHash = "";
        return;
    }

    const alertData = data.data;

    // Prevent duplicate processing if data hasn't changed
    const citiesHash = (alertData.data || []).sort().join('|');
    const isSameAttack = (currentAlertId === alertData.id && citiesHash === currentCitiesHash);

    // Always hide offline banner if we got here
    offlineBanner.style.display = 'none';

    if (!isSameAttack) {
        currentAlertId = alertData.id;
        currentCitiesHash = citiesHash;

        // UI Updates for New Attack
        alertTitle.innerText = alertData.title || "התרעה פעילה!";
        alertDesc.innerText = alertData.desc || "היכנסו למרחב מוגן.";
        locationsCount.innerText = (alertData.data || []).length;

        // Force-expand the locations scroll area
        const expander = document.querySelector('.locations-expander');
        if (expander) expander.setAttribute('open', ''); // Use setAttribute for safety

        citySelect.empty();
        citySelect.append(new Option('', '', false, false));
        locationsList.innerHTML = '';

        (alertData.data || []).forEach(city => {
            const option = new Option(city, city, false, false);
            citySelect.append(option);

            const li = document.createElement('li');
            li.className = 'location-item';
            li.innerText = city;
            li.addEventListener('click', () => panToCity(city));
            locationsList.appendChild(li);
        });
        citySelect.trigger('change');
    }

    // Update status based on current response
    if (data.is_online === false) setStatus('danger', 'מערכת לא זמינה');
    else setStatus('danger', 'מצב חירום פעיל');

    noAlertsScreen.classList.remove('active');
    activeAlertsScreen.classList.add('active');

    // Trigger Geo-cording and Mapping
    plotCitiesOnMap(alertData.data);

    // --- TRIGGER NOTIFICATIONS & MEDIA ---
    const locationsText = alertData.data.slice(0, 10).join(', ') + (alertData.data.length > 10 ? ' ועוד...' : '');

    if (desktopToggle.checked) {
        showDesktopNotification(alertTitle.innerText, locationsText);
    }

    if (soundToggle.checked) {
        playAlertAudio(false);
    }

    if (voiceToggle.checked) {
        speakAlert(`צבע אדום ב: ${locationsText}`);
    }

    // Refresh history since there is a new alert!
    fetchHistory();
}

let isMappingInProgress = false;

/**
 * Geocodes city names and places markers.
 * Optimized for large lists: Won't re-plot already existing markers.
 */
async function plotCitiesOnMap(cities) {
    if (!cities || cities.length === 0) return;
    if (isMappingInProgress) return; // Prevent concurrent loops fighting each other
    isMappingInProgress = true;

    try {
        const bounds = L.latLngBounds();
        let hasValidBounds = false;

        // 1. Clean up stale markers and calculate bounds for existing ones
        const updatedCitiesSet = new Set(cities);
        markersLayer.eachLayer(layer => {
            if (layer._cityName && !updatedCitiesSet.has(layer._cityName)) {
                markersLayer.removeLayer(layer);
                plottedCities.delete(layer._cityName);
            } else if (layer._cityName) {
                // Robust bounds fitting for BOTH markers and polygons
                let lb = null;
                if (typeof layer.getBounds === 'function') {
                    lb = layer.getBounds();
                } else if (typeof layer.getLatLng === 'function') {
                    const ll = layer.getLatLng();
                    lb = L.latLngBounds(ll, ll);
                }

                if (lb && lb.isValid()) {
                    bounds.extend(lb);
                    hasValidBounds = true;
                }
            }
        });

        // 2. Queue missing cities
        const citiesToProcess = cities.filter(city => !plottedCities.has(city));

        for (let i = 0; i < citiesToProcess.length; i++) {
            const city = citiesToProcess[i];

            // --- HIGH PERFORMANCE LOOKUP ---
            // If we have it in localGeoData (from eladnava's dataset), use it INSTANTLY
            let geoData = localGeoData[city] ? localGeoData[city].polygon : null;

            // If it's a "multipolygon" or simple polygon from our JSON, it's just coordinates.
            // We need to wrap it into a GeoJSON feature.
            if (geoData) {
                geoData = {
                    type: "Feature",
                    geometry: {
                        type: "Polygon", // Most are polygons, some might be MultiPolygon but eladnava's usually wraps them
                        coordinates: geoData
                    }
                };
            }

            // Fallback to existing geoCache (Nominatim results)
            if (!geoData) {
                geoData = geoCache[city];
            }

            if (geoData && geoData !== "NOT_FOUND" && geoData !== "NOT_FOUND_AGAIN") {
                try {
                    const layer = L.geoJSON(geoData, {
                        style: { color: "#ff0000", weight: 2, opacity: 1, fillColor: "#ff0000", fillOpacity: 0.3 },
                        pointToLayer: function (feature, latlng) {
                            return L.circleMarker(latlng, { radius: 8, fillColor: "#ff0000", color: "#ffffff", weight: 1, opacity: 1, fillOpacity: 0.8 });
                        }
                    }).addTo(markersLayer);

                    layer._cityName = city;
                    layer.bindTooltip(city, { direction: 'center', className: 'custom-tooltip' });
                    plottedCities.add(city);

                    const layerBounds = layer.getBounds();
                    if (layerBounds.isValid()) {
                        bounds.extend(layerBounds);
                        hasValidBounds = true;
                        // Zoom in if it's the first few cities
                        if (plottedCities.size < 5) map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
                    }
                } catch (err) {
                    console.error(`Error plotting ${city}`, err);
                }
            } else if (!geoData || geoData === "NOT_FOUND") {
                // Only fall back to external geocoding if we really don't have it
                await fetchMissingCityOnMap(city, bounds, i, citiesToProcess.length);
            }
        }

        if (hasValidBounds) map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });

    } finally {
        isMappingInProgress = false;
    }
}

async function fetchMissingCityOnMap(city, bounds, index, total) {
    let searchCity = city.split('-')[0].trim();
    if (searchCity.includes("אזור תעשייה") || searchCity.includes("פארק תעשיות") || searchCity.startsWith("רחוב")) {
        searchCity = city.replace(/-/g, " ").trim();
    }
    searchCity = searchCity.replace(/^רחוב\s+/g, "").replace(/^שדרות\s+(?!(השביעית|הציונות|ירושלים))/g, "").replace(/^פארק\s+/g, "").replace("בי\"ס", "").trim();

    // Rate limiting progress update in console so user knows we are working
    if (index % 10 === 0) setStatus('fetching', `מאחזר מיקום: ${index + 1}/${total}...`);

    await new Promise(r => setTimeout(r, 1000)); // Respect Nominatim limits

    try {
        const baseUrl = "https://nominatim.openstreetmap.org/search?format=json&polygon_geojson=1&limit=1&countrycodes=il&accept-language=he&addressdetails=1";
        let res = await fetch(`${baseUrl}&q=${encodeURIComponent(searchCity)}`, {
            headers: { 'User-Agent': 'PikudHaoref_Alerts_Webapp/1.2' }
        });
        let json = await res.json();

        if (json.length === 0 && searchCity.split(' ').length > 1) {
            const lastWord = searchCity.split(' ').pop();
            await new Promise(r => setTimeout(r, 1000));
            res = await fetch(`${baseUrl}&q=${encodeURIComponent(lastWord)}`);
            json = await res.json();
        }

        let fetchedData = null;
        if (json && json.length > 0) {
            const result = json[0];
            const allowedClasses = ['place', 'boundary'];
            const forbiddenTypes = ['highway', 'street', 'road', 'footway', 'residential', 'service'];
            if (allowedClasses.includes(result.class) && !forbiddenTypes.includes(result.type)) {
                if (result.geojson) fetchedData = result.geojson;
                else if (result.lat && result.lon) fetchedData = { type: "Point", coordinates: [parseFloat(result.lon), parseFloat(result.lat)] };
            }
        }

        if (fetchedData) {
            geoCache[city] = fetchedData;
            const asyncLayer = L.geoJSON(fetchedData, {
                style: { color: "#ff0000", weight: 2, opacity: 1, fillColor: "#ff0000", fillOpacity: 0.3 },
                pointToLayer: function (feature, latlng) { return L.circleMarker(latlng, { radius: 8, fillColor: "#ff0000", color: "#ffffff", weight: 1, opacity: 1, fillOpacity: 0.8 }); }
            }).addTo(markersLayer);

            asyncLayer._cityName = city;
            asyncLayer.bindTooltip(city, { direction: 'center', className: 'custom-tooltip' });
            plottedCities.add(city);

            let lb = null;
            if (typeof asyncLayer.getBounds === 'function') {
                lb = asyncLayer.getBounds();
            } else if (typeof asyncLayer.getLatLng === 'function') {
                const ll = asyncLayer.getLatLng();
                lb = L.latLngBounds(ll, ll);
            }

            if (lb && lb.isValid()) {
                bounds.extend(lb);
                if (plottedCities.size < 5 || plottedCities.size % 10 === 0) {
                    map.fitBounds(bounds, { padding: [60, 60], maxZoom: 12, animate: true });
                }
            }
        } else {
            geoCache[city] = "NOT_FOUND_AGAIN";
        }
        localStorage.setItem('geoCache_v5', JSON.stringify(geoCache));
    } catch (err) {
        console.warn(`[GEO-FETCH-FAIL] ${city}: ${err.message}`);
        // Don't mark as NOT_FOUND_AGAIN, let it retry on next poll if it was a network error
    }
}

// Map Interaction
function panToCity(cityName) {
    // Try local data first
    let geoData = localGeoData[cityName] ? localGeoData[cityName].polygon : null;

    if (geoData) {
        // Wrap for Leaflet
        const tempLayer = L.geoJSON({
            type: "Feature",
            geometry: { type: "Polygon", coordinates: geoData }
        });
        if (tempLayer.getBounds().isValid()) {
            map.fitBounds(tempLayer.getBounds(), { maxZoom: 14, duration: 1.5 });
            return;
        }
    }

    // Fallback to cache
    geoData = geoCache[cityName];
    if (geoData && geoData !== "NOT_FOUND" && geoData !== "NOT_FOUND_AGAIN") {
        if (geoData.type === "Point") {
            map.setView([geoData.coordinates[1], geoData.coordinates[0]], 14, { animate: true, duration: 1.5 });
        } else {
            const tempLayer = L.geoJSON(geoData);
            if (tempLayer.getBounds().isValid()) {
                map.fitBounds(tempLayer.getBounds(), { maxZoom: 14, duration: 1.5 });
            }
        }
    }
}

// Fetch Logic
// Poll Manager
let pollInterval = 10000;
let pollTimeout = null;

async function fetchAlerts() {
    setStatus('fetching', 'בודק מול השרת...');
    try {
        const urlParams = new URLSearchParams(window.location.search);
        const isMock = urlParams.get('mock') === 'true';
        const endpoint = isMock ? '/api/alerts?mock=true' : '/api/alerts';

        const res = await fetch(endpoint);
        if (!res.ok) throw new Error("HTTP " + res.status);

        const data = await res.json();
        updateUI(data);

        // Success -> Reset slow poll
        pollInterval = 10000;
    } catch (err) {
        console.error("Failed to fetch alerts", err);
        // FORCE offline state in UI because we couldn't even talk to the backend
        updateUI({ message: "Network Error", is_online: false, data: null });

        // Error -> Fast poll for recovery
        pollInterval = 3000;
    } finally {
        // Schedule next poll
        if (pollTimeout) clearTimeout(pollTimeout);
        pollTimeout = setTimeout(fetchAlerts, pollInterval);
    }
}

// History Fetching
async function fetchHistory() {
    try {
        const res = await fetch('/api/alerts/history');
        const json = await res.json();

        if (json.data && json.data.length > 0) {
            historyContent.innerHTML = '';
            json.data.forEach(alert => {
                const el = document.createElement('div');
                el.style.marginBottom = '0.8rem';
                el.style.borderBottom = '1px solid rgba(255, 255, 255, 0.08)';
                el.style.paddingBottom = '0.5rem';

                const timeStr = new Date(alert.timestamp).toLocaleTimeString('he-IL', { hour: '2-digit', minute: '2-digit' });
                const locationsStr = alert.locations.join(', ');

                el.innerHTML = `<strong style="color: var(--accent-color);">${timeStr} - ${alert.title}</strong><br><span style="color: var(--text-secondary); font-size: 0.85rem;">${locationsStr}</span>`;
                historyContent.appendChild(el);
            });
        } else {
            historyContent.innerHTML = 'אין התרעות ב-24 שעות האחרונות. נהדר!';
        }
    } catch (err) {
        console.error("Failed to fetch history", err);
        historyContent.innerHTML = 'שגיאה בטעינת הארכיון.';
    }
}

// Media & Notification Helpers
function playAlertAudio(force = false) {
    if (!force && !soundToggle.checked) return;

    // Instead of missing MP3 files, generate a synthetic alarm using Web Audio API!
    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const type = soundSelect.value;

    if (type === 'bell') {
        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(880, audioCtx.currentTime); // A5
        gainNode.gain.setValueAtTime(1, audioCtx.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 1.5);
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 1.5);
    } else {
        // Siren
        const osc = audioCtx.createOscillator();
        const gainNode = audioCtx.createGain();
        osc.type = 'square';
        osc.frequency.setValueAtTime(600, audioCtx.currentTime);
        osc.frequency.linearRampToValueAtTime(1200, audioCtx.currentTime + 1);
        osc.frequency.linearRampToValueAtTime(600, audioCtx.currentTime + 2);
        gainNode.gain.setValueAtTime(0.3, audioCtx.currentTime);
        osc.connect(gainNode);
        gainNode.connect(audioCtx.destination);
        osc.start();
        osc.stop(audioCtx.currentTime + 2);
    }
}

function speakAlert(text) {
    if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel(); // Stop current
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = 'he-IL';
        utterance.rate = 0.9; // Slightly slower for clarity
        window.speechSynthesis.speak(utterance);
    }
}

function showDesktopNotification(title, body) {
    if (Notification.permission === "granted") {
        new Notification(title, {
            body: body,
            icon: '/static/favicon.ico' // Or any alert icon
        });
    }
}

// Init
fetchAlerts();
fetchHistory();
// Polling is now handled inside fetchAlerts with setTimeout for adaptive rates

// --- PWA Installation Logic ---
let deferredPrompt;
const pwaInstallBtn = document.getElementById('pwa-install-btn');

window.addEventListener('beforeinstallprompt', (e) => {
    // Prevent the mini-infobar from appearing on mobile
    e.preventDefault();
    // Stash the event so it can be triggered later.
    deferredPrompt = e;

    // Show the install button
    if (pwaInstallBtn) {
        pwaInstallBtn.style.display = 'flex';
        // Trigger transition
        setTimeout(() => {
            pwaInstallBtn.style.opacity = '1';
            pwaInstallBtn.style.transform = 'translate(-50%, 0)';
        }, 10);

        console.log('PWA: Install prompt available, showing button.');

        // Auto-hide after 7 seconds
        setTimeout(() => {
            if (pwaInstallBtn) {
                pwaInstallBtn.style.opacity = '0';
                pwaInstallBtn.style.transform = 'translate(-50%, -20px)';
                setTimeout(() => {
                    pwaInstallBtn.style.display = 'none';
                }, 500); // Wait for transition
            }
        }, 7000);
    }
});

if (pwaInstallBtn) {
    pwaInstallBtn.addEventListener('click', async () => {
        if (!deferredPrompt) return;

        // Show the install prompt
        deferredPrompt.prompt();

        // Wait for the user to respond to the prompt
        const { outcome } = await deferredPrompt.userChoice;
        console.log(`PWA: User response to install prompt: ${outcome}`);

        // We've used the prompt, and can't use it again, throw it away
        deferredPrompt = null;

        // Hide the button
        pwaInstallBtn.style.display = 'none';
    });
}

window.addEventListener('appinstalled', () => {
    // Log install to analytics or hide UI
    console.log('PWA: App was installed successfully.');
    if (pwaInstallBtn) pwaInstallBtn.style.display = 'none';
});
