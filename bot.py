import asyncio
import json
import sqlite3
import uuid
import random
from datetime import datetime
from typing import Optional, Tuple

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import requests

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8830098882:AAEQVdiWSpcNhV4vZk5dxtIZ7Hj4lnCU3Qw"  # Ваш токен
CRYPTOBOT_TOKEN = "583403:AAfrNWLb7jwLrPAIQavMgItheP4X3X5GthY"  # Токен от @CryptoBot
ADMIN_ID = 7673683792  # Ваш Telegram ID (один администратор)

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
    status TEXT DEFAULT 'pending',
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
    status TEXT DEFAULT 'pending',
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

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def generate_deal_tag() -> str:
    """Генерация уникального тега для сделки #00:AABBCC"""
    hex_part = ''.join(random.choices('0123456789ABCDEF', k=6))
    return f"#{random.randint(10,99)}:{hex_part}"

def get_commission() -> float:
    cursor.execute("SELECT value FROM admin_settings WHERE key='commission'")
    return float(cursor.fetchone()[0])

def format_balance(amount: float) -> str:
    return f"{amount:.2f} RUB"

async def create_crypto_invoice(amount_rub: float) -> Tuple[Optional[str], Optional[str]]:
    """Создание инвойса через CryptoBot API"""
    if not CRYPTOBOT_TOKEN or CRYPTOBOT_TOKEN == "ВАШ_CRYPTOBOT_TOKEN":
        return None, None
    
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "asset": "RUB",
        "amount": str(amount_rub),
        "paid_btn_name": "callback",
        "paid_btn_url": f"https://t.me/{BOT_TOKEN.split(':')[0]}"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=10)
        result = response.json()
        if result.get("ok"):
            return result["result"]["invoice_id"], result["result"]["pay_url"]
        return None, None
    except Exception as e:
        print(f"CryptoBot error: {e}")
        return None, None

# ========== КЛАВИАТУРЫ ==========
def main_menu(user_id: int) -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text="➕ Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")],
        [InlineKeyboardButton(text="💰 Пополнить баланс", callback_data="deposit")],
        [InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw")],
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Установить комиссию", callback_data="admin_commission")],
        [InlineKeyboardButton(text="📋 Все сделки", callback_data="admin_deals")],
        [InlineKeyboardButton(text="💬 Чат сделки", callback_data="admin_watch_chat")],
        [InlineKeyboardButton(text="📤 Заявки на вывод", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

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
    waiting_broadcast_text = State()
    watching_chat = State()
    waiting_deal_id = State()

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
        "Здесь вы можете безопасно проводить сделки.\n"
        "Бот выступает гарантом: деньги блокируются до подтверждения покупателя.\n\n"
        "Используйте кнопки для навигации:",
        reply_markup=main_menu(user_id),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.edit_text("🏠 *Главное меню:*", reply_markup=main_menu(callback.from_user.id), parse_mode="Markdown")
    await callback.answer()

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
        await message.answer("👤 Введите ID продавца (кому переведут деньги):")
        await state.set_state(CreateDeal.waiting_for_partner_id)
    except:
        await message.answer("❌ Неверная сумма! Минимум 100 RUB. Попробуйте снова:")

@dp.message(CreateDeal.waiting_for_partner_id)
async def process_partner(message: Message, state: FSMContext):
    partner_input = message.text.strip()
    partner_id = None
    
    # Поиск партнера
    if partner_input.isdigit():
        partner_id = int(partner_input)
    
    if not partner_id or partner_id == message.from_user.id:
        await message.answer("❌ Продавец не найден или это вы сами! Попробуйте снова:")
        return
    
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (partner_id,))
    if not cursor.fetchone():
        await message.answer("❌ Пользователь не зарегистрирован в боте! Ему нужно запустить бота командой /start")
        return
    
    data = await state.get_data()
    amount = data['amount']
    commission = get_commission()
    deal_id = str(uuid.uuid4())[:8]
    tag = generate_deal_tag()
    chat_id = random.randint(100000, 999999999)
    
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
    
    # Уведомляем продавца
    try:
        await bot.send_message(
            partner_id,
            f"🆕 *Новая сделка!*\n\n"
            f"📌 Тег: `{tag}`\n"
            f"💰 Сумма: {format_balance(amount)}\n"
            f"👤 Покупатель: {message.from_user.id}\n\n"
            f"Ожидайте оплаты от покупателя.",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await state.clear()

# ========== ОПЛАТА СДЕЛКИ ==========
@dp.callback_query(F.data.startswith("pay_deal_"))
async def pay_deal(callback: CallbackQuery):
    deal_id = callback.data.split("_")[2]
    cursor.execute("SELECT * FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal:
        await callback.answer("❌ Сделка не найдена", show_alert=True)
        return
    
    if deal[7] != "pending":
        await callback.answer("❌ Сделка уже оплачена или завершена", show_alert=True)
        return
    
    if callback.from_user.id != deal[4]:
        await callback.answer("❌ Только покупатель может оплатить сделку", show_alert=True)
        return
    
    invoice_id, pay_url = await create_crypto_invoice(deal[5])
    if not invoice_id:
        await callback.answer("❌ Ошибка создания платежа. Проверьте настройки CryptoBot", show_alert=True)
        return
    
    cursor.execute("UPDATE deals SET invoice_id=? WHERE deal_id=?", (invoice_id, deal_id))
    db.commit()
    
    await callback.message.answer(
        f"💳 *Оплата сделки {deal[1]}*\n\n"
        f"Сумма: {format_balance(deal[5])}\n"
        f"Перейдите по ссылке для оплаты через CryptoBot:\n{pay_url}\n\n"
        f"⚠️ После оплаты нажмите *«Проверить оплату»*",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment_{deal_id}_{invoice_id}")]
        ]),
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery):
    parts = callback.data.split("_")
    deal_id = parts[2]
    invoice_id = parts[3]
    
    if not CRYPTOBOT_TOKEN or CRYPTOBOT_TOKEN == "ВАШ_CRYPTOBOT_TOKEN":
        await callback.answer("❌ CryptoBot не настроен", show_alert=True)
        return
    
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {"invoice_ids": invoice_id}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        result = response.json()
        
        if result.get("ok") and result["result"]["items"]:
            invoice = result["result"]["items"][0]
            if invoice["status"] == "paid":
                cursor.execute("UPDATE deals SET status='funded', funded_at=? WHERE deal_id=?", (datetime.now(), deal_id))
                db.commit()
                await callback.message.answer("✅ *Оплата подтверждена! Деньги заморожены до подтверждения покупателя.*", parse_mode="Markdown")
                await callback.answer("Оплата подтверждена!")
            else:
                await callback.answer("❌ Платеж еще не оплачен", show_alert=True)
        else:
            await callback.answer("❌ Не удалось проверить платеж", show_alert=True)
    except Exception as e:
        await callback.answer(f"❌ Ошибка: {str(e)[:50]}", show_alert=True)

# ========== ПОДТВЕРЖДЕНИЕ ПОЛУЧЕНИЯ ==========
@dp.callback_query(F.data.startswith("confirm_deal_"))
async def confirm_deal(callback: CallbackQuery):
    deal_id = callback.data.split("_")[2]
    cursor.execute("SELECT * FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal or deal[7] != "funded":
        await callback.answer("❌ Невозможно подтвердить", show_alert=True)
        return
    
    if callback.from_user.id != deal[4]:
        await callback.answer("❌ Только покупатель может подтвердить", show_alert=True)
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
    
    # Уведомляем продавца
    try:
        await bot.send_message(
            deal[3],
            f"✅ *Сделка {deal[1]} завершена!*\n\n"
            f"Вам начислено {format_balance(seller_payout)}",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await callback.answer()

# ========== МОИ СДЕЛКИ ==========
@dp.callback_query(F.data == "my_deals")
async def my_deals(callback: CallbackQuery):
    user_id = cursor.execute("""
        SELECT deal_id, tag, amount, status, seller_id, buyer_id 
        FROM deals WHERE seller_id=? OR buyer_id=?
    """, (callback.from_user.id, callback.from_user.id))
    deals = cursor.fetchall()
    
    if not deals:
        await callback.message.answer("📭 У вас пока нет сделок")
        await callback.answer()
        return
    
    text = "📋 *Ваши сделки:*\n\n"
    for deal in deals:
        role = "📤 Продавец" if deal[4] == callback.from_user.id else "📥 Покупатель"
        status_emoji = {
            "pending": "⏳ Ожидает оплаты",
            "funded": "💎 Средства заморожены",
            "completed": "✅ Завершена"
        }.get(deal[3], deal[3])
        
        text += f"`{deal[1]}`\n{role} | {format_balance(deal[2])} | {status_emoji}\n"
        
        # Добавляем кнопку чата если сделка активна
        if deal[3] in ["pending", "funded"]:
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Чат сделки", callback_data=f"chat_{deal[0]}")]
            ])
            await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
            text = ""
    
    if text:
        await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ========== ЧАТ ==========
@dp.callback_query(F.data.startswith("chat_"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    deal_id = callback.data.split("_")[1]
    cursor.execute("SELECT seller_id, buyer_id FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal or callback.from_user.id not in [deal[0], deal[1]]:
        await callback.answer("❌ Нет доступа к чату", show_alert=True)
        return
    
    await state.update_data(current_deal=deal_id, current_chat_deal=deal_id)
    await callback.message.answer(
        "💬 *Чат сделки*\n"
        "Отправляйте сообщения, они будут видны только участникам сделки.\n"
        "Для выхода нажмите /exit_chat",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🚪 Выйти из чата", callback_data="exit_chat")]
        ]),
        parse_mode="Markdown"
    )
    await state.set_state(AdminState.watching_chat)
    await callback.answer()

@dp.callback_query(F.data == "exit_chat")
async def exit_chat_cmd(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("🚪 Вы вышли из чата", reply_markup=main_menu(callback.from_user.id))
    await callback.answer()

@dp.message(AdminState.watching_chat)
async def handle_chat_message(message: Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('current_chat_deal')
    if not deal_id:
        return
    
    cursor.execute("SELECT seller_id, buyer_id FROM deals WHERE deal_id=?", (deal_id,))
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
            f"💬 *Новое сообщение в сделке*\n"
            f"От: {'Продавец' if message.from_user.id == deal[0] else 'Покупатель'}\n\n"
            f"{message.text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Ответить", callback_data=f"chat_{deal_id}")]
            ])
        )
    except Exception as e:
        print(f"Failed to send message to {partner_id}: {e}")

# ========== ПОПОЛНЕНИЕ БАЛАНСА ==========
@dp.callback_query(F.data == "deposit")
async def deposit(callback: CallbackQuery):
    await callback.message.answer("💰 Пополнение баланса через CryptoBot временно недоступно.\nИспользуйте создание сделки для оплаты.")
    await callback.answer()

# ========== ВЫВОД СРЕДСТВ ==========
@dp.callback_query(F.data == "withdraw")
async def withdraw_start(callback: CallbackQuery, state: FSMContext):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (callback.from_user.id,))
    balance = cursor.fetchone()[0]
    await callback.message.answer(f"💰 Ваш баланс: {format_balance(balance)}\n\nВведите сумму вывода (мин. 100 RUB):")
    await state.set_state(WithdrawState.waiting_for_amount)
    await callback.answer()

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
        await message.answer("❌ Неверная сумма или недостаточно средств! Минимум 100 RUB.")

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
    
    # Уведомляем администратора
    await bot.send_message(
        ADMIN_ID,
        f"📤 *Новая заявка на вывод*\n\n"
        f"ID: {withdraw_id}\n"
        f"Пользователь: {message.from_user.id}\n"
        f"Сумма: {format_balance(data['amount'])}\n"
        f"Кошелек: {message.text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"approve_withdraw_{withdraw_id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_withdraw_{withdraw_id}")]
        ])
    )
    await state.clear()

# ========== АДМИН-ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_panel")
async def admin_panel_cmd(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа", show_alert=True)
        return
    await callback.message.edit_text("⚙️ *Админ-панель:*", reply_markup=admin_panel(), parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_commission")
async def set_commission(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("💰 Введите новую комиссию (0-50):")
    await state.set_state(AdminState.waiting_commission)
    await callback.answer()

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
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("SELECT deal_id, tag, amount, status, seller_id, buyer_id FROM deals ORDER BY created_at DESC LIMIT 20")
    deals = cursor.fetchall()
    
    if not deals:
        await callback.message.answer("📭 Нет сделок")
        await callback.answer()
        return
    
    text = "📋 *Последние сделки:*\n\n"
    for deal in deals:
        text += f"`{deal[1]}` | {format_balance(deal[2])} | {deal[3]}\nПродавец: {deal[4]} | Покупатель: {deal[5]}\n\n"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_withdraws")
async def admin_withdraws(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("SELECT withdraw_id, user_id, amount, wallet_address, status FROM withdraws WHERE status='pending'")
    withdraws = cursor.fetchall()
    
    if not withdraws:
        await callback.message.answer("📭 Нет заявок на вывод")
        await callback.answer()
        return
    
    for w in withdraws:
        await callback.message.answer(
            f"📤 *Заявка {w[0]}*\n"
            f"Пользователь: {w[1]}\n"
            f"Сумма: {format_balance(w[2])}\n"
            f"Кошелек: `{w[3]}`",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"approve_withdraw_{w[0]}"),
                 InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_withdraw_{w[0]}")]
            ]),
            parse_mode="Markdown"
        )
    await callback.answer()

@dp.callback_query(F.data.startswith("approve_withdraw_"))
async def approve_withdraw(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    withdraw_id = callback.data.split("_")[2]
    cursor.execute("UPDATE withdraws SET status='completed' WHERE withdraw_id=?", (withdraw_id,))
    db.commit()
    await callback.message.edit_text(f"✅ Вывод {withdraw_id} подтвержден!")
    await callback.answer()

@dp.callback_query(F.data.startswith("reject_withdraw_"))
async def reject_withdraw(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    withdraw_id = callback.data.split("_")[2]
    cursor.execute("SELECT user_id, amount FROM withdraws WHERE withdraw_id=?", (withdraw_id,))
    w = cursor.fetchone()
    if w:
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (w[1], w[0]))
        cursor.execute("UPDATE withdraws SET status='rejected' WHERE withdraw_id=?", (withdraw_id,))
        db.commit()
        await bot.send_message(w[0], f"❌ Ваша заявка на вывод {format_balance(w[1])} отклонена. Средства возвращены на баланс.")
    
    await callback.message.edit_text(f"❌ Вывод {withdraw_id} отклонен!")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("📢 Введите текст для рассылки:")
    await state.set_state(AdminState.waiting_broadcast_text)
    await callback.answer()

@dp.message(AdminState.waiting_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    
    success = 0
    fail = 0
    
    await message.answer(f"🚀 Начинаю рассылку {len(users)} пользователям...")
    
    for user in users:
        try:
            await bot.send_message(user[0], f"📢 *Рассылка от администратора:*\n\n{message.text}", parse_mode="Markdown")
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)  # Защита от блокировки
    
    await message.answer(f"✅ Рассылка завершена!\nДоставлено: {success}\nОшибок: {fail}")
    await state.clear()

@dp.callback_query(F.data == "admin_watch_chat")
async def admin_watch_chat(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("SELECT deal_id, tag FROM deals WHERE status != 'completed'")
    deals = cursor.fetchall()
    
    if not deals:
        await callback.message.answer("📭 Нет активных сделок")
        await callback.answer()
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{deal[1]}", callback_data=f"admin_chat_{deal[0]}")] for deal in deals[:10]
    ])
    
    await callback.message.answer("Выберите сделку для просмотра чата:", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_chat_"))
async def admin_enter_chat(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    deal_id = callback.data.split("_")[2]
    await state.update_data(current_chat_deal=deal_id)
    
    # Показываем последние 20 сообщений
    cursor.execute("SELECT from_id, message_text, timestamp FROM messages WHERE deal_id=? ORDER BY timestamp DESC LIMIT 20", (deal_id,))
    messages = cursor.fetchall()
    
    if messages:
        text = "📜 *История чата:*\n\n"
        for msg in reversed(messages):
            text += f"[{msg[2].strftime('%H:%M')}] Пользователь {msg[0]}: {msg[1][:50]}\n"
        await callback.message.answer(text[:4000], parse_mode="Markdown")
    
    await callback.message.answer(
        "👁️ *Вы наблюдаете за чатом*\n"
        "Администратор видит все сообщения, но может только читать.\n"
        "Для выхода нажмите /exit_chat",
        parse_mode="Markdown"
    )
    await state.set_state(AdminState.watching_chat)
    await callback.answer()

@dp.callback_query(F.data == "admin_close_deal")
async def admin_close_deal_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("Введите ID или тег сделки для принудительного закрытия:")
    await state.set_state(AdminState.waiting_deal_id)
    await callback.answer()

@dp.message(AdminState.waiting_deal_id)
async def admin_close_deal(message: Message, state: FSMContext):
    deal_input = message.text.strip()
    
    # Поиск сделки по тегу или ID
    cursor.execute("SELECT deal_id, seller_id, buyer_id, amount, commission, status FROM deals WHERE tag=? OR deal_id=?", (deal_input, deal_input))
    deal = cursor.fetchone()
    
    if not deal:
        await message.answer("❌ Сделка не найдена")
        return
    
    if deal[5] == "completed":
        await message.answer("❌ Сделка уже завершена")
        return
    
    # Принудительное закрытие
    if deal[5] == "funded":
        seller_payout = deal[3] * (1 - deal[4] / 100)
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (seller_payout, deal[1]))
        cursor.execute("UPDATE deals SET status='completed' WHERE deal_id=?", (deal[0],))
        db.commit()
        await message.answer(f"✅ Сделка принудительно закрыта. Продавцу начислено {format_balance(seller_payout)}")
    else:
        cursor.execute("UPDATE deals SET status='closed' WHERE deal_id=?", (deal[0],))
        db.commit()
        await message.answer(f"✅ Сделка отменена администратором")
    
    await state.clear()

# ========== ЗАПУСК БОТА ==========
async def main():
    print("🤖 Бот-гарант запущен!")
    print(f"Администратор: {ADMIN_ID}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
