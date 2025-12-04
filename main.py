from aiogram import Bot, Dispatcher, executor, types
from aiohttp import web
import os

# --- ВАШ ТОКЕН ---
# Переконайтеся, що тут стоїть правильний токен!
TOKEN = "8516307940:AAGBqIn662FbQXFBhwLesgtczeGtfcju4PA" 

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# --- СТАРТ ---
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    # Створюємо кнопку
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📄 Прайс-лист")
    
    await message.answer(
        "👋 Вітаємо в LabHub!\n"
        "Тут студенти допомагають одне одному вирішувати питання з навчання.\n\n"
        "Обери опцію нижче 👇", 
        reply_markup=keyboard
    )

# --- КНОПКА З ЦІНАМИ (ОНОВЛЕНА) ---
@dp.message_handler(lambda msg: msg.text == "📄 Прайс-лист")
async def price_btn(message: types.Message):
    # Використовуємо HTML теги <b> для жирного шрифту
    response_text = (
        "🔬 Лабораторна робота — <b>50 грн</b>\n"
        "📝 Практична робота — <b>50 грн</b>"
    )
    # parse_mode="HTML" робить текст жирним і красивим
    await message.answer(response_text, parse_mode="HTML")

# --- СЕРВЕР ДЛЯ RENDER (ЩОБ БОТ НЕ ВИМИКАВСЯ) ---
async def on_startup(dp):
    app = web.Application()
    app.add_routes([web.get('/', lambda req: web.Response(text="Bot is alive!"))])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- ЗАПУСК ---
if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)
