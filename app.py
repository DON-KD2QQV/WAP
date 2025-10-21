#!/usr/bin/python3
"""
Weather Alert Pro - Real-time Weather Application
A comprehensive weather monitoring application that fetches real-time data from OpenWeatherMap API and NOAA.

Features:
- Country State City or zipcode lookup with the capitals of each Country automatically selected for instant weather information anywhere
- Current weather conditions with temperature graphs
- 5-day and detailed forecasts  
- Air quality monitoring with pollutant breakdowns
- UV index with safety interpretations
- Weather alerts for severe conditions
- Interactive US radar maps with NOAA data
- ZIP code lookup and favorites management
- Responsive UI with zoom/pan controls

Author: Donald Bryant
Copyright: © 2025 Donald Bryant  
License: MIT License
Version: 1.0.1
Created: August 2025

Dependencies:
- Python 3.x
- flup advanced web server integration
- flask lets you create web servers and REST APIs in Python
- requests for API calls
- OpenWeatherMap API key required

This project demonstrates advanced Python programming with:
- REST API integration (OpenWeatherMap, NOAA)
- Interactive GUI development with Kivy
- Data visualization with matplotlib
- Real-time weather data processing
- Professional error handling and resource management

MIT License

Copyright (c) 2025 Donald Bryant

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

# Weather Alert Pro - Real-time Weather Application  
# Copyright (c) 2025 Donald Bryant
# This software fetches real-time weather data from OpenWeatherMap and NOAA
# --- Imports ---
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'site-packages'))
# Copy this file to cgi-bin/app.py
from flask import Flask, request, render_template, jsonify, send_from_directory
import json
import time
import requests
import traceback

def decode_bytes(obj):
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    elif isinstance(obj, dict):
        return {k: decode_bytes(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [decode_bytes(v) for v in obj]
    else:
        return obj
        
app = Flask(__name__, template_folder='templates', static_folder='static')

# Weather alerts endpoint
@app.route('/api/alerts', methods=['POST'])
def api_alerts():
    allowed, usage_count = increment_api_counter()
    if not allowed:
        return jsonify(success=False, error=f"API daily limit of {API_DAILY_LIMIT} reached. Try again tomorrow.")
    try:
        data = request.get_json(force=True, silent=True) or {}
        city = data.get('city')
        state = data.get('state')
        zip_code = data.get('zip_code')
        country = data.get('country')
        units = data.get('units', 'imperial')

        if not API_KEY:
            return jsonify(success=False, error='API key not set')

        lat, lon, city, state = get_location(city, state, zip_code, country)
        if not lat or not lon:
            return jsonify(success=False, error='Location not found')

        cache_key = f'{lat},{lon},{units}'
        cached = get_cached_result('alerts', cache_key)
        if cached:
            return jsonify(success=True, data=cached, city=city, state=state, country=country, cached=True)

        url = f'https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={API_KEY}&units={units}'
        try:
            resp = requests.get(url, timeout=10)
        except Exception as e:
            return jsonify(success=False, error=f'Alerts API request failed: {str(e)}')

        if not resp.ok:
            try:
                err = resp.json()
                err_msg = err.get('message', str(err))
            except Exception:
                err_msg = resp.text
            return jsonify(success=False, error=f'Alerts API error: {err_msg}')

        result = resp.json()
        alerts = result.get('alerts', [])
        response_data = decode_bytes({'alerts': alerts})
        set_cached_result('alerts', cache_key, response_data)
        return jsonify(success=True, data=response_data, city=city, state=state, country=country, cached=False)
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify(success=False, error=f"Internal server error: {str(e)}\n{tb}")

# User-friendly HTML dashboard for API usage and cache
@app.route('/api/usage/html', methods=['GET'])
def api_usage_html():
    today, count = get_api_usage()
    cache = load_cache()
    # Read recent API usage log entries
    usage_log_rows = ""
    log_path = os.path.join(os.path.dirname(__file__), 'api_usage_log.txt')
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()[-50:]  # Show last 50 entries
        for line in reversed(lines):
            parts = line.strip().split('|')
            if len(parts) == 4:
                dt, endpoint, ip, location = [p.strip() for p in parts]
                usage_log_rows += f"<tr><td>{dt}</td><td>{endpoint}</td><td>{ip}</td><td>{location}</td></tr>"
    except Exception:
        usage_log_rows = "<tr><td colspan='4'>No usage log found or error reading log.</td></tr>"

    html = f"""
    <html>
    <head>
        <title>API Usage Dashboard</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 2em; }}
            table {{ border-collapse: collapse; width: 100%; margin-bottom: 2em; }}
            th, td {{ border: 1px solid #ccc; padding: 8px; text-align: left; }}
            th {{ background: #f0f0f0; }}
            .section {{ margin-bottom: 2em; }}
        </style>
    </head>
    <body>
        <h1>API Usage Dashboard</h1>
        <div class="section">
            <h2>Usage</h2>
            <table>
                <tr><th>Date</th><td>{today}</td></tr>
                <tr><th>API Requests Today</th><td>{count}</td></tr>
                <tr><th>API Daily Limit</th><td>{API_DAILY_LIMIT}</td></tr>
            </table>
        </div>
        <div class="section">
            <h2>Recent API Usage Log (IP & Location)</h2>
            <table>
                <tr><th>Date/Time</th><th>Endpoint</th><th>IP</th><th>Location</th></tr>
                {usage_log_rows}
            </table>
        </div>
        <div class="section">
            <h2>Cache Contents</h2>
            <table>
                <tr><th>Feature</th><th>Key</th><th>Timestamp</th><th>Data (truncated)</th></tr>
    """
    for feature, items in cache.items():
        for key, (ts, data) in items.items():
            short_data = str(data)
            if len(short_data) > 100:
                short_data = short_data[:100] + '...'
            html += f"<tr><td>{feature}</td><td>{key}</td><td>{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(ts))}</td><td>{short_data}</td></tr>"
    html += """
            </table>
        </div>
    </body>
    </html>
    """
    return html

# Endpoint to view API usage and cache contents
@app.route('/api/usage', methods=['GET'])
def api_usage():
    today, count = get_api_usage()
    cache = load_cache()
    return jsonify({
        'date': today,
        'api_requests_today': count,
        'api_daily_limit': API_DAILY_LIMIT,
        'cache': cache
    })

# --- File-based API usage counter ---
API_COUNTER_FILE = os.path.join(os.path.dirname(__file__), 'api_counter.txt')
API_DAILY_LIMIT = 1000
# --- API usage log with IP and location ---
API_USAGE_LOG_FILE = os.path.join(os.path.dirname(__file__), 'api_usage_log.txt')
def log_api_usage(endpoint):
    ip = request.remote_addr or 'unknown'
    location = 'unknown'
    try:
        geo_resp = requests.get(f'http://ip-api.com/json/{ip}', timeout=3)
        if geo_resp.ok:
            geo = geo_resp.json()
            if geo.get('status') == 'success':
                location = f"{geo.get('city','')}, {geo.get('regionName','')}, {geo.get('country','')}"
    except Exception:
        pass
    log_line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {endpoint} | {ip} | {location}\n"
    try:
        with open(API_USAGE_LOG_FILE, 'a') as f:
            f.write(log_line)
    except Exception:
        pass

# --- Daily Reset Logic ---
def daily_reset():
    today = time.strftime('%Y-%m-%d')
    # Reset API usage log if date changed
    log_path = API_USAGE_LOG_FILE
    counter_path = API_COUNTER_FILE
    cache_path = CACHE_FILE
    # Check counter file for date
    last_date = None
    if os.path.exists(counter_path):
        try:
            with open(counter_path, 'r') as f:
                line = f.read().strip()
                if line:
                    last_date = line.split(',')[0]
        except Exception:
            pass
    if last_date != today:
        # Clear log file
        try:
            with open(log_path, 'w') as f:
                f.write('')
        except Exception:
            pass
        # Clear cache file
        try:
            with open(cache_path, 'w') as f:
                json.dump({}, f)
        except Exception:
            pass
        # Reset counter file
        try:
            with open(counter_path, 'w') as f:
                f.write(f'{today},0')
        except Exception:
            pass

def get_api_usage():
    daily_reset()
    today = time.strftime('%Y-%m-%d')
    if not os.path.exists(API_COUNTER_FILE):
        return today, 0
    try:
        with open(API_COUNTER_FILE, 'r') as f:
            line = f.read().strip()
            if line:
                date, count = line.split(',')
                if date == today:
                    return date, int(count)
    except Exception:
        pass
    return today, 0

def increment_api_counter():
    today, count = get_api_usage()
    if count >= API_DAILY_LIMIT:
        return False, count
    count += 1
    with open(API_COUNTER_FILE, 'w') as f:
        f.write(f'{today},{count}')
    return True, count

# --- File-based cache ---
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'api_cache.json')
CACHE_TTL = 900  # 15 minutes
def load_cache():
    if not os.path.exists(CACHE_FILE):
        return {}
    try:
        with open(CACHE_FILE, 'r') as f:
            return json.load(f)
    except Exception:
        return {}

def save_cache(cache):
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def get_cached_result(feature, key):
    cache = load_cache()
    entry = cache.get(feature, {}).get(key)
    if entry:
        ts, data = entry
        if time.time() - ts < CACHE_TTL:
            return data
    return None

def set_cached_result(feature, key, data):
    cache = load_cache()
    if feature not in cache:
        cache[feature] = {}
    cache[feature][key] = [time.time(), data]
    save_cache(cache)

API_KEY = None
API_KEY_PATH = os.path.join(os.path.dirname(__file__), 'apikey.txt')
if os.path.exists(API_KEY_PATH):
    with open(API_KEY_PATH) as f:
        API_KEY = f.read().strip()
# Removed debug print for API_KEY

# Helper to get lat/lon from city/state/zip

def get_location(city, state, zip_code, country=None):
    # Default country to US if state is provided and country is missing
    if not country and state:
        country = 'US'
    # Try zip code lookup (US only, fallback to global if country provided)
    if zip_code:
        if country and country.upper() != 'US':
            # Try Zippopotam.us for other countries
            resp = requests.get(f'https://api.zippopotam.us/{country.lower()}/{zip_code}')
        else:
            resp = requests.get(f'https://api.zippopotam.us/us/{zip_code}')
        if resp.ok:
            data = resp.json()
            lat = float(data['places'][0]['latitude'])
            lon = float(data['places'][0]['longitude'])
            city = data['places'][0]['place name']
            state = data['places'][0].get('state abbreviation', '')
            return lat, lon, city, state
    # City/country/state lookup (global)
    if city:
        city_clean = city.strip().title()
        geo_url = 'https://api.openweathermap.org/geo/1.0/direct'
        key = API_KEY or os.environ.get('OPENWEATHERMAP_API_KEY')
        q = city_clean
        if state:
            q += f',{state.strip()}'
        if country:
            q += f',{country.strip()}'
        params = {
            'q': q,
            'limit': 1,
            'appid': key
        }
        print(f"DEBUG: Geocoding query: {params['q']}", file=sys.stderr)
        resp = requests.get(geo_url, params=params)
        try:
            data = resp.json()
        except Exception:
            data = None
        print(f"DEBUG: Geocoding API response: {data}", file=sys.stderr)
        if resp.ok and data and len(data) > 0:
            d = data[0]
            return d['lat'], d['lon'], d.get('name', city_clean), d.get('state', state)
    return None, None, city, state

@app.route('/')
def index():
    return render_template('weather_alert_pro.html')

@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory(os.path.join(app.root_path, 'static'), filename)

@app.route('/api/weather', methods=['POST'])
def api_weather():
    log_api_usage('/api/weather')
    allowed, usage_count = increment_api_counter()
    if not allowed:
        return jsonify(success=False, error=f"API daily limit of {API_DAILY_LIMIT} reached. Try again tomorrow.")
    try:
        data = request.get_json(force=True, silent=True) or {}
        city = data.get('city')
        state = data.get('state')
        zip_code = data.get('zip_code')
        country = data.get('country')
        units = data.get('units', 'imperial')

        if not API_KEY:
            return jsonify(success=False, error='API key not set')

        lat, lon, city, state = get_location(city, state, zip_code, country)
        if not lat or not lon:
            return jsonify(success=False, error='Location not found')

        cache_key = f'{lat},{lon},{units}'
        cached = get_cached_result('weather', cache_key)
        if cached:
            return jsonify(success=True, data=cached, city=city, state=state, country=country, cached=True)

        url = f'https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={API_KEY}&units={units}'
        try:
            resp = requests.get(url, timeout=10)
        except Exception as e:
            return jsonify(success=False, error=f'Weather API request failed: {str(e)}')

        if not resp.ok:
            try:
                err = resp.json()
                err_msg = err.get('message', str(err))
            except Exception:
                err_msg = resp.text
            return jsonify(success=False, error=f'Weather API error: {err_msg}')

        result = resp.json()
        current = result.get('current', {})
        # Wind direction conversion
        def deg_to_compass(deg):
            dirs = ['N', 'NNE', 'NE', 'ENE', 'E', 'ESE', 'SE', 'SSE',
                    'S', 'SSW', 'SW', 'WSW', 'W', 'WNW', 'NW', 'NNW']
            ix = int((deg/22.5)+0.5) % 16
            return dirs[ix]
        wind_deg = current.get('wind_deg')
        wind_dir = deg_to_compass(wind_deg) if wind_deg is not None else None
        wind_speed_mps = current.get('wind_speed', 0)
        wind_speed_mph = round(wind_speed_mps * 2.23694, 2)
        pressure_hpa = current.get('pressure', 0)
        pressure_inhg = round(pressure_hpa * 0.02953, 2)
        # Build enhanced current data
        enhanced_current = dict(current)
        enhanced_current['wind_direction_degrees'] = wind_deg
        enhanced_current['wind_direction_compass'] = wind_dir
        enhanced_current['wind_speed_mph'] = wind_speed_mph
        enhanced_current['pressure_inhg'] = pressure_inhg
        response_data = {
            'current': enhanced_current,
            'location': {'city': city, 'state': state, 'lat': lat, 'lon': lon, 'country': country},
            'timezone_offset': result.get('timezone_offset', 0)
        }
        response_data = decode_bytes(response_data)
        set_cached_result('weather', cache_key, response_data)
        return jsonify(success=True, data=response_data, cached=False)
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify(success=False, error=f"Internal server error: {str(e)}\n{tb}")

@app.route('/api/forecast', methods=['POST'])
def api_forecast():
    log_api_usage('/api/forecast')
    allowed, usage_count = increment_api_counter()
    if not allowed:
        return jsonify(success=False, error=f"API daily limit of {API_DAILY_LIMIT} reached. Try again tomorrow.")
    try:
        data = request.get_json(force=True, silent=True) or {}
        city = data.get('city')
        state = data.get('state')
        zip_code = data.get('zip_code')
        country = data.get('country')
        units = data.get('units', 'imperial')

        if not API_KEY:
            return jsonify(success=False, error='API key not set')

        lat, lon, city, state = get_location(city, state, zip_code, country)
        if not lat or not lon:
            return jsonify(success=False, error='Location not found')

        cache_key = f'{lat},{lon},{units}'
        cached = get_cached_result('forecast', cache_key)
        if cached:
            return jsonify(success=True, data=cached, city=city, state=state, country=country, cached=True)

        url = f'https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={API_KEY}&units={units}'
        try:
            resp = requests.get(url, timeout=10)
        except Exception as e:
            return jsonify(success=False, error=f'Forecast API request failed: {str(e)}')

        if not resp.ok:
            try:
                err = resp.json()
                err_msg = err.get('message', str(err))
            except Exception:
                err_msg = resp.text
            return jsonify(success=False, error=f'Forecast API error: {err_msg}')

        result = resp.json()
        if 'hourly' not in result or 'daily' not in result:
            return jsonify(success=False, error=f"Forecast data missing from API response: {result}")

        hourly = result.get('hourly', [])
        daily = result.get('daily', [])
        response_data = {
            'daily': daily,
            'hourly': hourly,
            'location': {'city': city, 'state': state, 'lat': lat, 'lon': lon, 'country': country},
            'timezone_offset': result.get('timezone_offset', 0)
        }
        response_data = decode_bytes(response_data)
        set_cached_result('forecast', cache_key, response_data)
        return jsonify(success=True, data=response_data, cached=False)
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify(success=False, error=f"Internal server error: {str(e)}\n{tb}")


@app.route('/api/air_quality', methods=['POST'])
def api_air_quality():
    log_api_usage('/api/air_quality')
    allowed, usage_count = increment_api_counter()
    if not allowed:
        return jsonify(success=False, error=f"API daily limit of {API_DAILY_LIMIT} reached. Try again tomorrow.")
    try:
        data = request.get_json()
        city = data.get('city')
        state = data.get('state')
        zip_code = data.get('zip_code')
        country = data.get('country')
        lat, lon, city, state = get_location(city, state, zip_code, country)
        if not lat or not lon:
            return jsonify(success=False, error='Location not found')
        cache_key = f'{lat},{lon}'
        cached = get_cached_result('air_quality', cache_key)
        if cached:
            return jsonify(success=True, data=cached, city=city, state=state, cached=True)
        url = f'https://api.openweathermap.org/data/2.5/air_pollution?lat={lat}&lon={lon}&appid={API_KEY}'
        resp = requests.get(url)
        if not resp.ok:
            try:
                err = resp.json()
                err_msg = err.get('message', str(err))
            except Exception:
                err_msg = resp.text
            return jsonify(success=False, error=f'Air Quality API error: {err_msg}')
        result = resp.json()
        response_data = decode_bytes(result)
        set_cached_result('air_quality', cache_key, response_data)
        return jsonify(success=True, data=response_data, cached=False)
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify(success=False, error=f"Internal server error: {str(e)}\n{tb}")

@app.route('/api/uv', methods=['POST'])
def api_uv():
    log_api_usage('/api/uv')
    try:
        data = request.get_json()
        city = data.get('city')
        state = data.get('state')
        zip_code = data.get('zip_code')
        country = data.get('country')
        lat, lon, city, state = get_location(city, state, zip_code, country)
        if not lat or not lon:
            return jsonify(success=False, error='Location not found')
        url = f'https://api.openweathermap.org/data/3.0/onecall?lat={lat}&lon={lon}&appid={API_KEY}'
        resp = requests.get(url)
        log_api_usage('/api/alerts')
        allowed, usage_count = increment_api_counter()
        if not allowed:
            return jsonify(success=False, error=f"API daily limit of {API_DAILY_LIMIT} reached. Try again tomorrow.")
        if not resp.ok:
            try:
                err = resp.json()
                err_msg = err.get('message', str(err))
            except Exception:
                err_msg = resp.text
            return jsonify(success=False, error=f'UV API error: {err_msg}')
        result = resp.json()
        current = result.get('current', {})
        uvi = current.get('uvi', 0)
        sunrise = current.get('sunrise')
        sunset = current.get('sunset')
        clouds = current.get('clouds')
        humidity = current.get('humidity')
        pressure = current.get('pressure')
        response_data = decode_bytes({
            'uvi': uvi,
            'sunrise': sunrise,
            'sunset': sunset,
            'clouds': clouds,
            'humidity': humidity,
            'pressure': pressure,
            'location': {'city': city, 'state': state, 'lat': lat, 'lon': lon}
        })
        cache_key = f'{lat},{lon}'
        set_cached_result('uv', cache_key, response_data)
        return jsonify(success=True, data=response_data, cached=False)
    except Exception as e:
        tb = traceback.format_exc()
        return jsonify(success=False, error=f"Internal server error: {str(e)}\n{tb}")

if __name__ == '__main__':
    from flup.server.cgi import WSGIServer
    WSGIServer(app).run()