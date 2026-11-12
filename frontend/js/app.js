
/* =========================================================
   RENEWABLE ENERGY INTELLIGENCE — INDIA
   Frontend application
   ========================================================= */

"use strict";


/* =========================================================
   1. CONFIGURATION
========================================================= */

const API_BASE = "http://127.0.0.1:8000/api";

const GEOJSON_PATH = "data/india_states.geojson";

const MAP_COLORS = {
    background: "#f3f5ef",

    defaultFill: "#dce9df",
    defaultBorder: "#91ae99",

    hoverFill: "#bfd8c5",
    hoverBorder: "#527b60",

    selectedFill: "#a9cbb2",
    selectedBorder: "#315e40",

    noDataFill: "#eeeeea",
    noDataBorder: "#c8cec8"
};

const SMALL_REGIONS = [
    "Delhi",
    "Chandigarh",
    "Puducherry",
    "Lakshadweep",
    "Andaman and Nicobar",
    "Andaman and Nicobar Islands",
    "Dadra and Nagar Haveli and Daman and Diu"
];

const METRIC_CONFIGURATION = {
    renewable_share: {
        title: "Renewable Share",
        unit: "%",
        format: "percentage",
        description: "Renewable generation as a percentage of total generation."
    },

    fossil_share: {
        title: "Fossil Share",
        unit: "%",
        format: "percentage",
        description: "Fossil generation as a percentage of total generation."
    },

    renewable_generation: {
        title: "Renewable Generation",
        unit: "GWh",
        format: "generation",
        description: "Total recorded renewable electricity generation."
    },

    solar_generation: {
        title: "Solar Generation",
        unit: "GWh",
        format: "generation",
        description: "Recorded solar electricity generation."
    },

    wind_generation: {
        title: "Wind Generation",
        unit: "GWh",
        format: "generation",
        description: "Recorded wind electricity generation."
    },

    hydro_generation: {
        title: "Hydro Generation",
        unit: "GWh",
        format: "generation",
        description: "Recorded hydro electricity generation."
    },

    bioenergy_generation: {
        title: "Bioenergy Generation",
        unit: "GWh",
        format: "generation",
        description: "Recorded bioenergy electricity generation."
    },

    renewable_capacity: {
        title: "Renewable Capacity",
        unit: "MW",
        format: "capacity",
        description: "Installed renewable energy capacity."
    },

    capacity_factor: {
        title: "Capacity Factor",
        unit: "%",
        format: "percentage",
        description: "Generation relative to theoretical generation at installed capacity."
    },

    total_emissions: {
        title: "Total Emissions",
        unit: "ktCO2",
        format: "emissions",
        description: "Reported absolute power-sector emissions."
    },

    co2_intensity: {
        title: "CO2 Intensity",
        unit: "gCO2/kWh",
        format: "intensity",
        description: "Reported power-sector emissions intensity."
    }
};

const SUPPORTED_MAP_METRICS = new Set([
    "renewable_share",
    "fossil_share",
    "renewable_generation",
    "solar_generation",
    "wind_generation",
    "hydro_generation",
    "bioenergy_generation"
]);

const CHART_COLORS = {
    renewable: "#438765",
    fossil: "#a66a56",
    solar: "#e6b94f",
    wind: "#78a8bd",
    hydro: "#6485b8",
    bioenergy: "#9c83b9",
    other: "#9ba79d",
    total: "#405d4b"
};


/* =========================================================
   2. DOM REFERENCES
========================================================= */

const metricSelect = document.getElementById("metric-select");
const periodSelect = document.getElementById("period-select");
const dateInput = document.getElementById("date-input");

const mapTitle = document.getElementById("map-title");
const metricUnit = document.getElementById("metric-unit");

const resetButton = document.getElementById("reset-button");
const periodDisclaimer = document.getElementById("period-disclaimer");

const mapContainer = document.getElementById("india-map");
const regionDetails = document.getElementById("region-details");

const mapLegend = document.getElementById("map-legend");

const navigation = document.getElementById("main-navigation");


/* =========================================================
   3. APPLICATION STATE
========================================================= */

let indiaMap = null;
let boundaryLayer = null;

let regionLayers = {};
let smallRegionMarkers = [];

let selectedLayer = null;
let selectedRegion = null;

let currentMapData = [];
let currentMapMetric = "renewable_share";

let currentMapPeriod = "monthly";
let currentMapDate = "2025-11";

let mapInitialized = false;

const chartInstances = {};


/* =========================================================
   4. GENERAL HELPERS
========================================================= */

function canonicalRegionKey(name) {
    if (!name) return "";

    const normalized = String(name).trim();

    const aliases = {
        "Andaman and Nicobar Islands": "Andaman and Nicobar",
        "Andaman & Nicobar Islands": "Andaman and Nicobar",
        "Dadra and Nagar Haveli and Daman and Diu":
            "Dadra and Nagar Haveli and Daman and Diu"
    };

    return aliases[normalized] || normalized;
}


function escapeHTML(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatNumber(value, decimals = 2) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return "Not available";
    }

    return Number(value).toLocaleString("en-IN", {
        minimumFractionDigits: decimals,
        maximumFractionDigits: decimals
    });
}


function formatMetricValue(value, metric) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return "Not available";
    }

    const configuration = METRIC_CONFIGURATION[metric];

    if (!configuration) {
        return formatNumber(value);
    }

    if (configuration.format === "percentage") {
        return `${formatNumber(value, 2)}%`;
    }

    return `${formatNumber(value, 2)} ${configuration.unit}`;
}


function getMetricConfiguration(metric) {
    return METRIC_CONFIGURATION[metric] || {
        title: metric,
        unit: "",
        format: "number",
        description: ""
    };
}


function setStatus(elementId, message, type = "") {
    const element = document.getElementById(elementId);

    if (!element) return;

    element.textContent = message;
    element.className = `data-status ${type}`.trim();
}


async function fetchJSON(url) {
    const response = await fetch(url);

    if (!response.ok) {
        let message = `Request failed (${response.status})`;

        try {
            const errorData = await response.json();
            message = errorData.detail || message;
        } catch {
            // Keep the HTTP error message.
        }

        throw new Error(message);
    }

    return response.json();
}


/* =========================================================
   5. NAVIGATION
========================================================= */

function setupNavigation() {
    const navigation = document.getElementById("main-navigation");

    if (!navigation) {
        console.error("Main navigation element not found.");
        return;
    }

    const links = Array.from(
        navigation.querySelectorAll('a[href^="#"]')
    );

    const sections = Array.from(
        document.querySelectorAll("main .page-section")
    );

    function activateSection(sectionId, updateHistory = false) {
        const target = document.getElementById(sectionId);

        if (!target || !target.classList.contains("page-section")) {
            return;
        }

        sections.forEach(section => {
            section.classList.toggle("active", section.id === sectionId);
        });

        links.forEach(link => {
            const isActive = link.getAttribute("href") === `#${sectionId}`;

            link.classList.toggle("active", isActive);

            if (isActive) {
                link.setAttribute("aria-current", "page");
            } else {
                link.removeAttribute("aria-current");
            }
        });

        if (updateHistory) {
            history.pushState(null, "", `#${sectionId}`);
        }

        window.scrollTo({
            top: 0,
            behavior: "instant"
        });
    }

    links.forEach(link => {
        link.addEventListener("click", event => {
            event.preventDefault();

            const sectionId = link.getAttribute("href").slice(1);
            activateSection(sectionId, true);
        });
    });

    window.addEventListener("popstate", () => {
        const sectionId = window.location.hash.slice(1) || "overview";
        activateSection(sectionId);
    });

    const initialSection = window.location.hash.slice(1) || "overview";
    activateSection(initialSection);
}


/* =========================================================
   6. MAP INITIALISATION
========================================================= */

function initializeMap() {
    if (!mapContainer || typeof L === "undefined") {
        console.error("Leaflet or map container is unavailable.");
        return;
    }

    indiaMap = L.map("india-map", {
        center: [22.8, 82.0],
        zoom: 4.6,
        minZoom: 4,
        maxZoom: 8,
        zoomControl: true,
        scrollWheelZoom: true,
        doubleClickZoom: true,
        attributionControl: true
    });

    indiaMap.setMaxBounds([
        [5.0, 65.0],
        [39.5, 101.0]
    ]);

    indiaMap.getContainer().style.background = MAP_COLORS.background;

    loadGeoJSON();
}


async function loadGeoJSON() {
    try {
        const geojson = await fetchJSON(GEOJSON_PATH);

        boundaryLayer = L.geoJSON(geojson, {
            style: getDefaultRegionStyle,

            onEachFeature: (feature, layer) => {
                const stateName = feature.properties.state_name;

                if (!stateName) return;

                const key = canonicalRegionKey(stateName);

                regionLayers[key] = layer;

                layer.bindTooltip(
                    escapeHTML(stateName),
                    {
                        sticky: true,
                        direction: "top",
                        className: "region-tooltip"
                    }
                );

                layer.on({
                    mouseover: () => handleRegionHover(key),
                    mouseout: () => handleRegionMouseOut(key),
                    click: () => selectRegion(key)
                });
            }
        }).addTo(indiaMap);

        const bounds = boundaryLayer.getBounds();

        if (bounds.isValid()) {
            indiaMap.fitBounds(bounds, {
                padding: [12, 12]
            });
        }

        createSmallRegionMarkers();

        mapInitialized = true;

        loadMapData();

    } catch (error) {
        console.error("Unable to load India GeoJSON:", error);

        if (mapContainer) {
            mapContainer.innerHTML = `
                <div class="map-status">
                    Unable to load the India boundary file.
                    Check that data/india_states.geojson exists.
                </div>
            `;
        }
    }
}


function getDefaultRegionStyle() {
    return {
        fillColor: MAP_COLORS.defaultFill,
        fillOpacity: 1,

        color: MAP_COLORS.defaultBorder,
        weight: 1.1,

        opacity: 1
    };
}


/* =========================================================
   7. SMALL REGION INTERACTION MARKERS
========================================================= */


function createSmallRegionMarkers() {
    if (!indiaMap || !boundaryLayer) return;

    smallRegionMarkers.forEach(marker => {
        indiaMap.removeLayer(marker);
    });

    smallRegionMarkers = [];

    const smallRegionKeys = new Set(
        SMALL_REGIONS.map(canonicalRegionKey)
    );

    Object.entries(regionLayers).forEach(([key, layer]) => {
        if (!smallRegionKeys.has(key)) return;

        const bounds = layer.getBounds();

        if (!bounds.isValid()) return;

        const center = bounds.getCenter();

        const marker = L.marker(center, {
            interactive: true,
            keyboard: false,
            zIndexOffset: 1000,

            icon: L.divIcon({
                className: "small-region-marker",
                html: '<span class="small-region-marker-inner"></span>',
                iconSize: [12, 12],
                iconAnchor: [6, 6]
            })
        });

        marker.bindTooltip(
            layer.feature?.properties?.state_name || key,
            {
                permanent: false,
                direction: "top",
                offset: [0, -8],
                opacity: 1,
                className: "region-tooltip"
            }
        );

        marker.on("mouseover", () => {
            handleRegionHover(key);
            marker.openTooltip();
        });

        marker.on("mouseout", () => {
            handleRegionMouseOut(key);
            marker.closeTooltip();
        });

        marker.on("click", () => {
            selectRegion(key);
        });

        marker.addTo(indiaMap);

        smallRegionMarkers.push(marker);
    });
}


/* =========================================================
   8. MAP HOVER AND SELECTION
========================================================= */

function handleRegionHover(key) {
    const layer = regionLayers[key];

    if (!layer || key === selectedRegion) return;

    layer.setStyle({
        fillColor: MAP_COLORS.hoverFill,
        color: MAP_COLORS.hoverBorder,
        weight: 2,
        fillOpacity: 1
    });

    layer.bringToFront();
}


function handleRegionMouseOut(key) {
    const layer = regionLayers[key];

    if (!layer) return;

    if (key === selectedRegion) {
        applyRegionStyle(key);
        return;
    }

    applyRegionStyle(key);
}



function selectRegion(key) {
    if (!regionLayers[key]) return;

    if (selectedLayer && selectedRegion && selectedRegion !== key) {
        applyRegionStyle(selectedRegion);
    }

    selectedRegion = key;
    selectedLayer = regionLayers[key];

    // Preserve the metric-based choropleth colour.
    applyRegionStyle(key);

    renderRegionDetails(key);
    loadRegionTrend(key);
}

function applyRegionStyle(key) {
    const layer = regionLayers[key];

    if (!layer) return;

    const data = currentMapData.find(
        item => canonicalRegionKey(item.state) === key
    );

    if (!data || data.value === null || data.value === undefined) {
        layer.setStyle({
            fillColor: MAP_COLORS.noDataFill,
            color: MAP_COLORS.noDataBorder,
            weight: 1,
            fillOpacity: 1
        });

        return;
    }

    const range = getCurrentDataRange();

    layer.setStyle({
        fillColor: getColorScale(data.value, range.min, range.max),
        color: MAP_COLORS.defaultBorder,
        weight: 1.1,
        fillOpacity: 1
    });
}

/* =========================================================
   9. MAP DATA AND COLOUR SCALE
========================================================= */

function getColorScale(value, min, max) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) {
        return MAP_COLORS.noDataFill;
    }

    if (max === min) {
        return "#a9cbb2";
    }

    const ratio = Math.max(0, Math.min(1, (value - min) / (max - min)));

    const start = [226, 239, 228];
    const end = [49, 105, 72];

    const rgb = start.map((component, index) => {
        return Math.round(
            component + (end[index] - component) * ratio
        );
    });

    return `rgb(${rgb[0]}, ${rgb[1]}, ${rgb[2]})`;
}


function getCurrentDataRange() {
    const values = currentMapData
        .map(item => item.value)
        .filter(value => value !== null && value !== undefined)
        .map(Number)
        .filter(Number.isFinite);

    if (!values.length) {
        return { min: 0, max: 0 };
    }

    return {
        min: Math.min(...values),
        max: Math.max(...values)
    };
}



function applyMapDataStyles() {
    Object.keys(regionLayers).forEach(key => {
        applyRegionStyle(key);
    });

    renderMapLegend(getCurrentDataRange());
}


function renderMapLegend(range) {
    if (!mapLegend) return;

    const configuration = getMetricConfiguration(currentMapMetric);

    mapLegend.innerHTML = `
        <div class="legend-scale">
            <span>${formatNumber(range.min, 1)} ${escapeHTML(configuration.unit)}</span>

            <div class="legend-gradient"></div>

            <span>${formatNumber(range.max, 1)} ${escapeHTML(configuration.unit)}</span>
        </div>

        <div class="legend-note">
            <span class="legend-no-data"></span>
            No available observation
        </div>
    `;
}


/* =========================================================
   10. MAP API REQUEST
========================================================= */

async function loadMapData() {
    if (!mapInitialized) return;

    const metric = metricSelect?.value || "renewable_share";
    const period = periodSelect?.value || "monthly";
    const date = dateInput?.value || "2025-11";

    currentMapMetric = metric;
    currentMapPeriod = period;
    currentMapDate = date;

    const configuration = getMetricConfiguration(metric);

    if (mapTitle) mapTitle.textContent = configuration.title;
    if (metricUnit) metricUnit.textContent = configuration.unit;

    if (!SUPPORTED_MAP_METRICS.has(metric)) {
        currentMapData = [];

        Object.entries(regionLayers).forEach(([key, layer]) => {
            layer.setStyle({
                fillColor: MAP_COLORS.noDataFill,
                color: MAP_COLORS.noDataBorder,
                weight: 1,
                fillOpacity: 1
            });
        });

        if (periodDisclaimer) {
            periodDisclaimer.textContent =
                "This metric is not yet connected to the map API. Its analytical section will use the corresponding analysis output.";
        }

        if (regionDetails) {
            regionDetails.innerHTML = `
                <div class="details-placeholder">
                    <p>
                        The selected metric is not yet available through
                        the map endpoint.
                    </p>
                </div>
            `;
        }

        renderMapLegend({ min: 0, max: 0 });

        return;
    }

    if (periodDisclaimer) {
        periodDisclaimer.textContent =
            period === "annual"
                ? `Annual values for ${date}. Annual generation metrics are aggregated across available months.`
                : `Monthly values for ${date}.`;
    }

    const query = new URLSearchParams({
        metric,
        period,
        date
    });

    try {
        const response = await fetchJSON(
            `${API_BASE}/map-data?${query.toString()}`
        );

        currentMapData = response.regions || [];

        applyMapDataStyles();

        if (selectedRegion) {
            renderRegionDetails(selectedRegion);
        }

        renderRegionComparisonChart();

    } catch (error) {
        console.error("Map data request failed:", error);

        if (periodDisclaimer) {
            periodDisclaimer.textContent =
                `Unable to retrieve map data: ${error.message}`;
        }
    }
}


/* =========================================================
   11. REGION DETAILS
========================================================= */

function renderRegionDetails(key) {
    if (!regionDetails) return;

    const region = currentMapData.find(
        item => canonicalRegionKey(item.state) === key
    );

    if (!region) {
        regionDetails.innerHTML = `
            <div class="details-placeholder">
                <p>
                    No observation is available for this region
                    and selected period.
                </p>
            </div>
        `;

        return;
    }

    const configuration = getMetricConfiguration(currentMapMetric);

    const value = formatMetricValue(
        region.value,
        currentMapMetric
    );

    const expected = region.months_expected ?? "Not available";
    const available = region.months_available ?? "Not available";

    regionDetails.innerHTML = `
        <div class="region-detail-content">

            <div class="region-detail-heading">
                <span class="region-detail-label">Selected region</span>
                <h3>${escapeHTML(region.state)}</h3>
            </div>

            <div class="region-detail-value">
                <span>${escapeHTML(configuration.title)}</span>
                <strong>${escapeHTML(value)}</strong>
            </div>

            <div class="region-detail-meta">
                <div>
                    <span>Reporting type</span>
                    <strong>${escapeHTML(region.state_type || "State / UT")}</strong>
                </div>

                <div>
                    <span>Observations available</span>
                    <strong>${escapeHTML(available)} / ${escapeHTML(expected)}</strong>
                </div>

                <div>
                    <span>Selected period</span>
                    <strong>${escapeHTML(currentMapDate)}</strong>
                </div>
            </div>

            <p class="region-detail-description">
                ${escapeHTML(configuration.description)}
            </p>

        </div>
    `;
}


/* =========================================================
   12. REGION TREND
========================================================= */


async function loadRegionTrend(key) {
    const canvas = document.getElementById("region-trend-chart");

    if (!canvas || typeof Chart === "undefined") {
        console.error("Region trend chart canvas or Chart.js is unavailable.");
        return;
    }

    const metric = currentMapMetric;

    if (!SUPPORTED_MAP_METRICS.has(metric)) {
        destroyChart("regionTrend");
        return;
    }

    const query = new URLSearchParams({
        metric: metric
    });

    try {
        const response = await fetchJSON(
            `${API_BASE}/regions/${encodeURIComponent(key)}/trend?${query.toString()}`
        );

        const observations = response.observations || response.trend || [];

        if (!observations.length) {
            console.warn(`No historical trend data available for ${key}.`);
            destroyChart("regionTrend");
            return;
        }

        // Backend returns month, not date.
        const labels = observations.map(item => item.month);
        const values = observations.map(item => item.value);

        renderLineChart(
            "regionTrend",
            "region-trend-chart",
            labels,
            [{
                label: `${response.region || key} — ${getMetricConfiguration(metric).title}`,
                data: values,
                borderColor: CHART_COLORS.renewable,
                backgroundColor: "rgba(67, 135, 101, 0.12)",
                fill: true,
                tension: 0.25,
                pointRadius: 2
            }],
            getMetricConfiguration(metric).unit
        );

    } catch (error) {
        console.error("Region trend request failed:", error);
        destroyChart("regionTrend");
    }
}

/* =========================================================
   13. CHART HELPERS
========================================================= */

function destroyChart(chartKey) {
    if (chartInstances[chartKey]) {
        chartInstances[chartKey].destroy();
        delete chartInstances[chartKey];
    }
}


function getChartContext(canvasId) {
    const canvas = document.getElementById(canvasId);

    if (!canvas || typeof Chart === "undefined") {
        return null;
    }

    return canvas.getContext("2d");
}


function renderLineChart(chartKey, canvasId, labels, datasets, unit = "") {
    const context = getChartContext(canvasId);

    if (!context) return;

    destroyChart(chartKey);

    chartInstances[chartKey] = new Chart(context, {
        type: "line",

        data: {
            labels,
            datasets
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            interaction: {
                intersect: false,
                mode: "index"
            },

            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        padding: 16
                    }
                },

                tooltip: {
                    callbacks: {
                        label: context => {
                            return `${context.dataset.label}: ${formatNumber(context.parsed.y)} ${unit}`;
                        }
                    }
                }
            },

            scales: {
                x: {
                    grid: {
                        display: false
                    },

                    ticks: {
                        maxTicksLimit: 12
                    }
                },

                y: {
                    beginAtZero: true,

                    title: {
                        display: Boolean(unit),
                        text: unit
                    }
                }
            }
        }
    });
}


function renderBarChart(chartKey, canvasId, labels, datasets, unit = "") {
    const context = getChartContext(canvasId);

    if (!context) return;

    destroyChart(chartKey);

    chartInstances[chartKey] = new Chart(context, {
        type: "bar",

        data: {
            labels,
            datasets
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        padding: 16
                    }
                },

                tooltip: {
                    callbacks: {
                        label: context => {
                            return `${context.dataset.label}: ${formatNumber(context.parsed.y)} ${unit}`;
                        }
                    }
                }
            },

            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },

                y: {
                    beginAtZero: true,

                    title: {
                        display: Boolean(unit),
                        text: unit
                    }
                }
            }
        }
    });
}


function renderDoughnutChart(chartKey, canvasId, labels, values) {
    const context = getChartContext(canvasId);

    if (!context) return;

    destroyChart(chartKey);

    chartInstances[chartKey] = new Chart(context, {
        type: "doughnut",

        data: {
            labels,

            datasets: [{
                data: values,

                backgroundColor: [
                    CHART_COLORS.solar,
                    CHART_COLORS.wind,
                    CHART_COLORS.hydro,
                    CHART_COLORS.bioenergy,
                    CHART_COLORS.other
                ],

                borderWidth: 2,
                borderColor: "#ffffff"
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    position: "bottom",

                    labels: {
                        usePointStyle: true,
                        boxWidth: 8,
                        padding: 15
                    }
                }
            }
        }
    });
}


/* =========================================================
   14. REGION COMPARISON CHART
========================================================= */

function renderRegionComparisonChart() {
    if (!currentMapData.length) return;

    const available = currentMapData
        .filter(item => item.value !== null && item.value !== undefined)
        .sort((a, b) => Number(b.value) - Number(a.value))
        .slice(0, 10);

    if (!available.length) return;

    const labels = available.map(item => item.state);
    const values = available.map(item => Number(item.value));

    renderBarChart(
        "regionComparison",
        "region-comparison-chart",
        labels,
        [{
            label: getMetricConfiguration(currentMapMetric).title,
            data: values,
            backgroundColor: CHART_COLORS.renewable,
            borderRadius: 4
        }],
        getMetricConfiguration(currentMapMetric).unit
    );
}


/* =========================================================
   15. ANALYSIS DATA CONNECTIONS
========================================================= */

/*
   All analytical charts consume finalized CSV outputs
   through the FastAPI endpoints.

   Backend response:
   {
       dataset,
       row_count,
       columns,
       records
   }
*/


async function fetchAnalysisRecords(endpoint) {
    const response = await fetchJSON(`${API_BASE}${endpoint}`);

    if (!Array.isArray(response.records)) {
        throw new Error(`Invalid records returned by ${endpoint}`);
    }

    return response.records;
}


function normalizeColumnName(name) {
    return String(name)
        .toLowerCase()
        .replace(/[^a-z0-9]/g, "");
}


function findColumn(records, candidates = []) {
    if (!records.length) return null;

    const columns = Object.keys(records[0]);

    for (const candidate of candidates) {
        const match = columns.find(
            column =>
                normalizeColumnName(column) ===
                normalizeColumnName(candidate)
        );

        if (match) return match;
    }

    return null;
}


function findSourceColumn(records, source, keyword) {
    if (!records.length) return null;

    const columns = Object.keys(records[0]);

    const normalizedSource = normalizeColumnName(source);
    const normalizedKeyword = normalizeColumnName(keyword);

    return columns.find(column => {
        const normalized = normalizeColumnName(column);

        return (
            normalized.includes(normalizedSource) &&
            normalized.includes(normalizedKeyword)
        );
    }) || null;
}


function numericValue(value) {
    if (
        value === null ||
        value === undefined ||
        value === ""
    ) {
        return null;
    }

    const number = Number(value);

    return Number.isFinite(number) ? number : null;
}


function sortByDate(records, dateColumn) {
    return [...records].sort((a, b) =>
        String(a[dateColumn]).localeCompare(String(b[dateColumn]))
    );
}


function groupRecords(records, groupColumn, valueColumn) {
    const grouped = new Map();

    records.forEach(record => {
        const key = String(record[groupColumn]);
        const value = numericValue(record[valueColumn]);

        if (value === null) return;

        grouped.set(
            key,
            (grouped.get(key) || 0) + value
        );
    });

    return [...grouped.entries()]
        .sort((a, b) => a[0].localeCompare(b[0]));
}


function setAnalysisStatus(message, type = "") {
    setStatus("national-chart-status", message, type);
}


function getSourceChartColor(source) {
    const colors = {
        Solar: CHART_COLORS.solar,
        Wind: CHART_COLORS.wind,
        Hydro: CHART_COLORS.hydro,
        Bioenergy: CHART_COLORS.bioenergy,
        "Other Renewables": CHART_COLORS.other
    };

    return colors[source] || CHART_COLORS.renewable;
}


/* ---------------------------------------------------------
   NATIONAL TRENDS
--------------------------------------------------------- */

async function loadNationalCharts() {
    setAnalysisStatus("Loading national analysis...", "loading");

    try {
        const [
            monthly,
            annual,
            sourceMonthly,
            sourceAnnual,
            composition
        ] = await Promise.all([
            fetchAnalysisRecords("/national/monthly-generation"),
            fetchAnalysisRecords("/national/annual-generation"),
            fetchAnalysisRecords("/national/source-monthly"),
            fetchAnalysisRecords("/national/source-annual"),
            fetchAnalysisRecords("/national/source-composition")
        ]);

        renderNationalGenerationChart(monthly);
        renderNationalMixChart(monthly);
        renderNationalShareChart(annual);

        renderSourceGenerationChart(sourceMonthly);
        renderSourceCompositionChart(composition);
        renderSourceAnnualChart(sourceAnnual);

        setAnalysisStatus(
            "National analysis data loaded.",
            "success"
        );

    } catch (error) {
        console.error("National analysis loading failed:", error);

        setAnalysisStatus(
            `Unable to load national analysis: ${error.message}`,
            "error"
        );
    }
}


function renderNationalGenerationChart(records) {
    const dateColumn = findColumn(records, [
        "Month",
        "Date"
    ]);

    const totalColumn = findColumn(records, [
        "Total Generation",
        "Total_Generation_GWh"
    ]);

    const renewableColumn = findColumn(records, [
        "Renewables",
        "Renewable Generation",
        "Renewable_Generation_GWh"
    ]);

    const fossilColumn = findColumn(records, [
        "Fossil",
        "Fossil Generation",
        "Fossil_Generation_GWh"
    ]);

    if (
        !dateColumn ||
        !totalColumn ||
        !renewableColumn ||
        !fossilColumn
    ) {
        console.error(
            "National generation columns not found.",
            records[0]
        );
        return;
    }

    const sorted = sortByDate(records, dateColumn);

    renderLineChart(
        "nationalGeneration",
        "national-generation-chart",
        sorted.map(row => row[dateColumn]),
        [
            {
                label: "Total Generation",
                data: sorted.map(row => numericValue(row[totalColumn])),
                borderColor: CHART_COLORS.total,
                tension: 0.25
            },
            {
                label: "Renewable Generation",
                data: sorted.map(row => numericValue(row[renewableColumn])),
                borderColor: CHART_COLORS.renewable,
                tension: 0.25
            },
            {
                label: "Fossil Generation",
                data: sorted.map(row => numericValue(row[fossilColumn])),
                borderColor: CHART_COLORS.fossil,
                tension: 0.25
            }
        ],
        "GWh"
    );
}


function renderNationalMixChart(records) {
    const dateColumn = findColumn(records, [
        "Month",
        "Date"
    ]);

    if (!dateColumn) return;

    const sorted = sortByDate(records, dateColumn);

    const sources = [
        "Solar",
        "Wind",
        "Hydro",
        "Bioenergy",
        "Other Renewables"
    ];

    const datasets = sources
        .map(source => {
            const column = findColumn(records, [
                source,
                `${source} Generation`,
                `${source}_Generation_GWh`
            ]);

            if (!column) return null;

            return {
                label: source,
                data: sorted.map(row => numericValue(row[column])),
                borderColor: getSourceChartColor(source),
                backgroundColor: getSourceChartColor(source),
                tension: 0.2
            };
        })
        .filter(Boolean);

    renderLineChart(
        "nationalMix",
        "national-mix-chart",
        sorted.map(row => row[dateColumn]),
        datasets,
        "GWh"
    );
}


function renderNationalShareChart(records) {
    const yearColumn = findColumn(records, [
        "Year"
    ]);

    const renewableShareColumn = findColumn(records, [
        "Renewable Share",
        "Renewable_Share_Pct",
        "Renewable Share Pct",
        "Renewable_Share_Percent"
    ]);

    const fossilShareColumn = findColumn(records, [
        "Fossil Share",
        "Fossil_Share_Pct",
        "Fossil Share Pct",
        "Fossil_Share_Percent"
    ]);

    if (!yearColumn || !renewableShareColumn) {
        console.error(
            "Annual share columns not found.",
            records[0]
        );
        return;
    }

    const sorted = [...records].sort(
        (a, b) => Number(a[yearColumn]) - Number(b[yearColumn])
    );

    const datasets = [{
        label: "Renewable Share",
        data: sorted.map(row =>
            numericValue(row[renewableShareColumn])
        ),
        borderColor: CHART_COLORS.renewable,
        tension: 0.25
    }];

    if (fossilShareColumn) {
        datasets.push({
            label: "Fossil Share",
            data: sorted.map(row =>
                numericValue(row[fossilShareColumn])
            ),
            borderColor: CHART_COLORS.fossil,
            tension: 0.25
        });
    }

    renderLineChart(
        "nationalShare",
        "national-share-chart",
        sorted.map(row => row[yearColumn]),
        datasets,
        "%"
    );
}


/* ---------------------------------------------------------
   RENEWABLE SOURCE ANALYSIS
--------------------------------------------------------- */

function renderSourceGenerationChart(records) {
    const dateColumn = findColumn(records, [
        "Month",
        "Date"
    ]);

    if (!dateColumn) return;

    const sorted = sortByDate(records, dateColumn);

    const sources = [
        "Solar",
        "Wind",
        "Hydro",
        "Bioenergy",
        "Other Renewables"
    ];

    const datasets = sources
        .map(source => {
            const column = findSourceColumn(
                records,
                source,
                "generation"
            );

            if (!column) return null;

            return {
                label: source,
                data: sorted.map(row => numericValue(row[column])),
                borderColor: getSourceChartColor(source),
                tension: 0.25
            };
        })
        .filter(Boolean);

    renderLineChart(
        "sourceGeneration",
        "source-generation-chart",
        sorted.map(row => row[dateColumn]),
        datasets,
        "GWh"
    );
}


function renderSourceCompositionChart(records) {
    const sourceColumn = findColumn(records, [
        "Source"
    ]);

    const valueColumn = findColumn(records, [
        "Generation_GWh",
        "Generation GWh",
        "Generation"
    ]);

    if (!sourceColumn || !valueColumn) {
        console.error(
            "Source composition columns not found.",
            records[0]
        );
        return;
    }

    const validRecords = records.filter(
        row => numericValue(row[valueColumn]) !== null
    );

    renderDoughnutChart(
        "sourceComposition",
        "source-composition-chart",
        validRecords.map(row => row[sourceColumn]),
        validRecords.map(row => numericValue(row[valueColumn]))
    );
}


function renderSourceAnnualChart(records) {
    const yearColumn = findColumn(records, [
        "Year"
    ]);

    if (!yearColumn) return;

    const sorted = [...records].sort(
        (a, b) => Number(a[yearColumn]) - Number(b[yearColumn])
    );

    const sources = [
        "Solar",
        "Wind",
        "Hydro",
        "Bioenergy",
        "Other Renewables"
    ];

    const datasets = sources
        .map(source => {
            const column = findSourceColumn(
                records,
                source,
                "generation"
            );

            if (!column) return null;

            return {
                label: source,
                data: sorted.map(row => numericValue(row[column])),
                backgroundColor: getSourceChartColor(source),
                borderRadius: 3
            };
        })
        .filter(Boolean);

    renderBarChart(
        "sourceAnnual",
        "source-annual-chart",
        sorted.map(row => row[yearColumn]),
        datasets,
        "GWh"
    );
}


/* ---------------------------------------------------------
   CAPACITY ANALYSIS
--------------------------------------------------------- */

async function loadCapacityCharts() {
    try {
        const [
            annualCapacity,
            nationalCapacity,
            nationalFactors
        ] = await Promise.all([
            fetchAnalysisRecords("/capacity/state-annual"),
            fetchAnalysisRecords("/capacity/national"),
            fetchAnalysisRecords("/capacity-factors/national")
        ]);

        renderCapacityTrendChart(annualCapacity);
        renderCapacitySourceChart(nationalCapacity);
        renderCapacityFactorChart(nationalFactors);

    } catch (error) {
        console.error("Capacity analysis loading failed:", error);
    }
}



function renderCapacityTrendChart(records) {
    if (!records || !records.length) {
        console.error("No annual capacity records received.");
        return;
    }

    const sources = [
        { name: "Renewables", column: "Renewables_Average_MW" },
        { name: "Solar", column: "Solar_Average_MW" },
        { name: "Wind", column: "Wind_Average_MW" },
        { name: "Hydro", column: "Hydro_Average_MW" },
        { name: "Bioenergy", column: "Bioenergy_Average_MW" },
        { name: "Fossil", column: "Fossil_Average_MW" }
    ];

    const yearlyData = new Map();

    records.forEach(record => {
        const year = Number(record.Year);

        if (!Number.isFinite(year)) return;

        if (!yearlyData.has(year)) {
            yearlyData.set(year, { count: {}, totals: {} });

            sources.forEach(source => {
                yearlyData.get(year).count[source.name] = 0;
                yearlyData.get(year).totals[source.name] = 0;
            });
        }

        const yearData = yearlyData.get(year);

        sources.forEach(source => {
            const value = Number(record[source.column]);

            if (record[source.column] === null ||
                record[source.column] === "" ||
                !Number.isFinite(value)) {
                return;
            }

            yearData.totals[source.name] += value;
            yearData.count[source.name]++;
        });
    });

    const years = [...yearlyData.keys()].sort((a, b) => a - b);

    const datasets = sources.map(source => ({
        label: source.name,
        data: years.map(year => {
            const yearData = yearlyData.get(year);

            return yearData.count[source.name] > 0
                ? Number(yearData.totals[source.name].toFixed(2))
                : null;
        })
    }));

    renderLineChart(
        "capacityTrend",
        "capacity-trend-chart",
        years.map(String),
        datasets,
        "MW"
    );
}


function renderCapacitySourceChart(records) {
    const variableColumn = findColumn(records, [
        "Variable"
    ]);

    const valueColumn = findColumn(records, [
        "Latest National Capacity",
        "Latest_National_Capacity_MW",
        "Latest National Capacity MW"
    ]);

    if (!variableColumn || !valueColumn) {
        console.error(
            "National capacity columns not found.",
            records[0]
        );
        return;
    }

    const valid = records.filter(row =>
        numericValue(row[valueColumn]) !== null &&
        row[variableColumn] !== "Other Renewables"
    );

    renderBarChart(
        "capacitySource",
        "capacity-source-chart",
        valid.map(row => row[variableColumn]),
        [{
            label: "Latest National Capacity",
            data: valid.map(row => numericValue(row[valueColumn])),
            backgroundColor: CHART_COLORS.renewable,
            borderRadius: 4
        }],
        "MW"
    );
}



function renderCapacityFactorChart(records) {
    if (!records || !records.length) {
        console.error("No national capacity factor records received.");
        return;
    }

    const validRecords = records.filter(record => {
        const value = Number(record.Capacity_Weighted_Factor_Pct);

        return (
            record.Source &&
            record.Capacity_Weighted_Factor_Pct !== null &&
            record.Capacity_Weighted_Factor_Pct !== "" &&
            Number.isFinite(value)
        );
    });

    if (!validRecords.length) {
        console.error("No valid weighted capacity factor values found.");
        return;
    }

    const labels = validRecords.map(record => record.Source);

    const values = validRecords.map(record =>
        Number(Number(record.Capacity_Weighted_Factor_Pct).toFixed(2))
    );

    renderBarChart(
        "capacityFactor",
        "capacity-factor-chart",
        labels,
        [
            {
                label: "Weighted Capacity Factor",
                data: values
            }
        ],
        "%"
    );
}



/* ---------------------------------------------------------
   EMISSIONS ANALYSIS
--------------------------------------------------------- */

async function loadEmissionsCharts() {
    try {
        const [
            monthly,
            statePeriod
        ] = await Promise.all([
            fetchAnalysisRecords("/emissions/monthly"),
            fetchAnalysisRecords("/emissions/state-period")
        ]);

        renderEmissionsTrendChart(monthly);
        renderEmissionsStateChart(statePeriod);
        renderEmissionsIntensityChart(statePeriod);

    } catch (error) {
        console.error("Emissions analysis loading failed:", error);
    }
}


function renderEmissionsTrendChart(records) {
    const monthColumn = findColumn(records, [
        "Month"
    ]);

    const emissionsColumn = findColumn(records, [
        "Total_Emissions_ktCO2",
        "Total Emissions ktCO2"
    ]);

    if (!monthColumn || !emissionsColumn) {
        console.error(
            "Monthly emissions columns not found.",
            records[0]
        );
        return;
    }

    const grouped = groupRecords(
        records,
        monthColumn,
        emissionsColumn
    );

    renderLineChart(
        "emissionsTrend",
        "emissions-trend-chart",
        grouped.map(item => item[0]),
        [{
            label: "Total Emissions",
            data: grouped.map(item => item[1]),
            borderColor: CHART_COLORS.fossil,
            tension: 0.25
        }],
        "ktCO2"
    );
}


function renderEmissionsStateChart(records) {
    const stateColumn = findColumn(records, [
        "State"
    ]);

    const emissionsColumn = findColumn(records, [
        "Total_Emissions_ktCO2",
        "Total Emissions ktCO2"
    ]);

    if (!stateColumn || !emissionsColumn) return;

    const sorted = [...records]
        .filter(row => numericValue(row[emissionsColumn]) !== null)
        .sort((a, b) =>
            numericValue(b[emissionsColumn]) -
            numericValue(a[emissionsColumn])
        )
        .slice(0, 10);

    renderBarChart(
        "emissionsState",
        "emissions-state-chart",
        sorted.map(row => row[stateColumn]),
        [{
            label: "Total Emissions",
            data: sorted.map(row => numericValue(row[emissionsColumn])),
            backgroundColor: CHART_COLORS.fossil,
            borderRadius: 4
        }],
        "ktCO2"
    );
}


function renderEmissionsIntensityChart(records) {
    const stateColumn = findColumn(records, [
        "State"
    ]);

    const intensityColumn = findColumn(records, [
        "Generation_Weighted_CO2_Intensity_gCO2_kWh",
        "Generation Weighted CO2 Intensity gCO2 kWh",
        "Calculated_Period_CO2_Intensity_gCO2_kWh",
        "Calculated Period CO2 Intensity gCO2 kWh"
    ]);

    if (!stateColumn || !intensityColumn) {
        console.error(
            "Emissions intensity columns not found.",
            records[0]
        );
        return;
    }

    const sorted = [...records]
        .filter(row => numericValue(row[intensityColumn]) !== null)
        .sort((a, b) =>
            numericValue(b[intensityColumn]) -
            numericValue(a[intensityColumn])
        )
        .slice(0, 10);

    renderBarChart(
        "emissionsIntensity",
        "emissions-intensity-chart",
        sorted.map(row => row[stateColumn]),
        [{
            label: "CO2 Intensity",
            data: sorted.map(row => numericValue(row[intensityColumn])),
            backgroundColor: CHART_COLORS.fossil,
            borderRadius: 4
        }],
        "gCO2/kWh"
    );
}


/* ---------------------------------------------------------
   LOAD ALL ANALYSIS SECTIONS
--------------------------------------------------------- */

async function loadAnalysisSections() {
    await Promise.allSettled([
        loadNationalCharts(),
        loadCapacityCharts(),
        loadEmissionsCharts()
    ]);
}

/* =========================================================
   16. MAP CONTROL EVENTS
========================================================= */

function setupMapControls() {
    if (metricSelect) {
        metricSelect.addEventListener("change", () => {
            loadMapData();

            if (selectedRegion) {
                loadRegionTrend(selectedRegion);
            }
        });
    }

    if (periodSelect) {
        periodSelect.addEventListener("change", updateDateControl);
    }

    if (dateInput) {
        dateInput.addEventListener("change", loadMapData);
    }

    if (resetButton) {
        resetButton.addEventListener("click", resetMapControls);
    }
}


function updateDateControl() {
    if (!periodSelect || !dateInput) return;

    const period = periodSelect.value;

    if (period === "annual") {
        dateInput.type = "number";
        dateInput.min = "2021";
        dateInput.max = "2025";
        dateInput.step = "1";
        dateInput.value = "2025";
    } else {
        dateInput.type = "month";
        dateInput.min = "2021-07";
        dateInput.max = "2025-11";
        dateInput.value = "2025-11";
    }

    loadMapData();
}


function resetMapControls() {
    if (metricSelect) metricSelect.value = "renewable_share";

    if (periodSelect) periodSelect.value = "monthly";

    if (dateInput) {
        dateInput.type = "month";
        dateInput.min = "2021-07";
        dateInput.max = "2025-11";
        dateInput.value = "2025-11";
    }

    if (selectedLayer && selectedRegion) {
        applyRegionStyle(selectedRegion);
    }

    selectedLayer = null;
    selectedRegion = null;

    loadMapData();

    if (regionDetails) {
        regionDetails.innerHTML = `
            <div class="details-placeholder">
                <p>
                    Select a State or Union Territory to view
                    its metric value and historical information.
                </p>
            </div>
        `;
    }

    destroyChart("regionTrend");
}


/* =========================================================
   17. ANALYSIS CONTROL EVENTS
========================================================= */

function setupAnalysisControls() {
    const nationalControls = [
        "national-period",
        "national-metric"
    ];

    const sourceControls = [
        "source-period",
        "source-metric"
    ];

    const capacityControls = [
        "capacity-metric",
        "capacity-source"
    ];

    const emissionsControls = [
        "emissions-metric"
    ];

    nationalControls.forEach(id => {
        const element = document.getElementById(id);

        if (element) {
            element.addEventListener("change", loadNationalCharts);
        }
    });

    sourceControls.forEach(id => {
        const element = document.getElementById(id);

        if (element) {
            element.addEventListener("change", loadNationalCharts);
        }
    });

    capacityControls.forEach(id => {
        const element = document.getElementById(id);

        if (element) {
            element.addEventListener("change", loadCapacityCharts);
        }
    });

    emissionsControls.forEach(id => {
        const element = document.getElementById(id);

        if (element) {
            element.addEventListener("change", loadEmissionsCharts);
        }
    });
}

/* =========================================================
   18. APPLICATION STARTUP
========================================================= */

function initializeApplication() {
    setupNavigation();

    setupMapControls();

    setupAnalysisControls();

    initializeMap();

    loadAnalysisSections();
}


document.addEventListener("DOMContentLoaded", initializeApplication);
