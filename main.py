import asyncio
import logging
import aiosqlite
import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.telegram import TelegramAPIServer
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, LabeledPrice, PreCheckoutQuery, 
    BotCommand, BusinessConnection
)
from aiogram.utils.keyboard import InlineKeyboardBuilder

# --- КОНФИГ ---
BOT_TOKEN = "1780243279:BhjQV2nQtCT0uOfz8nrGKUbdGcgJflg-HBy"  # <--- ОБЯЗАТЕЛЬНО ЗАМЕНИ
API_BASE = "https://api.xirogram.ru"
ADMIN_ID = 1780243202
BANK_USERNAME = "@mrktbank"
DB_PATH = "mrkt.db"
WITHDRAW_FEE = 30

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MRKT")
router = Router()

# --- БД ---
async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, username TEXT, stars_balance INTEGER DEFAULT 0)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS gifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT, owner_id INTEGER, gift_id TEXT UNIQUE,
            name TEXT, status TEXT DEFAULT 'inventory')""")
        await db.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT)""")
        await db.commit()

async def get_setting(key):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT value FROM settings WHERE key=?", (key,)) as cur:
            row = await cur.fetchone()
            return row[0] if row else None

async def set_setting(key, value):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT OR REPLACE INTO settings VALUES (?, ?)", (key, value))
        await db.commit()

# --- КЛАВИАТУРЫ ---
def main_kb():
    b = InlineKeyboardBuilder()
    b.button(text="📦 Мои подарки", callback_data="my_gifts")
    b.button(text="💸 Вывод (30⭐)", callback_data="withdraw")
    b.adjust(1)
    return b.as_markup()

# --- ФОНОВАЯ СИНХРОНИЗАЦИЯ ПОДАРКОВ ---
async def sync_bank_gifts():
    while True:
        try:
            conn_id = await get_setting("business_connection_id")
            if conn_id:
                url = f"{API_BASE}/bot{BOT_TOKEN}/getBusinessAccountGifts"
                async with aiohttp.ClientSession() as session:
                    async with session.post(url, json={"business_connection_id": conn_id}) as resp:
                        data = await resp.json()
                        if data.get("ok"):
                            gifts = data.get("result", {}).get("gifts", [])
                            async with aiosqlite.connect(DB_PATH) as db:
                                for g in gifts:
                                    gid = str(g["id"])
                                    async with db.execute("SELECT 1 FROM gifts WHERE gift_id=?", (gid,)) as cur:
                                        if await cur.fetchone():
                                            continue
                                    # Пытаемся взять ID отправителя, иначе кидаем админу
                                    sender = g.get("sender_id") or ADMIN_ID
                                    name = g.get("sticker", {}).get("emoji", "NFT Подарок")
                                    await db.execute(
                                        "INSERT OR IGNORE INTO gifts (owner_id, gift_id, name, status) VALUES (?, ?, ?, 'inventory')",
                                        (sender, gid, name)
                                    )
                                await db.commit()
                        else:
                            logger.error(f"API error: {data}")
        except Exception as e:
            logger.error(f"Sync error: {e}")
        await asyncio.sleep(15)

# --- ЛОВИМ BUSINESS CONNECTION ---
@router.business_connection()
async def on_business_connection(conn: BusinessConnection):
    logger.info(f"✅ Получен business_connection: {conn.id} от @{conn.user.username}")
    await set_setting("business_connection_id", conn.id)
    # Сразу запускаем синхронизацию
    asyncio.create_task(sync_bank_gifts())

# --- СТАРТ ---
@router.message(Command("start"))
async def start(m: Message):
    await m.answer(
        f"👋 <b>MRKT — маркетплейс NFT-подарков</b>\n\n"
        f"📤 Отправь любой подарок на <b>{BANK_USERNAME}</b> — он автоматически появится в твоём инвентаре.\n\n"
        f"💸 Вывод: 30 ⭐ (бот отправит подарок от себя).",
        reply_markup=main_kb()
    )

# --- ПРОСМОТР ПОДАРКОВ ---
@router.callback_query(F.data == "my_gifts")
async def my_gifts(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT name, gift_id FROM gifts WHERE owner_id=? AND status='inventory'", (c.from_user.id,)) as cur:
            rows = await cur.fetchall()
    if not rows:
        return await c.answer("У тебя нет подарков в инвентаре.", show_alert=True)
    text = "📦 <b>Твои подарки:</b>\n\n" + "\n".join([f"• {r[0]} (ID: {r[1]})" for r in rows])
    await c.message.answer(text, parse_mode="HTML")
    await c.answer()

# --- ВЫВОД ---
@router.callback_query(F.data == "withdraw")
async def withdraw(c: CallbackQuery):
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT stars_balance FROM users WHERE user_id=?", (c.from_user.id,)) as cur:
            row = await cur.fetchone()
        bal = row[0] if row else 0
        async with db.execute("SELECT gift_id FROM gifts WHERE owner_id=? AND status='inventory' LIMIT 1", (c.from_user.id,)) as cur:
            gift = await cur.fetchone()
    
    if bal < WITHDRAW_FEE:
        return await c.answer(f"Недостаточно звёзд. Нужно {WITHDRAW_FEE} ⭐, у тебя {bal} ⭐.", show_alert=True)
    if not gift:
        return await c.answer("Нет подарков для вывода.", show_alert=True)
    
    await c.message.answer_invoice(
        title="Вывод NFT-подарка",
        description=f"Комиссия за вывод: {WITHDRAW_FEE} ⭐",
        payload=f"wd|{c.from_user.id}|{gift[0]}",
        currency="XTR",
        prices=[LabeledPrice(label="Вывод", amount=WITHDRAW_FEE)],
        provider_token=""
    )
    await c.answer()

@router.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await q.answer(ok=True)

@router.message(F.successful_payment)
async def paid(m: Message):
    parts = m.successful_payment.invoice_payload.split("|")
    if parts[0] != "wd":
        return
    uid, gift_id = int(parts[1]), parts[2]
    
    # Списываем звёзды и помечаем подарок как выведенный
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE users SET stars_balance=stars_balance-? WHERE user_id=?", (WITHDRAW_FEE, uid))
        await db.execute("UPDATE gifts SET status='withdrawn' WHERE gift_id=? AND owner_id=?", (gift_id, uid))
        await db.commit()
    
    # Отправляем подарок через sendGift
    url = f"{API_BASE}/bot{BOT_TOKEN}/sendGift"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json={
                "user_id": uid,
                "gift_id": int(gift_id),
                "text": "Вывод из MRKT"
            }) as resp:
                res = await resp.json()
                if res.get("ok"):
                    await m.answer(f"✅ Подарок успешно выведен и отправлен тебе!")
                else:
                    await m.answer(f"⚠️ Ошибка API при отправке: {res.get('description')}")
    except Exception as e:
        await m.answer(f"⚠️ Ошибка: {e}")

# --- ЗАПУСК ---
async def main():
    await init_db()
    session = AiohttpSession(api=TelegramAPIServer.from_base(API_BASE))
    bot = Bot(token=BOT_TOKEN, session=session, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)
    
    # Запускаем фоновую синхронизацию (на случай, если connection_id уже в БД)
    asyncio.create_task(sync_bank_gifts())
    
    await bot.set_my_commands([BotCommand(command="start", description="Меню")])
    logger.info("MRKT запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())