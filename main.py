from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiohttp import web
import os
import logging

# --- НАЛАШТУВАННЯ ---

# 👇 ВСТАВТЕ СЮДИ ВАШ РОБОЧИЙ ТОКЕН!
TOKEN = "8516307940:AAEhZ84NunCwC470Au2LQTDTPT2rDzHTR_s"

# ВАШ ID ГРУПИ (Вже правильний)
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

# --- КЛАВІАТУРА ---
def get_main_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Ряд 1: Прайс і Звичайне замовлення
    keyboard.add("📄 Прайс-лист", "📚 Замовити роботу")
    # Ряд 2: ТЕРМІНОВЕ ЗАМОВЛЕННЯ (Нова кнопка)
    keyboard.add("🔥 Термінове замовлення")
    # Ряд 3: Підтримка і Попередження
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

# --- 1. ПРАЙС-ЛИСТ (ОНОВЛЕНИЙ) ---
@dp.message_handler(lambda msg: msg.text == "📄 Прайс-лист")
async def price_btn(message: types.Message):
    response_text = (
        "🔬 Лабораторна робота — <b>50 грн / шт.</b>\n"
        "📝 Практична робота — <b>50 грн / шт.</b>\n\n"
        "⏳ <i>Термінове виконання оплачується за додаткову суму (узгоджується індивідуально).</i>"
    )
    await message.answer(response_text, parse_mode="HTML")

# --- 2. ПОПЕРЕДЖЕННЯ ---
@dp.message_handler(lambda msg: msg.text == "⚠️ Попередження")
async def warning_btn(message: types.Message):
    warning_text = (
        "<b>⚠️ ВІДМОВА ВІД ВІДПОВІДАЛЬНОСТІ</b>\n\n"
        "Адміністрація бота не несе відповідальності за можливі академічні наслідки, "
        "включно з ситуаціями, коли викладач або навчальний заклад виявляє підозру "
        "щодо походження поданих матеріалів.\n\n"
        "Усі ризики, пов’язані з використанням отриманих матеріалів, "
        "повністю покладаються на користувача."
    )
    await message.answer(warning_text, parse_mode="HTML")

# --- 3. ЗАМОВИТИ РОБОТУ (ЗВИЧАЙНЕ) ---
@dp.message_handler(lambda msg: msg.text == "📚 Замовити роботу", state="*")
async def start_order(message: types.Message, state: FSMContext):
    await OrderState.waiting_for_name.set()
    # Запам'ятовуємо, що це НЕ термінове
    async with state.proxy() as data:
        data['is_urgent'] = False
        
    await message.answer("1️⃣ Як вас звати? (Ім'я та прізвище)", reply_markup=types.ReplyKeyboardRemove())

# --- 4. ТЕРМІНОВЕ ЗАМОВЛЕННЯ (НОВЕ) ---
@dp.message_handler(lambda msg: msg.text == "🔥 Термінове замовлення", state="*")
async def start_urgent_order(message: types.Message, state: FSMContext):
    await OrderState.waiting_for_name.set()
    # Запам'ятовуємо, що це ТЕРМІНОВЕ
    async with state.proxy() as data:
        data['is_urgent'] = True
    
    await message.answer(
        "🚀 <b>Ви обрали термінове замовлення.</b>\n"
        "Ми візьмемо це завдання в пріоритет. Вартість буде вищою за звичайну.\n\n"
        "Заповніть анкету, і ми швидко оцінимо роботу.\n"
        "👇👇👇\n\n"
        "1️⃣ Як вас звати? (Ім'я та прізвище)", 
        reply_markup=types.ReplyKeyboardRemove(),
        parse_mode="HTML"
    )

# --- ЕТАПИ АНКЕТИ (СПІЛЬНІ ДЛЯ ОБОХ ТИПІВ) ---

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
    await message.answer("4️⃣ Напишіть прізвище викладача (та ініціали, якщо знаєте):")

@dp.message_handler(state=OrderState.waiting_for_teacher)
async def process_teacher(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        data['teacher'] = message.text
    await OrderState.next()
    await message.answer("5️⃣ Опишіть завдання (номер, тема, ваш варіант/номер у списку) або прикріпіть фото/файл:")

# ФІНІШ АНКЕТИ
@dp.message_handler(state=OrderState.waiting_for_details, content_types=types.ContentTypes.ANY)
async def process_details(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        msg_text = message.text or message.caption or "[Фото/Файл без опису]"
        data['details'] = msg_text
        
        # Перевіряємо, чи це термінове замовлення, і змінюємо заголовок
        is_urgent = data.get('is_urgent', False)
        title = "🔥🔥🔥 ТЕРМІНОВЕ ЗАМОВЛЕННЯ! 🔥🔥🔥" if is_urgent else "⚡️ НОВЕ ЗАМОВЛЕННЯ!"
        
        report = (
            f"<b>{title}</b>\n\n"
            f"👤 <b>Від:</b> {data['name']} (@{message.from_user.username})\n"
            f"🎓 <b>Група:</b> {data['group']}\n"
            f"📚 <b>Предмет:</b> {data['subject']}\n"
            f"👨‍🏫 <b>Викладач:</b> {data['teacher']}\n"
            f"📝 <b>Деталі:</b> {data['details']}\n\n"
            f"ℹ️ <i>Щоб відповісти клієнту, натисніть REPLY на це повідомлення.</i>\n"
            f"🆔 <code>{message.from_user.id}</code>"
        )
    
    if ADMIN_GROUP_ID != 0:
        await bot.send_message(ADMIN_GROUP_ID, report, parse_mode="HTML")
        if message.content_type != 'text':
            await message.forward(ADMIN_GROUP_ID)
    
    await state.finish()
    await message.answer("✅ Замовлення прийнято! Ми зв'яжемося з вами найближчим часом.", reply_markup=get_main_keyboard())

# --- 5. ПІДТРИМКА ---
@dp.message_handler(lambda msg: msg.text == "💬 Підтримка", state="*")
async def start_support(message: types.Message):
    await SupportState.waiting_for_message.set()
    await message.answer(
        "✍️ Напишіть ваше повідомлення.\n"
        "Можна надсилати текст, фото або файли.", 
        reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add("🔙 Скасувати")
    )

@dp.message_handler(lambda msg: msg.text == "🔙 Скасувати", state=SupportState.waiting_for_message)
async def cancel_support(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("Діалог завершено.", reply_markup=get_main_keyboard())

@dp.message_handler(state=SupportState.waiting_for_message, content_types=types.ContentTypes.ANY)
async def process_support_msg(message: types.Message, state: FSMContext):
    if ADMIN_GROUP_ID != 0:
        forward_text = (
            f"📩 <b>ПОВІДОМЛЕННЯ ВІД КОРИСТУВАЧА</b>\n"
            f"👤 {message.from_user.full_name} (@{message.from_user.username})\n"
            f"🆔 <code>{message.from_user.id}</code>\n"
            f"⬇️ <i>Відповідайте на повідомлення нижче:</i>"
        )
        await bot.send_message(ADMIN_GROUP_ID, forward_text, parse_mode="HTML")
        await message.forward(ADMIN_GROUP_ID)
    
    await state.finish()
    await message.answer("✅ Надіслано! Чекайте на відповідь.", reply_markup=get_main_keyboard())

# --- 6. РЕЖИМ ЧАТУ (АДМІН ВІДПОВІДАЄ) ---
@dp.message_handler(lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message, content_types=types.ContentTypes.ANY)
async def admin_reply_handler(message: types.Message):
    try:
        reply_msg = message.reply_to_message
        user_id = None
        text_to_check = reply_msg.text or reply_msg.caption or ""
        
        if "🆔" in text_to_check:
            parts = text_to_check.split("🆔")
            if len(parts) > 1:
                code_part = parts[1]
                if "<code>" in code_part:
                    user_id = int(code_part.split("<code>")[1].split("</code>")[0])
        elif reply_msg.forward_from:
            user_id = reply_msg.forward_from.id
            
        if user_id:
            await message.copy_to(user_id)
            await message.reply("✅ Відповідь надіслано!")
        else:
            pass

    except Exception as e:
        pass

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
