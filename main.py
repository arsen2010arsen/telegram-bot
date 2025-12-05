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

# 👇 ВСТАВТЕ СЮДИ ВАШ ТОКЕН
TOKEN = "8516307940:AAHecLuAJqpmlv0Oz-morWAR7z_1Nr8nmcE"

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
    waiting_for_deadline = State()
    waiting_for_details = State()

class SupportState(StatesGroup):
    waiting_for_message = State()

# --- КЛАВІАТУРИ ---
def get_main_keyboard():
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("📄 Прайс-лист", "📚 Замовити роботу")
    kb.add("🔥 Термінове замовлення")
    kb.add("💬 Підтримка", "⚠️ Попередження")
    return kb

def get_cancel_kb():
    return types.ReplyKeyboardMarkup(resize_keyboard=True).add("🚫 Скасувати")

def get_finish_chat_kb():
    return types.ReplyKeyboardMarkup(resize_keyboard=True).add("🏁 Закінчити переписку")

# --- ГЛОБАЛЬНЕ СКАСУВАННЯ ---
@dp.message_handler(lambda m: m.text in ["🚫 Скасувати", "🏁 Закінчити переписку"], state="*")
async def global_cancel(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        return
    
    await state.finish()
    await message.answer("✅ Діалог завершено. Ви в головному меню.", reply_markup=get_main_keyboard())

# --- СТАРТ ---
@dp.message_handler(commands=['start'], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()
    await message.answer("👋 Вітаємо в LabHub!\nОбери опцію нижче 👇", reply_markup=get_main_keyboard())

# --- ID ГРУПИ ---
@dp.message_handler(commands=['getid'])
async def get_id(message: types.Message):
    await message.reply(f"ID: `{message.chat.id}`", parse_mode="Markdown")

# --- КНОПКИ ---
@dp.message_handler(lambda m: m.text == "📄 Прайс-лист")
async def price(m: types.Message):
    text = (
        "🔬 Лабораторна робота — <b>50 грн / шт.</b>\n"
        "📝 Практична робота — <b>50 грн / шт.</b>\n\n"
        "⏳ <i>Термінове виконання оплачується додатково.</i>"
    )
    await m.answer(text, parse_mode="HTML")

@dp.message_handler(lambda m: m.text == "⚠️ Попередження")
async def warn(m: types.Message):
    text = (
        "<b>⚠️ ВАЖЛИВА ІНФОРМАЦІЯ</b>\n\n"
        "Ми докладаємо максимум зусиль, щоб виконати завдання якісно та правильно. ✅\n\n"
        "Проте, <b>ми не надаємо 100% гарантії</b> на повну відсутність помилок або отримання найвищого балу.\n\n"
        "Адміністрація бота не несе відповідальності за ваші оцінки. Використовуючи отримані матеріали, ви берете всі ризики на себе."
    )
    await m.answer(text, parse_mode="HTML")

# --- ЗАМОВЛЕННЯ ---
@dp.message_handler(lambda m: m.text == "📚 Замовити роботу", state="*")
async def order_start(m: types.Message, state: FSMContext):
    await OrderState.waiting_for_name.set()
    async with state.proxy() as data: data['is_urgent'] = False
    await m.answer("1️⃣ Введіть ПІБ:", reply_markup=get_cancel_kb())

@dp.message_handler(lambda m: m.text == "🔥 Термінове замовлення", state="*")
async def order_urgent(m: types.Message, state: FSMContext):
    await OrderState.waiting_for_name.set()
    async with state.proxy() as data: data['is_urgent'] = True
    await m.answer("🚀 <b>ТЕРМІНОВО!</b>\n1️⃣ Введіть ПІБ:", parse_mode="HTML", reply_markup=get_cancel_kb())

# --- ЕТАПИ АНКЕТИ ---
@dp.message_handler(state=OrderState.waiting_for_name)
async def s1(m: types.Message, state: FSMContext):
    async with state.proxy() as d: d['name'] = m.text
    await OrderState.next()
    await m.answer("2️⃣ Група:", reply_markup=get_cancel_kb())

@dp.message_handler(state=OrderState.waiting_for_group)
async def s2(m: types.Message, state: FSMContext):
    async with state.proxy() as d: d['group'] = m.text
    await OrderState.next()
    await m.answer("3️⃣ Предмет:", reply_markup=get_cancel_kb())

@dp.message_handler(state=OrderState.waiting_for_subject)
async def s3(m: types.Message, state: FSMContext):
    async with state.proxy() as d: d['subject'] = m.text
    await OrderState.next()
    await m.answer("4️⃣ Викладач:", reply_markup=get_cancel_kb())

@dp.message_handler(state=OrderState.waiting_for_teacher)
async def s4(m: types.Message, state: FSMContext):
    async with state.proxy() as d: d['teacher'] = m.text
    
    if d['is_urgent']:
        await OrderState.waiting_for_deadline.set()
        await m.answer("⏰ <b>На коли потрібно?</b> (Дата/Час):", parse_mode="HTML", reply_markup=get_cancel_kb())
    else:
        d['deadline'] = "Не вказано (Стандарт)"
        d['media'] = []
        d['desc'] = []
        await OrderState.waiting_for_details.set()
        kb = get_cancel_kb().add("✅ Відправити замовлення")
        await m.answer("5️⃣ Скиньте завдання (фото/файл) і натисніть кнопку:", reply_markup=kb)

@dp.message_handler(state=OrderState.waiting_for_deadline)
async def s4_deadline(m: types.Message, state: FSMContext):
    async with state.proxy() as d:
        d['deadline'] = m.text
        d['media'] = []
        d['desc'] = []
    
    await OrderState.waiting_for_details.set()
    kb = get_cancel_kb().add("✅ Відправити замовлення")
    await m.answer("5️⃣ Скиньте завдання (фото/файл) і натисніть кнопку:", reply_markup=kb)

# --- ЗБІР ТА ВІДПРАВКА ---
@dp.message_handler(state=OrderState.waiting_for_details, content_types=types.ContentTypes.ANY)
async def s5(m: types.Message, state: FSMContext):
    if m.text == "✅ Відправити замовлення":
        async with state.proxy() as d:
            desc = "\n".join(d['desc']) or "[Без опису]"
            
            if d['is_urgent']:
                title = "🔥🔥🔥 ТЕРМІНОВО!"
                deadl = f"⏰ <b>ТЕРМІН:</b> {d['deadline']}"
            else:
                title = "⚡️ НОВЕ ЗАМОВЛЕННЯ!"
                deadl = ""

            report = (
                f"<b>{title}</b>\n\n"
                f"👤 <b>ПІБ:</b> {d['name']} (@{m.from_user.username})\n"
                f"🎓 <b>Група:</b> {d['group']}\n"
                f"📚 <b>Предмет:</b> {d['subject']}\n"
                f"👨‍🏫 <b>Викладач:</b> {d['teacher']}\n"
                f"{deadl}\n"
                f"📝 <b>Деталі:</b> {desc}\n\n"
                f"🆔 <code>{m.from_user.id}</code>"
            )
            
            if ADMIN_GROUP_ID != 0:
                await bot.send_message(ADMIN_GROUP_ID, report, parse_mode="HTML")
                for mid in d['media']:
                    try: await bot.forward_message(ADMIN_GROUP_ID, m.chat.id, mid)
                    except: pass
        
        await SupportState.waiting_for_message.set()
        await m.answer(
            "✅ <b>Замовлення прийнято!</b>\n\n"
            "💬 <b>Режим чату активний.</b>\n"
            "Ви можете дописати деталі або скинути ще файли сюди.\n"
            "Щоб вийти, натисніть «🏁 Закінчити переписку».", 
            parse_mode="HTML",
            reply_markup=get_finish_chat_kb()
        )
        return

    async with state.proxy() as d:
        if m.text: d['desc'].append(m.text)
        if m.content_type != 'text':
            d['media'].append(m.message_id)
            if m.caption: d['desc'].append(m.caption)

# --- ПІДТРИМКА ---
@dp.message_handler(lambda m: m.text == "💬 Підтримка", state="*")
async def supp(m: types.Message):
    await SupportState.waiting_for_message.set()
    await m.answer(
        "✍️ <b>Ви на зв'язку з адміном.</b>\n"
        "Пишіть ваше питання/повідомлення. Можна відправляти фото та файли.", 
        parse_mode="HTML",
        reply_markup=get_finish_chat_kb()
    )

# --- ОБРОБКА ПОВІДОМЛЕНЬ ВІД КОРИСТУВАЧА ---
@dp.message_handler(state=SupportState.waiting_for_message, content_types=types.ContentTypes.ANY)
async def supp_msg(m: types.Message, state: FSMContext):
    if m.text in ["🚫 Скасувати", "🏁 Закінчити переписку"]:
        await state.finish()
        await m.answer("Діалог завершено.", reply_markup=get_main_keyboard())
        return

    if ADMIN_GROUP_ID != 0:
        await bot.send_message(ADMIN_GROUP_ID, f"📩 <b>ПОВІДОМЛЕННЯ</b>\nВід: {m.from_user.full_name}\n🆔 <code>{m.from_user.id}</code>", parse_mode="HTML")
        await m.forward(ADMIN_GROUP_ID)

# --- ОБРОБКА REPLY (КОЛИ КОРИСТУВАЧ ПРОСТО ВІДПОВІДАЄ В ПП) ---
# ЦЕЙ ХЕНДЛЕР ПРАЦЮЄ ТІЛЬКИ В ОСОБИСТИХ ЧАТАХ (НЕ В ГРУПІ)
@dp.message_handler(lambda m: m.chat.type == 'private' and m.reply_to_message and m.reply_to_message.from_user.id == bot.id, content_types=types.ContentTypes.ANY)
async def user_reply_to_admin(m: types.Message):
    if ADMIN_GROUP_ID != 0:
        await bot.send_message(ADMIN_GROUP_ID, f"↩️ <b>REPLY ВІД КОРИСТУВАЧА</b>\nВід: {m.from_user.full_name}\n🆔 <code>{m.from_user.id}</code>", parse_mode="HTML")
        await m.forward(ADMIN_GROUP_ID)
    await m.answer("✅ Передано адміну.")

# --- АДМІН ВІДПОВІДАЄ (ТІЛЬКИ В ГРУПІ) ---
@dp.message_handler(lambda m: m.chat.id == ADMIN_GROUP_ID and m.reply_to_message, content_types=types.ContentTypes.ANY)
async def reply(m: types.Message):
    try:
        rep = m.reply_to_message
        txt = rep.text or rep.caption or ""
        uid = None
        # Шукаємо ID через Regex або Forward
        if match := re.search(r"🆔\s*(\d+)", txt): uid = int(match.group(1))
        elif rep.forward_from: uid = rep.forward_from.id
        
        if uid:
            await m.copy_to(uid)
            await m.reply("✅ Відповідь надіслано!")
        else:
            # Якщо адмін відповів на повідомлення без ID, просто ігноруємо
            # або можна вивести повідомлення, що ID не знайдено
            pass 
    except Exception as e:
        await m.reply(f"❌ Помилка: {e}")

# --- СЕРВЕР ---
async def keep_alive(request):
    return web.Response(text="I am alive!")

async def on_startup(dp):
    app = web.Application()
    app.router.add_get('/', keep_alive)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get('PORT', 8080)))
    await site.start()

if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup)
