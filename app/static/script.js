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
const locationsList = document.getElementById('locations-list');
const locationsCount = document.getElementById('locations-count');
const lastUpdated = document.getElementById('last-updated');

// Caching Geocoding Results to be gentle on Nominatim
const geoCache = JSON.parse(localStorage.getItem('geoCache')) || {};

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

    // Populate List
    locationsList.innerHTML = '';
    alertData.data.forEach(city => {
        const li = document.createElement('li');
        li.className = 'location-item';
        li.innerText = city;
        locationsList.appendChild(li);
    });

    noAlertsScreen.classList.remove('active');
    activeAlertsScreen.classList.add('active');
    setStatus('danger', 'מצב חירום פעיל');

    // Trigger Geo-cording and Mapping
    plotCitiesOnMap(alertData.data);
}

// Map Plotting Logic
async function plotCitiesOnMap(cities) {
    markersLayer.clearLayers(); // Clear old markers

    // Custom DIV icon for nice pulsating effect
    const alertIcon = L.divIcon({
        className: 'custom-alert-marker',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
    });

    const bounds = L.latLngBounds();

    for (let i = 0; i < cities.length; i++) {
        const city = cities[i];
        let coords = geoCache[city];

        if (!coords) {
            // Wait 1 second before calling Nominatim to respect Usage Policy
            await new Promise(r => setTimeout(r, 1000));
            try {
                // Fetch coords for city in Israel context
                const res = await fetch(`https://nominatim.openstreetmap.org/search?format=json&q=${encodeURIComponent(city + ', Israel')}&limit=1`);
                const json = await res.json();

                if (json && json.length > 0) {
                    coords = [parseFloat(json[0].lat), parseFloat(json[0].lon)];
                    geoCache[city] = coords;
                    localStorage.setItem('geoCache', JSON.stringify(geoCache));
                }
            } catch (err) {
                console.error("Geocoding failed for", city, err);
            }
        }

        if (coords) {
            const marker = L.marker(coords, { icon: alertIcon }).addTo(markersLayer);
            marker.bindTooltip(city, { direction: 'top', className: 'custom-tooltip' });
            bounds.extend(coords);
        }
    }

    // Fit map bounds to show all markers if any exist
    if (Object.keys(markersLayer._layers).length > 0) {
        map.fitBounds(bounds, { padding: [50, 50], maxZoom: 12 });
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
