import asyncio
import threading
import os
from webapp import app
from bot import dp, bot
from database import init_db

# Функция для запуска Flask-сайта
def run_flask():
    # Render сам назначит порт через переменную окружения PORT
    port = int(os.environ.get("PORT", 5000))
    # Запускаем сайт на всех интерфейсах (0.0.0.0)
    app.run(host="0.0.0.0", port=port)

# Функция для запуска Telegram-бота
async def run_bot():
    print("Инициализация базы данных...")
    init_db()
    print("Бот запущен и готов к работе!")
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == "__main__":
    # 1. Запускаем сайт в отдельном потоке
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    # 2. Запускаем бота в основном потоке (через asyncio)
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        print("Проект остановлен.")
