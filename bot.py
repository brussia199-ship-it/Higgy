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
BOT_TOKEN = "8830098882:AAEQVdiWSpcNhV4vZk5dxtIZ7Hj4lnCU3Qw"
CRYPTOBOT_TOKEN = "583403:AAfrNWLb7jwLrPAIQavMgItheP4X3X5GthY"  # Получите у @CryptoBot
ADMIN_ID = 7673683792

# Настройки
MIN_DEAL_AMOUNT = 0.5  # Минимальная сумма сделки в USDT
CURRENCY = "USDT"  # Валюта

# ========== БАЗА ДАННЫХ ==========
db = sqlite3.connect("guarantee_bot.db", check_same_thread=False)
cursor = db.cursor()

# Создание таблиц
cursor.executescript("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    balance REAL DEFAULT 0,
    total_spent REAL DEFAULT 0,
    total_earned REAL DEFAULT 0,
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
    completed_at TIMESTAMP,
    chat_id INTEGER UNIQUE,
    invoice_id TEXT,
    payment_url TEXT
);

CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deal_id TEXT,
    from_id INTEGER,
    message_text TEXT,
    timestamp TIMESTAMP
);

CREATE TABLE IF NOT EXISTS withdraws (
    withdraw_id TEXT PRIMARY KEY,
    user_id INTEGER,
    amount REAL,
    wallet_address TEXT,
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP,
    processed_at TIMESTAMP
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

def format_amount(amount: float) -> str:
    """Форматирование суммы с 2 знаками после запятой"""
    return f"{amount:.2f} {CURRENCY}"

def get_deal_status_text(status: str) -> str:
    statuses = {
        "pending": "⏳ Ожидает оплаты",
        "funded": "💎 Средства заморожены",
        "completed": "✅ Завершена",
        "disputed": "⚠️ Спор",
        "closed": "❌ Закрыта"
    }
    return statuses.get(status, status)

async def create_crypto_invoice(amount_usdt: float) -> Tuple[Optional[str], Optional[str]]:
    """Создание инвойса через CryptoBot API в USDT"""
    if not CRYPTOBOT_TOKEN or CRYPTOBOT_TOKEN == "ВАШ_CRYPTOBOT_TOKEN":
        print("CryptoBot token not configured")
        return None, None
    
    url = "https://pay.crypt.bot/api/createInvoice"
    headers = {
        "Crypto-Pay-API-Token": CRYPTOBOT_TOKEN,
        "Content-Type": "application/json"
    }
    data = {
        "asset": "USDT",
        "amount": str(amount_usdt),
        "paid_btn_name": "callback",
        "paid_btn_url": f"https://t.me/{BOT_TOKEN.split(':')[0]}",
        "description": f"Оплата сделки-гаранта UralGarant"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        result = response.json()
        print(f"CryptoBot response: {result}")
        if result.get("ok"):
            return result["result"]["invoice_id"], result["result"]["pay_url"]
        return None, None
    except Exception as e:
        print(f"CryptoBot error: {e}")
        return None, None

async def check_invoice_status(invoice_id: str) -> str:
    """Проверка статуса инвойса"""
    url = "https://pay.crypt.bot/api/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_TOKEN}
    params = {"invoice_ids": invoice_id}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        result = response.json()
        if result.get("ok") and result["result"]["items"]:
            return result["result"]["items"][0]["status"]
        return "invalid"
    except Exception as e:
        print(f"Check invoice error: {e}")
        return "error"

# ========== КЛАВИАТУРЫ ==========
def main_menu(user_id: int) -> InlineKeyboardMarkup:
    # Получаем баланс пользователя
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (user_id,))
    balance = cursor.fetchone()
    balance_text = format_amount(balance[0]) if balance else f"0.00 {CURRENCY}"
    
    buttons = [
        [InlineKeyboardButton(text="➕ Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")],
        [InlineKeyboardButton(text="💬 Чат поддержки", callback_data="support_chat")],
        [InlineKeyboardButton(text=f"💰 Баланс: {balance_text}", callback_data="show_balance")],
        [InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw")],
    ]
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Установить комиссию", callback_data="admin_commission")],
        [InlineKeyboardButton(text="📋 Все сделки", callback_data="admin_deals")],
        [InlineKeyboardButton(text="🔄 Сбросить статус сделки", callback_data="admin_reset_deal")],
        [InlineKeyboardButton(text="💬 Просмотр чатов", callback_data="admin_watch_chat")],
        [InlineKeyboardButton(text="📤 Заявки на вывод", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="➕ Ручное начисление", callback_data="admin_manual_balance")],
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
    waiting_broadcast_text = State()
    watching_chat = State()
    waiting_deal_id = State()
    waiting_reset_deal = State()
    waiting_support_reply = State()
    waiting_manual_user = State()
    waiting_manual_amount = State()

class SupportState(StatesGroup):
    waiting_message = State()

# ========== ОБРАБОТЧИКИ ==========
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
        f"🤝 *Добро пожаловать в UralGarant!*\n\n"
        f"🔐 *Сервис гарант-сделок в {CURRENCY}*\n\n"
        f"💰 Минимальная сделка: {format_amount(MIN_DEAL_AMOUNT)}\n\n"
        f"Я помогаю безопасно проводить сделки между продавцом и покупателем.\n\n"
        f"📌 *Как это работает:*\n"
        f"1️⃣ Покупатель создает сделку\n"
        f"2️⃣ Оплачивает через CryptoBot (USDT)\n"
        f"3️⃣ Продавец выполняет обязательства\n"
        f"4️⃣ Покупатель подтверждает получение\n"
        f"5️⃣ Продавец получает {CURRENCY} на баланс\n\n"
        f"Используйте кнопки для навигации:",
        reply_markup=main_menu(user_id),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu(callback: CallbackQuery):
    await callback.message.delete()
    await cmd_start(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "show_balance")
async def show_balance(callback: CallbackQuery):
    cursor.execute("SELECT balance, total_spent, total_earned FROM users WHERE user_id=?", (callback.from_user.id,))
    balance, spent, earned = cursor.fetchone()
    await callback.answer(
        f"💰 *Ваш баланс:*\n\n"
        f"Доступно: {format_amount(balance)}\n"
        f"Всего потрачено: {format_amount(spent or 0)}\n"
        f"Всего заработано: {format_amount(earned or 0)}",
        show_alert=True,
        parse_mode="Markdown"
    )

# ========== СОЗДАНИЕ СДЕЛКИ ==========
@dp.callback_query(F.data == "create_deal")
async def create_deal_start(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(f"💰 Введите сумму сделки в {CURRENCY} (мин. {format_amount(MIN_DEAL_AMOUNT)}):")
    await state.set_state(CreateDeal.waiting_for_amount)
    await callback.answer()

@dp.message(CreateDeal.waiting_for_amount)
async def process_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount < MIN_DEAL_AMOUNT:
            await message.answer(f"❌ Минимальная сумма сделки: {format_amount(MIN_DEAL_AMOUNT)}")
            return
        await state.update_data(amount=amount)
        await message.answer("👤 Введите ID продавца (кому переведут деньги):\n\nПример: `7804485863`", parse_mode="Markdown")
        await state.set_state(CreateDeal.waiting_for_partner_id)
    except ValueError:
        await message.answer(f"❌ Введите корректную сумму в {CURRENCY} (например: 100.50)")

@dp.message(CreateDeal.waiting_for_partner_id)
async def process_partner(message: Message, state: FSMContext):
    partner_input = message.text.strip()
    partner_id = None
    
    if partner_input.isdigit():
        partner_id = int(partner_input)
    
    if not partner_id or partner_id == message.from_user.id:
        await message.answer("❌ Продавец не найден или это вы сами! Попробуйте снова:")
        return
    
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (partner_id,))
    if not cursor.fetchone():
        await message.answer("❌ Пользователь не зарегистрирован! Ему нужно запустить бота командой /start")
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
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Оплатить сделку", callback_data=f"pay_deal_{deal_id}")],
        [InlineKeyboardButton(text="💬 Чат с продавцом", callback_data=f"chat_{deal_id}")]
    ])
    
    await message.answer(
        f"✅ *Сделка создана!*\n\n"
        f"📌 Тег: `{tag}`\n"
        f"💰 Сумма: {format_amount(amount)}\n"
        f"👤 Продавец: `{partner_id}`\n"
        f"👤 Покупатель: `{message.from_user.id}`\n"
        f"💸 Комиссия: {commission}%\n\n"
        f"📊 Статус: {get_deal_status_text('pending')}\n\n"
        f"*Покупатель, нажмите кнопку для оплаты:*",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    
    # Уведомляем продавца
    try:
        await bot.send_message(
            partner_id,
            f"🆕 *Новая сделка!*\n\n"
            f"📌 Тег: `{tag}`\n"
            f"💰 Сумма: {format_amount(amount)}\n"
            f"👤 Покупатель: `{message.from_user.id}`\n\n"
            f"Ожидайте оплаты от покупателя.\n"
            f"После оплаты вы получите уведомление.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Чат с покупателем", callback_data=f"chat_{deal_id}")]
            ]),
            parse_mode="Markdown"
        )
    except Exception as e:
        print(f"Failed to notify seller: {e}")
    
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
    
    (deal_id_db, tag, seller_id, buyer_id, amount, commission, 
     status, created_at, funded_at, completed_at, chat_id, invoice_id, payment_url) = deal
    
    if status == "completed":
        await callback.answer("❌ Сделка уже завершена", show_alert=True)
        return
    
    if status == "funded":
        await callback.answer("❌ Сделка уже оплачена! Средства заморожены.", show_alert=True)
        return
    
    if callback.from_user.id != buyer_id:
        await callback.answer("❌ Только покупатель может оплатить сделку", show_alert=True)
        return
    
    # Проверяем существующий инвойс
    if invoice_id:
        inv_status = await check_invoice_status(invoice_id)
        if inv_status == "paid":
            cursor.execute("UPDATE deals SET status='funded', funded_at=? WHERE deal_id=?", (datetime.now(), deal_id))
            db.commit()
            await callback.message.answer("✅ *Оплата подтверждена!*", parse_mode="Markdown")
            await callback.answer("Оплата подтверждена!")
            return
    
    # Создаем новый инвойс
    await callback.message.answer("🔄 Создаю платеж в USDT...")
    
    invoice_id_new, pay_url_new = await create_crypto_invoice(amount)
    
    if not invoice_id_new:
        await callback.message.answer(
            "❌ *Ошибка создания платежа*\n\n"
            "Пожалуйста, сообщите администратору о проблеме.\n"
            "Возможные причины:\n"
            "- Не настроен CryptoBot токен\n"
            "- Проблемы с соединением",
            parse_mode="Markdown"
        )
        await callback.answer()
        return
    
    cursor.execute("UPDATE deals SET invoice_id=?, payment_url=? WHERE deal_id=?", (invoice_id_new, pay_url_new, deal_id))
    db.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Перейти к оплате USDT", url=pay_url_new)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_payment_{deal_id}_{invoice_id_new}")],
        [InlineKeyboardButton(text="💬 Чат с продавцом", callback_data=f"chat_{deal_id}")]
    ])
    
    await callback.message.answer(
        f"💳 *Оплата сделки {tag}*\n\n"
        f"💰 Сумма: {format_amount(amount)}\n"
        f"📌 Комиссия: {commission}%\n\n"
        f"*Инструкция:*\n"
        f"1️⃣ Нажмите «Перейти к оплате USDT»\n"
        f"2️⃣ Оплатите через CryptoBot (USDT)\n"
        f"3️⃣ После оплаты нажмите «Проверить оплату»\n\n"
        f"⚠️ Деньги будут заморожены до вашего подтверждения.",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: CallbackQuery):
    parts = callback.data.split("_")
    deal_id = parts[2]
    invoice_id = parts[3]
    
    await callback.message.answer("🔄 Проверяю статус платежа...")
    
    inv_status = await check_invoice_status(invoice_id)
    
    if inv_status == "paid":
        cursor.execute("UPDATE deals SET status='funded', funded_at=? WHERE deal_id=?", (datetime.now(), deal_id))
        
        # Обновляем статистику покупателя
        cursor.execute("SELECT amount FROM deals WHERE deal_id=?", (deal_id,))
        amount = cursor.fetchone()[0]
        cursor.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id=?", (amount, callback.from_user.id))
        
        db.commit()
        
        cursor.execute("SELECT tag, seller_id, buyer_id, amount FROM deals WHERE deal_id=?", (deal_id,))
        deal = cursor.fetchone()
        
        # Уведомляем продавца
        try:
            await bot.send_message(
                deal[1],
                f"✅ *Сделка {deal[0]} оплачена!*\n\n"
                f"💰 Сумма: {format_amount(deal[3])}\n"
                f"Деньги заморожены до подтверждения покупателя.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить получение", callback_data=f"confirm_deal_{deal_id}")],
            [InlineKeyboardButton(text="💬 Чат с продавцом", callback_data=f"chat_{deal_id}")]
        ])
        
        await callback.message.answer(
            "✅ *Оплата подтверждена!*\n\n"
            f"💰 Сумма {format_amount(deal[3])} заморожена на счете гаранта.\n"
            "После получения товара/услуги нажмите «Подтвердить получение».",
            reply_markup=kb,
            parse_mode="Markdown"
        )
        
    elif inv_status == "active":
        await callback.message.answer("⏳ *Платеж еще не оплачен*\n\nОплатите счет и нажмите проверку снова.", parse_mode="Markdown")
    else:
        await callback.message.answer("❌ *Не удалось проверить платеж*\n\nПопробуйте позже или обратитесь к администратору.", parse_mode="Markdown")
    
    await callback.answer()

# ========== ПОДТВЕРЖДЕНИЕ ПОЛУЧЕНИЯ ==========
@dp.callback_query(F.data.startswith("confirm_deal_"))
async def confirm_deal(callback: CallbackQuery):
    deal_id = callback.data.split("_")[2]
    cursor.execute("SELECT * FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal:
        await callback.answer("❌ Сделка не найдена", show_alert=True)
        return
    
    (deal_id_db, tag, seller_id, buyer_id, amount, commission, 
     status, created_at, funded_at, completed_at, chat_id, invoice_id, payment_url) = deal
    
    if status != "funded":
        await callback.answer(f"❌ Невозможно подтвердить. Статус: {status}", show_alert=True)
        return
    
    if callback.from_user.id != buyer_id:
        await callback.answer("❌ Только покупатель может подтвердить получение", show_alert=True)
        return
    
    seller_payout = amount * (1 - commission / 100)
    
    cursor.execute("UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id=?", 
                   (seller_payout, seller_payout, seller_id))
    cursor.execute("UPDATE deals SET status='completed', completed_at=? WHERE deal_id=?", (datetime.now(), deal_id))
    db.commit()
    
    await callback.message.answer(
        f"✅ *Сделка успешно завершена!*\n\n"
        f"📌 Тег: {tag}\n"
        f"💰 Продавцу начислено: {format_amount(seller_payout)}\n"
        f"💸 Комиссия сервиса: {format_amount(amount * commission / 100)}\n\n"
        f"Спасибо за использование сервиса!",
        parse_mode="Markdown"
    )
    
    try:
        await bot.send_message(
            seller_id,
            f"✅ *Сделка {tag} завершена!*\n\n"
            f"💰 Вам начислено: {format_amount(seller_payout)}\n"
            f"💸 Комиссия: {commission}%",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await callback.answer()

# ========== ЧАТ МЕЖДУ УЧАСТНИКАМИ ==========
@dp.callback_query(F.data.startswith("chat_"))
async def open_chat(callback: CallbackQuery, state: FSMContext):
    deal_id = callback.data.split("_")[1]
    cursor.execute("SELECT seller_id, buyer_id, tag FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    if not deal or callback.from_user.id not in [deal[0], deal[1]]:
        await callback.answer("❌ Нет доступа к чату", show_alert=True)
        return
    
    await state.update_data(current_chat_deal=deal_id, current_chat_tag=deal[2])
    
    # Показываем последние сообщения
    cursor.execute("SELECT from_id, message_text, timestamp FROM messages WHERE deal_id=? ORDER BY timestamp DESC LIMIT 10", (deal_id,))
    messages = cursor.fetchall()
    
    if messages:
        history = "📜 *Последние сообщения:*\n\n"
        for msg in reversed(messages):
            sender = "Вы" if msg[0] == callback.from_user.id else ("Продавец" if msg[0] == deal[0] else "Покупатель")
            history += f"`[{msg[2].strftime('%H:%M')}]` {sender}: {msg[1][:50]}\n"
        await callback.message.answer(history[:4000], parse_mode="Markdown")
    
    await callback.message.answer(
        f"💬 *Чат сделки {deal[2]}*\n\n"
        f"Отправляйте сообщения, они будут видны только участникам сделки.\n"
        f"Для выхода нажмите /exit_chat",
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
    await callback.message.answer("🚪 Вы вышли из чата", reply_markup=main_menu(callback.from_user.id))
    await callback.answer()

@dp.message(AdminState.watching_chat)
async def handle_chat_message(message: Message, state: FSMContext):
    data = await state.get_data()
    deal_id = data.get('current_chat_deal')
    if not deal_id:
        return
    
    cursor.execute("SELECT seller_id, buyer_id, tag FROM deals WHERE deal_id=?", (deal_id,))
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
            f"💬 *Новое сообщение в сделке {deal[2]}*\n"
            f"От: {'Продавец' if message.from_user.id == deal[0] else 'Покупатель'}\n\n"
            f"{message.text}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="💬 Ответить", callback_data=f"chat_{deal_id}")]
            ])
        )
    except Exception as e:
        print(f"Failed to send: {e}")

# ========== ЧАТ ПОДДЕРЖКИ ==========
@dp.callback_query(F.data == "support_chat")
async def support_chat(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "💬 *Чат поддержки*\n\n"
        "Напишите ваше сообщение администратору.\n"
        "Мы ответим вам в ближайшее время.\n\n"
        "Для отмены нажмите /cancel",
        parse_mode="Markdown"
    )
    await state.set_state(SupportState.waiting_message)
    await callback.answer()

@dp.message(SupportState.waiting_message)
async def process_support_message(message: Message, state: FSMContext):
    cursor.execute("""
        INSERT INTO messages (deal_id, from_id, message_text, timestamp)
        VALUES (?, ?, ?, ?)
    """, ("support", message.from_user.id, f"[ПОДДЕРЖКА] {message.text}", datetime.now()))
    db.commit()
    
    await bot.send_message(
        ADMIN_ID,
        f"📩 *Новое сообщение в поддержку*\n\n"
        f"От: {message.from_user.id}\n"
        f"Username: @{message.from_user.username or 'None'}\n\n"
        f"Сообщение:\n{message.text}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить", callback_data=f"reply_support_{message.from_user.id}")]
        ])
    )
    
    await message.answer("✅ Ваше сообщение отправлено администратору. Ответ придет в этот чат.")
    await state.clear()

@dp.callback_query(F.data.startswith("reply_support_"))
async def reply_support(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    user_id = int(callback.data.split("_")[2])
    await state.update_data(reply_user_id=user_id)
    await callback.message.answer("✏️ Введите ответ пользователю:")
    await state.set_state(AdminState.waiting_support_reply)
    await callback.answer()

@dp.message(AdminState.waiting_support_reply)
async def process_support_reply(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('reply_user_id')
    
    if not user_id:
        await message.answer("❌ Ошибка")
        await state.clear()
        return
    
    try:
        await bot.send_message(
            user_id,
            f"📩 *Ответ от поддержки:*\n\n{message.text}\n\n"
            f"Для нового вопроса напишите /start и нажмите «Чат поддержки»",
            parse_mode="Markdown"
        )
        await message.answer("✅ Ответ отправлен пользователю")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")
    
    await state.clear()

# ========== ВЫВОД СРЕДСТВ ==========
@dp.callback_query(F.data == "withdraw")
async def withdraw_start(callback: CallbackQuery, state: FSMContext):
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (callback.from_user.id,))
    balance = cursor.fetchone()[0]
    
    if balance < MIN_DEAL_AMOUNT:
        await callback.answer(f"❌ Минимальная сумма вывода {format_amount(MIN_DEAL_AMOUNT)}. Ваш баланс: {format_amount(balance)}", show_alert=True)
        return
    
    await callback.message.answer(
        f"💰 *Вывод средств ({CURRENCY})*\n\n"
        f"Ваш баланс: {format_amount(balance)}\n"
        f"Мин. сумма: {format_amount(MIN_DEAL_AMOUNT)}\n"
        f"Комиссия за вывод: 0%\n\n"
        f"Введите сумму вывода в {CURRENCY}:",
        parse_mode="Markdown"
    )
    await state.set_state(WithdrawState.waiting_for_amount)
    await callback.answer()

@dp.message(WithdrawState.waiting_for_amount)
async def withdraw_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        cursor.execute("SELECT balance FROM users WHERE user_id=?", (message.from_user.id,))
        balance = cursor.fetchone()[0]
        
        if amount < MIN_DEAL_AMOUNT:
            await message.answer(f"❌ Минимальная сумма вывода {format_amount(MIN_DEAL_AMOUNT)}")
            return
        if amount > balance:
            await message.answer(f"❌ Недостаточно средств. Ваш баланс: {format_amount(balance)}")
            return
        
        await state.update_data(amount=amount)
        await message.answer("💳 Введите адрес кошелька USDT (TRC20):\n\nПример: `TX7cqUBeJovQRfZq5YHtT7jqHByL5ZpXtZ`", parse_mode="Markdown")
        await state.set_state(WithdrawState.waiting_for_wallet)
    except ValueError:
        await message.answer(f"❌ Введите корректную сумму в {CURRENCY} (например: 50.75)")

@dp.message(WithdrawState.waiting_for_wallet)
async def withdraw_wallet(message: Message, state: FSMContext):
    data = await state.get_data()
    withdraw_id = str(uuid.uuid4())[:8]
    wallet = message.text.strip()
    
    # Простая проверка адреса TRC20
    if not wallet.startswith('T') or len(wallet) < 30 or len(wallet) > 42:
        await message.answer("❌ Неверный формат адреса TRC20. Адрес должен начинаться с 'T' и иметь длину 34-42 символа.\nПопробуйте снова:")
        return
    
    cursor.execute("""
        INSERT INTO withdraws (withdraw_id, user_id, amount, wallet_address, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (withdraw_id, message.from_user.id, data['amount'], wallet, "pending", datetime.now()))
    
    cursor.execute("UPDATE users SET balance = balance - ? WHERE user_id=?", (data['amount'], message.from_user.id))
    db.commit()
    
    await message.answer(
        f"✅ *Заявка на вывод создана!*\n\n"
        f"📤 ID: {withdraw_id}\n"
        f"💰 Сумма: {format_amount(data['amount'])}\n"
        f"💳 Кошелек: `{wallet}`\n\n"
        f"Статус: ⏳ Ожидает обработки\n\n"
        f"Администратор обработает заявку в ближайшее время.",
        parse_mode="Markdown"
    )
    
    await bot.send_message(
        ADMIN_ID,
        f"📤 *Новая заявка на вывод USDT*\n\n"
        f"🆔 ID: {withdraw_id}\n"
        f"👤 Пользователь: {message.from_user.id}\n"
        f"💰 Сумма: {format_amount(data['amount'])}\n"
        f"💳 Кошелек: `{wallet}`\n"
        f"📅 Создана: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Выполнено", callback_data=f"approve_withdraw_{withdraw_id}"),
             InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_withdraw_{withdraw_id}")]
        ])
    )
    
    await state.clear()

# ========== МОИ СДЕЛКИ ==========
@dp.callback_query(F.data == "my_deals")
async def my_deals(callback: CallbackQuery):
    user_id = callback.from_user.id
    cursor.execute("""
        SELECT deal_id, tag, amount, status, seller_id, buyer_id, created_at 
        FROM deals WHERE seller_id=? OR buyer_id=?
        ORDER BY created_at DESC
    """, (user_id, user_id))
    deals = cursor.fetchall()
    
    if not deals:
        await callback.message.answer("📭 *У вас пока нет сделок*\n\nСоздайте новую сделку через главное меню.", parse_mode="Markdown")
        await callback.answer()
        return
    
    for deal in deals:
        (deal_id, tag, amount, status, seller_id, buyer_id, created_at) = deal
        role = "📤 Продавец" if seller_id == user_id else "📥 Покупатель"
        
        text = (
            f"┌ *Сделка*\n"
            f"├ 📌 Тег: `{tag}`\n"
            f"├ 💰 Сумма: {format_amount(amount)}\n"
            f"├ 👤 {role}\n"
            f"├ 📅 Создана: {created_at.strftime('%d.%m.%Y %H:%M')}\n"
            f"└ 📊 Статус: {get_deal_status_text(status)}\n"
        )
        
        buttons = []
        
        if status == "pending" and role == "📥 Покупатель":
            buttons.append([InlineKeyboardButton(text="💰 Оплатить", callback_data=f"pay_deal_{deal_id}")])
        
        if status == "funded" and role == "📥 Покупатель":
            buttons.append([InlineKeyboardButton(text="✅ Подтвердить получение", callback_data=f"confirm_deal_{deal_id}")])
        
        if status in ["pending", "funded"]:
            buttons.append([InlineKeyboardButton(text="💬 Чат", callback_data=f"chat_{deal_id}")])
        
        if buttons:
            await callback.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons), parse_mode="Markdown")
        else:
            await callback.message.answer(text, parse_mode="Markdown")
    
    await callback.answer()

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
    
    current = get_commission()
    await callback.message.answer(f"💰 Текущая комиссия: {current}%\n\nВведите новую комиссию (0-50):")
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
    
    cursor.execute("SELECT tag, amount, status, seller_id, buyer_id, created_at FROM deals ORDER BY created_at DESC LIMIT 20")
    deals = cursor.fetchall()
    
    if not deals:
        await callback.message.answer("📭 Нет сделок")
        await callback.answer()
        return
    
    text = "📋 *Последние 20 сделок:*\n\n"
    for deal in deals:
        text += f"`{deal[0]}` | {format_amount(deal[1])} | {deal[2]}\n"
        text += f"└ Продавец: {deal[3]} | Покупатель: {deal[4]}\n"
        text += f"└ Создана: {deal[5].strftime('%d.%m.%Y %H:%M')}\n\n"
    
    if len(text) > 4000:
        text = text[:4000]
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("SELECT COUNT(*) FROM users")
    users_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM deals")
    total_deals = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM deals WHERE status='completed'")
    completed_deals = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM deals WHERE status='completed'")
    total_volume = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT COUNT(*) FROM withdraws WHERE status='pending'")
    pending_withdraws = cursor.fetchone()[0]
    
    cursor.execute("SELECT SUM(amount) FROM withdraws WHERE status='pending'")
    pending_amount = cursor.fetchone()[0] or 0
    
    text = (
        f"📊 *Статистика бота*\n\n"
        f"👥 Пользователей: {users_count}\n"
        f"📋 Всего сделок: {total_deals}\n"
        f"✅ Завершенных: {completed_deals}\n"
        f"💰 Общий объем: {format_amount(total_volume)}\n"
        f"💸 Заявок на вывод: {pending_withdraws} ({format_amount(pending_amount)})\n"
        f"💸 Комиссия: {get_commission()}%\n"
        f"💱 Валюта: {CURRENCY}"
    )
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_manual_balance")
async def manual_balance_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    await callback.message.answer("➕ *Ручное начисление/списание*\n\nВведите ID пользователя:")
    await state.set_state(AdminState.waiting_manual_user)
    await callback.answer()

@dp.message(AdminState.waiting_manual_user)
async def manual_balance_user(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
        if not cursor.fetchone():
            await message.answer("❌ Пользователь не найден")
            return
        await state.update_data(manual_user_id=user_id)
        await message.answer(f"💰 Введите сумму для начисления (положительное число) или списания (отрицательное):\n\nПример: `+50` или `-20`")
        await state.set_state(AdminState.waiting_manual_amount)
    except ValueError:
        await message.answer("❌ Введите корректный ID пользователя")

@dp.message(AdminState.waiting_manual_amount)
async def manual_balance_amount(message: Message, state: FSMContext):
    data = await state.get_data()
    user_id = data.get('manual_user_id')
    
    try:
        amount = float(message.text.replace(',', '.'))
        cursor.execute("UPDATE users SET balance = balance + ? WHERE user_id=?", (amount, user_id))
        db.commit()
        
        action = "начислено" if amount > 0 else "списано"
        await message.answer(f"✅ Пользователю {user_id} {action} {format_amount(abs(amount))}")
        
        try:
            await bot.send_message(
                user_id,
                f"{'➕' if amount > 0 else '➖'} *Изменение баланса*\n\n"
                f"Вам {action}: {format_amount(abs(amount))}\n"
                f"Текущий баланс можно проверить в главном меню.",
                parse_mode="Markdown"
            )
        except:
            pass
        
        await state.clear()
    except ValueError:
        await message.answer("❌ Введите корректную сумму")

@dp.callback_query(F.data == "admin_reset_deal")
async def admin_reset_deal(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("SELECT deal_id, tag, status FROM deals WHERE status != 'completed'")
    deals = cursor.fetchall()
    
    if not deals:
        await callback.message.answer("📭 Нет активных сделок")
        await callback.answer()
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{deal[1]} [{get_deal_status_text(deal[2])}]", callback_data=f"reset_deal_{deal[0]}")] 
        for deal in deals[:10]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    
    await callback.message.answer("🔧 *Выберите сделку для сброса статуса:*\n\nПосле сброса статус станет 'pending'", 
                                  reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("reset_deal_"))
async def reset_deal_status(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    deal_id = callback.data.split("_")[2]
    
    cursor.execute("UPDATE deals SET status='pending', funded_at=NULL, completed_at=NULL WHERE deal_id=?", (deal_id,))
    db.commit()
    
    cursor.execute("SELECT tag, buyer_id FROM deals WHERE deal_id=?", (deal_id,))
    deal = cursor.fetchone()
    
    await callback.message.answer(f"✅ Статус сделки {deal[0]} сброшен на 'pending'")
    
    try:
        await bot.send_message(
            deal[1],
            f"🔄 *Статус сделки {deal[0]} сброшен администратором*\n\n"
            f"Вы можете снова оплатить сделку через «Мои сделки»",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await callback.answer()

@dp.callback_query(F.data == "admin_withdraws")
async def admin_withdraws(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("SELECT withdraw_id, user_id, amount, wallet_address, created_at FROM withdraws WHERE status='pending' ORDER BY created_at ASC")
    withdraws = cursor.fetchall()
    
    if not withdraws:
        await callback.message.answer("📭 Нет заявок на вывод")
        await callback.answer()
        return
    
    for w in withdraws:
        await callback.message.answer(
            f"📤 *Заявка на вывод USDT*\n\n"
            f"🆔 ID: `{w[0]}`\n"
            f"👤 Пользователь: {w[1]}\n"
            f"💰 Сумма: {format_amount(w[2])}\n"
            f"💳 Кошелек: `{w[3]}`\n"
            f"📅 Создана: {w[4].strftime('%d.%m.%Y %H:%M')}",
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
    cursor.execute("UPDATE withdraws SET status='completed', processed_at=? WHERE withdraw_id=?", (datetime.now(), withdraw_id))
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
        cursor.execute("UPDATE withdraws SET status='rejected', processed_at=? WHERE withdraw_id=?", (datetime.now(), withdraw_id))
        db.commit()
        
        try:
            await bot.send_message(w[0], f"❌ Ваша заявка на вывод {format_amount(w[1])} отклонена. Средства возвращены на баланс.")
        except:
            pass
    
    await callback.message.edit_text(f"❌ Вывод {withdraw_id} отклонен!")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def broadcast_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    await callback.message.answer("📢 Введите текст для рассылки (поддерживается Markdown):")
    await state.set_state(AdminState.waiting_broadcast_text)
    await callback.answer()

@dp.message(AdminState.waiting_broadcast_text)
async def process_broadcast(message: Message, state: FSMContext):
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    
    success = 0
    fail = 0
    
    status_msg = await message.answer(f"🚀 Начинаю рассылку {len(users)} пользователям...")
    
    for user in users:
        try:
            await bot.send_message(
                user[0], 
                f"📢 *Рассылка от администратора:*\n\n{message.text}", 
                parse_mode="Markdown"
            )
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    
    await status_msg.edit_text(f"✅ Рассылка завершена!\n\n📨 Доставлено: {success}\n❌ Ошибок: {fail}")
    await state.clear()

@dp.callback_query(F.data == "admin_watch_chat")
async def admin_watch_chat(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("SELECT deal_id, tag, status FROM deals WHERE status != 'completed' ORDER BY created_at DESC LIMIT 20")
    deals = cursor.fetchall()
    
    if not deals:
        await callback.message.answer("📭 Нет активных сделок")
        await callback.answer()
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{deal[1]} [{get_deal_status_text(deal[2])}]", callback_data=f"admin_chat_{deal[0]}")] 
        for deal in deals[:15]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    
    await callback.message.answer("👁 *Выберите сделку для просмотра чата:*", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_chat_"))
async def admin_enter_chat(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    deal_id = callback.data.split("_")[2]
    await state.update_data(current_chat_deal=deal_id)
    
    cursor.execute("SELECT from_id, message_text, timestamp FROM messages WHERE deal_id=? ORDER BY timestamp DESC LIMIT 30", (deal_id,))
    messages = cursor.fetchall()
    
    if messages:
        text = "📜 *История чата:*\n\n"
        for msg in reversed(messages):
            text += f"`[{msg[2].strftime('%H:%M:%S')}]` Пользователь {msg[0]}: {msg[1][:60]}\n"
        await callback.message.answer(text[:4000], parse_mode="Markdown")
    
    await callback.message.answer(
        "👁️ *Вы наблюдаете за чатом*\n\n"
        "Администратор видит все сообщения, но может только читать.\n"
        "Для выхода нажмите /exit_chat",
        parse_mode="Markdown"
    )
    await state.set_state(AdminState.watching_chat)
    await callback.answer()

@dp.message(Command("cancel"))
async def cancel_cmd(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Действие отменено", reply_markup=main_menu(message.from_user.id))

# ========== ЗАПУСК ==========
async def main():
    print("🤖 UralGarant бот запущен!")
    print(f"👑 Администратор: {ADMIN_ID}")
    print(f"💱 Валюта: {CURRENCY}")
    print(f"💰 Минимальная сделка: {MIN_DEAL_AMOUNT} {CURRENCY}")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
