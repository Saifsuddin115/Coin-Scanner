from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
import os
import json

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3.1-flash-lite")


from flask import Flask, render_template
import requests


CACHE_FILE = "halal_cache.json"

def load_cache():
    with open(CACHE_FILE, "r") as f:
        return json.load(f)

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def check_halal(symbol, name):
    cache = load_cache()

    if symbol in cache:
        return cache[symbol]

    prompt = f"""
You are screening a cryptocurrency project for Islamic finance compliance.

Project Name: {name}
Ticker: {symbol}

Determine whether the PRIMARY purpose of this project is:

- halal
- haram
- unclear

A project should only be "haram" if its primary utility revolves around:
- interest or lending
- perpetual futures or leveraged derivatives
- gambling or betting
-meme coin

Do NOT classify a project as haram simply because it can be traded.

Respond ONLY as valid JSON.

{{
    "status": "halal",
    "confidence score":"number",
    "reason": "One short sentence explaining why."
}}
"""

    response = model.generate_content(prompt)
    result = json.loads(response.text)

   
    cache[symbol] = result
    save_cache(cache)

    return result

BLACKLIST = {"PIRATE"}

app = Flask(__name__)


@app.route("/")
def home():
    return render_template("index.html")

@app.route("/rules")
def rules():
    return render_template("Rules.html")

@app.route("/calendar")
def calendar():
    return render_template("Calendar.html")



@app.route("/api/gainers")
def gainers():
    response = requests.get("https://api.coinbase.com/api/v3/brokerage/market/products")
    data = response.json()

    products = data["products"]

    filtered = [
        p for p in products
        if p["product_type"] == "SPOT"
        and p["quote_currency_id"] == "USD"
        and p["trading_disabled"] == False
        and p["is_disabled"] == False
        and p["base_currency_id"] not in BLACKLIST
      
    ]

    sorted_products = sorted(
        filtered,
        key=lambda p: float(p["price_percentage_change_24h"]),
        reverse=True
    )

    top_15 = sorted_products[:15]
    cleaned = []
    for p in top_15:
     symbol = p["base_currency_id"]
     name = p["base_name"]

     cleaned.append({
        "name": name,
        "symbol": symbol,
        "price": p["price"],
        "change_24h": round(float(p["price_percentage_change_24h"]), 2),
        "volume_24h": round(float(p["volume_24h"]), 2),
        "halal_status": check_halal(symbol, name)
    })


    return cleaned


if __name__ == "__main__":
    app.run(debug=True)