from aiogram import Bot, Dispatcher, executor, types
from aiohttp import web
import os

# ВСТАВТЕ СЮДИ ВАШ НОВИЙ ТОКЕН ВІД BOTFATHER
TOKEN = "8516307940:AAGBqIn662FbQXFBhwLesgtczeGtfcju4PA" 

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Старт з кнопкою
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📄 Прайс-лист")
    await message.answer("Привіт! Обери опцію нижче 👇", reply_markup=keyboard)

# Реакція на кнопку
@dp.message_handler(lambda msg: msg.text == "📄 Прайс-лист")
async def price_btn(message: types.Message):
    await message.answer("Лабораторна робота 🟡 50 грн\nПрактична робота 🟡 50 грн")

# --- МАГІЯ ДЛЯ RENDER (Щоб не було помилки Port scan timeout) ---
async def on_startup(dp):
    app = web.Application()
    # Створюємо просту сторінку, яка каже "Я живий"
    app.add_routes([web.get('/', lambda req: web.Response(text="Bot is alive!"))])
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render дає порт через змінну оточення, або використовуємо 8080
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# Запуск
if __name__ == "__main__":
    # Параметр on_startup запускає наш веб-сервер разом із ботом
    executor.start_polling(dp, on_startup=on_startup)
