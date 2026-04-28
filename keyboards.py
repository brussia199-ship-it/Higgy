from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

def main_kb(role):
    buttons = [
        [KeyboardButton(text="💰 Баланс"), KeyboardButton(text="🛍️ Профиль")],
        [KeyboardButton(text="📦 Товары"), KeyboardButton(text="🛒 Купить товар")]
    ]
    if role == "seller":
        buttons.append([KeyboardButton(text="➕ Создать товар"), KeyboardButton(text="📋 Мои товары")])
        buttons.append([KeyboardButton(text="⭐ Поднять товар в топ (1 USDT)"), KeyboardButton(text="💸 Вывод средств")])
    if role == "admin":
        buttons.append([KeyboardButton(text="👑 Админ-панель")])
    buttons.append([KeyboardButton(text="📞 Подать заявку на продавца")])
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def admin_panel_kb():
    buttons = [
        [KeyboardButton(text="➕ Добавить администратора")],
        [KeyboardButton(text="👤 Добавить продавца")],
        [KeyboardButton(text="💰 Добавить баланс")],
        [KeyboardButton(text="🧾 Создать чек на баланс")],
        [KeyboardButton(text="🗑️ Удалить товар")],
        [KeyboardButton(text="✅ Проверить заявки продавцов")],
        [KeyboardButton(text="🔙 Назад")]
    ]
    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

def products_kb(products, prefix):
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for p in products:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"{p['name']} - {p['price']} USDT", callback_data=f"{prefix}_{p['id']}")])
    return kb

def confirm_payment_kb(invoice_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data=f"check_payment_{invoice_id}")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel_payment")]
    ])