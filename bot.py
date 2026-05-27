import asyncio
import json
import sqlite3
import uuid
import random
from datetime import datetime, timedelta
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
SUPPORT_BOT_LINK = "https://t.me/UralGarantSup_bot"  # Ссылка на бота поддержки

# Настройки
MIN_DEAL_AMOUNT = 0.5  # Минимальная сумма сделки в USDT
CURRENCY = "USDT"

# VIP статусы (при покупке комиссия отключается)
VIP_PLANS = {
    "7d": {"days": 7, "price": 3, "name": "VIP 7 дней", "commission": 0},
    "14d": {"days": 14, "price": 5, "name": "VIP 14 дней", "commission": 0},
    "30d": {"days": 30, "price": 10, "name": "VIP 30 дней", "commission": 0}
}

# Реферальные проценты для креаторов
CREATOR_BONUS_DEAL = 2  # 2% от сделок рефералов
CREATOR_BONUS_VIP = 25  # 25% от покупки VIP
CREATOR_BONUS_DEAL_AFTER_25 = 5  # 5% после 25 рефералов
CREATOR_BONUS_VIP_AFTER_25 = 50  # 50% после 25 рефералов

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
    registered_at TIMESTAMP,
    referrer_id INTEGER DEFAULT 0,
    vip_status TEXT DEFAULT 'none',
    vip_expires_at TIMESTAMP,
    vip_commission INTEGER DEFAULT 0,
    is_creator INTEGER DEFAULT 0,
    creator_approved_at TIMESTAMP,
    creator_social_links TEXT,
    total_referrals INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS deals (
    deal_id TEXT PRIMARY KEY,
    tag TEXT UNIQUE,
    seller_id INTEGER,
    buyer_id INTEGER,
    amount REAL,
    commission REAL DEFAULT 0,
    commission_percent REAL DEFAULT 0,
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

CREATE TABLE IF NOT EXISTS referrals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER,
    referred_id INTEGER,
    created_at TIMESTAMP,
    status TEXT DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS referral_earnings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    referrer_id INTEGER,
    amount REAL,
    source TEXT,
    source_id TEXT,
    created_at TIMESTAMP,
    commission_percent REAL
);

CREATE TABLE IF NOT EXISTS vip_purchases (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    plan TEXT,
    days INTEGER,
    price REAL,
    created_at TIMESTAMP,
    expires_at TIMESTAMP,
    invoice_id TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS creator_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    tiktok TEXT,
    telegram TEXT,
    instagram TEXT,
    youtube TEXT,
    created_at TIMESTAMP,
    status TEXT DEFAULT 'pending'
);
""")

# Установка комиссии по умолчанию
cursor.execute("INSERT OR IGNORE INTO admin_settings (key, value) VALUES ('commission', '5')")
db.commit()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
def generate_deal_tag() -> str:
    hex_part = ''.join(random.choices('0123456789ABCDEF', k=6))
    return f"#{random.randint(10,99)}:{hex_part}"

def get_commission() -> float:
    cursor.execute("SELECT value FROM admin_settings WHERE key='commission'")
    return float(cursor.fetchone()[0])

def format_amount(amount: float) -> str:
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

def get_user_commission(user_id: int, base_commission: float) -> float:
    """Возвращает комиссию для пользователя (0 если есть VIP)"""
    cursor.execute("SELECT vip_status, vip_expires_at FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    
    if result and result[0] != "none" and result[1]:
        expires_at = datetime.fromisoformat(result[1])
        if expires_at > datetime.now():
            return 0  # VIP - комиссия отключена
    return base_commission

def get_vip_status_text(user_id: int) -> str:
    cursor.execute("SELECT vip_status, vip_expires_at FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if not result or result[0] == "none":
        return "❌ Нет VIP статуса"
    
    if result[1]:
        expires_at = datetime.fromisoformat(result[1])
        if expires_at > datetime.now():
            days_left = (expires_at - datetime.now()).days
            return f"✅ VIP активен (комиссия 0%) до {expires_at.strftime('%d.%m.%Y')}"
        else:
            cursor.execute("UPDATE users SET vip_status='none', vip_expires_at=NULL WHERE user_id=?", (user_id,))
            db.commit()
    return "❌ VIP статус истек"

def check_vip_active(user_id: int) -> bool:
    cursor.execute("SELECT vip_status, vip_expires_at FROM users WHERE user_id=?", (user_id,))
    result = cursor.fetchone()
    if not result or result[0] == "none":
        return False
    if result[1]:
        expires_at = datetime.fromisoformat(result[1])
        if expires_at > datetime.now():
            return True
        else:
            cursor.execute("UPDATE users SET vip_status='none', vip_expires_at=NULL WHERE user_id=?", (user_id,))
            db.commit()
    return False

def get_referral_count(referrer_id: int) -> int:
    cursor.execute("SELECT COUNT(*) FROM referrals WHERE referrer_id=? AND status='active'", (referrer_id,))
    return cursor.fetchone()[0]

def get_creator_bonus_percent(referrer_id: int, bonus_type: str) -> float:
    """Возвращает процент бонуса для креатора в зависимости от количества рефералов"""
    referral_count = get_referral_count(referrer_id)
    
    if bonus_type == "deal":
        if referral_count >= 25:
            return CREATOR_BONUS_DEAL_AFTER_25
        return CREATOR_BONUS_DEAL
    else:  # vip
        if referral_count >= 25:
            return CREATOR_BONUS_VIP_AFTER_25
        return CREATOR_BONUS_VIP

def add_referral_earning(referrer_id: int, amount: float, source: str, source_id: str, percent: float):
    """Добавляет заработок рефереру"""
    cursor.execute("""
        INSERT INTO referral_earnings (referrer_id, amount, source, source_id, created_at, commission_percent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (referrer_id, amount, source, source_id, datetime.now(), percent))
    cursor.execute("UPDATE users SET balance = balance + ?, total_earned = total_earned + ? WHERE user_id=?", 
                   (amount, amount, referrer_id))
    db.commit()

async def create_crypto_invoice(amount_usdt: float, description: str = "") -> Tuple[Optional[str], Optional[str]]:
    """Создание инвойса через CryptoBot API в USDT"""
    if not CRYPTOBOT_TOKEN or CRYPTOBOT_TOKEN == "ВАШ_CRYPTOBOT_TOKEN":
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
        "description": description or f"Оплата в UralGarant"
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=15)
        result = response.json()
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

def generate_referral_link(user_id: int) -> str:
    """Генерация реферальной ссылки"""
    return f"https://t.me/{BOT_TOKEN.split(':')[0]}?start=ref_{user_id}"

# ========== КЛАВИАТУРЫ ==========
def main_menu(user_id: int) -> InlineKeyboardMarkup:
    cursor.execute("SELECT balance, vip_status FROM users WHERE user_id=?", (user_id,))
    balance, vip_status = cursor.fetchone()
    balance_text = format_amount(balance or 0)
    
    vip_text = "👑 VIP" if vip_status != "none" else "💎 Купить VIP"
    
    buttons = [
        [InlineKeyboardButton(text="➕ Создать сделку", callback_data="create_deal")],
        [InlineKeyboardButton(text="📋 Мои сделки", callback_data="my_deals")],
        [InlineKeyboardButton(text=vip_text, callback_data="buy_vip")],
        [InlineKeyboardButton(text="👥 Реферальная система", callback_data="referral_system")],
        [InlineKeyboardButton(text="💬 Поддержка", url=SUPPORT_BOT_LINK)],
        [InlineKeyboardButton(text=f"💰 Баланс: {balance_text}", callback_data="show_balance")],
        [InlineKeyboardButton(text="💸 Вывод средств", callback_data="withdraw")],
    ]
    
    # Проверяем, является ли пользователь креатором
    cursor.execute("SELECT is_creator FROM users WHERE user_id=?", (user_id,))
    is_creator = cursor.fetchone()[0]
    if is_creator:
        buttons.insert(3, [InlineKeyboardButton(text="🎨 Панель креатора", callback_data="creator_panel")])
    
    if user_id == ADMIN_ID:
        buttons.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_panel() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Установить комиссию", callback_data="admin_commission")],
        [InlineKeyboardButton(text="👑 Назначить креатора", callback_data="admin_add_creator")],
        [InlineKeyboardButton(text="📋 Все креаторы", callback_data="admin_creators")],
        [InlineKeyboardButton(text="👥 Рефералы креатора", callback_data="admin_creator_refs")],
        [InlineKeyboardButton(text="📋 Все сделки", callback_data="admin_deals")],
        [InlineKeyboardButton(text="🔄 Сбросить статус сделки", callback_data="admin_reset_deal")],
        [InlineKeyboardButton(text="💬 Просмотр чатов", callback_data="admin_watch_chat")],
        [InlineKeyboardButton(text="📤 Заявки на вывод", callback_data="admin_withdraws")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")],
        [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="➕ Ручное начисление", callback_data="admin_manual_balance")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

def creator_panel_markup(user_id: int) -> InlineKeyboardMarkup:
    referral_count = get_referral_count(user_id)
    link = generate_referral_link(user_id)
    
    # Получаем статистику заработка
    cursor.execute("SELECT SUM(amount) FROM referral_earnings WHERE referrer_id=?", (user_id,))
    total_earned = cursor.fetchone()[0] or 0
    
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💸 Вывод средств", callback_data="creator_withdraw")],
        [InlineKeyboardButton(text="👥 Мои рефералы", callback_data="creator_referrals")],
        [InlineKeyboardButton(text="📊 Статистика заработка", callback_data="creator_stats")],
        [InlineKeyboardButton(text="🔗 Моя реферальная ссылка", callback_data="creator_link")],
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
    waiting_creator_id = State()
    waiting_creator_tiktok = State()
    waiting_creator_telegram = State()
    waiting_creator_instagram = State()
    waiting_creator_youtube = State()

class SupportState(StatesGroup):
    waiting_message = State()

class BuyVIPState(StatesGroup):
    waiting_plan = State()

class CreatorWithdrawState(StatesGroup):
    waiting_amount = State()
    waiting_wallet = State()

# ========== ОБРАБОТЧИКИ ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def cmd_start(message: Message):
    user_id = message.from_user.id
    username = message.from_user.username or "NoUsername"
    
    # Обработка реферальной ссылки
    referrer_id = None
    if message.text and "ref_" in message.text:
        try:
            referrer_id = int(message.text.split("ref_")[1])
            if referrer_id == user_id:
                referrer_id = None
        except:
            pass
    
    # Регистрация пользователя
    cursor.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (user_id, username, registered_at, referrer_id)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, datetime.now(), referrer_id))
        
        # Добавляем реферала если есть
        if referrer_id:
            cursor.execute("""
                INSERT INTO referrals (referrer_id, referred_id, created_at)
                VALUES (?, ?, ?)
            """, (referrer_id, user_id, datetime.now()))
            cursor.execute("UPDATE users SET total_referrals = total_referrals + 1 WHERE user_id=?", (referrer_id,))
            db.commit()
            
            # Уведомляем креатора о новом реферале
            try:
                await bot.send_message(
                    referrer_id,
                    f"🎉 *Новый реферал!*\n\n"
                    f"Пользователь @{username} зарегистрировался по вашей ссылке.\n"
                    f"Всего рефералов: {get_referral_count(referrer_id)}",
                    parse_mode="Markdown"
                )
            except:
                pass
    
    db.commit()
    
    # Получаем баланс и VIP статус
    cursor.execute("SELECT balance, vip_status FROM users WHERE user_id=?", (user_id,))
    balance, vip_status = cursor.fetchone()
    
    vip_text = f"\n👑 VIP статус: {get_vip_status_text(user_id)}" if vip_status != "none" else ""
    
    await message.answer(
        f"🤝 *Добро пожаловать в UralGarant!*\n\n"
        f"🔐 *Сервис гарант-сделок в {CURRENCY}*\n\n"
        f"💰 Ваш баланс: {format_amount(balance or 0)}{vip_text}\n"
        f"💰 Минимальная сделка: {format_amount(MIN_DEAL_AMOUNT)}\n\n"
        f"📌 *Как это работает:*\n"
        f"1️⃣ Покупатель создает сделку\n"
        f"2️⃣ Оплачивает через CryptoBot (USDT)\n"
        f"3️⃣ Продавец выполняет обязательства\n"
        f"4️⃣ Покупатель подтверждает получение\n"
        f"5️⃣ Продавец получает {CURRENCY} на баланс\n\n"
        f"👑 VIP статус отключает комиссию при сделках!\n\n"
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
        f"Доступно: {format_amount(balance or 0)}\n"
        f"Всего потрачено: {format_amount(spent or 0)}\n"
        f"Всего заработано: {format_amount(earned or 0)}",
        show_alert=True,
        parse_mode="Markdown"
    )

# ========== VIP СТАТУСЫ ==========
@dp.callback_query(F.data == "buy_vip")
async def buy_vip(callback: CallbackQuery, state: FSMContext):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👑 7 дней — 3 USDT", callback_data="vip_7d")],
        [InlineKeyboardButton(text="👑 14 дней — 5 USDT", callback_data="vip_14d")],
        [InlineKeyboardButton(text="👑 30 дней — 10 USDT", callback_data="vip_30d")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])
    
    await callback.message.answer(
        "💎 *Купить VIP статус*\n\n"
        "VIP статус дает:\n"
        "✅ Комиссия 0% при сделках\n"
        "✅ Приоритетная поддержка\n"
        "✅ Повышенный лимит вывода\n\n"
        "*Выберите период:*",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("vip_"))
async def process_vip_purchase(callback: CallbackQuery, state: FSMContext):
    plan_key = callback.data.split("_")[1]
    plan = VIP_PLANS[f"{plan_key}d"]
    
    invoice_id, pay_url = await create_crypto_invoice(plan["price"], f"Покупка VIP статуса на {plan['days']} дней")
    
    if not invoice_id:
        await callback.message.answer("❌ Ошибка создания платежа. Попробуйте позже.")
        await callback.answer()
        return
    
    # Сохраняем информацию о покупке
    cursor.execute("""
        INSERT INTO vip_purchases (user_id, plan, days, price, created_at, expires_at, invoice_id, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (callback.from_user.id, plan_key, plan['days'], plan['price'], datetime.now(), 
          datetime.now() + timedelta(days=plan['days']), invoice_id, "pending"))
    db.commit()
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Оплатить", url=pay_url)],
        [InlineKeyboardButton(text="✅ Проверить оплату", callback_data=f"check_vip_{invoice_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="buy_vip")]
    ])
    
    await callback.message.answer(
        f"💎 *Покупка VIP статуса*\n\n"
        f"📅 Период: {plan['days']} дней\n"
        f"💰 Сумма: {format_amount(plan['price'])}\n\n"
        f"После оплаты нажмите «Проверить оплату»",
        reply_markup=kb,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("check_vip_"))
async def check_vip_payment(callback: CallbackQuery):
    invoice_id = callback.data.split("_")[2]
    
    cursor.execute("SELECT user_id, plan, days, price FROM vip_purchases WHERE invoice_id=? AND status='pending'", (invoice_id,))
    purchase = cursor.fetchone()
    
    if not purchase:
        await callback.answer("Платеж не найден", show_alert=True)
        return
    
    inv_status = await check_invoice_status(invoice_id)
    
    if inv_status == "paid":
        user_id, plan_key, days, price = purchase
        
        # Активируем VIP статус
        expires_at = datetime.now() + timedelta(days=days)
        cursor.execute("""
            UPDATE users SET vip_status=?, vip_expires_at=?, vip_commission=0 WHERE user_id=?
        """, (plan_key, expires_at, user_id))
        cursor.execute("UPDATE users SET total_spent = total_spent + ? WHERE user_id=?", (price, user_id))
        cursor.execute("UPDATE vip_purchases SET status='completed' WHERE invoice_id=?", (invoice_id,))
        
        # Начисляем бонус креатору (25% или 50%)
        cursor.execute("SELECT referrer_id FROM users WHERE user_id=?", (user_id,))
        referrer = cursor.fetchone()
        
        if referrer and referrer[0]:
            creator_id = referrer[0]
            cursor.execute("SELECT is_creator FROM users WHERE user_id=?", (creator_id,))
            is_creator = cursor.fetchone()
            
            if is_creator and is_creator[0]:
                bonus_percent = get_creator_bonus_percent(creator_id, "vip")
                bonus_amount = price * bonus_percent / 100
                add_referral_earning(creator_id, bonus_amount, "vip_purchase", str(user_id), bonus_percent)
                
                try:
                    await bot.send_message(
                        creator_id,
                        f"🎉 *Вы получили бонус за VIP покупку реферала!*\n\n"
                        f"Пользователь: {user_id}\n"
                        f"Сумма покупки: {format_amount(price)}\n"
                        f"Ваш бонус ({bonus_percent}%): {format_amount(bonus_amount)}",
                        parse_mode="Markdown"
                    )
                except:
                    pass
        
        db.commit()
        
        await callback.message.answer(
            f"✅ *VIP статус активирован!*\n\n"
            f"📅 Действует до: {expires_at.strftime('%d.%m.%Y')}\n"
            f"💰 Комиссия при сделках: 0%\n\n"
            f"Спасибо за покупку!",
            parse_mode="Markdown"
        )
    elif inv_status == "active":
        await callback.answer("⏳ Платеж еще не оплачен", show_alert=True)
    else:
        await callback.answer("❌ Платеж не найден", show_alert=True)
    
    await callback.answer()

# ========== РЕФЕРАЛЬНАЯ СИСТЕМА ==========
@dp.callback_query(F.data == "referral_system")
async def referral_system(callback: CallbackQuery):
    user_id = callback.from_user.id
    referral_link = generate_referral_link(user_id)
    referral_count = get_referral_count(user_id)
    
    cursor.execute("SELECT SUM(amount) FROM referral_earnings WHERE referrer_id=?", (user_id,))
    total_earned = cursor.fetchone()[0] or 0
    
    # Проверяем, является ли пользователь креатором
    cursor.execute("SELECT is_creator FROM users WHERE user_id=?", (user_id,))
    is_creator = cursor.fetchone()[0]
    
    if is_creator:
        deal_percent = get_creator_bonus_percent(user_id, "deal")
        vip_percent = get_creator_bonus_percent(user_id, "vip")
        text = (
            f"👑 *Вы КРЕАТОР!*\n\n"
            f"📊 Ваши бонусы:\n"
            f"💰 {deal_percent}% от сделок рефералов\n"
            f"👑 {vip_percent}% от покупок VIP статусов\n\n"
            f"👥 Всего рефералов: {referral_count}\n"
            f"💸 Всего заработано: {format_amount(total_earned)}\n\n"
        )
        if referral_count >= 25:
            text += "✨ *Достигнут уровень 25+ рефералов!*\nБонусы повышены!\n\n"
        else:
            text += f"⚡ До повышения бонусов осталось: {25 - referral_count} рефералов\n\n"
    else:
        text = (
            f"👥 *Реферальная система*\n\n"
            f"💰 Приглашайте друзей и получайте бонусы!\n\n"
            f"📊 Ваши бонусы:\n"
            f"• 2% от сделок приглашенных\n"
            f"• 25% от покупки VIP статусов\n\n"
            f"🎯 После 25 рефералов:\n"
            f"• 5% от сделок\n"
            f"• 50% от покупки VIP\n\n"
            f"👥 Ваших рефералов: {referral_count}\n"
            f"💸 Заработано: {format_amount(total_earned)}\n\n"
        )
    
    text += f"🔗 *Ваша реферальная ссылка:*\n`{referral_link}`\n\n"
    text += f"Отправьте ссылку друзьям, они зарегистрируются и начнут пользоваться ботом!"
    
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📤 Поделиться ссылкой", url=f"https://t.me/share/url?url={referral_link}&text=Присоединяйся к UralGarant!")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ]))
    await callback.answer()

# ========== КРЕАТОР ПАНЕЛЬ ==========
@dp.callback_query(F.data == "creator_panel")
async def creator_panel(callback: CallbackQuery):
    cursor.execute("SELECT is_creator FROM users WHERE user_id=?", (callback.from_user.id,))
    is_creator = cursor.fetchone()[0]
    
    if not is_creator:
        await callback.answer("У вас нет доступа к панели креатора", show_alert=True)
        return
    
    referral_count = get_referral_count(callback.from_user.id)
    referral_link = generate_referral_link(callback.from_user.id)
    
    cursor.execute("SELECT SUM(amount) FROM referral_earnings WHERE referrer_id=?", (callback.from_user.id,))
    total_earned = cursor.fetchone()[0] or 0
    
    deal_percent = get_creator_bonus_percent(callback.from_user.id, "deal")
    vip_percent = get_creator_bonus_percent(callback.from_user.id, "vip")
    
    text = (
        f"🎨 *Панель креатора*\n\n"
        f"📊 *Ваши бонусы:*\n"
        f"💰 {deal_percent}% от сделок рефералов\n"
        f"👑 {vip_percent}% от покупок VIP\n\n"
        f"👥 *Рефералов:* {referral_count}\n"
        f"💸 *Заработано:* {format_amount(total_earned)}\n\n"
        f"🔗 *Ваша ссылка:*\n`{referral_link}`"
    )
    
    await callback.message.answer(text, parse_mode="Markdown", reply_markup=creator_panel_markup(callback.from_user.id))
    await callback.answer()

@dp.callback_query(F.data == "creator_referrals")
async def creator_referrals(callback: CallbackQuery):
    cursor.execute("""
        SELECT u.user_id, u.username, u.registered_at 
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ? AND r.status = 'active'
        ORDER BY r.created_at DESC
    """, (callback.from_user.id,))
    referrals = cursor.fetchall()
    
    if not referrals:
        await callback.message.answer("📭 У вас пока нет рефералов")
        await callback.answer()
        return
    
    text = "👥 *Ваши рефералы:*\n\n"
    for ref in referrals[:20]:
        text += f"• {ref[1] or ref[0]} | зарегистрирован: {ref[2].strftime('%d.%m.%Y')}\n"
    
    if len(referrals) > 20:
        text += f"\n... и еще {len(referrals) - 20} рефералов"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "creator_stats")
async def creator_stats(callback: CallbackQuery):
    cursor.execute("""
        SELECT source, SUM(amount), COUNT(*), commission_percent 
        FROM referral_earnings 
        WHERE referrer_id = ? 
        GROUP BY source
    """, (callback.from_user.id,))
    earnings = cursor.fetchall()
    
    if not earnings:
        await callback.message.answer("📊 У вас пока нет заработка")
        await callback.answer()
        return
    
    text = "📊 *Статистика заработка:*\n\n"
    total = 0
    for e in earnings:
        source_name = "от сделок" if e[0] == "deal" else "от VIP покупок"
        text += f"• {source_name}: {format_amount(e[1] or 0)} ({e[2]} операций, комиссия {e[3]}%)\n"
        total += e[1] or 0
    
    text += f"\n💰 *Всего заработано:* {format_amount(total)}"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "creator_link")
async def creator_link(callback: CallbackQuery):
    link = generate_referral_link(callback.from_user.id)
    await callback.message.answer(
        f"🔗 *Ваша реферальная ссылка:*\n\n`{link}`\n\n"
        f"Отправьте её друзьям, чтобы получать бонусы!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Поделиться", url=f"https://t.me/share/url?url={link}&text=Присоединяйся к UralGarant!")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="creator_panel")]
        ])
    )
    await callback.answer()

@dp.callback_query(F.data == "creator_withdraw")
async def creator_withdraw_start(callback: CallbackQuery, state: FSMContext):
    cursor.execute("SELECT SUM(amount) FROM referral_earnings WHERE referrer_id=?", (callback.from_user.id,))
    total_earned = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT balance FROM users WHERE user_id=?", (callback.from_user.id,))
    balance = cursor.fetchone()[0] or 0
    
    if balance < MIN_DEAL_AMOUNT:
        await callback.answer(f"❌ Минимальная сумма вывода {format_amount(MIN_DEAL_AMOUNT)}. Ваш баланс: {format_amount(balance)}", show_alert=True)
        return
    
    await callback.message.answer(
        f"💸 *Вывод средств для креатора*\n\n"
        f"💰 Ваш баланс: {format_amount(balance)}\n"
        f"📊 Заработано всего: {format_amount(total_earned)}\n\n"
        f"Введите сумму вывода в {CURRENCY}:",
        parse_mode="Markdown"
    )
    await state.set_state(CreatorWithdrawState.waiting_amount)
    await callback.answer()

# ========== АДМИН-ПАНЕЛЬ (КРЕАТОРЫ) ==========
@dp.callback_query(F.data == "admin_add_creator")
async def admin_add_creator(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    await callback.message.answer(
        "👑 *Назначение креатора*\n\n"
        "Введите ID пользователя, которого хотите сделать креатором:"
    )
    await state.set_state(AdminState.waiting_creator_id)
    await callback.answer()

@dp.message(AdminState.waiting_creator_id)
async def process_creator_id(message: Message, state: FSMContext):
    try:
        user_id = int(message.text.strip())
        cursor.execute("SELECT user_id, username FROM users WHERE user_id=?", (user_id,))
        user = cursor.fetchone()
        
        if not user:
            await message.answer("❌ Пользователь не найден")
            return
        
        await state.update_data(creator_user_id=user_id, creator_username=user[1])
        await message.answer(
            f"📱 Введите ссылку на TikTok пользователя:\n"
            f"(можно пропустить, отправив '-' )"
        )
        await state.set_state(AdminState.waiting_creator_tiktok)
    except ValueError:
        await message.answer("❌ Введите корректный ID")

@dp.message(AdminState.waiting_creator_tiktok)
async def process_creator_tiktok(message: Message, state: FSMContext):
    tiktok = message.text.strip() if message.text != "-" else ""
    await state.update_data(creator_tiktok=tiktok)
    await message.answer("📱 Введите ссылку на Telegram (можно пропустить):")
    await state.set_state(AdminState.waiting_creator_telegram)

@dp.message(AdminState.waiting_creator_telegram)
async def process_creator_telegram(message: Message, state: FSMContext):
    telegram = message.text.strip() if message.text != "-" else ""
    await state.update_data(creator_telegram=telegram)
    await message.answer("📱 Введите ссылку на Instagram (можно пропустить):")
    await state.set_state(AdminState.waiting_creator_instagram)

@dp.message(AdminState.waiting_creator_instagram)
async def process_creator_instagram(message: Message, state: FSMContext):
    instagram = message.text.strip() if message.text != "-" else ""
    await state.update_data(creator_instagram=instagram)
    await message.answer("📱 Введите ссылку на YouTube (можно пропустить):")
    await state.set_state(AdminState.waiting_creator_youtube)

@dp.message(AdminState.waiting_creator_youtube)
async def process_creator_youtube(message: Message, state: FSMContext):
    youtube = message.text.strip() if message.text != "-" else ""
    data = await state.get_data()
    
    # Сохраняем ссылки в JSON
    social_links = json.dumps({
        "tiktok": data.get('creator_tiktok', ''),
        "telegram": data.get('creator_telegram', ''),
        "instagram": data.get('creator_instagram', ''),
        "youtube": youtube
    })
    
    user_id = data.get('creator_user_id')
    
    cursor.execute("""
        UPDATE users SET is_creator=1, creator_approved_at=?, creator_social_links=?
        WHERE user_id=?
    """, (datetime.now(), social_links, user_id))
    db.commit()
    
    await message.answer(f"✅ Пользователь {data.get('creator_username')} назначен креатором!")
    
    try:
        await bot.send_message(
            user_id,
            f"🎉 *Поздравляем! Вы стали КРЕАТОРОМ UralGarant!*\n\n"
            f"Теперь вам доступны бонусы:\n"
            f"💰 {CREATOR_BONUS_DEAL}% от сделок рефералов\n"
            f"👑 {CREATOR_BONUS_VIP}% от покупки VIP\n\n"
            f"🎯 После 25 рефералов бонусы повышаются!\n\n"
            f"Используйте панель креатора в главном меню!",
            parse_mode="Markdown"
        )
    except:
        pass
    
    await state.clear()

@dp.callback_query(F.data == "admin_creators")
async def admin_creators(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("""
        SELECT user_id, username, creator_approved_at, total_referrals 
        FROM users WHERE is_creator=1 ORDER BY creator_approved_at DESC
    """)
    creators = cursor.fetchall()
    
    if not creators:
        await callback.message.answer("📭 Нет назначенных креаторов")
        await callback.answer()
        return
    
    text = "👑 *Список креаторов:*\n\n"
    for c in creators:
        text += f"• {c[1] or c[0]} | рефералов: {c[3] or 0} | статус: с {c[2].strftime('%d.%m.%Y')}\n"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_creator_refs")
async def admin_creator_refs(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    cursor.execute("SELECT user_id, username FROM users WHERE is_creator=1")
    creators = cursor.fetchall()
    
    if not creators:
        await callback.message.answer("📭 Нет креаторов")
        await callback.answer()
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{c[1] or c[0]}", callback_data=f"admin_view_refs_{c[0]}")] for c in creators[:10]
    ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Назад", callback_data="admin_panel")])
    
    await callback.message.answer("👥 *Выберите креатора для просмотра рефералов:*", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_view_refs_"))
async def admin_view_refs(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Нет доступа")
        return
    
    creator_id = int(callback.data.split("_")[3])
    
    cursor.execute("""
        SELECT u.user_id, u.username, u.registered_at, u.total_spent
        FROM referrals r
        JOIN users u ON r.referred_id = u.user_id
        WHERE r.referrer_id = ? AND r.status = 'active'
    """, (creator_id,))
    referrals = cursor.fetchall()
    
    if not referrals:
        await callback.message.answer("📭 У этого креатора нет рефералов")
        await callback.answer()
        return
    
    text = f"👥 *Рефералы креатора {creator_id}:*\n\n"
    for ref in referrals[:20]:
        text += f"• {ref[1] or ref[0]} | рег: {ref[2].strftime('%d.%m.%Y')} | потрачено: {format_amount(ref[3] or 0)}\n"
    
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# ========== ЗАПУСК (продолжение) ==========
# ... (остальные функции из предыдущей версии: создание сделки, оплата, чат, вывод и т.д.)
# Для экономии места, остальные функции остаются такими же как в предыдущей версии
# Полный код доступен по запросу

async def main():
    print("🤖 UralGarant бот запущен!")
    print(f"👑 Администратор: {ADMIN_ID}")
    print(f"💱 Валюта: {CURRENCY}")
    print(f"💰 Минимальная сделка: {MIN_DEAL_AMOUNT} {CURRENCY}")
    print(f"👑 VIP статусы: 7д = 3$, 14д = 5$, 30д = 10$")
    print(f"🎨 Креаторам: {CREATOR_BONUS_DEAL}% от сделок, {CREATOR_BONUS_VIP}% от VIP")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
