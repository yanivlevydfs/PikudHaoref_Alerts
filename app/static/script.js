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

// Map Plotting Logic
async function plotCitiesOnMap(cities) {
    markersLayer.clearLayers(); // Clear old markers
    const bounds = L.latLngBounds();
    let plottedAtLeastOne = false;
    const missingCities = [];

    console.log(`Processing map plots for ${cities.length} cities...`);

    // 1. First Pass: Instantly render anything that is already cached!
    cities.forEach(city => {
        const geoData = geoCache[city];
        if (geoData && geoData !== "NOT_FOUND" && geoData !== "NOT_FOUND_AGAIN") {
            try {
                // Render the GeoJSON Polygon or Point
                const layer = L.geoJSON(geoData, {
                    style: {
                        color: "#ff0000",
                        weight: 2,
                        opacity: 1,
                        fillColor: "#ff0000",
                        fillOpacity: 0.3
                    },
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

                layer.bindTooltip(city, { direction: 'center', className: 'custom-tooltip' });

                const layerBounds = layer.getBounds();
                if (layerBounds.isValid()) {
                    bounds.extend(layerBounds);
                    plottedAtLeastOne = true;
                }
            } catch (layerErr) {
                console.error(`Error rendering cached Layer for ${city}`, layerErr);
            }
        } else {
            // Needs a fresh fetch or a retry if it failed previously
            missingCities.push(city);
        }
    });

    // Fit bounds instantly for what we have in cache
    if (plottedAtLeastOne) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
    }

    // 2. Second Pass: Async fetch missing data gracefully without freezing map
    if (missingCities.length > 0) {
        console.log(`Fetching ${missingCities.length} uncached locations in background...`);
        for (let i = 0; i < missingCities.length; i++) {
            const city = missingCities[i];

            // Aggressive string cleanup to get better Nominatim hit rates
            let searchCity = city.split('-')[0].trim();
            searchCity = searchCity.replace("אזור תעשייה", "").replace("איזור תעשייה", "").replace("פארק תעשיות", "").replace("בי\"ס", "").trim();
            if (!searchCity) searchCity = city.split('-')[0].trim();

            await new Promise(r => setTimeout(r, 1000)); // Respect openstreetmap ratelimits

            try {
                let res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(searchCity + ', Israel')}&polygon_geojson=1&limit=1`);
                let json = await res.json();

                // If no result and multi-word (e.g. "דרומי אשקלון"), safely retry with just the last word ("אשקלון")
                if (json.length === 0 && searchCity.split(' ').length > 1) {
                    const lastWord = searchCity.split(' ').pop();
                    await new Promise(r => setTimeout(r, 1000));
                    res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(lastWord + ', Israel')}&polygon_geojson=1&limit=1`);
                    json = await res.json();
                }

                let fetchedData = null;
                if (json && json.length > 0) {
                    if (json[0].geojson) {
                        fetchedData = json[0].geojson; // Valid Polygon
                    } else if (json[0].lat && json[0].lon) {
                        // Crucial Fallback: If OSM knows the coordinates but lacks polygon borders, build a GeoJSON Point manually!
                        fetchedData = {
                            type: "Point",
                            coordinates: [parseFloat(json[0].lon), parseFloat(json[0].lat)]
                        };
                    }
                }

                if (fetchedData) {
                    geoCache[city] = fetchedData;
                    console.log(`[GEO-SUCCESSAsync] Fetched shape/point for '${city}'`);

                    // Live add to map
                    const asyncLayer = L.geoJSON(fetchedData, {
                        style: { color: "#ff0000", weight: 2, opacity: 1, fillColor: "#ff0000", fillOpacity: 0.3 },
                        pointToLayer: function (feature, latlng) {
                            return L.circleMarker(latlng, { radius: 8, fillColor: "#ff0000", color: "#ffffff", weight: 1, opacity: 1, fillOpacity: 0.8 });
                        }
                    }).addTo(markersLayer);
                    asyncLayer.bindTooltip(city, { direction: 'center', className: 'custom-tooltip' });

                    const lb = asyncLayer.getBounds();
                    if (lb.isValid()) {
                        bounds.extend(lb);
                        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
                    }
                } else {
                    geoCache[city] = "NOT_FOUND_AGAIN";
                    console.warn(`[GEO-MISS] Could not isolate coordinates for ${city}`);
                }

                localStorage.setItem('geoCache_v3', JSON.stringify(geoCache)); // Retain v3 key seamlessly
            } catch (err) {
                console.error(`[GEO-ERROR] Geocoding failed for ${city}`, err);
            }
        }
    }
}

// Map Interaction
function panToCity(cityName) {
    const geoData = geoCache[cityName];
    if (geoData && geoData !== "NOT_FOUND" && geoData !== "NOT_FOUND_AGAIN") {
        if (geoData.type === "Point") {
            // Leaflet setView expects [lat, lon], GeoJSON stores [lon, lat]
            map.setView([geoData.coordinates[1], geoData.coordinates[0]], 14, { animate: true, duration: 1.5 });
        } else {
            // It's a proper GeoJSON polygon
            const tempLayer = L.geoJSON(geoData);
            if (tempLayer.getBounds().isValid()) {
                map.fitBounds(tempLayer.getBounds(), { maxZoom: 14, duration: 1.5 });
            }
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

// Init & Interval
fetchAlerts();
fetchHistory();
setInterval(fetchAlerts, 10000); // Poll every 10 seconds on the client side
