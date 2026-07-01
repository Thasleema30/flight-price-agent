import os
import json
import smtplib
import requests
from email.message import EmailMessage

TOKEN = os.getenv("TRAVELPAYOUTS_TOKEN")
EMAIL_USER = os.getenv("EMAIL_USER")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD")
ALERT_TO_EMAIL = os.getenv("ALERT_TO_EMAIL")

STATE_FILE = "price_state.json"

FLIGHTS = [
    {
        "origin": "DFW",
        "destination": "JFK",
        "departure_date": "2026-08"
    }
]


def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    with open(STATE_FILE, "r") as file:
        return json.load(file)


def save_state(state):
    with open(STATE_FILE, "w") as file:
        json.dump(state, file, indent=2)


def get_price(origin, destination, departure_date):
    url = "https://api.travelpayouts.com/aviasales/v3/prices_for_dates"

    params = {
        "origin": origin,
        "destination": destination,
        "departure_at": departure_date,
        "one_way": "true",
        "currency": "usd",
        "market": "us",
        "sorting": "price",
        "limit": 1,
        "token": TOKEN
    }

    response = requests.get(url, params=params)
    response.raise_for_status()
    data = response.json()

    if not data.get("data"):
        return None

    return float(data["data"][0]["price"])


def send_email(origin, destination, departure_date, old_price, new_price):
    msg = EmailMessage()
    msg["Subject"] = "Flight Price Drop Alert"
    msg["From"] = EMAIL_USER
    msg["To"] = ALERT_TO_EMAIL

    msg.set_content(f"""
Good news!

Your flight price dropped.

Route: {origin} to {destination}
Date: {departure_date}

Old lowest price: ${old_price}
New price: ${new_price}

Book soon because prices can change quickly.
""")

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(EMAIL_USER, EMAIL_APP_PASSWORD)
        smtp.send_message(msg)


def check_prices():
    print("Checking flight prices...")
    state = load_state()

    for flight in FLIGHTS:
        origin = flight["origin"]
        destination = flight["destination"]
        departure_date = flight["departure_date"]

        key = f"{origin}-{destination}-{departure_date}"

        current_price = get_price(origin, destination, departure_date)

        if current_price is None:
            print(f"No price found for {origin} to {destination}")
            continue

        print(f"{origin} to {destination} on {departure_date}: ${current_price}")

        old_price = state.get(key)

        if old_price is None:
            state[key] = current_price
            print("Initial price saved.")

        elif current_price < old_price:
            send_email(origin, destination, departure_date, old_price, current_price)
            state[key] = current_price
            print("Price dropped. Email sent.")

        else:
            print("No price drop.")

    save_state(state)


if __name__ == "__main__":
    check_prices()