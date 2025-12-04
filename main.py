from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiohttp import web
import os
import logging
import re  # Бібліотека для пошуку цифр

# --- НАЛАШТУВАННЯ ---

# 👇 ВСТАВТЕ ВАШ ТОКЕН
TOKEN = "8516307940:AAEhZ84NunCwC470Au2LQTDTPT2rDzHTR_s"

# ВАШ ID ГРУПИ (Вже вписаний)
ADMIN_GROUP_ID = -1003308912052

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

# --- МАШИНА СТАНІВ ---
class OrderState(StatesGroup):
    waiting_for_name = State()
    waiting_for_group = State()
    waiting_for_subject = State()
    waiting_for_teacher = State()
    waiting_for_details = State()

class SupportState(StatesGroup):
    waiting_for_message = State()

# --- ГОЛОВНА КЛАВІАТУРА ---
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("📄 Прайс-лист", "📚 Замовити роботу")
    keyboard.add("🔥 Термінове замовлення")
    keyboard.add("💬 Підтримка", "⚠️ Попередження")
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

# --- ОТРИМАТИ ID ГРУПИ ---
@dp.message_handler(commands=['getid'])
async def get_chat_id(message: types.Message):
    await message.reply(f"ID цього чату: `{message.chat.id}`", parse_mode="Markdown")

# --- 1. ПРАЙС-ЛИСТ ---
@dp.message_handler(lambda msg: msg.text == "📄 Прайс-лист")
async def price_btn(message: types.Message):
    response_text = (
        "🔬 Лабораторна робота — <b>50 грн / шт.</b>\n"
        "📝 Практична робота — <b>50 грн / шт.</b>\n\n"
        "⏳ <i>Термінове виконання оплачується додатково.</i>"
    )
    await message.answer(response_text, parse_mode="HTML")

# --- 2. ПОПЕРЕДЖЕННЯ ---
@dp.message_handler(lambda msg: msg.text == "⚠️ Попередження")
async def warning_btn(message: types.Message):
    warning_text = (
        "<b>⚠️ ВІДМОВА ВІД ВІДПОВІДАЛЬНОСТІ</b>\n\n"
        "Адміністрація бота не несе відповідальності за можливі академічні наслідки.\n"
        "Усі ризики повністю покладаються на користувача."
    )
    await message.answer(warning_text, parse_mode="HTML")

# --- 3. ЗАМОВИТИ РОБОТУ ---
@dp.message_handler(lambda msg: msg.text == "📚 Замовити роботу", state="*")
async def start_order(message: types.Message, state: FSMContext):
    await OrderState.waiting_for_name.set()
    async with state.proxy() as data:
        data['is_urgent'] = False
    await message.answer("1️⃣ Введіть ваше ПІБ (Прізвище, Ім'я, По батькові):", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda msg: msg.text == "🔥 Термінове замовлення", state="*")
async def start_urgent_order(message: types.Message, state: FSMContext):
    await OrderState.waiting_for_name.set()
    async with state.proxy() as data:
        data['is_urgent'] = True
    await message.answer("🚀 <b>Термінове замовлення!</b>\n\n1️⃣ Введіть ваше ПІБ (Прізвище, Ім'я, По батькові):", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())

# --- ЕТАПИ АНКЕТИ ---
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
    await message.answer("4️⃣ Прізвище викладача:")

@dp.message_handler(state=OrderState.waiting_for_teacher)
async def process_teacher(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['teacher'] = message.text
        data['media_messages'] = [] 
        data['description_parts'] = []
        
    await OrderState.next()
    
    finish_kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    finish_kb.add("✅ Відправити замовлення")
    
    await message.answer(
        "5️⃣ <b>Опишіть завдання та прикріпіть файли.</b>\n\n"
        "📎 Ви можете надіслати декілька фото, файлів або повідомлень.\n"
        "🏁 Коли все скинете — натисніть кнопку <b>«✅ Відправити замовлення»</b> внизу.",
        reply_markup=finish_kb,
        parse_mode="HTML"
    )

# --- ЗБІР ФАЙЛІВ ТА ФІНІШ ---
@dp.message_handler(state=OrderState.waiting_for_details, content_types=types.ContentTypes.ANY)
async def process_details_collect(message: types.Message, state: FSMContext):
    if message.text == "✅ Відправити замовлення":
        await finish_order_procedure(message, state)
        return

    async with state.proxy() as data:
        if message.text:
            data['description_parts'].append(message.text)
        
        if message.content_type != 'text':
            data['media_messages'].append(message.message_id)
            if message.caption:
                data['description_parts'].append(message.caption)

async def finish_order_procedure(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        full_details = "\n".join(data.get('description_parts', []))
        if not full_details:
            full_details = "[Без текстового опису]"

        is_urgent = data.get('is_urgent', False)
        title = "🔥🔥🔥 ТЕРМІНОВЕ ЗАМОВЛЕННЯ!" if is_urgent else "⚡️ НОВЕ ЗАМОВЛЕННЯ!"

        report = (
            f"<b>{title}</b>\n\n"
            f"👤 <b>ПІБ:</b> {data['name']} (@{message.from_user.username})\n"
            f"🎓 <b>Група:</b> {data['group']}\n"
            f"📚 <b>Предмет:</b> {data['subject']}\n"
            f"👨‍🏫 <b>Викладач:</b> {data['teacher']}\n"
            f"📝 <b>Деталі:</b> {full_details}\n\n"
            f"ℹ️ <i>Щоб відповісти, натисніть REPLY на це повідомлення.</i>\n"
            f"🆔 <code>{message.from_user.id}</code>"
        )
        
        media_ids = data.get('media_messages', [])

    if ADMIN_GROUP_ID != 0:
        await bot.send_message(ADMIN_GROUP_ID, report, parse_mode="HTML")
        if media_ids:
            for msg_id in media_ids:
                try:
                    await bot.forward_message(ADMIN_GROUP_ID, message.chat.id, msg_id)
                except Exception:
                    pass

    await state.finish()
    await message.answer("✅ Ваше замовлення прийнято! Очікуйте відповідь.", reply_markup=get_main_keyboard())


# --- 5. ПІДТРИМКА ---
@dp.message_handler(lambda msg: msg.text == "💬 Підтримка", state="*")
async def start_support(message: types.Message):
    await SupportState.waiting_for_message.set()
    await message.answer(
        "✍️ Напишіть ваше повідомлення.", 
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
            f"👤 {message.from_user.full_name} (@{message.from_user.username})\n"
            f"🆔 <code>{message.from_user.id}</code>\n"
            f"⬇️ <i>Відповідайте нижче:</i>"
        )
        await bot.send_message(ADMIN_GROUP_ID, forward_text, parse_mode="HTML")
        await message.forward(ADMIN_GROUP_ID)
    
    await state.finish()
    await message.answer("✅ Надіслано!", reply_markup=get_main_keyboard())

# --- 6. РЕЖИМ ЧАТУ (ДІАГНОСТИКА) ---
@dp.message_handler(lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message, content_types=types.ContentTypes.ANY)
async def admin_reply_handler(message: types.Message):
    # ЦЕЙ ТЕКСТ БУДЕ В ЛОГАХ RENDER
    print(f"DEBUG: Отримано повідомлення в групі {message.chat.id} від {message.from_user.full_name}")
    
    try:
        reply = message.reply_to_message
        text_to_check = reply.text or reply.caption or ""
        
        print(f"DEBUG: Текст реплаю (перші 50 симв): {text_to_check[:50]}...") 

        user_id = None

        # 1. Regex (найнадійніший спосіб)
        match = re.search(r"🆔\s*(\d+)", text_to_check)
        if match:
            user_id = int(match.group(1))
            print(f"DEBUG: Знайдено ID через Regex: {user_id}")
        
        # 2. Forward
        elif reply.forward_from:
            user_id = reply.forward_from.id
            print(f"DEBUG: Знайдено ID через Forward: {user_id}")
            
        if user_id:
            await message.copy_to(user_id)
            await message.reply("✅ Відповідь надіслано!")
            print("DEBUG: Успішно відправлено.")
        else:
            print("DEBUG: ID не знайдено.")
            await message.reply("❌ Не бачу ID! Перевірте, чи ви відповідаєте на анкету зі смайликом 🆔.")

    except Exception as e:
        print(f"DEBUG: Критична помилка: {e}")
        await message.reply(f"❌ Помилка: {e}")

# --- СЕРВЕР ---
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
