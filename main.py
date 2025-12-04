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
    response_text = (
        "🔬 Лабораторна робота — <b>50 грн</b>\n"
        "📝 Практична робота — <b>50 грн</b>"
    )
    # Важливо: додаємо parse_mode="HTML", щоб працював жирний шрифт
    await message.answer(response_text, parse_mode="HTML")

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

