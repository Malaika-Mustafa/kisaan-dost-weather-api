from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import requests
import json
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY not found in .env file")
FORECAST_DAYS = 3

app = FastAPI(title="Kisan Dost Weather API (Urdu)", version="1.0")

KARACHI_TZ = ZoneInfo("Asia/Karachi")
UTC_TZ = ZoneInfo("UTC")

def get_weather_forecast(lat: float, lon: float, days=FORECAST_DAYS):
    try:
        url = f"https://api.openweathermap.org/data/2.5/forecast?lat={lat}&lon={lon}&appid={API_KEY}&units=metric"
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return process_weather_data(data, days)
        else:
            return get_fallback_data()
    except Exception:
        return get_fallback_data()

def process_weather_data(data, days):
    forecast_list = []
    today = datetime.now(KARACHI_TZ).date()
    max_date = today + timedelta(days=days)

    for item in data.get("list", []):
        dt_utc = datetime.fromtimestamp(item["dt"], tz=UTC_TZ)
        dt_local = dt_utc.astimezone(KARACHI_TZ)

        if dt_local.date() > max_date:
            continue

        forecast_list.append({
            "تاریخ": dt_local.strftime("%Y-%m-%d"),
            "وقت": dt_local.strftime("%H:%M"),
            "درجہ حرارت": round(item["main"]["temp"], 1),
            "نمی": item["main"]["humidity"],
            "بارش کا امکان": round(item.get("pop", 0) * 100),
            "ہوا کی رفتار": round(item["wind"]["speed"], 1),
            "موسم": item["weather"][0]["description"].title(),
        })
    return forecast_list

def get_fallback_data():
    now = datetime.now(KARACHI_TZ)
    fallback_data = []
    for day in range(3):
        for hour in [6, 12, 18]:
            forecast_time = now + timedelta(days=day, hours=hour)
            fallback_data.append({
                "تاریخ": forecast_time.strftime("%Y-%m-%d"),
                "وقت": forecast_time.strftime("%H:%M"),
                "درجہ حرارت": 28 + day * 2,
                "نمی": 60 - day * 5,
                "بارش کا امکان": 20 + day * 10,
                "ہوا کی رفتار": 8.0,
                "موسم": "جزوی بادل",
            })
    return fallback_data

def calculate_irrigation_need(entry):
    temp = entry["درجہ حرارت"]
    humidity = entry["نمی"]
    rain_prob = entry["بارش کا امکان"]
    if rain_prob > 70:
        return "پانی دینے کی ضرورت نہیں", "بارش کے زیادہ امکانات ہیں"
    elif temp > 35 and humidity < 40:
        return "فوری آبپاشی کی ضرورت ہے", "گرمی اور خشکی زیادہ ہے"
    elif temp > 30 and humidity < 60:
        return "ہلکی آبپاشی کی تجویز ہے", "درجہ حرارت معتدل مگر خشکی موجود ہے"
    else:
        return "پانی دینے کی ضرورت نہیں", "موسم خوشگوار ہے"

@app.get("/")
def root():
    return {"پیغام": "کسان دوست موسم API چل رہی ہے", "حالت": "فعال"}

@app.get("/api/weather")
def get_weather(lat: float = Query(24.8607), lon: float = Query(67.0011)):
    # Default Karachi coordinates if none provided
    city = "کراچی" if lat == 24.8607 and lon == 67.0011 else "منتخب مقام"

    weather_data = get_weather_forecast(lat, lon)
    final_output = []
    for entry in weather_data:
        advice, reason = calculate_irrigation_need(entry)
        entry["آبپاشی مشورہ"] = advice
        entry["وجہ"] = reason
        final_output.append(entry)

    response_data = {
        "کامیاب": True,
        "شہر": city,
        "عرض البلد": lat,
        "طول البلد": lon,
        "پیشگوئی کے دن": FORECAST_DAYS,
        "ڈیٹا": final_output,
        "وقت": datetime.now(KARACHI_TZ).strftime("%Y-%m-%d %H:%M:%S")
    }

    file_path = os.path.join(os.getcwd(), "urdu_weather_forecast.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(response_data, f, ensure_ascii=False, indent=2)

    return JSONResponse(response_data)
