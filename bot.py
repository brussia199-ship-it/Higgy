import telebot
from telebot import types
from tinydb import TinyDB, Query
import time
import json
import shutil
from datetime import datetime
from config import TOKEN, CHANNEL_ID, CHANNEL_LINK, ADMIN_CHANNEL_ID
import os

# Функция для удаления вебхука
def delete_webhook():
    try:
        bot_temp = telebot.TeleBot(TOKEN)
        bot_temp.remove_webhook()
        time.sleep(1)
        print("✅ Вебхук успешно удалён")
        return True
    except Exception as e:
        print(f"❌ Ошибка при удалении вебхука: {e}")
        return False

# Функция для создания бэкапа базы данных
def backup_database():
    try:
        if os.path.exists('db.json'):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_dir = 'backups'
            if not os.path.exists(backup_dir):
                os.makedirs(backup_dir)
            shutil.copy('db.json', f'{backup_dir}/db_{timestamp}.json')
            # Оставляем только последние 10 бэкапов
            backups = sorted([f for f in os.listdir(backup_dir) if f.startswith('db_')])
            while len(backups) > 10:
                os.remove(f'{backup_dir}/{backups.pop(0)}')
            print(f"✅ Создан бэкап: db_{timestamp}.json")
    except Exception as e:
        print(f"❌ Ошибка создания бэкапа: {e}")

def create_bot():
    global BOT_USERNAME 
    try:
        # Сначала удаляем вебхук
        delete_webhook()
        
        bot = telebot.TeleBot(TOKEN)
        db = TinyDB('db.json')
        User = Query()
        bot_info = bot.get_me()
        BOT_USERNAME = bot_info.username
        print(f"🤖 Бот запущен: @{BOT_USERNAME}")

        # Словарь для хранения временных данных ставки
        temp_bets = {}

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
                        'reg_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        'first_name': first_name,
                        'last_name': last_name
                    })
                    print(f"📝 Новый пользователь: {user_id} (@{username})")

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
                    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
                    btn_profile = types.KeyboardButton("⚡️ Профиль")
                    btn_add_stars = types.KeyboardButton("💰 Пополнить звёзды")
                    btn_withdraw = types.KeyboardButton("🎁 Вывести звёзды")
                    btn_bet = types.KeyboardButton("🎲 Сделать ставку")
                    markup.add(btn_profile, btn_add_stars)
                    markup.add(btn_withdraw, btn_bet)
                    
                    bot.send_message(message.chat.id,
                                   f"<b>👋 Добро пожаловать, @{username}</b>\n\n"
                                   f"📢 Канал со ставками - <a href='{CHANNEL_LINK}'>тык</a>\n\n"
                                   f"🎲 Играй в 'Больше' или 'Меньше' и выигрывай x2!",
                                   parse_mode='HTML',
                                   reply_markup=markup)
            except Exception as e:
                print(f"Ошибка в start_handler: {e}")
                bot.send_message(message.chat.id, "❌ Произошла ошибка, попробуйте ещё раз")

        def process_bet_amount(message):
            try:
                user_id = message.from_user.id
                amount_text = message.text.strip()
                
                # Проверка на число
                if not amount_text.isdigit():
                    bot.send_message(message.chat.id, "❌ Пожалуйста, введите число!")
                    return
                    
                amount = int(amount_text)
                user_data = db.get(User.user_id == user_id)
                
                if amount <= 0:
                    bot.send_message(message.chat.id, "❌ Сумма ставки должна быть больше нуля!")
                    return
                    
                if amount < 5:
                    bot.send_message(message.chat.id, "❌ Минимальная ставка: 5 звёзд!")
                    return
                    
                if amount > user_data['balance']:
                    bot.send_message(message.chat.id, f"❌ Недостаточно звёзд! Ваш баланс: {user_data['balance']} звёзд")
                    return
                
                # Сохраняем сумму ставки во временный словарь
                temp_bets[user_id] = amount
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                btn_more = types.InlineKeyboardButton("🎲 БОЛЬШЕ (4-6)", callback_data=f"game_more")
                btn_less = types.InlineKeyboardButton("🎲 МЕНЬШЕ (1-3)", callback_data=f"game_less")
                markup.add(btn_more, btn_less)
                
                bot.send_message(message.chat.id,
                               f"<b>🎲 Ставка: {amount} звёзд</b>\n\n"
                               f"<b>Выберите исход:</b>\n"
                               f"🔹 БОЛЬШЕ - выпадет 4, 5 или 6\n"
                               f"🔹 МЕНЬШЕ - выпадет 1, 2 или 3",
                               parse_mode='HTML',
                               reply_markup=markup)
            except Exception as e:
                print(f"Ошибка в process_bet_amount: {e}")
                bot.send_message(message.chat.id, "❌ Произошла ошибка при обработке ставки")

        @bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
        def game_choice(call):
            try:
                user_id = call.from_user.id
                game_type = call.data.split("_")[1]  # "more" или "less"
                
                if user_id not in temp_bets:
                    bot.answer_callback_query(call.id, "❌ Ставка не найдена, начните заново")
                    return
                
                amount = temp_bets[user_id]
                
                markup = types.InlineKeyboardMarkup()
                btn_yes = types.InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_{game_type}")
                btn_cancel = types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_game")
                markup.add(btn_yes, btn_cancel)
                
                game_text = "БОЛЬШЕ (4-6)" if game_type == "more" else "МЕНЬШЕ (1-3)"
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"<b>🎲 Подтверждение ставки</b>\n\n"
                         f"💰 Сумма: {amount} звёзд\n"
                         f"🎯 Исход: {game_text}\n\n"
                         f"<b>Подтверждаете?</b>",
                    parse_mode='HTML',
                    reply_markup=markup
                )
            except Exception as e:
                print(f"Ошибка в game_choice: {e}")
                bot.answer_callback_query(call.id, "❌ Произошла ошибка")

        @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_"))
        def confirm_game(call):
            try:
                user_id = call.from_user.id
                game_type = call.data.split("_")[1]  # "more" или "less"
                
                if user_id not in temp_bets:
                    bot.answer_callback_query(call.id, "❌ Ставка не найдена")
                    return
                
                amount = temp_bets.pop(user_id)
                username = call.from_user.username or "NoUsername"
                user_data = db.get(User.user_id == user_id)
                
                # Проверяем баланс ещё раз
                if user_data['balance'] < amount:
                    bot.edit_message_text(
                        chat_id=call.message.chat.id,
                        message_id=call.message.message_id,
                        text="❌ Недостаточно средств для ставки!"
                    )
                    return
                
                # Списываем ставку
                new_balance = user_data['balance'] - amount
                new_bets_count = user_data['bets_count'] + 1
                new_total_wagered = user_data['total_wagered'] + amount
                
                db.update({
                    'balance': new_balance, 
                    'bets_count': new_bets_count,
                    'total_wagered': new_total_wagered
                }, User.user_id == user_id)
                
                # Сообщение о начале игры
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"🎲 <b>Игра началась!</b>\n\n"
                         f"Ставка: {amount} звёзд\n"
                         f"Исход: {'БОЛЬШЕ' if game_type == 'more' else 'МЕНЬШЕ'}\n\n"
                         f"🎲 Бросаем кубик...",
                    parse_mode='HTML'
                )
                
                # Отправляем анимацию кубика
                time.sleep(1)
                dice = bot.send_dice(call.message.chat.id)
                dice_value = dice.dice.value
                
                # Определяем победу
                win = (game_type == "more" and dice_value >= 4) or (game_type == "less" and dice_value <= 3)
                
                game_text = "БОЛЬШЕ (4-6)" if game_type == "more" else "МЕНЬШЕ (1-3)"
                
                if win:
                    win_amount = amount * 2
                    user_data = db.get(User.user_id == user_id)
                    new_balance = user_data['balance'] + win_amount
                    new_total_earned = user_data['total_earned'] + win_amount
                    new_wins = user_data['wins_count'] + 1
                    
                    db.update({
                        'balance': new_balance,
                        'total_earned': new_total_earned,
                        'wins_count': new_wins
                    }, User.user_id == user_id)
                    
                    bot.send_message(
                        call.message.chat.id,
                        f"<b>🎉 ПОБЕДА!</b>\n\n"
                        f"🎲 Выпало значение: <b>{dice_value}</b>\n"
                        f"🎯 Ваш выбор: {game_text}\n\n"
                        f"💰 Вы выиграли: <b>{win_amount} звёзд</b>\n"
                        f"💎 Новый баланс: <b>{new_balance} звёзд</b>",
                        parse_mode='HTML'
                    )
                    
                    # Отправляем в канал
                    try:
                        markup = types.InlineKeyboardMarkup()
                        bet_button = types.InlineKeyboardButton("🎲 Сделать ставку", url=f"https://t.me/{BOT_USERNAME}?start=bet")
                        markup.add(bet_button)
                        
                        bot.send_message(
                            CHANNEL_ID,
                            f"<b>🎉 ПОБЕДА!</b>\n\n"
                            f"👤 Игрок: @{username}\n"
                            f"🎲 Выпало: {dice_value}\n"
                            f"💰 Выигрыш: {win_amount} звёзд",
                            parse_mode='HTML',
                            reply_markup=markup
                        )
                    except:
                        pass
                        
                else:
                    new_losses = user_data['losses_count'] + 1
                    db.update({'losses_count': new_losses}, User.user_id == user_id)
                    
                    bot.send_message(
                        call.message.chat.id,
                        f"<b>😞 ПРОИГРЫШ</b>\n\n"
                        f"🎲 Выпало значение: <b>{dice_value}</b>\n"
                        f"🎯 Ваш выбор: {game_text}\n\n"
                        f"💔 Вы проиграли {amount} звёзд\n"
                        f"💎 Новый баланс: <b>{user_data['balance'] - amount}</b>",
                        parse_mode='HTML'
                    )
                    
                    # Отправляем в канал
                    try:
                        bot.send_message(
                            CHANNEL_ID,
                            f"<b>😞 ПРОИГРЫШ</b>\n\n"
                            f"👤 Игрок: @{username}\n"
                            f"🎲 Выпало: {dice_value}\n"
                            f"💔 Проигрыш: {amount} звёзд",
                            parse_mode='HTML'
                        )
                    except:
                        pass
                        
            except Exception as e:
                print(f"Ошибка в confirm_game: {e}")
                bot.send_message(call.message.chat.id, "❌ Произошла ошибка во время игры")

        @bot.callback_query_handler(func=lambda call: call.data == "cancel_game")
        def cancel_game(call):
            try:
                user_id = call.from_user.id
                if user_id in temp_bets:
                    del temp_bets[user_id]
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text="❌ Ставка отменена"
                )
            except Exception as e:
                pass

        @bot.message_handler(func=lambda message: message.text == "🎲 Сделать ставку")
        def make_bet_handler(message):
            user_id = message.from_user.id
            user_data = db.get(User.user_id == user_id)
            bot.send_message(message.chat.id,
                           f"<b>🎲 Сделать ставку</b>\n\n"
                           f"💰 Ваш баланс: <code>{user_data['balance']} звёзд</code>\n\n"
                           f"<b>Пришлите сумму звёзд для ставки.</b>\n"
                           f"<i>Минимальная ставка: 5 звёзд</i>\n"
                           f"<i>Выигрыш: x2 от ставки</i>",
                           parse_mode='HTML')
            bot.register_next_step_handler(message, process_bet_amount)

        @bot.message_handler(func=lambda message: message.text == "⚡️ Профиль")
        def profile_handler(message):
            try:
                user_id = message.from_user.id
                user_data = db.get(User.user_id == user_id)
                username = message.from_user.username or "NoUsername"
                
                winrate = 0
                if user_data['bets_count'] > 0:
                    winrate = (user_data['wins_count'] / user_data['bets_count']) * 100
                
                text = "🎲 <b>📊 ПРОФИЛЬ</b>\n"
                text += "═" * 20 + "\n"
                text += f"🆔 ID: <code>{user_id}</code>\n"
                text += f"👤 Ник: <code>@{username}</code>\n"
                text += f"💎 Имя: <code>{user_data['first_name']}</code>\n\n"
                text += "💰 <b>БАЛАНС</b>\n"
                text += f"⭐️ Баланс: <code>{user_data['balance']} звёзд</code>\n\n"
                text += "📈 <b>СТАТИСТИКА</b>\n"
                text += f"🎲 Всего ставок: <code>{user_data['bets_count']}</code>\n"
                text += f"✅ Побед: <code>{user_data['wins_count']}</code>\n"
                text += f"❌ Поражений: <code>{user_data['losses_count']}</code>\n"
                text += f"📊 Винрейт: <code>{winrate:.1f}%</code>\n"
                text += f"💸 Выиграно всего: <code>{user_data['total_earned']} звёзд</code>\n"
                text += f"🎲 Поставлено всего: <code>{user_data['total_wagered']} звёзд</code>\n\n"
                text += f"📅 Регистрация: <code>{user_data['reg_date']}</code>"
                
                bot.send_message(message.chat.id, text, parse_mode='HTML')
            except Exception as e:
                print(f"Ошибка в profile_handler: {e}")
                bot.send_message(message.chat.id, "❌ Ошибка при загрузке профиля")

        @bot.message_handler(func=lambda message: message.text == "💰 Пополнить звёзды")
        def add_stars_handler(message):
            try:
                bot.send_message(message.chat.id,
                               "<b>💰 Пополнение баланса</b>\n\n"
                               "Введите количество звёзд для пополнения:\n"
                               "<i>Минимальная сумма: 1 звезда</i>",
                               parse_mode='HTML')
                bot.register_next_step_handler(message, process_payment_amount)
            except Exception as e:
                print(f"Ошибка в add_stars_handler: {e}")

        def process_payment_amount(message):
            try:
                user_id = message.from_user.id
                amount = int(message.text)
                if amount <= 0:
                    bot.send_message(message.chat.id, "❌ Введите положительное число!")
                    return
                bot.send_invoice(
                    chat_id=message.chat.id,
                    title="⭐️ Пополнение звёзд",
                    description=f"Пополнение баланса на {amount} звёзд",
                    invoice_payload=f"payment_{user_id}_{amount}",
                    provider_token="",
                    currency="XTR",
                    prices=[types.LabeledPrice(label="⭐️ Звёзды", amount=amount)]
                )
            except ValueError:
                bot.send_message(message.chat.id, "❌ Введите число!")
            except Exception as e:
                print(f"Ошибка в process_payment_amount: {e}")
                bot.send_message(message.chat.id, "❌ Ошибка при создании платежа")

        @bot.pre_checkout_query_handler(func=lambda query: True)
        def process_pre_checkout_query(pre_checkout_query):
            try:
                bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
                print(f"✅ Платёж одобрен: {pre_checkout_query.id}")
            except Exception as e:
                print(f"Ошибка в pre_checkout: {e}")

        @bot.message_handler(content_types=['successful_payment'])
        def process_successful_payment(message):
            try:
                user_id = message.from_user.id
                amount = message.successful_payment.total_amount
                user_data = db.get(User.user_id == user_id)
                new_balance = user_data['balance'] + amount
                db.update({'balance': new_balance}, User.user_id == user_id)
                bot.send_message(
                    message.chat.id, 
                    f"<b>✅ Пополнение успешно!</b>\n\n"
                    f"⭐️ Зачислено: {amount} звёзд\n"
                    f"💰 Новый баланс: {new_balance} звёзд",
                    parse_mode='HTML'
                )
                print(f"💰 Пользователь {user_id} пополнил {amount} звёзд")
            except Exception as e:
                print(f"Ошибка в successful_payment: {e}")

        @bot.message_handler(func=lambda message: message.text == "🎁 Вывести звёзды")
        def withdraw_stars_handler(message):
            try:
                user_id = message.from_user.id
                user_data = db.get(User.user_id == user_id)
                balance = user_data['balance']
                
                if balance < 15:
                    bot.send_message(message.chat.id, "❌ Минимальная сумма вывода: 15 звёзд")
                    return
                
                markup = types.InlineKeyboardMarkup(row_width=2)
                buttons = []
                withdraw_amounts = [15, 25, 50, 100, 150, 350, 500]
                for amt in withdraw_amounts:
                    if balance >= amt:
                        buttons.append(types.InlineKeyboardButton(f"{amt}⭐️", callback_data=f"withdraw_{amt}"))
                markup.add(*buttons)
                
                bot.send_message(message.chat.id,
                               f"<b>🎁 Вывод звёзд</b>\n\n"
                               f"💰 Баланс: <code>{balance} звёзд</code>\n\n"
                               f"<b>Выберите сумму для вывода:</b>",
                               parse_mode='HTML',
                               reply_markup=markup)
            except Exception as e:
                print(f"Ошибка в withdraw_stars_handler: {e}")
                bot.send_message(message.chat.id, "❌ Произошла ошибка")

        @bot.callback_query_handler(func=lambda call: call.data.startswith("withdraw_"))
        def withdraw_amount_choice(call):
            try:
                user_id = call.from_user.id
                count = int(call.data.split("_")[1])
                user_data = db.get(User.user_id == user_id)
                
                if user_data['balance'] < count:
                    bot.answer_callback_query(call.id, "❌ Недостаточно звёзд!")
                    return
                
                markup = types.InlineKeyboardMarkup()
                btn_yes = types.InlineKeyboardButton("✅ Да", callback_data=f"confirm_withdraw_{count}")
                btn_no = types.InlineKeyboardButton("❌ Отмена", callback_data="cancel_withdraw")
                markup.add(btn_yes, btn_no)
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"<b>🎁 Подтверждение вывода</b>\n\n"
                         f"Вы хотите вывести {count} звёзд?\n"
                         f"<i>Заявка будет обработана в течение 72 часов</i>",
                    parse_mode='HTML',
                    reply_markup=markup
                )
            except Exception as e:
                print(f"Ошибка в withdraw_amount_choice: {e}")

        @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_withdraw_"))
        def confirm_withdraw(call):
            try:
                user_id = call.from_user.id
                count = int(call.data.split("_")[2])
                user_data = db.get(User.user_id == user_id)
                username = call.from_user.username or "NoUsername"
                
                new_balance = user_data['balance'] - count
                db.update({'balance': new_balance}, User.user_id == user_id)
                
                bot.edit_message_text(
                    chat_id=call.message.chat.id,
                    message_id=call.message.message_id,
                    text=f"<b>✅ Заявка на вывод отправлена!</b>\n\n"
                         f"⭐️ Сумма: {count} звёзд\n"
                         f"⏱ Ожидайте обработки в течение 72 часов",
                    parse_mode='HTML'
                )
                
                markup = types.InlineKeyboardMarkup()
                btn_issued = types.InlineKeyboardButton("✅ Выдано", callback_data=f"issued_{user_id}_{count}")
                markup.add(btn_issued)
                
                bot.send_message(
                    ADMIN_CHANNEL_ID,
                    f"<b>📝 НОВАЯ ЗАЯВКА НА ВЫВОД</b>\n\n"
                    f"👤 Пользователь: @{username}\n"
                    f"🆔 ID: {user_id}\n"
                    f"⭐️ Сумма: {count} звёзд",
                    parse_mode='HTML',
                    reply_markup=markup
                )
                print(f"📝 Заявка на вывод: {user_id} - {count} звёзд")
            except Exception as e:
                print(f"Ошибка в confirm_withdraw: {e}")

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
                    text=f"<b>✅ ЗАЯВКА ВЫПОЛНЕНА</b>\n\n"
                         f"👤 ID: {user_id}\n"
                         f"⭐️ Сумма: {count} звёзд\n\n"
                         f"<b>Статус: Выдано ✅</b>",
                    parse_mode='HTML'
                )
                
                bot.send_message(
                    user_id,
                    f"<b>✅ Ваша заявка на вывод {count} звёзд выполнена!</b>\n\n"
                    f"Ожидайте подарок от администратора.",
                    parse_mode='HTML'
                )
                bot.answer_callback_query(call.id, "Заявка отмечена как выполненная")
            except Exception as e:
                print(f"Ошибка в issue_withdraw: {e}")

        # Делаем бэкап каждые 100 сообщений (примерно)
        message_counter = 0
        
        @bot.message_handler(func=lambda message: True)
        def count_messages(message):
            nonlocal message_counter
            message_counter += 1
            if message_counter >= 100:
                message_counter = 0
                backup_database()

        return bot

    except Exception as e:
        print(f"Ошибка в create_bot: {e}")
        return None

def run_bot():
    global BOT_USERNAME  
    while True:
        try:
            # При каждом запуске удаляем вебхук
            delete_webhook()
            
            bot = create_bot()
            if bot is None:
                raise Exception("Не удалось создать бота")
            
            print("🚀 Бот запущен и работает...")
            backup_database()  # Создаём бэкап при старте
            
            # Запускаем polling с явным удалением вебхука
            bot.polling(none_stop=True, timeout=60, skip_pending=True)
            
        except Exception as e:
            print(f"❌ Ошибка: {str(e)}")
            print("🔄 Перезапуск через 5 секунд...")
            time.sleep(5)
            continue

if __name__ == "__main__":
    print("🎲 Бот для ставок 'Больше/Меньше' запускается...")
    run_bot()