import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Bot, Update
from telegram.ext import Dispatcher, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN)
app = Flask(__name__)

def get_fuel_prices():
    url = "https://www.neste.lv/lv/content/degvielas-cenas"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    table = soup.find("table")
    rows = table.find_all("tr")[1:]

    prices = []
    for row in rows:
        cols = row.find_all("td")
        if len(cols) >= 3:
            fuel_type = cols[0].get_text(strip=True)
            price = cols[1].get_text(strip=True)
            date = cols[2].get_text(strip=True)
            prices.append(f"{fuel_type}: {price} EUR ({date})")

    return "\n".join(prices) or "Цены не найдены."

dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

def prices_command(update, context):
    summary = get_fuel_prices()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"⛽ Цены на топливо:\n\n{summary}")

dispatcher.add_handler(CommandHandler("prices", prices_command))

def send_daily_summary():
    summary = get_fuel_prices()
    bot.send_message(chat_id=CHAT_ID, text=f"⛽ Цены на топливо:\n\n{summary}")

scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_summary, "cron", hour=9, timezone=pytz.UTC)
scheduler.start()

@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    update = Update.de_json(request.get_json(force=True), bot)
    dispatcher.process_update(update)
    return "ok"

if __name__ == "__main__":
    bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")
    app.run(host="0.0.0.0", port=10000)
