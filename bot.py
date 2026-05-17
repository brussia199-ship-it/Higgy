import asyncio
import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, Optional, Tuple

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8830098882:AAEQVdiWSpcNhV4vZk5dxtIZ7Hj4lnCU3Qw"  # Токен от @BotFather
CRYPTOBOT_TOKEN = "583403:AAfrNWLb7jwLrPAIQavMgItheP4X3X5GthY"  # Токен от @CryptoBot
ADMIN_IDS = 7673683792  # ID администраторов

# ========== БАЗА ДАННЫХ SQLite ==========
db = sqlite3.connect("guarantee_bot.db", check_same_thread=False)
cursor = db.cursor()

# Создание таблиц
cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    registered_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS deals (
    deal_id TEXT PRIMARY KEY,
    tag TEXT UNIQUE,
    seller_id INTEGER,
    buyer_id INTEGER,
    amount REAL,
    commission REAL DEFAULT 0,
    status TEXT DEFAULT 'pending',  -- pending, funded, completed, disputed, closed
    created_at TIMESTAMP,
    funded_at TIMESTAMP,
    chat_id INTEGER UNIQUE,
    invoice_id TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT,
    from_id INTEGER,
    message_text TEXT,
    timestamp TIMESTAMP,
    FOREIGN KEY(deal_id) REFERENCES deals(deal_id)
);

CREATE TABLE IF NOT EXISTS withdraws (
    withdraw_id TEXT PRIMARY KEY,
    user_id INTEGER,
    amount REAL,
    wallet_address TEXT,
    status TEXT DEFAULT 'pending',  -- pending, completed, rejected
    created_at TIMESTAMP
);

CREATE TABLE IF NOT EXISTS admin_settings (
    key TEXT PRIMARY KEY,
    value TEXT
);
""")

# Установка комиссии по умолчанию
cursor.execute("INSERT OR IGNORE INTO admin_settings (key, value) VALUES ('commission', '5')")
db.commit()

# ========== FSM СОСТОЯНИЯ ==========
class CreateDeal(StatesGroup):
    waiting_for_amount = State()
    waiting_for_partner_id = State()

class WithdrawState(StatesGroup):
    waiting_for_amount = State()
    waiting_for_wallet = State()

class AdminState(StatesGroup):
    waiting_commission = State()
    waiting_broadcast = State()
    watching_chat = State()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def generate_deal_tag() -> str:
    """Генерация уникального тега для сделки #00:AABBCC"""
    import random
    hex_part = ''.join(random.choices('0123456789ABCDEF', k=6))
    return f"#{random.randint(10,99)}:{hex_part}"

def get_commission() -> float:
    cursor.execute("SELECT value FROM admin_settings WHERE key='commission'")
    return float(cursor.fetchone()[0])

def format_balance(amount: float) -> str:
    return f"{amount:.2f} RUB"

async def create_crypto_invoice(amount_rub: float) -> Tuple[str, str]:
    """Создание инвойса через CryptoBot API"""
    import requests
    
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "asset": "RUB",
        "amount": str(amount_rub),
        "paid_btn_name": "callback",
        "paid_btn_url": "https://t.me/your_bot"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        result = response.json()
        if result.get("ok"):
            return result["result"]["invoice_id"], result["result"]["pay_url"]
        return None, None
    except:
        return None, None

# ========== КЛАВИАТУРЫ ==========
def main_menu(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")],
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw")],
    ]
    if user_id in ADMIN_IDS:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Установить комиссию", callback_data="admin_commission")],
        [InlineKeyboardButton(text="📋 Все сделки", callback_data="admin_deals")],
        [InlineKeyboardButton(text="❌ Закрыть сделку", callback_data="admin_close_deal")],
        [InlineKeyboardButton(text="💬 Чат сделки", callback_data="admin_watch_chat")],
        [InlineKeyboardButton(text="📤 Заявки на вывод", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def deal_buttons(deal_id: str, status: str, buyer_id: int, user_id: int) -> Optional[InlineKeyboardMarkup]:
    if status == "pending" and user_id == buyer_id:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💳 Оплатить", callback_data=f"pay_deal_{deal_id}")],
            [InlineKeyboardButton(text="💬 Чат", callback_data=f"chat_{deal_id}")]
        ])
    elif status in ["funded", "completed"]:
        buttons = [[InlineKeyboardButton(text="💬 Чат", callback_data=f"chat_{deal_id}")]]
        if status == "funded" and user_id == buyer_id:
            buttons.append([InlineKeyboardButton(text="✅ Подтвердить получение", callback_data=f"confirm_deal_{deal_id}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)
    return None

# ========== ОБРАБОТЧИКИ КОМАНД ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    
    cursor.execute("INSERT OR IGNORE INTO users (user_id, username, registered_at, balance) VALUES (?, ?, ?, ?)",
                   (user_id, username, datetime.now(), 0))
    db.commit()
    
    await message.answer(
        "🤝 *Добро пожаловать в Гарант Бот!*\n\n"
        "Здесь вы можете безопасно проводить сделки с криптовалютой.\n"
        "Бот выступает гарантом: деньги блокируются до подтверждения покупателя.\n\n"
        "Используйте кнопки для навигации:",
        reply_markup=main_menu(user_id),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("🏠 *Главное меню:*", reply_markup=main_menu(callback.from_user.id), parse_mode="Markdown")

# ========== СОЗДАНИЕ СДЕЛКИ ==========
@dp.callback_query(F.data == "create_deal")
async def create_deal_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 Введите сумму сделки в рублях (мин. 100 RUB):")
    await state.set_state(CreateDeal.waiting_for_amount)
    await callback.answer()

@dp.message(CreateDeal.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < 100:
            raise ValueError
        await state.update_data(amount=amount)
        await message.answer("👤 Введите ID или @username продавца (кому переведут деньги):")
        await state.set_state(CreateDeal.waiting_for_partner_id)
    except:
        await message.answer("❌ Неверная сумма! Минимум 100 RUB. Попробуйте снова:")

@dp.message(CreateDeal.waiting_for_partner_id)
async def process_partner(message: Message, state: FSMContext):
    partner_input = message.text.strip()
    partner_id = None
    
    # Поиск партнера
    if partner_input.startswith("@"):
        username = partner_input[1:]
        cursor.execute("SELECT user_id FROM users WHERE username=?", (username,))
        result = cursor.fetchone()
        if result:
            partner_id = result[0]
    elif partner_input.isdigit():
        partner_id = int(partner_input)
    
    if not partner_id or partner_id == message.from_user.id:
        await message.answer("❌ Продавец не найден или это вы сами! Попробуйте снова:")
        return
    
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (partner_id,))
    if not cursor.fetchone():
        await message.answer("❌ Пользователь не зарегистрирован в боте!")
        return
    
    data = await state.get_data()
    amount = data['amount']
    commission = get_commission()
    deal_id = str(uuid.uuid4())[:8]
    tag = generate_deal_tag()
    chat_id = abs(hash(f"{deal_id}_{message.from_user.id}_{partner_id}")) % (10**9)
    
    cursor.execute("""
        INSERT INTO deals (deal_id, tag, seller_id, buyer_id, amount, commission, status, created_at, chat_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (deal_id, tag, partner_id, message.from_user.id, amount, commission, "pending", datetime.now(), chat_id))
    db.commit()
    
    await message.answer(
        f"✅ *Сделка создана!*\n\n"
        f"📌 Тег: `{tag}`\n"
        f"💰 Сумма: {format_balance(amount)}\n"
        f"👤 Продавец: {partner_id}\n"
        f"👤 Покупатель: {message.from_user.id}\n"
        f"💸 Комиссия: {commission}%\n\n"
        f"Покупатель должен пополнить баланс сделки через кнопку ниже.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💰 Пополнить баланс сделки", callback_data=f"pay_deal_{deal_id}")]
        ]),
        parse_mode="Markdown"
    )
    
    await state.clear()

# ========== ОПЛАТА СДЕЛКИ ==========
@dp.callback_query(F.data.startswith("pay_deal_"))
async def pay_deal(callback: CallbackQuery):
    deal_id = callback.data.split("_")[2]
    cursor.execute("SELECT * FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal or deal[7] != "pending" or callback.from_user.id != deal[4]:
        await callback.answer("❌ Сделка недоступна для оплаты", show_alert=True)
        return
    
    invoice_id, pay_url = await create_crypto_invoice(deal[5])
    if not invoice_id:
        await callback.answer("❌ Ошибка создания платежа", show_alert=True)
        return
    
    cursor.execute("UPDATE deals SET invoice_id=? WHERE deal_id=?", (invoice_id, deal_id))
    db.commit()
    
    await callback.message.answer(
        f"💳 *Оплата сделки #{deal[1]}*\n\n"
        f"Сумма: {format_balance(deal[5])}\n"
        f"Перейдите по ссылке для оплаты через CryptoBot:\n{pay_url}\n\n"
        f"⚠️ После оплаты нажмите *«Проверить оплату»*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment_{deal_id}_{invoice_id}")]
        ]),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery):
    _, deal_id, invoice_id = callback.data.split("_")
    import requests
    
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {"invoice_ids": invoice_id}
    
    response = requests.get(url, headers=headers, params=params)
    result = response.json()
    
    if result.get("ok") and result["result"]["items"]:
        invoice = result["result"]["items"][0]
        if invoice["status"] == "paid":
            cursor.execute("UPDATE deals SET status='funded', funded_at=? WHERE deal_id=?", (datetime.now(), deal_id))
            db.commit()
            await callback.message.answer("✅ *Оплата подтверждена! Деньги заморожены до подтверждения покупателя.*", parse_mode="Markdown")
            await callback.answer("Оплата подтверждена!")
        else:
            await callback.answer("❌ Платеж не найден или не оплачен", show_alert=True)

# ========== ПОДТВЕРЖДЕНИЕ ПОЛУЧЕНИЯ ==========
@dp.callback_query(F.data.startswith("confirm_deal_"))
async def confirm_deal(callback: CallbackQuery):
    deal_id = callback.data.split("_")[2]
    cursor.execute("SELECT * FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal or deal[7] != "funded" or callback.from_user.id != deal[4]:
        await callback.answer("❌ Невозможно подтвердить", show_alert=True)
        return
    
    # Начисляем деньги продавцу с учетом комиссии
    amount = deal[5]
    commission = deal[6]
    seller_payout = amount * (1 - commission / 100)
    
    cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (seller_payout, deal[3]))
    cursor.execute("UPDATE deals SET status='completed' WHERE deal_id=?", (deal_id,))
    db.commit()
    
    await callback.message.answer(
        f"✅ *Сделка завершена!*\n\n"
        f"Продавцу {deal[3]} начислено {format_balance(seller_payout)} (комиссия {commission}%)",
        parse_mode="Markdown"
    )

# ========== МОИ СДЕЛКИ ==========
@dp.callback_query(F.data == "my_deals")
async def my_deals(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("""
        SELECT deal_id, tag, amount, status, seller_id, buyer_id 
        FROM deals WHERE seller_id=? OR buyer_id=?
    """, (user_id, user_id))
    deals = cursor.fetchall()
    
    if not deals:
        await callback.message.answer("📭 У вас пока нет сделок")
        return
    
    text = "📋 *Ваши сделки:*\n\n"
    for deal in deals:
        role = "Продавец" if deal[4] == user_id else "Покупатель"
        text += f"`{deal[1]}` | {role} | {format_balance(deal[2])} | {deal[3]}\n"
    
    await callback.message.answer(text, parse_mode="Markdown")

# ========== ЧАТ МЕЖДУ УЧАСТНИКАМИ ==========
@dp.callback_query(F.data.startswith("chat_"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    deal_id = callback.data.split("_")[1]
    cursor.execute("SELECT chat_id, seller_id, buyer_id FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal or callback.from_user.id not in [deal[1], deal[2]]:
        await callback.answer("❌ Нет доступа к чату", show_alert=True)
        return
    
    await state.update_data(current_deal=deal_id)
    await callback.message.answer(
        "💬 *Чат сделки*\nОтправляйте сообщения, они будут видны только участникам сделки.\nДля выхода нажмите /exit_chat",
        parse_mode="Markdown"
    )
    await state.set_state(AdminState.watching_chat)

@dp.message(AdminState.watching_chat)
async def handle_chat_message(message: Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('current_deal')
    if not deal_id:
        return
    
    cursor.execute("SELECT seller_id, buyer_id, chat_id FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal:
        return
    
    # Сохраняем сообщение
    cursor.execute("""
        INSERT INTO messages (deal_id, from_id, message_text, timestamp)
        VALUES (?, ?, ?, ?)
    """, (deal_id, message.from_user.id, message.text, datetime.now()))
    db.commit()
    
    # Пересылаем собеседнику
    partner_id = deal[1] if message.from_user.id == deal[0] else deal[0]
    try:
        await bot.send_message(
            partner_id,
            f"💬 *Сообщение от {'Продавца' if message.from_user.id == deal[0] else 'Покупателя'}*:\n\n{message.text}",
            parse_mode="Markdown"
        )
    except:
        pass

@dp.message(Command("exit_chat"))
async def exit_chat(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🚪 Вы вышли из чата", reply_markup=main_menu(message.from_user.id))

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_cmd(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("Нет доступа")
        return
    await callback.message.edit_text("⚙️ *Админ-панель:*", reply_markup=admin_panel(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_commission")
async def set_commission(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 Введите новую комиссию (0-50):")
    await state.set_state(AdminState.waiting_commission)

@dp.message(AdminState.waiting_commission)
async def process_commission(message: Message, state: FSMContext):
    try:
        commission = float(message.text)
        if 0 <= commission <= 50:
            cursor.execute("UPDATE admin_settings SET value=? WHERE key='commission'", (str(commission),))
            db.commit()
            await message.answer(f"✅ Комиссия установлена: {commission}%")
            await state.clear()
        else:
            raise ValueError
    except:
        await message.answer("❌ Неверное значение! Введите число от 0 до 50")

@dp.callback_query(F.data == "admin_deals")
async def admin_deals(callback: CallbackQuery):
    cursor.execute("SELECT deal_id, tag, amount, status FROM deals ORDER BY created_at DESC LIMIT 20")
    deals = cursor.fetchall()
    text = "📋 *Последние сделки:*\n\n" + "\n".join([f"`{d[1]}` | {format_balance(d[2])} | {d[3]}" for d in deals])
    await callback.message.answer(text, parse_mode="Markdown")

@dp.callback_query(F.data == "admin_withdraws")
async def admin_withdraws(callback: CallbackQuery):
    cursor.execute("SELECT withdraw_id, user_id, amount, status FROM withdraws WHERE status='pending'")
    withdraws = cursor.fetchall()
    if not withdraws:
        await callback.message.answer("📭 Нет заявок на вывод")
        return
    
    for w in withdraws:
        await callback.message.answer(
            f"📤 *Заявка {w[0]}*\nПользователь: {w[1]}\nСумма: {format_balance(w[2])}\nСтатус: {w[3]}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"approve_withdraw_{w[0]}"),
                 InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_withdraw_{w[0]}")]
            ]),
            parse_mode="Markdown"
        )

# ========== ВЫВОД СРЕДСТВ ==========
@dp.callback_query(F.data == "withdraw")
async def withdraw_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("💰 Введите сумму вывода (мин. 100 RUB):")
    await state.set_state(WithdrawState.waiting_for_amount)

@dp.message(WithdrawState.waiting_for_amount)
async def withdraw_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
        balance = cursor.fetchone()[0]
        if amount < 100 or amount > balance:
            raise ValueError
        await state.update_data(amount=amount)
        await message.answer("💳 Введите адрес кошелька USDT (TRC20):")
        await state.set_state(WithdrawState.waiting_for_wallet)
    except:
        await message.answer("❌ Неверная сумма или недостаточно средств!")

@dp.message(WithdrawState.waiting_for_wallet)
async def withdraw_wallet(message: Message, state: FSMContext):
    data = await state.get_data()
    withdraw_id = str(uuid.uuid4())[:8]
    cursor.execute("""
        INSERT INTO withdraws (withdraw_id, user_id, amount, wallet_address, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (withdraw_id, message.from_user.id, data['amount'], message.text, "pending", datetime.now()))
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (data['amount'], message.from_user.id))
    db.commit()
    
    await message.answer(f"✅ Заявка на вывод #{withdraw_id} создана! Ожидайте обработки администратором.")
    for admin_id in ADMIN_IDS:
        await bot.send_message(admin_id, f"📤 Новая заявка на вывод #{withdraw_id} от {message.from_user.id} на сумму {format_balance(data['amount'])}")
    await state.clear()

# ========== ЗАПУСК БОТА ==========
async def main():
    print("🤖 Бот-гарант запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
