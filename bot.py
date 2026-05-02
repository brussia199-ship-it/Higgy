import telebot
from telebot import types
from tinydb import TinyDB, Query
import time
import random
from datetime import datetime
from config import TOKEN, CHANNEL_ID, CHANNEL_LINK, ADMIN_CHANNEL_ID
import os
import shutil
import json

# Функция для удаления вебхука
def delete_webhook():
    try:
        bot_temp = telebot.TeleBot(TOKEN)
        bot_temp.remove_webhook()
        time.sleep(1)
        print("✅ Вебхук удалён")
    except Exception as e:
        print(f"Ошибка удаления вебхука: {e}")

# Функция для бэкапа
def backup_database():
    try:
        if os.path.exists('db.json'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = 'backups'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            shutil.copy('db.json', f'{backup_dir}/db_{timestamp}.json')
    except Exception as e:
        print(f"Ошибка бэкапа: {e}")

def create_bot():
    global BOT_USERNAME 
    try:
        delete_webhook()
        
        bot = telebot.TeleBot(TOKEN)
        db = TinyDB('db.json')
        User = Query()
        bot_info = bot.get_me()
        BOT_USERNAME = bot_info.username
        print(f"🤖 Бот запущен: @{BOT_USERNAME}")

        @bot.message_handler(commands=['start'])
        def start_handler(message):
            try:
                user_id = message.from_user.id
                username = message.from_user.username or "NoUsername"
                first_name = message.from_user.first_name
                last_name = message.from_user.last_name or ""
                param = message.text.split()[1] if len(message.text.split()) > 1 else None

                # Проверяем существование пользователя
                user = db.get(User.user_id == user_id)
                if not user:
                    db.insert({
                        'user_id': user_id,
                        'balance': 0,
                        'bets_count': 0,
                        'wins_count': 0,
                        'losses_count': 0,
                        'total_earned': 0,
                        'total_wagered': 0,
                        'slots_played': 0,
                        'slots_wins': 0,
                        'reg_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'first_name': first_name,
                        'last_name': last_name
                    })
                    print(f"📝 Новый пользователь: {user_id}")

                if param == "bet":
                    user_data = db.get(User.user_id == user_id)
                    bot.send_message(message.chat.id,
                                   f"<b>🎲 Сделать ставку</b>\n\n"
                                   f"💰 Ваш баланс: <code>{user_data['balance']} звёзд</code>\n\n"
                                   f"<b>Пришлите сумму звёзд для ставки.</b>\n"
                                   f"<i>Минимальная ставка: 5 звёзд</i>",
                                   parse_mode='HTML')
                    bot.register_next_step_handler(message, process_bet_amount)
                else:
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
                    btn_profile = types.KeyboardButton("⚡️ Профиль")
                    btn_add_stars = types.KeyboardButton("💰 Пополнить")
                    btn_withdraw = types.KeyboardButton("🎁 Вывести")
                    btn_bet = types.KeyboardButton("🎲 Ставка")
                    btn_slots = types.KeyboardButton("🎰 Слоты")
                    markup.add(btn_profile, btn_add_stars, btn_withdraw, btn_bet, btn_slots)
                    
                    bot.send_message(message.chat.id,
                                   f"<b>👋 Добро пожаловать, @{username}</b>\n\n"
                                   f"📢 Канал: <a href='{CHANNEL_LINK}'>тык</a>\n\n"
                                   f"🎲 Ставки - выигрыш x2\n"
                                   f"🎰 Слоты - x2, x5, x10",
                                   parse_mode='HTML',
                                   reply_markup=markup)
            except Exception as e:
                print(f"Ошибка start: {e}")
                bot.send_message(message.chat.id, "❌ Ошибка")

        # ========== СТАВКИ ==========
        def process_bet_amount(message):
            try:
                user_id = message.from_user.id
                amount_text = message.text.strip()
                
                if not amount_text.isdigit():
                    bot.send_message(message.chat.id, "❌ Введите число!")
                    return
                    
                amount = int(amount_text)
                user_data = db.get(User.user_id == user_id)
                
                if amount < 5:
                    bot.send_message(message.chat.id, "❌ Минимум 5 звёзд!")
                    return
                    
                if amount > user_data['balance']:
                    bot.send_message(message.chat.id, f"❌ Недостаточно! Баланс: {user_data['balance']}⭐")
                    return
                
                # Сохраняем ставку В БАЗУ ДАННЫХ
                db.update({
                    'temp_bet_amount': amount,
                    'temp_bet_step': 'waiting_choice'
                }, User.user_id == user_id)
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                btn_more = types.InlineKeyboardButton("🎲 БОЛЬШЕ (4-6)", callback_data="game_more")
                btn_less = types.InlineKeyboardButton("🎲 МЕНЬШЕ (1-3)", callback_data="game_less")
                markup.add(btn_more, btn_less)
                
                bot.send_message(message.chat.id,
                               f"<b>🎲 Ставка: {amount}⭐</b>\n\n"
                               f"<b>Выберите исход:</b>",
                               parse_mode='HTML',
                               reply_markup=markup)
            except Exception as e:
                print(f"Ошибка process_bet: {e}")
                bot.send_message(message.chat.id, "❌ Ошибка")

        @bot.callback_query_handler(func=lambda call: call.data in ["game_more", "game_less"])
        def game_choice(call):
            try:
                user_id = call.from_user.id
                game_type = call.data.split("_")[1]
                
                user_data = db.get(User.user_id == user_id)
                
                # Проверяем есть ли временная ставка
                if 'temp_bet_amount' not in user_data or user_data.get('temp_bet_step') != 'waiting_choice':
                    bot.answer_callback_query(call.id, "❌ Ставка не найдена. Начните заново /start bet")
                    return
                
                amount = user_data['temp_bet_amount']
                
                # Сохраняем выбор
                db.update({
                    'temp_bet_choice': game_type,
                    'temp_bet_step': 'waiting_confirm'
                }, User.user_id == user_id)
                
                markup = types.InlineKeyboardMarkup()
                btn_yes = types.InlineKeyboardButton("✅ Да", callback_data="confirm_bet")
                btn_no = types.InlineKeyboardButton("❌ Нет", callback_data="cancel_bet")
                markup.add(btn_yes, btn_no)
                
                game_text = "БОЛЬШЕ" if game_type == "more" else "МЕНЬШЕ"
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"<b>🎲 Подтверждение</b>\n\n"
                         f"💰 Сумма: {amount}⭐\n"
                         f"🎯 Исход: {game_text}\n\n"
                         f"Подтверждаете?",
                    parse_mode='HTML',
                    reply_markup=markup
                )
            except Exception as e:
                print(f"Ошибка game_choice: {e}")
                bot.answer_callback_query(call.id, "❌ Ошибка")

        @bot.callback_query_handler(func=lambda call: call.data == "confirm_bet")
        def confirm_game(call):
            try:
                user_id = call.from_user.id
                username = call.from_user.username or "NoUsername"
                user_data = db.get(User.user_id == user_id)
                
                if 'temp_bet_amount' not in user_data or user_data.get('temp_bet_step') != 'waiting_confirm':
                    bot.answer_callback_query(call.id, "❌ Ставка не найдена!")
                    return
                
                amount = user_data['temp_bet_amount']
                game_type = user_data['temp_bet_choice']
                
                # Проверяем баланс
                if user_data['balance'] < amount:
                    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text="❌ Недостаточно средств!")
                    db.update({'temp_bet_step': None}, User.user_id == user_id)
                    return
                
                # Списываем ставку
                new_balance = user_data['balance'] - amount
                new_bets_count = user_data['bets_count'] + 1
                new_total_wagered = user_data['total_wagered'] + amount
                
                db.update({
                    'balance': new_balance,
                    'bets_count': new_bets_count,
                    'total_wagered': new_total_wagered,
                    'temp_bet_step': 'playing'
                }, User.user_id == user_id)
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"🎲 <b>Игра!</b>\n\nСтавка: {amount}⭐\n🎲 Бросаем кубик...",
                    parse_mode='HTML'
                )
                
                time.sleep(1)
                dice = bot.send_dice(call.message.chat.id)
                dice_value = dice.dice.value
                
                win = (game_type == "more" and dice_value >= 4) or (game_type == "less" and dice_value <= 3)
                game_text = "БОЛЬШЕ" if game_type == "more" else "МЕНЬШЕ"
                
                if win:
                    win_amount = amount * 2
                    user_data = db.get(User.user_id == user_id)
                    new_balance = user_data['balance'] + win_amount
                    new_total_earned = user_data['total_earned'] + win_amount
                    new_wins = user_data['wins_count'] + 1
                    
                    db.update({
                        'balance': new_balance,
                        'total_earned': new_total_earned,
                        'wins_count': new_wins,
                        'temp_bet_step': None
                    }, User.user_id == user_id)
                    
                    bot.send_message(call.message.chat.id,
                        f"<b>🎉 ПОБЕДА!</b>\n\n"
                        f"🎲 Выпало: {dice_value}\n"
                        f"🎯 Выбор: {game_text}\n\n"
                        f"💰 Выигрыш: {win_amount}⭐\n"
                        f"💎 Баланс: {new_balance}⭐",
                        parse_mode='HTML')
                else:
                    new_losses = user_data['losses_count'] + 1
                    db.update({
                        'losses_count': new_losses,
                        'temp_bet_step': None
                    }, User.user_id == user_id)
                    
                    bot.send_message(call.message.chat.id,
                        f"<b>😞 ПРОИГРЫШ</b>\n\n"
                        f"🎲 Выпало: {dice_value}\n"
                        f"🎯 Выбор: {game_text}\n\n"
                        f"💔 Проигрыш: {amount}⭐\n"
                        f"💎 Баланс: {user_data['balance'] - amount}⭐",
                        parse_mode='HTML')
                        
            except Exception as e:
                print(f"Ошибка confirm_game: {e}")
                bot.send_message(call.message.chat.id, "❌ Ошибка")

        @bot.callback_query_handler(func=lambda call: call.data == "cancel_bet")
        def cancel_game(call):
            try:
                user_id = call.from_user.id
                db.update({'temp_bet_step': None}, User.user_id == user_id)
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="❌ Ставка отменена"
                )
            except Exception as e:
                pass

        # ========== СЛОТЫ ==========
        @bot.message_handler(func=lambda message: message.text == "🎰 Слоты")
        def slots_handler(message):
            try:
                user_id = message.from_user.id
                user_data = db.get(User.user_id == user_id)
                
                markup = types.InlineKeyboardMarkup(row_width=3)
                buttons = [
                    types.InlineKeyboardButton("10⭐", callback_data="slot_10"),
                    types.InlineKeyboardButton("25⭐", callback_data="slot_25"),
                    types.InlineKeyboardButton("50⭐", callback_data="slot_50"),
                    types.InlineKeyboardButton("100⭐", callback_data="slot_100"),
                    types.InlineKeyboardButton("250⭐", callback_data="slot_250"),
                    types.InlineKeyboardButton("500⭐", callback_data="slot_500")
                ]
                markup.add(*buttons)
                
                bot.send_message(message.chat.id,
                    f"<b>🎰 СЛОТЫ</b>\n\n"
                    f"💰 Баланс: {user_data['balance']}⭐\n\n"
                    f"<b>Выберите ставку:</b>\n"
                    f"🎁 Выигрыши: x2, x5, x10\n"
                    f"🎲 3 кубика - комбинации дают множитель!",
                    parse_mode='HTML',
                    reply_markup=markup)
            except Exception as e:
                print(f"Ошибка slots: {e}")

        @bot.callback_query_handler(func=lambda call: call.data.startswith("slot_"))
        def play_slots(call):
            try:
                user_id = call.from_user.id
                bet = int(call.data.split("_")[1])
                username = call.from_user.username or "NoUsername"
                user_data = db.get(User.user_id == user_id)
                
                if user_data['balance'] < bet:
                    bot.answer_callback_query(call.id, "❌ Недостаточно звёзд!")
                    return
                
                # Списываем ставку
                new_balance = user_data['balance'] - bet
                new_slots_played = user_data.get('slots_played', 0) + 1
                
                db.update({
                    'balance': new_balance,
                    'slots_played': new_slots_played,
                    'total_wagered': user_data['total_wagered'] + bet
                }, User.user_id == user_id)
                
                # Сообщение о начале
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"🎰 <b>СЛОТЫ</b>\n\nСтавка: {bet}⭐\n🎲 Крутим барабаны...",
                    parse_mode='HTML'
                )
                
                time.sleep(1)
                
                # Бросаем 3 кубика
                dice1 = bot.send_dice(call.message.chat.id)
                time.sleep(0.5)
                dice2 = bot.send_dice(call.message.chat.id)
                time.sleep(0.5)
                dice3 = bot.send_dice(call.message.chat.id)
                
                val1 = dice1.dice.value
                val2 = dice2.dice.value
                val3 = dice3.dice.value
                
                # Определяем множитель
                multiplier = 1
                if val1 == val2 == val3:
                    # Три одинаковых
                    if val1 == 6:
                        multiplier = 10  # Джекпот
                    elif val1 in [5, 4]:
                        multiplier = 5
                    else:
                        multiplier = 3
                elif val1 == val2 or val2 == val3 or val1 == val3:
                    multiplier = 2
                
                win_amount = bet * multiplier
                
                if multiplier > 1:
                    user_data = db.get(User.user_id == user_id)
                    new_balance = user_data['balance'] + win_amount
                    new_slots_wins = user_data.get('slots_wins', 0) + 1
                    new_total_earned = user_data['total_earned'] + win_amount
                    
                    db.update({
                        'balance': new_balance,
                        'slots_wins': new_slots_wins,
                        'total_earned': new_total_earned
                    }, User.user_id == user_id)
                    
                    # Эмодзи для кубиков
                    emoji_map = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}
                    
                    bot.send_message(call.message.chat.id,
                        f"<b>🎉 ПОБЕДА В СЛОТАХ!</b>\n\n"
                        f"🎲 {emoji_map[val1]} {emoji_map[val2]} {emoji_map[val3]}\n\n"
                        f"⭐ Множитель: <b>x{multiplier}</b>\n"
                        f"💰 Выигрыш: <b>{win_amount}⭐</b>\n"
                        f"💎 Баланс: <b>{new_balance}⭐</b>",
                        parse_mode='HTML')
                else:
                    emoji_map = {1: "1️⃣", 2: "2️⃣", 3: "3️⃣", 4: "4️⃣", 5: "5️⃣", 6: "6️⃣"}
                    
                    bot.send_message(call.message.chat.id,
                        f"<b>😞 ПРОИГРЫШ В СЛОТАХ</b>\n\n"
                        f"🎲 {emoji_map[val1]} {emoji_map[val2]} {emoji_map[val3]}\n\n"
                        f"💔 Проигрыш: {bet}⭐\n"
                        f"💎 Баланс: <b>{user_data['balance'] - bet}⭐</b>",
                        parse_mode='HTML')
                        
            except Exception as e:
                print(f"Ошибка play_slots: {e}")
                bot.send_message(call.message.chat.id, "❌ Ошибка в слотах")

        # ========== ПРОФИЛЬ ==========
        @bot.message_handler(func=lambda message: message.text == "⚡️ Профиль")
        def profile_handler(message):
            try:
                user_id = message.from_user.id
                user_data = db.get(User.user_id == user_id)
                username = message.from_user.username or "NoUsername"
                
                winrate = 0
                if user_data['bets_count'] > 0:
                    winrate = (user_data['wins_count'] / user_data['bets_count']) * 100
                
                slots_winrate = 0
                if user_data.get('slots_played', 0) > 0:
                    slots_winrate = (user_data.get('slots_wins', 0) / user_data['slots_played']) * 100
                
                text = "🎲 <b>📊 ПРОФИЛЬ</b>\n"
                text += "═" * 20 + "\n"
                text += f"🆔 ID: <code>{user_id}</code>\n"
                text += f"👤 Юзер: <code>@{username}</code>\n\n"
                text += "💰 <b>БАЛАНС</b>\n"
                text += f"⭐️ {user_data['balance']} звёзд\n\n"
                text += "🎲 <b>СТАВКИ</b>\n"
                text += f"📊 Всего: {user_data['bets_count']}\n"
                text += f"✅ Побед: {user_data['wins_count']}\n"
                text += f"❌ Поражений: {user_data['losses_count']}\n"
                text += f"📈 Винрейт: {winrate:.1f}%\n"
                text += f"💸 Выиграно: {user_data['total_earned']}⭐\n"
                text += f"🎲 Поставлено: {user_data['total_wagered']}⭐\n\n"
                text += "🎰 <b>СЛОТЫ</b>\n"
                text += f"🎲 Игр: {user_data.get('slots_played', 0)}\n"
                text += f"✅ Побед: {user_data.get('slots_wins', 0)}\n"
                text += f"📈 Винрейт: {slots_winrate:.1f}%\n\n"
                text += f"📅 Рег: {user_data['reg_date']}"
                
                bot.send_message(message.chat.id, text, parse_mode='HTML')
            except Exception as e:
                print(f"Ошибка profile: {e}")
                bot.send_message(message.chat.id, "❌ Ошибка")

        # ========== ПОПОЛНЕНИЕ ==========
        @bot.message_handler(func=lambda message: message.text == "💰 Пополнить")
        def add_stars_handler(message):
            try:
                bot.send_message(message.chat.id,
                               "<b>💰 Пополнение</b>\n\nВведите количество звёзд:",
                               parse_mode='HTML')
                bot.register_next_step_handler(message, process_payment_amount)
            except Exception as e:
                print(f"Ошибка add: {e}")

        def process_payment_amount(message):
            try:
                user_id = message.from_user.id
                amount = int(message.text)
                if amount <= 0:
                    bot.send_message(message.chat.id, "❌ Введите положительное число!")
                    return
                bot.send_invoice(
                    chat_id=message.chat.id,
                    title="⭐️ Пополнение",
                    description=f"Пополнение на {amount} звёзд",
                    invoice_payload=f"payment_{user_id}_{amount}",
                    provider_token="",
                    currency="XTR",
                    prices=[types.LabeledPrice(label="⭐️ Звёзды", amount=amount)]
                )
            except ValueError:
                bot.send_message(message.chat.id, "❌ Введите число!")
            except Exception as e:
                print(f"Ошибка payment: {e}")

        @bot.pre_checkout_query_handler(func=lambda query: True)
        def process_pre_checkout_query(pre_checkout_query):
            try:
                bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
            except Exception as e:
                print(f"Ошибка pre_checkout: {e}")

        @bot.message_handler(content_types=['successful_payment'])
        def process_successful_payment(message):
            try:
                user_id = message.from_user.id
                amount = message.successful_payment.total_amount
                user_data = db.get(User.user_id == user_id)
                new_balance = user_data['balance'] + amount
                db.update({'balance': new_balance}, User.user_id == user_id)
                bot.send_message(message.chat.id, f"<b>✅ Пополнено!</b>\n\n⭐ {amount} звёзд\n💰 Новый баланс: {new_balance}⭐", parse_mode='HTML')
            except Exception as e:
                print(f"Ошибка success: {e}")

        # ========== ВЫВОД ==========
        @bot.message_handler(func=lambda message: message.text == "🎁 Вывести")
        def withdraw_stars_handler(message):
            try:
                user_id = message.from_user.id
                user_data = db.get(User.user_id == user_id)
                balance = user_data['balance']
                
                if balance < 15:
                    bot.send_message(message.chat.id, "❌ Минимум 15 звёзд")
                    return
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                buttons = []
                for amt in [15, 25, 50, 100, 150, 350, 500]:
                    if balance >= amt:
                        buttons.append(types.InlineKeyboardButton(f"{amt}⭐", callback_data=f"withdraw_{amt}"))
                markup.add(*buttons)
                
                bot.send_message(message.chat.id,
                               f"<b>🎁 Вывод</b>\n\n💰 Баланс: {balance}⭐\n\nВыберите сумму:",
                               parse_mode='HTML',
                               reply_markup=markup)
            except Exception as e:
                print(f"Ошибка withdraw: {e}")

        @bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_"))
        def withdraw_amount_choice(call):
            try:
                user_id = call.from_user.id
                count = int(call.data.split("_")[1])
                
                markup = types.InlineKeyboardMarkup()
                markup.add(
                    types.InlineKeyboardButton("✅ Да", callback_data=f"confirm_withdraw_{count}"),
                    types.InlineKeyboardButton("❌ Нет", callback_data="cancel_withdraw")
                )
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"<b>🎁 Подтверждение</b>\n\nВывести {count} звёзд?",
                    parse_mode='HTML',
                    reply_markup=markup
                )
            except Exception as e:
                print(f"Ошибка withdraw_choice: {e}")

        @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_withdraw_"))
        def confirm_withdraw(call):
            try:
                user_id = call.from_user.id
                count = int(call.data.split("_")[2])
                user_data = db.get(User.user_id == user_id)
                username = call.from_user.username or "NoUsername"
                
                if user_data['balance'] < count:
                    bot.answer_callback_query(call.id, "❌ Недостаточно!")
                    return
                
                new_balance = user_data['balance'] - count
                db.update({'balance': new_balance}, User.user_id == user_id)
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"<b>✅ Заявка отправлена!</b>\n\n⭐ {count} звёзд\n⏱ Ожидайте 72 часа",
                    parse_mode='HTML'
                )
                
                # Отправляем админу
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("✅ Выдано", callback_data=f"issued_{user_id}_{count}"))
                
                bot.send_message(
                    ADMIN_CHANNEL_ID,
                    f"<b>📝 НОВАЯ ЗАЯВКА</b>\n\n👤 @{username}\n🆔 {user_id}\n⭐ {count} звёзд",
                    parse_mode='HTML',
                    reply_markup=markup
                )
            except Exception as e:
                print(f"Ошибка confirm_withdraw: {e}")

        @bot.callback_query_handler(func=lambda call: call.data == "cancel_withdraw")
        def cancel_withdraw(call):
            try:
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="❌ Вывод отменён"
                )
            except Exception as e:
                pass

        @bot.callback_query_handler(func=lambda call: call.data.startswith("issued_"))
        def issue_withdraw(call):
            try:
                user_id = int(call.data.split("_")[1])
                count = int(call.data.split("_")[2])
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=call.message.text + "\n\n✅ ВЫДАНО",
                    parse_mode='HTML'
                )
                
                bot.send_message(user_id, f"<b>✅ Заявка на вывод {count}⭐ выполнена!</b>", parse_mode='HTML')
            except Exception as e:
                print(f"Ошибка issued: {e}")

        # ========== КНОПКА СТАВКА ==========
        @bot.message_handler(func=lambda message: message.text == "🎲 Ставка")
        def bet_button_handler(message):
            user_id = message.from_user.id
            user_data = db.get(User.user_id == user_id)
            bot.send_message(message.chat.id,
                           f"<b>🎲 СТАВКА</b>\n\n💰 Баланс: {user_data['balance']}⭐\n\nВведите сумму (мин 5⭐):",
                           parse_mode='HTML')
            bot.register_next_step_handler(message, process_bet_amount)

        return bot

    except Exception as e:
        print(f"Ошибка create_bot: {e}")
        return None

def run_bot():
    while True:
        try:
            delete_webhook()
            bot = create_bot()
            if bot is None:
                raise Exception("Не удалось создать бота")
            
            print("🚀 Бот запущен!")
            backup_database()
            bot.polling(none_stop=True, timeout=60, skip_pending=True)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)

if __name__ == "__main__":
    print("🎲 Бот запускается...")
    run_bot()