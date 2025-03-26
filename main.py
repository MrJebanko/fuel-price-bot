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
        results = []
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 3:
                fuel = cols[0].get_text(strip=True)
                price = cols[1].get_text(strip=True)
                stations = cols[2].get_text(strip=True)
                results.append(f"• {fuel}: {price} — {stations}")
        return results if results else ["• Данные не найдены."]
    except Exception as e:
        print("Neste error:", e)
        return ["• Ошибка при получении данных."]

def get_fuel_summary():
    data = get_neste_prices()
    return "\n".join(["⛽ Цены на Neste:"] + data)

dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

def start_command(update, context):
    keyboard = [["Проверить цену"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Привет! Нажми кнопку ниже, чтобы узнать актуальные цены:", reply_markup=reply_markup)

def price_command(update, context):
    summary = get_fuel_summary()
    context.bot.send_message(chat_id=update.effective_chat.id, text=summary)

dispatcher.add_handler(CommandHandler("start", start_command))
dispatcher.add_handler(CommandHandler("cena", price_command))

# Также обрабатываем текст кнопки
def handle_text(update, context):
    if update.message.text == "Проверить цену":
        summary = get_fuel_summary()
        update.message.reply_text(summary)

dispatcher.add_handler(CommandHandler("cena", price_command))
dispatcher.add_handler(CommandHandler("start", start_command))
dispatcher.add_handler(CommandHandler("help", start_command))  # на всякий случай
dispatcher.add_handler(CommandHandler("start", start_command))
dispatcher.add_handler(CommandHandler("cena", price_command))
dispatcher.add_handler(CommandHandler("price", price_command))
dispatcher.add_handler(CommandHandler("check", price_command))
dispatcher.add_handler(CommandHandler("get", price_command))
dispatcher.add_handler(CommandHandler("getprice", price_command))
dispatcher.add_handler(CommandHandler("fuel", price_command))
dispatcher.add_handler(CommandHandler("fuelprice", price_command))
dispatcher.add_handler(CommandHandler("fuel_price", price_command))

from telegram.ext import MessageHandler, Filters
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))

def send_daily_summary():
    summary = get_fuel_summary()
    bot.send_message(chat_id=CHAT_ID, text=summary)

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
