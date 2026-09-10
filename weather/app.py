"""
Weather Dashboard - a completely self-contained single-file Flask app.

Live weather data comes from Open-Meteo (https://open-meteo.com), a free
API that requires no API key. Only the Python standard library is used for
the HTTP calls, so nothing beyond Flask itself needs to be installed.

Run:
    python3 app.py

Then open http://127.0.0.1:8000 in your browser.
"""

import json
import urllib.parse
import urllib.request

from flask import Flask, jsonify, render_template_string, request

app = Flask(__name__)

# ---------------------------------------------------------------------------
# Live weather data from Open-Meteo (free, no API key required).
#   1. Geocoding API resolves the city name to coordinates.
#   2. Forecast API returns current conditions for those coordinates.
# ---------------------------------------------------------------------------
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HTTP_TIMEOUT_SECONDS = 10

# WMO weather interpretation codes -> dashboard conditions. The four values
# below match the themes defined in the front-end, so every response gets an
# exact icon/color match.
WMO_CONDITIONS = {
    0: "Sunny",
    1: "Cloudy",
    2: "Cloudy",
    3: "Cloudy",
    45: "Cloudy",
    48: "Cloudy",
    51: "Rainy",
    53: "Rainy",
    55: "Rainy",
    56: "Snowy",
    57: "Snowy",
    61: "Rainy",
    63: "Rainy",
    65: "Rainy",
    66: "Rainy",
    67: "Rainy",
    71: "Snowy",
    73: "Snowy",
    75: "Snowy",
    77: "Snowy",
    80: "Rainy",
    81: "Rainy",
    82: "Rainy",
    85: "Snowy",
    86: "Snowy",
    95: "Rainy",
    96: "Rainy",
    99: "Rainy",
}


def _http_get_json(url):
    with urllib.request.urlopen(url, timeout=HTTP_TIMEOUT_SECONDS) as response:
        return json.load(response)


def _geocode(city):
    """Resolve `city` to an Open-Meteo geocoding result. Raises LookupError
    if the city cannot be found."""
    geo_query = urllib.parse.urlencode(
        {"name": city, "count": 1, "language": "en", "format": "json"}
    )
    place = (_http_get_json("%s?%s" % (GEOCODING_URL, geo_query)).get("results") or [None])[0]
    if place is None:
        raise LookupError(city)
    return place


def fetch_weather(city, units="f"):
    """Resolve `city` and return its current conditions from Open-Meteo.

    Temperature is returned in the given unit ('c' or 'f'). Raises LookupError
    if the city cannot be found. Other failures (network errors, timeouts,
    unexpected API responses) propagate to the caller.
    """
    place = _geocode(city)

    forecast_query = urllib.parse.urlencode(
        {
            "latitude": place["latitude"],
            "longitude": place["longitude"],
            "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "temperature_unit": "fahrenheit" if units == "f" else "celsius",
            "timezone": "auto",
            "forecast_days": 5,
        }
    )
    full_forecast = _http_get_json("%s?%s" % (FORECAST_URL, forecast_query))
    current = full_forecast["current"]
    daily = full_forecast.get("daily", {"time": [], "temperature_2m_max": [], "temperature_2m_min": [], "weather_code": []})

    country = place.get("country") or ""
    city_name = "%s, %s" % (place["name"], country) if country else place["name"]

    return {
        "city": city_name,
        "temperature": round(current["temperature_2m"]),
        "humidity": int(round(current["relative_humidity_2m"])),
        "wind_speed": int(round(current["wind_speed_10m"])),
        "condition": WMO_CONDITIONS.get(current["weather_code"], "Cloudy"),
        "forecast": [
            {
                "date": date,
                "temp_max": round(t_max),
                "temp_min": round(t_min),
                "condition": WMO_CONDITIONS.get(w_code, "Cloudy"),
            }
            for date, t_max, t_min, w_code in zip(
                daily["time"],
                daily["temperature_2m_max"],
                daily["temperature_2m_min"],
                daily["weather_code"],
            )
        ],
    }


def fetch_map_weather(city, units="f"):
    """Resolve `city` and return current conditions at its location.

    Raises LookupError if the city cannot be found. Other failures (network
    errors, timeouts, unexpected API responses) propagate to the caller.
    """
    place = _geocode(city)
    lat0 = place["latitude"]
    lon0 = place["longitude"]

    map_query = urllib.parse.urlencode(
        {
            "latitude": lat0,
            "longitude": lon0,
            "current": "temperature_2m,weather_code",
            "temperature_unit": "fahrenheit" if units == "f" else "celsius",
        }
    )
    result = _http_get_json("%s?%s" % (FORECAST_URL, map_query))

    country = place.get("country") or ""
    city_name = "%s, %s" % (place["name"], country) if country else place["name"]

    return {
        "city": city_name,
        "center": {"lat": lat0, "lon": lon0},
        "points": [
            {
                "lat": result["latitude"],
                "lon": result["longitude"],
                "temperature": round(result["current"]["temperature_2m"]),
                "condition": WMO_CONDITIONS.get(result["current"]["weather_code"], "Cloudy"),
            }
        ],
    }


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Weather Dashboard</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>.leaflet-pane img { max-width: none !important; }</style>
</head>
<body class="min-h-full bg-fixed bg-gradient-to-br from-slate-900 via-indigo-950 to-slate-900 text-white flex items-center justify-center p-6">
  <div class="w-full max-w-md lg:max-w-4xl">
    <h1 class="text-3xl font-bold text-center mb-1">Weather Dashboard</h1>
    <p class="text-center text-slate-400 mb-6 text-sm">Search a city to see current conditions</p>

    <form id="search-form" class="flex gap-3 mb-4" autocomplete="off">
      <input
        id="city-input"
        type="text"
        placeholder="e.g. New York"
        class="flex-1 min-w-0 rounded-xl bg-white/10 border border-white/20 px-4 py-3 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-400"
      />
      <button
        id="search-btn"
        type="submit"
        class="rounded-xl bg-indigo-500 hover:bg-indigo-400 disabled:opacity-50 disabled:cursor-not-allowed px-6 py-3 font-semibold transition"
      >Search</button>
    </form>

    <div id="unit-toggle" class="flex justify-center gap-2 mb-5">
      <button data-unit="c" type="button" class="unit-btn px-4 py-1.5 rounded-full text-sm border transition bg-white/10 border-white/10 hover:bg-white/20">&deg;C</button>
      <button data-unit="f" type="button" class="unit-btn px-4 py-1.5 rounded-full text-sm border transition bg-indigo-500 border-indigo-400 font-semibold">&deg;F</button>
    </div>

    <div id="suggestions" class="flex flex-wrap items-center gap-2 justify-center mb-5">
      <span class="text-xs text-slate-500">Try:</span>
      <button data-city="New York" class="chip px-3 py-1 rounded-full text-xs bg-white/10 hover:bg-white/20 border border-white/10 transition">New York</button>
      <button data-city="London" class="chip px-3 py-1 rounded-full text-xs bg-white/10 hover:bg-white/20 border border-white/10 transition">London</button>
      <button data-city="Tokyo" class="chip px-3 py-1 rounded-full text-xs bg-white/10 hover:bg-white/20 border border-white/10 transition">Tokyo</button>
      <button data-city="Moscow" class="chip px-3 py-1 rounded-full text-xs bg-white/10 hover:bg-white/20 border border-white/10 transition">Moscow</button>
    </div>

    <div id="status" class="text-center text-sm mb-4" aria-live="polite"></div>

    <div class="flex flex-col lg:flex-row gap-5 items-stretch">
      <div
        id="weather-card"
        class="hidden flex-1 rounded-2xl bg-white/10 backdrop-blur border border-white/10 p-6 shadow-2xl"
      ></div>

      <div id="map-card" class="hidden flex-1 flex flex-col rounded-2xl bg-white/10 backdrop-blur border border-white/10 p-4 shadow-2xl">
        <h3 class="text-sm font-semibold text-slate-400 mb-3 uppercase tracking-wider px-2">Area Map</h3>
        <div id="weather-map" class="w-full h-72 lg:h-auto lg:flex-1 min-h-[18rem] rounded-xl overflow-hidden"></div>
      </div>
    </div>
  </div>

  <script>
    var SUN_SVG = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4"/><path d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32 1.41 1.41M2 12h2m16 0h2M6.34 17.66l-1.41 1.41M19.07 4.93l-1.41 1.41"/></svg>';
    var CLOUD_SVG = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M18 10h-1.26A8 8 0 1 0 9 20h9a4 4 0 0 0 0-8z"/></svg>';
    var RAIN_SVG = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M16 14v6M8 14v6M12 16v6"/></svg>';
    var SNOW_SVG = '<svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/><path d="M8 15h.01M8 19h.01M12 17h.01M12 21h.01M16 15h.01M16 19h.01"/></svg>';

    var THEMES = {
      "Sunny":  { icon: SUN_SVG,   color: "#fbbf24", badge: "rgba(251, 191, 36, 0.15)" },
      "Rainy":  { icon: RAIN_SVG,  color: "#60a5fa", badge: "rgba(96, 165, 250, 0.15)" },
      "Cloudy": { icon: CLOUD_SVG, color: "#cbd5e1", badge: "rgba(203, 213, 225, 0.15)" },
      "Snowy":  { icon: SNOW_SVG,  color: "#a5b4fc", badge: "rgba(165, 180, 252, 0.15)" }
    };
    var FALLBACK_THEME = THEMES["Cloudy"];

    var form = document.getElementById("search-form");
    var input = document.getElementById("city-input");
    var btn = document.getElementById("search-btn");
    var card = document.getElementById("weather-card");
    var status = document.getElementById("status");
    var mapCard = document.getElementById("map-card");
    var leafletMap = null;
    var mapMarkers = [];
    var unit = "f";

    function escapeHtml(value) {
      var div = document.createElement("div");
      div.textContent = value;
      return div.innerHTML;
    }

    function setStatus(message, isError) {
      status.textContent = message;
      status.className = "text-center text-sm mb-4 " +
        (isError ? "text-rose-300" : "text-emerald-300");
    }

    function renderCard(data) {
      var theme = THEMES[data.condition] || FALLBACK_THEME;
      var cityName = escapeHtml(data.city);
      var condition = escapeHtml(data.condition);
      var degreeSymbol = unit === "c" ? "&deg;C" : "&deg;F";

      var forecastHtml = "";
      if (data.forecast && data.forecast.length > 0) {
        forecastHtml = '<div class="mt-8 pt-6 border-t border-white/10"><h3 class="text-sm font-semibold text-slate-400 mb-4 uppercase tracking-wider">5-Day Forecast</h3><div class="grid grid-cols-5 gap-2">';
        data.forecast.forEach(function(day) {
          var dayTheme = THEMES[day.condition] || FALLBACK_THEME;
          var parts = day.date.split("-");
          var date = new Date(Number(parts[0]), Number(parts[1]) - 1, Number(parts[2])).toLocaleDateString(undefined, { weekday: "short" });
          forecastHtml +=
            '<div class="text-center">' +
              '<div class="text-xs text-slate-400 mb-1">' + date + '</div>' +
              '<div class="flex justify-center my-1">' + dayTheme.icon + '</div>' +
              '<div class="text-sm font-bold">' + Math.round(day.temp_max) + "&#176;" +
              '</div><div class="text-[10px] text-slate-400">' + Math.round(day.temp_min) + "&#176;" +
            '</div>' +
          '</div>';
        });
        forecastHtml += '</div></div>';
      }

      card.innerHTML =
        '<div class="flex items-start justify-between mb-4">' +
          "<div>" +
            '<h2 class="text-2xl font-bold">' + cityName + "</h2>" +
            '<div class="mt-2 flex items-center gap-2" style="color:' + theme.color + '">' +
              '<span>' + theme.icon + "</span>" +
              '<span class="px-3 py-1 rounded-full text-sm font-medium" style="background:' + theme.badge + '">' + condition + "</span>" +
            "</div>" +
          "</div>" +
        "</div>" +
        '<div class="text-6xl font-extrabold mb-6">' + data.temperature + degreeSymbol + "</div>" +
        '<div class="grid grid-cols-2 gap-4">' +
          '<div class="rounded-xl bg-white/10 p-4 text-center">' +
            '<div class="text-slate-300 text-sm mb-1">Humidity</div>' +
            '<div class="text-xl font-semibold">' + data.humidity + "%</div>" +
          "</div>" +
          '<div class="rounded-xl bg-white/10 p-4 text-center">' +
            '<div class="text-slate-300 text-sm mb-1">Wind</div>' +
            '<div class="text-xl font-semibold">' + data.wind_speed + " km/h</div>" +
          "</div>" +
        "</div>" +
        forecastHtml;

      card.classList.remove("hidden");
    }

    function tempColor(temp, minTemp, maxTemp) {
      var span = maxTemp - minTemp;
      var frac = span > 0 ? (temp - minTemp) / span : 0.5;
      return "hsl(" + Math.round(240 * (1 - frac)) + ", 85%, 60%)";
    }

    function loadMap(city) {
      mapCard.classList.add("hidden");
      fetch("/api/map?city=" + encodeURIComponent(city) + "&units=" + unit).then(function (res) {
        return res.json().then(function (data) {
          if (!res.ok) {
            return;
          }
          drawMap(data);
        });
      }).catch(function () {});
    }

    function drawMap(data) {
      var center = data.center;
      mapCard.classList.remove("hidden");

      if (!leafletMap) {
        leafletMap = L.map("weather-map", { scrollWheelZoom: false }).setView([center.lat, center.lon], 13);
        L.tileLayer("https://tile.openstreetmap.org/{z}/{x}/{y}.png", {
          maxZoom: 18,
          attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
        }).addTo(leafletMap);
      } else {
        leafletMap.setView([center.lat, center.lon], 13);
      }

      var temps = [];
      data.points.forEach(function (point) {
        temps.push(point.temperature);
      });
      var minTemp = Math.min.apply(null, temps);
      var maxTemp = Math.max.apply(null, temps);

      mapMarkers.forEach(function (marker) {
        marker.remove();
      });
      mapMarkers = [];

      data.points.forEach(function (point) {
        var color = tempColor(point.temperature, minTemp, maxTemp);
        var marker = L.circleMarker([point.lat, point.lon], {
          radius: 13,
          color: "#ffffff",
          weight: 1,
          fillColor: color,
          fillOpacity: 0.85
        }).bindTooltip(point.temperature + (unit === "c" ? "&deg;C" : "&deg;F") + " &middot; " + escapeHtml(point.condition));
        marker.addTo(leafletMap);
        mapMarkers.push(marker);
      });

      leafletMap.invalidateSize();
    }

    async function search(city) {
      var trimmed = city.trim();
      if (!trimmed) {
        setStatus("Please enter a city name.", true);
        return;
      }

      btn.disabled = true;
      btn.textContent = "Searching...";
      card.classList.add("hidden");
      mapCard.classList.add("hidden");

      try {
        var res = await fetch("/api/weather?city=" + encodeURIComponent(trimmed) + "&units=" + unit);
        var data = await res.json();

        if (!res.ok) {
          setStatus(data.error || "Could not load weather data.", true);
          return;
        }

        setStatus("");
        renderCard(data);
        loadMap(trimmed);
      } catch (err) {
        setStatus("Network error - is the server still running?", true);
      } finally {
        btn.disabled = false;
        btn.textContent = "Search";
      }
    }

    form.addEventListener("submit", function (event) {
      event.preventDefault();
      search(input.value);
    });

    document.querySelectorAll(".chip").forEach(function (chip) {
      chip.addEventListener("click", function () {
        input.value = chip.getAttribute("data-city");
        search(input.value);
      });
    });

    var unitButtons = document.querySelectorAll(".unit-btn");

    function setUnit(next) {
      if (next === unit) return;
      unit = next;
      unitButtons.forEach(function (button) {
        var active = button.getAttribute("data-unit") === unit;
        button.className = "unit-btn px-4 py-1.5 rounded-full text-sm border transition " +
          (active ? "bg-indigo-500 border-indigo-400 font-semibold" : "bg-white/10 border-white/10 hover:bg-white/20");
      });
      if (input.value.trim()) {
        search(input.value);
      }
    }

    unitButtons.forEach(function (button) {
      button.addEventListener("click", function () {
        setUnit(button.getAttribute("data-unit"));
      });
    });

    window.addEventListener("resize", function () {
      if (leafletMap) leafletMap.invalidateSize();
    });

    input.focus();
  </script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)


@app.route("/api/weather")
def api_weather():
    city = (request.args.get("city") or "").strip()

    if not city:
        return jsonify({"error": "Missing 'city' query parameter."}), 400

    units = (request.args.get("units") or "f").strip().lower()
    if units not in ("c", "f"):
        return jsonify({"error": "'units' must be 'c' or 'f'."}), 400

    try:
        data = fetch_weather(city, units)
    except LookupError:
        return (
            jsonify(
                {
                    "error": "City '%s' not found. Try a different spelling or a larger town."
                    % city
                }
            ),
            404,
        )
    except Exception:
        app.logger.exception("Weather lookup failed for %r", city)
        return (
            jsonify(
                {
                    "error": "The weather service is unavailable right now. Please try again in a moment."
                }
            ),
            502,
        )

    return jsonify(data)


@app.route("/api/map")
def api_map():
    city = (request.args.get("city") or "").strip()

    if not city:
        return jsonify({"error": "Missing 'city' query parameter."}), 400

    units = (request.args.get("units") or "f").strip().lower()
    if units not in ("c", "f"):
        return jsonify({"error": "'units' must be 'c' or 'f'."}), 400

    try:
        data = fetch_map_weather(city, units)
    except LookupError:
        return (
            jsonify(
                {
                    "error": "City '%s' not found. Try a different spelling or a larger town."
                    % city
                }
            ),
            404,
        )
    except Exception:
        app.logger.exception("Map lookup failed for %r", city)
        return (
            jsonify(
                {
                    "error": "The weather service is unavailable right now. Please try again in a moment."
                }
            ),
            502,
        )

    return jsonify(data)


if __name__ == "__main__":
    app.run(debug=True, port=8000)
