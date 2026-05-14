# main.py
import asyncio
import threading
import os
from webapp import app  # Твой Flask-сайт
from bot import dp, bot # Твой бот
from database import init_db

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

async def run_bot():
    init_db()
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запускаем сайт в фоновом потоке
    threading.Thread(target=run_flask, daemon=True).start()
    
    # Запускаем бота в основном потоке
    asyncio.run(run_bot())
