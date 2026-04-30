import telebot
from telebot import types
from tinydb import TinyDB, Query
import requests
from datetime import datetime, timedelta
import time

from config import TOKEN, ADMIN_ID, CRYPTOBOT_TOKEN, CRYPTOBOT_API_URL, DB_CHANNEL_ID

bot = telebot.TeleBot(TOKEN)
db = TinyDB('database.json')
users = db.table('users')
products = db.table('products')
stats = db.table('stats')
categories = db.table('categories')
purchases = db.table('purchases')

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    if not users.get(Query().user_id == user_id):
        users.insert({'user_id': user_id, 'balance': 0, 'purchases': 0, 'total_spent': 0, 'total_deposited': 0, 'join_date': datetime.now().strftime('%Y-%m-%d')})
        stats.insert({'type': 'new_user', 'timestamp': datetime.now().strftime('%Y-%m-%d')})
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row(types.KeyboardButton("🏪 Купить"), types.KeyboardButton("📋 Товары"))
    markup.row(types.KeyboardButton("👤 Профиль"), types.KeyboardButton("💳 Пополнить баланс"))
    markup.row(types.KeyboardButton("🛒 Мои покупки"))
    bot.send_message(message.chat.id, "<b>Привет! Добро пожаловать в наш магазин!</b>", reply_markup=markup, parse_mode='HTML')

@bot.message_handler(commands=['admin'])
def admin_panel(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "У вас нет доступа к админ-панели")
        return
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Добавить товар", callback_data="admin_add"), types.InlineKeyboardButton("Удалить товар", callback_data="admin_delete"))
    markup.add(types.InlineKeyboardButton("Создать раздел", callback_data="admin_create_category"), types.InlineKeyboardButton("Удалить раздел", callback_data="admin_delete_category"))
    markup.add(types.InlineKeyboardButton("Статистика", callback_data="admin_stats"))
    bot.send_message(message.chat.id, "Админ меню", reply_markup=markup)

@bot.message_handler(content_types=['text'])
def handle_text(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    if message.text == "👤 Профиль":
        user = users.get(Query().user_id == user_id)
        if user:
            text = (f"Ваш профиль:\n Ваш ID: <code>{user_id}</code>\n\nИнформация:\n├ Сумма покупок: <code>{user['total_spent']}$</code>\n└ Сумма пополнений: <code>{user['total_deposited']}$</code>\n\n🏦 Ваш баланс: <code>{user['balance']}$</code>")
            bot.send_message(chat_id, text, parse_mode='HTML')
        else:
            bot.send_message(chat_id, "Профиль не найден. Попробуйте перезапустить бота с помощью /start")
    elif message.text == "💳 Пополнить баланс":
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🤖 CryptoBot | USDT", callback_data="pay_usdt"))
        bot.send_message(chat_id, "➖ Пополнение баланса ➖\n\nВыберите способ пополнения баланса.", reply_markup=markup)
    elif message.text == "🏪 Купить":
        markup = types.InlineKeyboardMarkup()
        all_categories = categories.all()
        for i in range(0, len(all_categories), 2):
            row = []
            row.append(types.InlineKeyboardButton(all_categories[i]['name'], callback_data=f"category_{all_categories[i]['id']}"))
            if i + 1 < len(all_categories):
                row.append(types.InlineKeyboardButton(all_categories[i+1]['name'], callback_data=f"category_{all_categories[i+1]['id']}"))
            markup.add(*row)
        bot.send_message(chat_id, "Каталог", reply_markup=markup)
    elif message.text == "📋 Товары":
        show_products_list(chat_id)
    elif message.text == "🛒 Мои покупки":
        show_purchases(chat_id, user_id)

def process_amount(message):
    try:
        amount = float(message.text)
        if not (0.0001 <= amount <= 500):
            raise ValueError("Сумма должна быть от 0.0001$ до 500$")
        markup = types.InlineKeyboardMarkup()
        invoice = create_cryptobot_invoice(amount, message.from_user.id)
        markup.add(types.InlineKeyboardButton("🌍 Перейти к оплате", url=invoice['pay_url']))
        markup.add(types.InlineKeyboardButton("🔄 Проверить оплату", callback_data=f"check_{invoice['invoice_id']}"))
        bot.send_message(message.chat.id, f"➖ Пополнение ➖\n\n💰 Сумма: <code>{amount}$</code>", reply_markup=markup, parse_mode='HTML')
    except ValueError as e:
        bot.send_message(message.chat.id, str(e))

@bot.callback_query_handler(func=lambda call: True)
def callback_handler(call):
    chat_id = call.message.chat.id
    message_id = call.message.message_id
    user_id = call.from_user.id
    
    try:
        if call.data.startswith("category_"):
            category_id = int(call.data.split("_")[1])
            category = categories.get(Query().id == category_id)
            if category:
                bot.delete_message(chat_id, message_id)
                markup = types.InlineKeyboardMarkup()
                items = products.search(Query().category_id == category_id)
                for i in range(0, len(items), 2):
                    row = []
                    row.append(types.InlineKeyboardButton(items[i]['name'], callback_data=f"item_{items[i]['id']}"))
                    if i + 1 < len(items):
                        row.append(types.InlineKeyboardButton(items[i+1]['name'], callback_data=f"item_{items[i+1]['id']}"))
                    markup.add(*row)
                markup.add(types.InlineKeyboardButton("Назад", callback_data="back_to_catalog"))
                bot.send_message(chat_id, f"Каталог: {category['name']}", reply_markup=markup)
        
        elif call.data.startswith("item_"):
            item_id = int(call.data.split("_")[1])
            item = products.get(Query().id == item_id)
            is_purchased = purchases.contains((Query().user_id == user_id) & (Query().item_id == item_id))
            if item:
                bot.delete_message(chat_id, message_id)
                text = (f"➖ Покупка ➖\n\n📦 Товар: {item['name']}\n💰 Цена: {item['price']}$\n⭐ Stars: {item['stars_price']} \n\nОписание:\n{item['description']}")
                markup = types.InlineKeyboardMarkup()
                if is_purchased:
                    markup.add(types.InlineKeyboardButton("📥 Скачать", callback_data=f"download_item_{item_id}"))
                    text += "\n\n<b>Вы уже приобрели этот товар!</b>"
                else:
                    markup.add(
                        types.InlineKeyboardButton("🛍 Купить за $", callback_data=f"buy_{item_id}"),
                        types.InlineKeyboardButton("Оплата через Stars", callback_data=f"buy_stars_{item_id}")
                    )
                markup.add(types.InlineKeyboardButton("Назад", callback_data=f"category_{item['category_id']}"))
                bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')
        
        elif call.data == "goto_buy":
            bot.delete_message(chat_id, message_id)
            markup = types.InlineKeyboardMarkup()
            all_categories = categories.all()
            for i in range(0, len(all_categories), 2):
                row = []
                row.append(types.InlineKeyboardButton(all_categories[i]['name'], callback_data=f"category_{all_categories[i]['id']}"))
                if i + 1 < len(all_categories):
                    row.append(types.InlineKeyboardButton(all_categories[i+1]['name'], callback_data=f"category_{all_categories[i+1]['id']}"))
                markup.add(*row)
            bot.send_message(chat_id, "Каталог", reply_markup=markup)
        
        elif call.data.startswith("buy_stars_"):
            item_id = int(call.data.split("_")[2])
            item = products.get(Query().id == item_id)
            if item:
                bot.delete_message(chat_id, message_id)
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Да", callback_data=f"confirm_stars_{item_id}"), types.InlineKeyboardButton("Отмена", callback_data=f"item_{item_id}"))
                bot.send_message(chat_id, f"<b>Вы точно хотите купить '{item['name']}' за {item['stars_price']} Telegram Stars?</b>", reply_markup=markup, parse_mode='HTML')
        
        elif call.data.startswith("confirm_stars_"):
            item_id = int(call.data.split("_")[2])
            item = products.get(Query().id == item_id)
            if item:
                bot.delete_message(chat_id, message_id)
                bot.send_invoice(
                    chat_id=chat_id,
                    title=item['name'],
                    description=item['description'],
                    invoice_payload=f"purchase_{item_id}_{user_id}",
                    provider_token="",
                    currency="XTR",
                    prices=[types.LabeledPrice(label="Price", amount=item['stars_price'])],
                    start_parameter="purchase"
                )
        
        elif call.data == "back_to_catalog":
            bot.delete_message(chat_id, message_id)
            markup = types.InlineKeyboardMarkup()
            all_categories = categories.all()
            for i in range(0, len(all_categories), 2):
                row = []
                row.append(types.InlineKeyboardButton(all_categories[i]['name'], callback_data=f"category_{all_categories[i]['id']}"))
                if i + 1 < len(all_categories):
                    row.append(types.InlineKeyboardButton(all_categories[i+1]['name'], callback_data=f"category_{all_categories[i+1]['id']}"))
                markup.add(*row)
            bot.send_message(chat_id, "Каталог", reply_markup=markup)
        
        elif call.data.startswith("buy_"):
            item_id = int(call.data.split("_")[1])
            item = products.get(Query().id == item_id)
            if item:
                bot.delete_message(chat_id, message_id)
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("Да", callback_data=f"confirm_{item_id}"), types.InlineKeyboardButton("Отмена", callback_data=f"item_{item_id}"))
                bot.send_message(chat_id, "<b>Вы точно хотите купить этот товар?</b>", reply_markup=markup, parse_mode='HTML')
        
        elif call.data.startswith("confirm_"):
            item_id = int(call.data.split("_")[1])
            item = products.get(Query().id == item_id)
            user = users.get(Query().user_id == user_id)
            if item and user:
                if user['balance'] >= item['price']:
                    bot.delete_message(chat_id, message_id)
                    users.update({'balance': user['balance'] - item['price'], 'purchases': user['purchases'] + 1, 'total_spent': user['total_spent'] + item['price']}, Query().user_id == user_id)
                    purchases.insert({'user_id': user_id, 'item_id': item_id, 'price': item['price'], 'currency': '$', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                    bot.send_message(chat_id, "⚡️")
                    if 'file_id' in item:
                        bot.send_document(chat_id, item['file_id'], caption=f"Ваш товар: {item['name']}")
                else:
                    bot.edit_message_text("❌ Недостаточно средств на балансе!", chat_id, message_id)
        
        elif call.data == "pay_usdt":
            bot.delete_message(chat_id, message_id)
            msg = bot.send_message(chat_id, "➖ Пополнение баланса ➖\n\nВведите сумму пополнения, от 1$ до 1500$:")
            bot.register_next_step_handler(msg, process_amount)
        
        elif call.data.startswith("check_"):
            invoice_id = call.data.split("_")[1]
            status = check_payment(invoice_id)
            if status:
                amount = float(status['amount'])
                user = users.get(Query().user_id == user_id)
                users.update({'balance': user['balance'] + amount, 'total_deposited': user['total_deposited'] + amount}, Query().user_id == user_id)
                stats.insert({'type': 'payment', 'amount': amount, 'timestamp': datetime.now().strftime('%Y-%m-%d')})
                bot.edit_message_text("✅ Оплата успешно завершена!", chat_id, message_id)
            else:
                bot.answer_callback_query(call.id, "Платеж еще не завершен")
        
        elif call.data == "admin_stats":
            stats_text = get_stats()
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Назад", callback_data="admin_back"))
            bot.edit_message_text(stats_text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
        
        elif call.data == "admin_add":
            markup = types.InlineKeyboardMarkup()
            all_categories = categories.all()
            for i in range(0, len(all_categories), 2):
                row = []
                row.append(types.InlineKeyboardButton(all_categories[i]['name'], callback_data=f"admin_select_category_{all_categories[i]['id']}"))
                if i + 1 < len(all_categories):
                    row.append(types.InlineKeyboardButton(all_categories[i+1]['name'], callback_data=f"admin_select_category_{all_categories[i+1]['id']}"))
                markup.add(*row)
            bot.send_message(chat_id, "Выберите раздел для создания товара", reply_markup=markup)
        
        elif call.data == "admin_create_category":
            bot.delete_message(chat_id, message_id)
            msg = bot.send_message(chat_id, "Введите название раздела")
            bot.register_next_step_handler(msg, create_category)
        
        elif call.data == "admin_delete_category":
            show_categories_to_delete(chat_id)
        
        elif call.data == "admin_delete":
            show_products_to_delete(chat_id)
        
        elif call.data == "admin_back":
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton("Добавить товар", callback_data="admin_add"), types.InlineKeyboardButton("Удалить товар", callback_data="admin_delete"))
            markup.add(types.InlineKeyboardButton("Создать раздел", callback_data="admin_create_category"), types.InlineKeyboardButton("Удалить раздел", callback_data="admin_delete_category"))
            markup.add(types.InlineKeyboardButton("Статистика", callback_data="admin_stats"))
            bot.edit_message_text("Админ меню", chat_id, message_id, reply_markup=markup)
        
        elif call.data.startswith("admin_select_category_"):
            category_id = int(call.data.split("_")[3])
            bot.delete_message(chat_id, message_id)
            msg = bot.send_message(chat_id, "Введите название товара")
            bot.register_next_step_handler(msg, lambda m: add_product_name(m, category_id))
        
        elif call.data.startswith("purchase_"):
            purchase_id = int(call.data.split("_")[1])
            purchase = purchases.get(doc_id=purchase_id)
            item = products.get(Query().id == purchase['item_id'])
            text = (f"📦 Товар: {item['name']}\n"
                    f"💰 Цена: {purchase['price']} {purchase['currency']}\n"
                    f"⏰ Время покупки: {purchase['timestamp']}\n\n"
                    f"Описание:\n{item['description']}")
            markup = types.InlineKeyboardMarkup()
            markup.add(
                types.InlineKeyboardButton("Скачать", callback_data=f"download_{purchase_id}"),
                types.InlineKeyboardButton("Назад", callback_data="back_to_purchases")
            )
            bot.edit_message_text(text, chat_id, message_id, reply_markup=markup, parse_mode='HTML')
        
        elif call.data.startswith("download_"):
            purchase_id = int(call.data.split("_")[1])
            purchase = purchases.get(doc_id=purchase_id)
            item = products.get(Query().id == purchase['item_id'])
            bot.delete_message(chat_id, message_id)
            bot.send_document(chat_id, item['file_id'], caption=f"Ваш товар: {item['name']}")
        
        elif call.data.startswith("download_item_"):
            item_id = int(call.data.split("_")[2])
            item = products.get(Query().id == item_id)
            bot.delete_message(chat_id, message_id)
            bot.send_document(chat_id, item['file_id'], caption=f"Ваш товар: {item['name']}")
        
        elif call.data == "back_to_purchases":
            bot.delete_message(chat_id, message_id)
            show_purchases(chat_id, user_id)

    except Exception as e:
        bot.send_message(chat_id, f"Произошла ошибка: {str(e)}")
        print(f"Ошибка в callback_handler: {str(e)}")

@bot.pre_checkout_query_handler(func=lambda query: True)
def process_pre_checkout_query(pre_checkout_query):
    bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@bot.message_handler(content_types=['successful_payment'])
def process_successful_payment(message):
    try:
        payment = message.successful_payment
        payload = payment.invoice_payload.split('_')
        if len(payload) == 3 and payload[0] == 'purchase':
            item_id = int(payload[1])
            user_id = int(payload[2])
            item = products.get(Query().id == item_id)
            if item:
                users.update({'purchases': users.get(Query().user_id == user_id)['purchases'] + 1}, Query().user_id == user_id)
                purchases.insert({'user_id': user_id, 'item_id': item_id, 'price': item['stars_price'], 'currency': 'Telegram Stars', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})
                bot.send_message(message.chat.id, "⚡️")
                if 'file_id' in item:
                    bot.send_document(message.chat.id, item['file_id'], caption=f"Ваш товар: {item['name']}")
    except Exception as e:
        bot.send_message(message.chat.id, f"Произошла ошибка при обработке платежа: {str(e)}")
        print(f"Ошибка в process_successful_payment: {str(e)}")

def create_category(message):
    if not message.text:
        bot.send_message(message.chat.id, "Название раздела не может быть пустым!")
        return
    name = message.text
    category_id = len(categories) + 1
    categories.insert({'id': category_id, 'name': name})
    bot.send_message(message.chat.id, "Раздел создан")

def show_categories_to_delete(chat_id):
    all_categories = categories.all()
    if not all_categories:
        bot.send_message(chat_id, "Разделов пока нет")
        return
    text = "<b>Список разделов</b>\n\n"
    for i, category in enumerate(all_categories, 1):
        text += f"{i}. <b>{category['name']}</b>\n"
    text += "\n<b>Введите номер раздела, который хотите удалить</b>"
    msg = bot.send_message(chat_id, text, parse_mode='HTML')
    bot.register_next_step_handler(msg, delete_category)

def delete_category(message):
    try:
        num = int(message.text) - 1
        all_categories = categories.all()
        if 0 <= num < len(all_categories):
            category_id = all_categories[num]['id']
            products.remove(Query().category_id == category_id)
            categories.remove(doc_ids=[all_categories[num].doc_id])
            bot.send_message(message.chat.id, "Раздел удален!")
        else:
            bot.send_message(message.chat.id, "Неверный номер раздела!")
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректный номер!")

def create_cryptobot_invoice(amount, user_id):
    headers = {'Crypto-Pay-API-Token': CRYPTOBOT_TOKEN, 'Content-Type': 'application/json'}
    payload = {'amount': str(amount), 'asset': 'USDT', 'description': f'Пополнение баланса пользователя {user_id}'}
    try:
        response = requests.post(f'{CRYPTOBOT_API_URL}createInvoice', headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        if 'ok' in data and data['ok'] and 'result' in data:
            return data['result']
        else:
            error_msg = data.get('error', 'Неизвестная ошибка')
            raise Exception(f"Ошибка API Crypto Bot: {error_msg}")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Ошибка соединения с Crypto Bot: {str(e)}")
    except ValueError as e:
        raise Exception(f"Ошибка обработки ответа от Crypto Bot: {str(e)}")

def check_payment(invoice_id):
    headers = {'Crypto-Pay-API-Token': CRYPTOBOT_TOKEN, 'Content-Type': 'application/json'}
    try:
        response = requests.get(f'{CRYPTOBOT_API_URL}getInvoices?invoice_ids={invoice_id}', headers=headers)
        response.raise_for_status()
        data = response.json()
        if data['ok'] and 'result' in data and data['result']['items']:
            return data['result']['items'][0] if data['result']['items'][0]['status'] == 'paid' else False
        return False
    except Exception as e:
        return False

def get_stats():
    Stat = Query()
    today = datetime.now().strftime('%Y-%m-%d')
    week_ago = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
    users_day = len(stats.search((Stat.type == 'new_user') & (Stat.timestamp >= today)))
    users_week = len(stats.search((Stat.type == 'new_user') & (Stat.timestamp >= week_ago)))
    users_total = len(stats.search(Stat.type == 'new_user'))
    payments_day = len(stats.search((Stat.type == 'payment') & (Stat.timestamp >= today)))
    payments_week = len(stats.search((Stat.type == 'payment') & (Stat.timestamp >= week_ago)))
    payments_total = len(stats.search(Stat.type == 'payment'))
    return (f"<b>📊 Статистика:</b>\n\n<b>👤 Юзеры:</b>\nЗа день: <code>{users_day}</code>\nЗа неделю: <code>{users_week}</code>\nЗа Всё время: <code>{users_total}</code>\n\n<b>💰Пополнения:</b>\nПополнений за День: <code>{payments_day}</code>\nПополнений за Неделю: <code>{payments_week}</code>\nПополнений за Все время: <code>{payments_total}</code>")

def add_product_name(message, category_id):
    if not message.text:
        bot.send_message(message.chat.id, "Название не может быть пустым!")
        return
    name = message.text
    bot.delete_message(message.chat.id, message.message_id - 1)
    msg = bot.send_message(message.chat.id, "Введите описание товара")
    bot.register_next_step_handler(msg, lambda m: add_product_desc(m, name, category_id))

def add_product_desc(message, name, category_id):
    if not message.text:
        bot.send_message(message.chat.id, "Описание не может быть пустым!")
        return
    desc = message.text
    bot.delete_message(message.chat.id, message.message_id - 1)
    msg = bot.send_message(message.chat.id, "Введите цену товара в $")
    bot.register_next_step_handler(msg, lambda m: add_product_price(m, name, desc, category_id))

def add_product_price(message, name, desc, category_id):
    try:
        price = float(message.text)
        if price <= 0:
            raise ValueError("Цена должна быть положительной")
        bot.delete_message(message.chat.id, message.message_id - 1)
        msg = bot.send_message(message.chat.id, "Введите цену товара в Telegram Stars")
        bot.register_next_step_handler(msg, lambda m: add_product_stars_price(m, name, desc, price, category_id))
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректную положительную цену!")

def add_product_stars_price(message, name, desc, price, category_id):
    try:
        stars_price = int(message.text)
        if stars_price <= 0:
            raise ValueError("Цена должна быть положительной")
        bot.delete_message(message.chat.id, message.message_id - 1)
        msg = bot.send_message(message.chat.id, "Отправьте файл который будет отправляться после покупки")
        bot.register_next_step_handler(msg, lambda m: add_product_file(m, name, desc, price, stars_price, category_id))
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректное положительное число для Telegram Stars!")

def add_product_file(message, name, desc, price, stars_price, category_id):
    if message.content_type == 'document':
        file_msg = bot.send_document(DB_CHANNEL_ID, message.document.file_id)
        file_id = file_msg.document.file_id
        bot.delete_message(message.chat.id, message.message_id - 1)
        product_id = len(products) + 1
        products.insert({'id': product_id, 'name': name, 'description': desc, 'price': price, 'stars_price': stars_price, 'file_id': file_id, 'category_id': category_id})
        bot.send_message(message.chat.id, "Товар создан")
    else:
        bot.send_message(message.chat.id, "Пожалуйста, отправьте документ!")

def show_products_list(chat_id):
    all_categories = categories.all()
    text = ""
    for category in all_categories:
        text += f"\n<b>{category['name']}</b>\n"
        items = products.search(Query().category_id == category['id'])
        for item in items:
            text += f"  {item['name']} | <code>{item['price']}$</code>\n"
    if not text:
        text = "Товаров пока нет"
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("Купить", callback_data="goto_buy"))
    bot.send_message(chat_id, text, reply_markup=markup, parse_mode='HTML')

def show_purchases(chat_id, user_id):
    user_purchases = purchases.search(Query().user_id == user_id)
    if not user_purchases:
        bot.send_message(chat_id, "У вас пока нет покупок")
        return
    text = "Ваши покупки\n\n"
    markup = types.InlineKeyboardMarkup()
    for purchase in user_purchases:
        item = products.get(Query().id == purchase['item_id'])
        markup.add(types.InlineKeyboardButton(
            f"{item['name']} • {purchase['timestamp']} • {purchase['price']} {purchase['currency']}",
            callback_data=f"purchase_{purchase.doc_id}"
        ))
    bot.send_message(chat_id, text, reply_markup=markup)

def show_products_to_delete(chat_id):
    items = products.all()
    if not items:
        bot.send_message(chat_id, "Товаров пока нет")
        return
    text = "<b>Список товаров</b>\n\n"
    for i, item in enumerate(items, 1):
        text += f"{i}. <b>{item['name']}</b> | <code>{item['price']}$</code>\n"
    text += "\n<b>Введите номер товара который хотите удалить</b>"
    msg = bot.send_message(chat_id, text, parse_mode='HTML')
    bot.register_next_step_handler(msg, delete_product)

def delete_product(message):
    try:
        num = int(message.text) - 1
        items = products.all()
        if 0 <= num < len(items):
            products.remove(doc_ids=[items[num].doc_id])
            bot.send_message(message.chat.id, "Товар удален!")
        else:
            bot.send_message(message.chat.id, "Неверный номер товара!")
    except ValueError:
        bot.send_message(message.chat.id, "Введите корректный номер!")

if __name__ == "__main__":
    while True:
        try:
            bot.polling(none_stop=True)
        except Exception as e:
            print(f"Ошибка при запуске бота: {str(e)}")
            time.sleep(5)
