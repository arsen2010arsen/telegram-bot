from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiohttp import web
import os
import logging
import re
import asyncio

# --- НАЛАШТУВАННЯ ---

# 👇 ВСТАВТЕ СЮДИ ВАШ ТОКЕН!
TOKEN = "8516307940:AAHecLuAJqpmlv0Oz-morWAR7z_1Nr8nmcE"

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

# --- КЛАВІАТУРА ---
def get_main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Прайс-лист", "📚 Замовити роботу")
    kb.add("🔥 Термінове замовлення")
    kb.add("💬 Підтримка", "⚠️ Попередження")
    return kb

# --- СТАРТ ---
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("👋 Вітаємо в LabHub!\nОбери опцію нижче 👇", reply_markup=get_main_keyboard())

# --- ID ГРУПИ ---
@dp.message_handler(commands=['getid'])
async def get_id(message: types.Message):
    await message.reply(f"ID: `{message.chat.id}`", parse_mode="Markdown")

# --- ПРАЙС-ЛИСТ ---
@dp.message_handler(lambda m: m.text == "📄 Прайс-лист")
async def price(m: types.Message):
    text = (
        "🔬 Лабораторна робота — <b>50 грн / шт.</b>\n"
        "📝 Практична робота — <b>50 грн / шт.</b>\n\n"
        "⏳ <i>Термінове виконання оплачується додатково.</i>"
    )
    await m.answer(text, parse_mode="HTML")

# --- ПОПЕРЕДЖЕННЯ (НОВИЙ ТЕКСТ) ---
@dp.message_handler(lambda m: m.text == "⚠️ Попередження")
async def warn(m: types.Message):
    text = (
        "<b>⚠️ ВАЖЛИВА ІНФОРМАЦІЯ</b>\n\n"
        "Ми докладаємо максимум зусиль, щоб виконати завдання якісно та правильно. ✅\n\n"
        "Проте, <b>ми не надаємо 100% гарантії</b> на повну відсутність помилок або отримання найвищого балу, "
        "оскільки вимоги у кожного викладача можуть відрізнятися.\n\n"
        "Адміністрація бота не несе відповідальності за ваші оцінки та можливі академічні наслідки. "
        "Використовуючи отримані матеріали, ви берете всі ризики на себе."
    )
    await m.answer(text, parse_mode="HTML")

# --- ЗАМОВЛЕННЯ ---
@dp.message_handler(lambda m: m.text == "📚 Замовити роботу", state="*")
async def order_start(m: types.Message, state: FSMContext):
    await OrderState.waiting_for_name.set()
    async with state.proxy() as data: data['is_urgent'] = False
    await m.answer("1️⃣ Введіть ПІБ:", reply_markup=types.ReplyKeyboardRemove())

@dp.message_handler(lambda m: m.text == "🔥 Термінове замовлення", state="*")
async def order_urgent(m: types.Message, state: FSMContext):
    await OrderState.waiting_for_name.set()
    async with state.proxy() as data: data['is_urgent'] = True
    await m.answer("🚀 <b>ТЕРМІНОВО!</b>\n1️⃣ Введіть ПІБ:", parse_mode="HTML", reply_markup=types.ReplyKeyboardRemove())

# --- ЕТАПИ АНКЕТИ ---
@dp.message_handler(state=OrderState.waiting_for_name)
async def s1(m: types.Message, state: FSMContext):
    async with state.proxy() as d: d['name'] = m.text
    await OrderState.next()
    await m.answer("2️⃣ Група:")

@dp.message_handler(state=OrderState.waiting_for_group)
async def s2(m: types.Message, state: FSMContext):
    async with state.proxy() as d: d['group'] = m.text
    await OrderState.next()
    await m.answer("3️⃣ Предмет:")

@dp.message_handler(state=OrderState.waiting_for_subject)
async def s3(m: types.Message, state: FSMContext):
    async with state.proxy() as d: d['subject'] = m.text
    await OrderState.next()
    await m.answer("4️⃣ Викладач:")

@dp.message_handler(state=OrderState.waiting_for_teacher)
async def s4(m: types.Message, state: FSMContext):
    async with state.proxy() as d:
        d['teacher'] = m.text
        d['media'] = []
        d['desc'] = []
    await OrderState.next()
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True).add("✅ Відправити замовлення")
    await m.answer("5️⃣ Скиньте завдання (фото/файл) і натисніть кнопку:", reply_markup=kb)

# --- ЗБІР І ВІДПРАВКА ---
@dp.message_handler(state=OrderState.waiting_for_details, content_types=types.ContentTypes.ANY)
async def s5(m: types.Message, state: FSMContext):
    if m.text == "✅ Відправити замовлення":
        async with state.proxy() as d:
            desc = "\n".join(d['desc']) or "[Без опису]"
            title = "🔥🔥🔥 ТЕРМІНОВО!" if d['is_urgent'] else "⚡️ НОВЕ ЗАМОВЛЕННЯ!"
            report = (f"<b>{title}</b>\n👤 {d['name']}\n🎓 {d['group']}\n📚 {d['subject']}\n"
                      f"👨‍🏫 {d['teacher']}\n📝 {desc}\n🆔 <code>{m.from_user.id}</code>")
            
            if ADMIN_GROUP_ID != 0:
                await bot.send_message(ADMIN_GROUP_ID, report, parse_mode="HTML")
                for mid in d['media']:
                    try: await bot.forward_message(ADMIN_GROUP_ID, m.chat.id, mid)
                    except: pass
        
        await state.finish()
        await m.answer("✅ Прийнято!", reply_markup=get_main_keyboard())
        return

    async with state.proxy() as d:
        if m.text: d['desc'].append(m
