import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Bot, Update, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN)
app = Flask(__name__)

def get_neste_prices():
    try:
        url = "https://www.neste.lv/lv/content/degvielas-cenas"
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.find("table")
        rows = table.find_all("tr")[1:]
        prices = {}
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                fuel = cols[0].get_text(strip=True).lower()
                price = cols[1].get_text(strip=True).replace(" EUR", "").replace(",", ".")
                prices[fuel] = float(price)
        return prices
    except Exception as e:
        print("Neste error:", e)
        return {}

def get_fuel_summary():
    data = get_neste_prices()
    summary = ["🏷 Neste"]
    if not data:
        summary.append("• Нет данных.")
    for name, price in data.items():
        summary.append(f"• {name.capitalize()}: {price:.3f} EUR")
    return "\n".join(summary)

dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

def start_command(update, context):
    keyboard = [["/cena"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Привет! Нажми кнопку ниже, чтобы узнать цены:", reply_markup=reply_markup)

def price_command(update, context):
    summary = get_fuel_summary()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"⛽ Цены на топливо:

{summary}")

dispatcher.add_handler(CommandHandler("start", start_command))
dispatcher.add_handler(CommandHandler("cena", price_command))

def send_daily_summary():
    summary = get_fuel_summary()
    bot.send_message(chat_id=CHAT_ID, text=f"⛽ Ежедневная сводка цен:

{summary}")

scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_summary, "cron", hour=7, timezone=pytz.UTC)
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
