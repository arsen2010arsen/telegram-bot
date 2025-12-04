from aiogram import Bot, Dispatcher, executor, types
from aiohttp import web
import os

# ВАШ ТОКЕН (Залиште як є, якщо це новий)
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

# --- ОСЬ ЦІЄЇ ЧАСТИНИ У ВАС НЕМАЄ ---
async def on_startup(dp):
    app = web.Application()
    app.add_routes([web.get('/', lambda req: web.Response(text="Bot is alive!"))])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

if __name__ == "__main__":
    # Тут теж важливо: додано параметр on_startup
    executor.start_polling(dp, on_startup=on_startup)
