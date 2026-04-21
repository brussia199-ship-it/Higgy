import sqlite3
import random
import string
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.utils import executor
from aiogram.contrib.fsm_storage.memory import MemoryStorage

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8655230768:AAFnkU2Sqk3ZkP2M1NWp4yvZQnwBdMJL_lw"
ADMIN_IDS = [7673683792]  # Ваш Telegram ID

# ========== БАЗА ДАННЫХ ==========
class Database:
    def __init__(self, db_file="gifts.db"):
        self.connection = sqlite3.connect(db_file, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self._create_tables()

    def _create_tables(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS gifts (
                id INTEGER PRIMARY KEY,
                stars_original INTEGER NOT NULL,
                stars_discounted INTEGER NOT NULL
            )
        """)
        
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS checks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                gift_id INTEGER NOT NULL,
                user_id INTEGER,
                status TEXT DEFAULT 'active',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Добавляем подарки по умолчанию
        default_gifts = [(15, 9), (25, 15), (50, 30), (100, 60)]
        for orig, disc in default_gifts:
            self.cursor.execute(
                "INSERT OR IGNORE INTO gifts (id, stars_original, stars_discounted) VALUES (?, ?, ?)",
                (orig, orig, disc)
            )
        self.connection.commit()

    def get_gift_price(self, stars_original):
        result = self.cursor.execute(
            "SELECT stars_discounted FROM gifts WHERE stars_original = ?",
            (stars_original,)
        ).fetchone()
        return result[0] if result else None

    def get_all_gifts(self):
        return self.cursor.execute(
            "SELECT stars_original, stars_discounted FROM gifts ORDER BY stars_original"
        ).fetchall()

    def update_gift_price(self, stars_original, new_price):
        self.cursor.execute(
            "UPDATE gifts SET stars_discounted = ? WHERE stars_original = ?",
            (new_price, stars_original)
        )
        self.connection.commit()

    def create_check(self, code, gift_id):
        self.cursor.execute(
            "INSERT INTO checks (code, gift_id) VALUES (?, ?)",
            (code, gift_id)
        )
        self.connection.commit()
        return code

    def use_check(self, code, user_id):
        check = self.cursor.execute(
            "SELECT id, gift_id FROM checks WHERE code = ? AND status = 'active'",
            (code,)
        ).fetchone()
        if check:
            self.cursor.execute(
                "UPDATE checks SET status = 'used', user_id = ? WHERE code = ?",
                (user_id, code)
            )
            self.connection.commit()
            return check[1]
        return None

    def get_all_checks(self):
        return self.cursor.execute(
            "SELECT code, gift_id, status, user_id, created_at FROM checks ORDER BY created_at DESC"
        ).fetchall()

    def get_stats(self):
        total = self.cursor.execute("SELECT COUNT(*) FROM checks").fetchone()[0]
        used = self.cursor.execute("SELECT COUNT(*) FROM checks WHERE status = 'used'").fetchone()[0]
        active = total - used
        return total, active, used
    
    def get_all_users(self):
        # Получаем всех пользователей, которые активировали чеки
        users = self.cursor.execute(
            "SELECT DISTINCT user_id FROM checks WHERE user_id IS NOT NULL"
        ).fetchall()
        return [u[0] for u in users]

db = Database()

# ========== КЛАВИАТУРЫ ==========
def main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("🎁 Купить подарок", callback_data="buy_gift"),
        InlineKeyboardButton("✅ Активировать чек", callback_data="activate_check"),
        InlineKeyboardButton("ℹ️ О магазине", callback_data="about")
    ]
    keyboard.add(*buttons)
    return keyboard

def gifts_keyboard():
    gifts = db.get_all_gifts()
    keyboard = InlineKeyboardMarkup(row_width=2)
    for stars_original, stars_discounted in gifts:
        keyboard.add(InlineKeyboardButton(
            f"⭐ {stars_original} → {stars_discounted} ⭐",
            callback_data=f"gift_{stars_original}"
        ))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_menu"))
    return keyboard

def admin_panel():
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton("📝 Создать чек", callback_data="admin_create_check"),
        InlineKeyboardButton("💰 Редактировать цены", callback_data="admin_edit_prices"),
        InlineKeyboardButton("📢 Сделать рассылку", callback_data="admin_mailing"),
        InlineKeyboardButton("📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton("📜 Все чеки", callback_data="admin_checks")
    )
    return keyboard

def edit_prices_keyboard():
    gifts = db.get_all_gifts()
    keyboard = InlineKeyboardMarkup(row_width=1)
    for stars_original, stars_discounted in gifts:
        keyboard.add(InlineKeyboardButton(
            f"✏️ {stars_original}⭐ → сейчас {stars_discounted}⭐",
            callback_data=f"edit_{stars_original}"
        ))
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_admin"))
    return keyboard

def cancel_button():
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("❌ Отмена"))
    return keyboard

# ========== СОСТОЯНИЯ ==========
class Form(StatesGroup):
    waiting_check_code = State()
    waiting_edit_price = State()
    waiting_mailing = State()
    waiting_mailing_text = State()

# ========== ИНИЦИАЛИЗАЦИЯ БОТА ==========
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())

# ========== ПРОВЕРКА АДМИНА ==========
def is_admin(user_id):
    return user_id in ADMIN_IDS

# ========== ХЕНДЛЕРЫ ==========

@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    await message.answer(
        "🎁 *Добро пожаловать в GiftShop Bot!*\n\n"
        "У нас вы можете купить Telegram Подарки со скидкой:\n"
        "• 15⭐ → 9⭐\n"
        "• 25⭐ → 15⭐\n"
        "• 50⭐ → 30⭐\n"
        "• 100⭐ → 60⭐\n\n"
        "Выберите действие:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "back_menu")
async def back_to_menu(call: types.CallbackQuery):
    await call.message.edit_text(
        "🎁 *Главное меню*\n\nВыберите действие:",
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "buy_gift")
async def buy_gift(call: types.CallbackQuery):
    await call.message.edit_text(
        "🎁 *Выберите подарок:*\n\n"
        "Нажмите на нужный вариант, чтобы получить счёт для оплаты:",
        reply_markup=gifts_keyboard(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("gift_"))
async def process_gift(call: types.CallbackQuery):
    stars_original = int(call.data.split("_")[1])
    price = db.get_gift_price(stars_original)
    
    if price:
        # Создаём инвойс для оплаты звёздами
        await bot.send_invoice(
            chat_id=call.from_user.id,
            title=f"Telegram Подарок на {stars_original} ⭐",
            description=f"Подарок стоимостью {stars_original}⭐ по специальной цене {price}⭐",
            payload=f"gift_{stars_original}",
            provider_token="",  # Для звёзд оставляем пустым
            currency="XTR",  # Валюта Telegram Stars
            prices=[types.LabeledPrice(label="Подарок", amount=price)],
            start_parameter="gift_purchase"
        )
    await call.answer()

@dp.pre_checkout_query_handler(lambda query: True)
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=['successful_payment'])
async def process_successful_payment(message: types.Message):
    payload = message.successful_payment.invoice_payload
    stars_original = int(payload.split("_")[1])
    
    # Генерируем чек
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))
    db.create_check(code, stars_original)
    
    await message.answer(
        f"✅ *Оплата прошла успешно!*\n\n"
        f"🎁 Ваш подарок на {stars_original}⭐ готов!\n"
        f"📝 *Чек для активации:* `{code}`\n\n"
        f"⚠️ Сохраните этот код. Чтобы получить подарок, нажмите «Активировать чек» в главном меню.",
        parse_mode="Markdown"
    )

@dp.callback_query_handler(lambda c: c.data == "activate_check")
async def activate_check_start(call: types.CallbackQuery, state: FSMContext):
    await call.message.edit_text(
        "🔑 *Введите код чека:*\n\n"
        "Пример: `ABC123XYZ789`\n\n"
        "Или нажмите «Отмена»",
        reply_markup=cancel_button(),
        parse_mode="Markdown"
    )
    await Form.waiting_check_code.set()
    await call.answer()

@dp.message_handler(state=Form.waiting_check_code)
async def process_check_code(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("❌ Операция отменена", reply_markup=main_menu())
        return
    
    code = message.text.strip().upper()
    gift_id = db.use_check(code, message.from_user.id)
    
    if gift_id:
        # Здесь должен быть код отправки реального подарка через Bot API
        # Для демонстрации просто выводим сообщение
        await message.answer(
            f"✅ *Чек успешно активирован!*\n\n"
            f"🎁 Вы получили Telegram Подарок на {gift_id}⭐!\n\n"
            f"Подарок отправлен вам в чат (демо-режим).",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    else:
        await message.answer(
            "❌ *Неверный или уже использованный код!*\n\n"
            "Проверьте правильность ввода.",
            parse_mode="Markdown",
            reply_markup=main_menu()
        )
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "about")
async def about(call: types.CallbackQuery):
    gifts = db.get_all_gifts()
    text = "🎁 *Наши цены:*\n\n"
    for orig, disc in gifts:
        text += f"• {orig}⭐ → *{disc}⭐* (экономия {orig - disc}⭐)\n"
    text += "\n🤖 *Как это работает:*\n"
    text += "1. Выберите подарок\n"
    text += "2. Оплатите звёздами\n"
    text += "3. Получите чек\n"
    text += "4. Активируйте чек и заберите подарок\n\n"
    text += "По вопросам: @support"
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=back_button())
    await call.answer()

def back_button():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_menu"))
    return keyboard

# ========== АДМИН-ХЕНДЛЕРЫ ==========

@dp.message_handler(commands=['admin'])
async def admin_cmd(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.answer("⛔ Доступ запрещён")
        return
    await message.answer("👑 *Админ-панель*", reply_markup=admin_panel(), parse_mode="Markdown")

@dp.callback_query_handler(lambda c: c.data == "back_admin")
async def back_admin(call: types.CallbackQuery):
    await call.message.edit_text("👑 *Админ-панель*", reply_markup=admin_panel(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_stats")
async def admin_stats(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    total, active, used = db.get_stats()
    gifts = db.get_all_gifts()
    
    text = "📊 *Статистика:*\n\n"
    text += f"📦 Всего чеков: {total}\n"
    text += f"✅ Активных: {active}\n"
    text += f"❌ Использовано: {used}\n\n"
    text += "💰 *Текущие цены:*\n"
    for orig, disc in gifts:
        text += f"• {orig}⭐ → {disc}⭐\n"
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_checks")
async def admin_checks(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    checks = db.get_all_checks()
    if not checks:
        await call.message.edit_text("📜 *Чеков пока нет*", parse_mode="Markdown", reply_markup=admin_panel())
        return
    
    text = "📜 *Последние 20 чеков:*\n\n"
    for code, gift_id, status, user_id, created_at in checks[:20]:
        status_emoji = "✅" if status == "active" else "❌"
        user_info = f"пользователь {user_id}" if user_id else "не активирован"
        text += f"{status_emoji} `{code}` → {gift_id}⭐ ({user_info})\n"
    
    await call.message.edit_text(text, parse_mode="Markdown", reply_markup=admin_panel())
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_create_check")
async def admin_create_check_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await call.message.edit_text(
        "📝 *Создание чека*\n\n"
        "Выберите тип подарка:",
        reply_markup=gifts_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state("waiting_gift_for_check")
    await call.answer()

@dp.callback_query_handler(state="waiting_gift_for_check", lambda c: c.data.startswith("gift_"))
async def process_create_check(call: types.CallbackQuery, state: FSMContext):
    stars_original = int(call.data.split("_")[1])
    code = generate_code()
    db.create_check(code, stars_original)
    
    await call.message.edit_text(
        f"✅ *Чек создан!*\n\n"
        f"🎁 Подарок: {stars_original}⭐\n"
        f"🔑 Код: `{code}`\n\n"
        f"Отправьте этот код пользователю.",
        parse_mode="Markdown",
        reply_markup=admin_panel()
    )
    await state.finish()
    await call.answer()

@dp.callback_query_handler(lambda c: c.data == "admin_edit_prices")
async def admin_edit_prices(call: types.CallbackQuery):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await call.message.edit_text(
        "💰 *Редактирование цен*\n\n"
        "Выберите подарок для изменения цены:",
        reply_markup=edit_prices_keyboard(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("edit_"))
async def edit_price_start(call: types.CallbackQuery, state: FSMContext):
    stars_original = int(call.data.split("_")[1])
    current_price = db.get_gift_price(stars_original)
    
    await state.update_data(edit_gift=stars_original)
    await call.message.edit_text(
        f"✏️ *Изменение цены*\n\n"
        f"Подарок: {stars_original}⭐\n"
        f"Текущая цена: {current_price}⭐\n\n"
        f"Введите новую цену (в звёздах):",
        parse_mode="Markdown",
        reply_markup=cancel_button()
    )
    await Form.waiting_edit_price.set()
    await call.answer()

@dp.message_handler(state=Form.waiting_edit_price)
async def process_edit_price(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("❌ Отменено", reply_markup=admin_panel())
        return
    
    try:
        new_price = int(message.text)
        if new_price <= 0:
            raise ValueError
        
        data = await state.get_data()
        stars_original = data.get('edit_gift')
        db.update_gift_price(stars_original, new_price)
        
        await message.answer(
            f"✅ *Цена обновлена!*\n\n"
            f"Подарок {stars_original}⭐ теперь стоит {new_price}⭐",
            parse_mode="Markdown",
            reply_markup=admin_panel()
        )
    except ValueError:
        await message.answer("❌ Введите корректное число (больше 0)", reply_markup=cancel_button())
        return
    
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == "admin_mailing")
async def admin_mailing_start(call: types.CallbackQuery, state: FSMContext):
    if not is_admin(call.from_user.id):
        await call.answer("⛔ Доступ запрещён", show_alert=True)
        return
    
    await call.message.edit_text(
        "📢 *Рассылка*\n\n"
        "Введите текст для рассылки (можно с HTML-разметкой):\n\n"
        "Пример: <b>Жирный текст</b>",
        parse_mode="Markdown",
        reply_markup=cancel_button()
    )
    await Form.waiting_mailing.set()
    await call.answer()

@dp.message_handler(state=Form.waiting_mailing)
async def process_mailing_text(message: types.Message, state: FSMContext):
    if message.text == "❌ Отмена":
        await state.finish()
        await message.answer("❌ Рассылка отменена", reply_markup=admin_panel())
        return
    
    await state.update_data(mailing_text=message.text)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ Отправить", callback_data="mailing_send"),
        InlineKeyboardButton("❌ Отмена", callback_data="mailing_cancel")
    )
    
    await message.answer(
        f"📢 *Предпросмотр рассылки:*\n\n{message.text}\n\n"
        f"Подтвердите отправку:",
        parse_mode="HTML",
        reply_markup=keyboard
    )
    await Form.waiting_mailing_text.set()

@dp.callback_query_handler(state=Form.waiting_mailing_text, lambda c: c.data == "mailing_send")
async def send_mailing(call: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    text = data.get('mailing_text')
    
    users = db.get_all_users()
    success = 0
    fail = 0
    
    await call.message.edit_text("⏳ Отправка рассылки...")
    
    for user_id in users:
        try:
            await bot.send_message(user_id, text, parse_mode="HTML")
            success += 1
        except:
            fail += 1
    
    await call.message.edit_text(
        f"✅ *Рассылка завершена!*\n\n"
        f"📤 Отправлено: {success}\n"
        f"❌ Ошибок: {fail}",
        parse_mode="Markdown",
        reply_markup=admin_panel()
    )
    await state.finish()

@dp.callback_query_handler(state=Form.waiting_mailing_text, lambda c: c.data == "mailing_cancel")
async def cancel_mailing(call: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await call.message.edit_text("❌ Рассылка отменена", reply_markup=admin_panel())
    await call.answer()

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=12))

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🎁 Бот запущен!")
    executor.start_polling(dp, skip_updates=True)
