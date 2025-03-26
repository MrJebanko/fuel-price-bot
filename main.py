print("Neste:", get_neste_prices())
print("Circle K:", get_circlek_prices())
print("Viada:", get_viada_prices())
print("Virši:", get_virsi_prices())
import os
import requests
from bs4 import BeautifulSoup
from flask import Flask, request
from telegram import Bot, Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Dispatcher, CommandHandler, CallbackQueryHandler
from apscheduler.schedulers.background import BackgroundScheduler
import pytz

TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

bot = Bot(token=TOKEN)
app = Flask(__name__)

def get_neste_prices():
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

def get_circlek_prices():
    url = "https://www.circlek.lv/degviela-miles/degvielas-cenas"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    prices = {}
    for block in soup.select(".fuel-price-item"):
        fuel = block.select_one(".fuel-price-title").get_text(strip=True).lower()
        price = block.select_one(".fuel-price-number").get_text(strip=True).replace("€", "").replace(",", ".")
        prices[fuel] = float(price)
    return prices

def get_viada_prices():
    url = "https://www.viada.lv/zemakas-degvielas-cenas"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    prices = {}
    for row in soup.select("table tr")[1:]:
        cols = row.find_all("td")
        if len(cols) >= 2:
            fuel = cols[0].get_text(strip=True).lower()
            price = cols[1].get_text(strip=True).replace("€", "").replace("EUR", "").replace(",", ".").strip()
            try:
                prices[fuel] = float(price)
            except ValueError:
                continue
    return prices

def get_virsi_prices():
    url = "https://www.virsi.lv/lv/privatpersonam/degviela/degvielas-un-elektrouzlades-cenas"
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    prices = {}
    for block in soup.select(".views-row"):
        fuel_block = block.select_one(".field-content")
        if fuel_block:
            lines = fuel_block.get_text("\n", strip=True).split("\n")
            if len(lines) >= 2:
                fuel = lines[0].lower()
                price = lines[1].replace("EUR", "").replace(",", ".").strip()
                try:
                    prices[fuel] = float(price)
                except:
                    continue
    return prices

def collect_all_prices():
    return {
        "Neste": get_neste_prices(),
        "Circle K": get_circlek_prices(),
        "Viada": get_viada_prices(),
        "Virši": get_virsi_prices()
    }

def get_fuel_summary():
    data = collect_all_prices()
    summary = []
    for source, fuels in data.items():
        summary.append(f"🏷 {source}")
        for name, price in fuels.items():
            summary.append(f"• {name.capitalize()}: {price:.3f} EUR")
        summary.append("")
    return "\n".join(summary)

def compare_fuel_type(fuel_type):
    fuel_type = fuel_type.lower()
    data = collect_all_prices()
    best_price = None
    best_source = None
    for source, fuels in data.items():
        for name, price in fuels.items():
            if fuel_type in name:
                if best_price is None or price < best_price:
                    best_price = price
                    best_source = source
    if best_price is not None:
        return f"💰 Самая низкая цена на {fuel_type} у {best_source} — {best_price:.3f} EUR"
    return f"⚠️ Не удалось найти цены на '{fuel_type}'."

dispatcher = Dispatcher(bot, None, workers=0, use_context=True)

def start_command(update, context):
    keyboard = [["/prices", "/compare"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    update.message.reply_text("Привет! Выбери команду ниже:", reply_markup=reply_markup)

def prices_command(update, context):
    summary = get_fuel_summary()
    context.bot.send_message(chat_id=update.effective_chat.id, text=f"⛽ Цены на топливо:\n\n{summary}")

def compare_command(update, context):
    keyboard = [
        [InlineKeyboardButton("⛽ 95", callback_data='compare_95')],
        [InlineKeyboardButton("⛽ 98", callback_data='compare_98')],
        [InlineKeyboardButton("⛽ Dīzeļdegviela", callback_data='compare_dīzeļdegviela')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Выбери топливо для сравнения:", reply_markup=reply_markup)

def button_handler(update, context):
    query = update.callback_query
    query.answer()
    fuel_type = query.data.replace("compare_", "")
    result = compare_fuel_type(fuel_type)
    query.edit_message_text(result)

dispatcher.add_handler(CommandHandler("start", start_command))
dispatcher.add_handler(CommandHandler("prices", prices_command))
dispatcher.add_handler(CommandHandler("compare", compare_command))
dispatcher.add_handler(CallbackQueryHandler(button_handler))

def send_daily_summary():
    summary = get_fuel_summary()
    bot.send_message(chat_id=CHAT_ID, text=f"⛽ Ежедневная сводка цен:\n\n{summary}")

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
