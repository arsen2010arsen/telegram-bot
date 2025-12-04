from aiogram import Bot, Dispatcher, executor, types

TOKEN = "8516307940:AAGBqIn662FbQXFBhwLesgtczeGtfcju4PA"

bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

# Старт з кнопкою
@dp.message_handler(commands=['start'])
async def start_cmd(message: types.Message):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("🧾 Прайс-лист")
    await message.answer("Привіт! Обери опцію нижче 👇", reply_markup=keyboard)

# Реакція на кнопку
@dp.message_handler(lambda msg: msg.text == "🧾 Прайс-лист")
async def price_btn(message: types.Message):
    await message.answer("Лабораторна робота – 50 грн\nПрактична робота – 50 грн")

# Запуск
if __name__ == "__main__":
    executor.start_polling(dp)
