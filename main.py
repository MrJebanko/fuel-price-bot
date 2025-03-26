import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot
from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask

TOKEN = os.getenv('BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')
bot = Bot(token=TOKEN)
app = Flask(__name__)

def get_fuel_prices():
    url = 'https://www.neste.lv/lv/content/degvielas-cenas'
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')

    table = soup.find('table')
    rows = table.find_all('tr')[1:]

    prices = []
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 3:
            fuel_type = cols[0].get_text(strip=True)
            price = cols[1].get_text(strip=True)
            date = cols[2].get_text(strip=True)
            prices.append(f"{fuel_type}: {price} EUR ({date})")

    return '\n'.join(prices) or 'Цены не найдены.'

def send_daily_summary():
    summary = get_fuel_prices()
    bot.send_message(chat_id=CHAT_ID, text=f'⛽ Цены на топливо:\n\n{summary}')

# Планировщик
scheduler = BackgroundScheduler()
scheduler.add_job(send_daily_summary, 'cron', hour=9)
scheduler.start()

@app.route('/')
def index():
    return 'Bot is running!'

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=10000)
