from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiohttp import web
import os
import logging

# --- НАЛАШТУВАННЯ ---
# ВАШ ТОКЕН
TOKEN = "8516307940:AAGBqIn662FbQXFBhwLesgtczeGtfcju4PA"

# ID ВАШОЇ ГРУПИ
# 1. Спочатку залиште 0.
# 2. Залийте код, запустіть бота.
# 3. Напишіть у групу /getid, отримайте цифри.
# 4. Замініть 0 на ці цифри (з мінусом).
ADMIN_GROUP_ID = 0

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- МАШИНА СТАНІВ ---
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_group = State()
    waiting_for_subject = State()
    waiting_for_details = State()

class SupportState(StatesGroup):
    waiting_for_message = State()

# --- КЛАВІАТУРА ---
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📄 Прайс-лист", "📚 Замовити роботу")
    keyboard.add("💬 Підтримка")
    return keyboard

# --- СТАРТ ---
@dp.message_handler(commands=['start'], state="*")
async def start_cmd(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer(
        "👋 Вітаємо в LabHub!\n"
        "Тут студенти допомагають одне одному вирішувати питання з навчання.\n\n"
        "Обери опцію нижче 👇", 
        reply_markup=get_main_keyboard()
    )

# --- ОТРИМАТИ ID ГРУПИ (Щоб ви дізналися куди писати боту) ---
@dp.message_handler(commands=['getid'])
async def get_chat_id(message: types.Message):
    await message.reply(f"ID цього чату (скопіюйте в код): `{message.chat.id}`", parse_mode="Markdown")

# --- 1. ПРАЙС-ЛИСТ ---
@dp.message_handler(lambda msg: msg.text == "📄 Прайс-лист")
async def price_btn(message: types.Message):
    response_text = (
        "🔬 Лабораторна робота — <b>50 грн</b>\n"
        "📝 Практична робота — <b>50 грн</b>"
    )
    await message.answer(response_text, parse_mode="HTML")

# --- 2. ЗАМОВИТИ РОБОТУ ---
@dp.message_handler(lambda msg: msg.text == "📚 Замовити роботу", state="*")
async def start_order(message: types.Message):
    await OrderState.waiting_for_name.set()
    await message.answer("1️⃣ Як вас звати? (Ім'я та прізвище)", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(state=OrderState.waiting_for_name)
async def process_name(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['name'] = message.text
    await OrderState.next()
    await message.answer("2️⃣ З якої ви групи?")

@dp.message_handler(state=OrderState.waiting_for_group)
async def process_group(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['group'] = message.text
    await OrderState.next()
    await message.answer("3️⃣ Який предмет?")

@dp.message_handler(state=OrderState.waiting_for_subject)
async def process_subject(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['subject'] = message.text
    await OrderState.next()
    await message.answer("4️⃣ Напишіть номер роботи та тему (або просто опишіть завдання):")

@dp.message_handler(state=OrderState.waiting_for_details)
async def process_details(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['details'] = message.text
        
        # Повідомлення для адмінів
        report = (
            f"⚡️ <b>НОВЕ ЗАМОВЛЕННЯ!</b>\n\n"
            f"👤 <b>Від:</b> {data['name']} (@{message.from_user.username})\n"
            f"🎓 <b>Група:</b> {data['group']}\n"
            f"📚 <b>Предмет:</b> {data['subject']}\n"
            f"📝 <b>Деталі:</b> {data['details']}\n\n"
            f"ℹ️ <i>Щоб відповісти, натисніть Reply на це повідомлення</i>\n"
            f"🆔 <code>{message.from_user.id}</code>"
        )
    
    if ADMIN_GROUP_ID != 0:
        await bot.send_message(ADMIN_GROUP_ID, report, parse_mode="HTML")
    
    await state.finish()
    await message.answer("✅ Замовлення надіслано! Менеджер скоро зв'яжеться з вами.", reply_markup=get_main_keyboard())

# --- 3. ПІДТРИМКА ---
@dp.message_handler(lambda msg: msg.text == "💬 Підтримка", state="*")
async def start_support(message: types.Message):
    await SupportState.waiting_for_message.set()
    await message.answer(
        "✍️ Напишіть ваше питання.\n"
        "Ми перешлемо його адміністратору.", 
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("🔙 Скасувати")
    )

@dp.message_handler(lambda msg: msg.text == "🔙 Скасувати", state=SupportState.waiting_for_message)
async def cancel_support(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Скасовано.", reply_markup=get_main_keyboard())

@dp.message_handler(state=SupportState.waiting_for_message, content_types=types.ContentTypes.ANY)
async def process_support_msg(message: types.Message, state: FSMContext):
    if ADMIN_GROUP_ID != 0:
        forward_text = (
            f"📩 <b>ПОВІДОМЛЕННЯ ВІД КОРИСТУВАЧА</b>\n"
            f"👤 {message.from_user.full_name} (@{message.from_user.username})\n\n"
            f"{message.text if message.text else '[Файл/Фото]'}\n\n"
            f"🆔 <code>{message.from_user.id}</code>"
        )
        await bot.send_message(ADMIN_GROUP_ID, forward_text, parse_mode="HTML")
        if not message.text:
            await message.forward(ADMIN_GROUP_ID)
    
    await state.finish()
    await message.answer("✅ Надіслано! Чекайте на відповідь.", reply_markup=get_main_keyboard())

# --- 4. ВІДПОВІДЬ АДМІНА (REPLY) ---
@dp.message_handler(lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message, content_types=types.ContentTypes.ANY)
async def admin_reply_handler(message: types.Message):
    try:
        # Витягуємо ID користувача з повідомлення, на яке відповіли
        reply_text = message.reply_to_message.text or message.reply_to_message.caption
        if "🆔" in reply_text:
            user_id = int(reply_text.split("<code>")[1].split("</code>")[0])
            
            # Що відправляємо користувачу
            reply_to_user = f"🔔 <b>Відповідь від LabHub:</b>\n\n{message.text}"
            
            await bot.send_message(user_id, reply_to_user, parse_mode="HTML")
            await message.reply("✅ Відповідь доставлена!")
        else:
            await message.reply("⚠️ Не можу знайти ID користувача в цьому повідомленні.")
    except Exception as e:
        pass # Ігноруємо помилки, якщо це просто розмова між адмінами

# --- СЕРВЕР RENDER ---
async def on_startup(dp):
    app = web.Application()
    app.add_routes([web.get('/', lambda req: web.Response(text="Bot is alive!"))])
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

if __name__ == "__main__":
    executor.start_polling(dp, on_startup=on_startup)
