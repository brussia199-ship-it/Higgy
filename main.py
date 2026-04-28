import asyncio
import aiohttp
import json
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext

from config import BOT_TOKEN, CRYPTOBOT_API_KEY, ADMIN_IDS, CRYPTOBOT_API_URL
from database import *
from states import *
from keyboards import *

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ========== CRYPTOBOT API ==========
async def create_cryptobot_invoice(amount_usdt: float, user_id: int) -> str | None:
    url = f"{CRYPTOBOT_API_URL}/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_API_KEY}
    payload = {"asset": "USDT", "amount": str(amount_usdt)}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, json=payload) as resp:
            data = await resp.json()
            if data.get("ok"):
                invoice_id = data["result"]["invoice_id"]
                save_invoice(user_id, amount_usdt, invoice_id)
                return data["result"]["pay_url"]
    return None

async def check_invoice_status(invoice_id: str) -> bool:
    url = f"{CRYPTOBOT_API_URL}/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTOBOT_API_KEY}
    params = {"invoice_ids": invoice_id}
    
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as resp:
            data = await resp.json()
            if data.get("ok") and data["result"]["items"]:
                return data["result"]["items"][0]["status"] == "paid"
    return False

# ========== ХЭНДЛЕРЫ ==========
@dp.message(Command("start"))
async def start(message: types.Message):
    register_user(message.from_user.id, message.from_user.username)
    user = get_user(message.from_user.id)
    await message.answer("Добро пожаловать в магазин!", reply_markup=main_kb(user["role"]))

@dp.message(F.text == "💰 Баланс")
async def show_balance(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(f"Ваш баланс: {user['balance']} USDT")

@dp.message(F.text == "🛍️ Профиль")
async def profile(message: types.Message):
    user = get_user(message.from_user.id)
    await message.answer(f"ID: {user['user_id']}\nИмя: {user['username']}\nРоль: {user['role']}\nБаланс: {user['balance']} USDT")

@dp.message(F.text == "📦 Товары")
async def list_products(message: types.Message):
    products = get_products(only_top=False)
    if not products:
        await message.answer("Товаров пока нет")
        return
    text = "\n\n".join([f"📌 {p['name']}\n💰 {p['price']} USDT\n📝 {p['description']}\n⭐ {'ТОП' if p['is_top'] else 'Обычный'}" for p in products[:10]])
    await message.answer(text[:4000])

@dp.message(F.text == "🛒 Купить товар")
async def buy_product_list(message: types.Message):
    products = get_products(only_top=False)
    if not products:
        await message.answer("Нет товаров для покупки")
        return
    await message.answer("Выберите товар:", reply_markup=products_kb(products, "buy"))

@dp.callback_query(F.data.startswith("buy_"))
async def process_buy(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    product = get_product(product_id)
    if not product:
        await callback.answer("Товар не найден")
        return
    
    user = get_user(callback.from_user.id)
    if user["balance"] < product["price"]:
        # Создаем счет через CryptoBot
        pay_url = await create_cryptobot_invoice(product["price"], callback.from_user.id)
        if pay_url:
            await callback.message.answer(f"💰 Недостаточно средств. Оплатите {product['price']} USDT по ссылке:\n{pay_url}\nПосле оплаты нажмите 'Я оплатил'")
        else:
            await callback.message.answer("Ошибка создания счета. Попробуйте позже.")
        await callback.answer()
        return
    
    # Списание и создание сделки
    update_balance(callback.from_user.id, -product["price"])
    deal_id = create_deal(product_id, callback.from_user.id, product["seller_id"], product["contact"])
    await callback.message.answer(f"✅ Оплата прошла! Контакт продавца: {product['contact']}\nID сделки: {deal_id}\nПосле получения товара нажмите /complete_{deal_id}")
    await callback.answer()

@dp.message(F.text.startswith("/complete_"))
async def complete_order(message: types.Message):
    try:
        deal_id = int(message.text.split("_")[1])
        complete_deal(deal_id)
        await message.answer("✅ Спасибо! Сделка завершена.")
    except:
        await message.answer("Ошибка")

@dp.message(F.text == "➕ Создать товар")
async def start_create_product(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if user["role"] not in ["seller", "admin"]:
        await message.answer("Доступно только продавцам")
        return
    await state.set_state(CreateProduct.name)
    await message.answer("Введите название товара:")

@dp.message(CreateProduct.name)
async def product_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await state.set_state(CreateProduct.description)
    await message.answer("Введите описание:")

@dp.message(CreateProduct.description)
async def product_desc(message: types.Message, state: FSMContext):
    await state.update_data(description=message.text)
    await state.set_state(CreateProduct.price)
    await message.answer("Введите цену в USDT:")

@dp.message(CreateProduct.price)
async def product_price(message: types.Message, state: FSMContext):
    try:
        price = float(message.text)
        await state.update_data(price=price)
        await state.set_state(CreateProduct.contact)
        await message.answer("Введите контакт для связи (Telegram/WhatsApp и т.д.):")
    except:
        await message.answer("Введите число")

@dp.message(CreateProduct.contact)
async def product_contact(message: types.Message, state: FSMContext):
    data = await state.update_data(contact=message.text)
    user = get_user(message.from_user.id)
    add_product(user["user_id"], data["name"], data["description"], data["price"], data["contact"])
    await state.clear()
    await message.answer("✅ Товар создан!")

@dp.message(F.text == "📋 Мои товары")
async def my_products(message: types.Message):
    user = get_user(message.from_user.id)
    products = get_products(seller_id=user["user_id"])
    if not products:
        await message.answer("У вас нет товаров")
        return
    text = "\n\n".join([f"ID:{p['id']} {p['name']} - {p['price']} USDT" for p in products])
    await message.answer(text)

@dp.message(F.text == "⭐ Поднять товар в топ (1 USDT)")
async def promote_product(message: types.Message):
    user = get_user(message.from_user.id)
    if user["balance"] < 1:
        pay_url = await create_cryptobot_invoice(1, user["user_id"])
        await message.answer(f"Недостаточно средств. Оплатите 1 USDT: {pay_url}")
        return
    update_balance(user["user_id"], -1)
    products = get_products(seller_id=user["user_id"])
    if not products:
        await message.answer("У вас нет товаров")
        return
    await message.answer("Выберите товар для поднятия в топ:", reply_markup=products_kb(products, "top"))

@dp.callback_query(F.data.startswith("top_"))
async def process_top(callback: types.CallbackQuery):
    product_id = int(callback.data.split("_")[1])
    promote_to_top(product_id)
    await callback.message.answer("✅ Товар поднят в топ!")
    await callback.answer()

@dp.message(F.text == "💸 Вывод средств")
async def withdraw_menu(message: types.Message, state: FSMContext):
    await state.set_state(WithdrawMoney.amount)
    await message.answer("Введите сумму вывода в USDT:")

@dp.message(WithdrawMoney.amount)
async def process_withdraw(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        user = get_user(message.from_user.id)
        if user["balance"] < amount:
            await message.answer("Недостаточно средств")
            return
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO withdraw_requests (user_id, amount) VALUES (%s, %s)", (message.from_user.id, amount))
        conn.commit()
        cursor.close()
        conn.close()
        await state.clear()
        await message.answer(f"✅ Заявка на вывод {amount} USDT отправлена администратору")
    except:
        await message.answer("Ошибка")

@dp.message(F.text == "📞 Подать заявку на продавца")
async def request_seller(message: types.Message):
    add_seller_request(message.from_user.id, message.from_user.username)
    await message.answer("Заявка отправлена администратору")

@dp.message(F.text == "👑 Админ-панель")
async def admin_panel(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("Нет доступа")
        return
    await message.answer("Админ-панель", reply_markup=admin_panel_kb())

@dp.message(F.text == "✅ Проверить заявки продавцов")
async def check_requests(message: types.Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    requests = get_pending_requests()
    if not requests:
        await message.answer("Нет заявок")
        return
    for req in requests:
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Принять", callback_data=f"accept_seller_{req['user_id']}")]
        ])
        await message.answer(f"Заявка от @{req['username']} (ID:{req['user_id']})", reply_markup=kb)

@dp.callback_query(F.data.startswith("accept_seller_"))
async def accept_seller(callback: types.CallbackQuery):
    user_id = int(callback.data.split("_")[2])
    accept_seller_request(user_id)
    await callback.message.answer(f"Продавец {user_id} добавлен")
    await callback.answer()

@dp.message(F.text == "💰 Добавить баланс")
async def admin_add_balance(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminAddBalance.user_id)
    await message.answer("Введите user_id пользователя:")

@dp.message(AdminAddBalance.user_id)
async def admin_balance_user_id(message: types.Message, state: FSMContext):
    await state.update_data(user_id=int(message.text))
    await state.set_state(AdminAddBalance.amount)
    await message.answer("Введите сумму:")

@dp.message(AdminAddBalance.amount)
async def admin_balance_amount(message: types.Message, state: FSMContext):
    data = await state.get_data()
    update_balance(data["user_id"], float(message.text))
    await state.clear()
    await message.answer("✅ Баланс обновлен")

@dp.message(F.text == "🗑️ Удалить товар")
async def admin_delete_product(message: types.Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    await state.set_state(AdminDeleteProduct.product_id)
    await message.answer("Введите ID товара:")

@dp.message(AdminDeleteProduct.product_id)
async def admin_delete_product_id(message: types.Message, state: FSMContext):
    delete_product(int(message.text))
    await state.clear()
    await message.answer("✅ Товар удален")

@dp.callback_query(F.data.startswith("check_payment_"))
async def check_payment(callback: types.CallbackQuery):
    invoice_id = int(callback.data.split("_")[2])
    invoice = get_pending_invoice(callback.from_user.id)
    if not invoice:
        await callback.answer("Счет не найден")
        return
    paid = await check_invoice_status(str(invoice["cryptobot_invoice_id"]))
    if paid:
        mark_invoice_paid(invoice["cryptobot_invoice_id"])
        update_balance(callback.from_user.id, invoice["amount"])
        await callback.message.answer(f"✅ Баланс пополнен на {invoice['amount']} USDT")
    else:
        await callback.answer("Оплата не найдена", show_alert=True)
    await callback.answer()

async def main():
    init_db()
    print("Бот запущен")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())