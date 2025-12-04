from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiohttp import web
import os
import logging
import re  # <--- ДОДАЛИ БІБЛІОТЕКУ ДЛЯ ПОШУКУ ЦИФР

# --- НАЛАШТУВАННЯ ---

# 👇 ВСТАВТЕ СЮДИ ВАШ ТОКЕН
TOKEN = "8516307940:AAEhZ84NunCwC470Au2LQTDTPT2rDzHTR_s"

# ВАШ ID ГРУПИ
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

async
