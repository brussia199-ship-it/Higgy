import logging
import asyncio
import mysql.connector
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.filters import Command
import json

# ========== НАСТРОЙКИ ==========
TOKEN = "8600527005:AAFYeIcMzjKfIkn41amkWkJ2_eqIoddiF5E"  # ЗАМЕНИ НА НОВЫЙ ТОКЕН!
ADMIN_ID = 7673683792

# MySQL настройки (замени на свои)
DB_CONFIG = {
    'host': 'localhost',
    'user': 'whg107696_higgy',
    'password': 'Pawlin228',
    'database': 'whg107696_higgy',
    'charset': 'utf8mb4'
}

# ========== ИНИЦИАЛИЗАЦИЯ ==========
logging.basicConfig(level=logging.INFO)
bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словарь для активных игр
games = {}

# Доступные игры
GAMES = {
    'dice': {'name': 'Кости', 'emoji': '🎲', 'min': 1, 'max': 6},
    'basketball': {'name': 'Баскетбол', 'emoji': '🏀', 'min': 1, 'max': 5},
    'darts': {'name': 'Дартс', 'emoji': '🎯', 'min': 1, 'max': 6},
    'football': {'name': 'Футбол', 'emoji': '⚽', 'min': 1, 'max': 5}
}

# ========== РАБОТА С БАЗОЙ ДАННЫХ ==========
def get_db_connection():
    return mysql.connector.connect(**DB_CONFIG)

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Таблица статистики игроков
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS players (
            user_id BIGINT PRIMARY KEY,
            name VARCHAR(255),
            wins INT DEFAULT 0,
            games_played INT DEFAULT 0
        )
    ''')
    
    # Таблица для рассылки (подписанные чаты)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chats (
            chat_id BIGINT PRIMARY KEY,
            chat_name VARCHAR(255),
            is_active BOOLEAN DEFAULT TRUE
        )
    ''')
    
    conn.commit()
    cursor.close()
    conn.close()

def add_win(user_id: int, name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO players (user_id, name, wins, games_played)
        VALUES (%s, %s, 1, 1)
        ON DUPLICATE KEY UPDATE
        wins = wins + 1,
        games_played = games_played + 1,
        name = %s
    ''', (user_id, name, name))
    conn.commit()
    cursor.close()
    conn.close()

def add_loss(user_id: int, name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO players (user_id, name, wins, games_played)
        VALUES (%s, %s, 0, 1)
        ON DUPLICATE KEY UPDATE
        games_played = games_played + 1,
        name = %s
    ''', (user_id, name, name))
    conn.commit()
    cursor.close()
    conn.close()

def get_top(limit: int = 10):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT user_id, name, wins, games_played
        FROM players
        ORDER BY wins DESC
        LIMIT %s
    ''', (limit,))
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

def get_player_stats(user_id: int):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('''
        SELECT user_id, name, wins, games_played
        FROM players
        WHERE user_id = %s
    ''', (user_id,))
    result = cursor.fetchone()
    cursor.close()
    conn.close()
    return result

def reset_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('TRUNCATE TABLE players')
    conn.commit()
    cursor.close()
    conn.close()

def add_win_to_player(user_id: int, name: str, wins_to_add: int):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO players (user_id, name, wins, games_played)
        VALUES (%s, %s, %s, 0)
        ON DUPLICATE KEY UPDATE
        wins = wins + %s,
        name = %s
    ''', (user_id, name, wins_to_add, wins_to_add, name))
    conn.commit()
    cursor.close()
    conn.close()

def add_chat(chat_id: int, chat_name: str):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO chats (chat_id, chat_name, is_active)
        VALUES (%s, %s, TRUE)
        ON DUPLICATE KEY UPDATE
        chat_name = %s, is_active = TRUE
    ''', (chat_id, chat_name, chat_name))
    conn.commit()
    cursor.close()
    conn.close()

def get_all_chats():
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute('SELECT chat_id, chat_name FROM chats WHERE is_active = TRUE')
    result = cursor.fetchall()
    cursor.close()
    conn.close()
    return result

# ========== АДМИНСКИЕ КОМАНДЫ ==========
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if not is_admin(message.from_user.id):
        await message.reply("❌ У вас нет прав администратора!")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Обнулить всю статистику", callback_data="admin_reset_stats")],
        [InlineKeyboardButton(text="➕ Добавить победы игроку", callback_data="admin_add_wins")],
        [InlineKeyboardButton(text="📢 Сделать рассылку", callback_data="admin_mailing")],
        [InlineKeyboardButton(text="📋 Список чатов", callback_data="admin_list_chats")]
    ])
    
    await message.reply("👑 *Панель администратора*\n\nВыберите действие:", parse_mode="Markdown", reply_markup=keyboard)

@dp.callback_query(F.data == "admin_reset_stats")
async def admin_reset_stats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!")
        return
    
    reset_stats()
    await callback.answer("✅ Статистика обнулена!", show_alert=True)
    await callback.message.edit_text("✅ Статистика успешно обнулена!")

@dp.callback_query(F.data == "admin_add_wins")
async def admin_add_wins_prompt(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!")
        return
    
    await callback.message.edit_text(
        "➕ *Добавление побед игроку*\n\n"
        "Отправьте ID пользователя и количество побед в формате:\n"
        "`123456789 5`\n\n"
        "Пример: `7673683792 10`",
        parse_mode="Markdown"
    )
    
    @dp.message(lambda msg: msg.from_user.id == ADMIN_ID and msg.text and len(msg.text.split()) == 2)
    async def add_wins_handler(msg: types.Message):
        try:
            user_id, wins = msg.text.split()
            user_id = int(user_id)
            wins = int(wins)
            
            # Получаем имя пользователя
            try:
                user = await bot.get_chat(user_id)
                name = user.first_name
            except:
                name = f"User_{user_id}"
            
            add_win_to_player(user_id, name, wins)
            await msg.reply(f"✅ Добавлено {wins} побед игроку {name} (ID: {user_id})")
        except Exception as e:
            await msg.reply(f"❌ Ошибка: {e}")
        
        # Удаляем временный хендлер
        dp.message.handlers.pop()

@dp.callback_query(F.data == "admin_mailing")
async def admin_mailing_prompt(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!")
        return
    
    await callback.message.edit_text(
        "📢 *Рассылка*\n\n"
        "Отправьте текст сообщения для рассылки.\n"
        "Сообщение будет отправлено во все чаты и лично каждому игроку.",
        parse_mode="Markdown"
    )
    
    @dp.message(lambda msg: msg.from_user.id == ADMIN_ID and msg.text)
    async def mailing_handler(msg: types.Message):
        text = msg.text
        
        # Отправляем в чаты
        chats = get_all_chats()
        success = 0
        for chat in chats:
            try:
                await bot.send_message(chat['chat_id'], f"📢 *Рассылка от администратора:*\n\n{text}", parse_mode="Markdown")
                success += 1
            except:
                pass
        
        # Отправляем лично игрокам из статистики
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT user_id FROM players')
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        
        user_success = 0
        for (user_id,) in users:
            try:
                await bot.send_message(user_id, f"📢 *Рассылка от администратора:*\n\n{text}", parse_mode="Markdown")
                user_success += 1
            except:
                pass
        
        await msg.reply(f"✅ Рассылка завершена!\n📢 Чатов получено: {success}\n👤 Игроков получено: {user_success}")
        
        # Удаляем временный хендлер
        dp.message.handlers.pop()

@dp.callback_query(F.data == "admin_list_chats")
async def admin_list_chats(callback: types.CallbackQuery):
    if not is_admin(callback.from_user.id):
        await callback.answer("Нет доступа!")
        return
    
    chats = get_all_chats()
    if not chats:
        await callback.message.edit_text("📋 Нет активных чатов")
        return
    
    text = "📋 *Список активных чатов:*\n\n"
    for chat in chats:
        text += f"• {chat['chat_name']} (ID: {chat['chat_id']})\n"
    
    await callback.message.edit_text(text, parse_mode="Markdown")

# ========== ИГРОВЫЕ КОМАНДЫ ==========
async def start_game(message: types.Message, game_type: str):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Игра работает только в групповых чатах!")
        return
    
    chat_id = message.chat.id
    
    if chat_id in games:
        await message.reply("⚠️ Игра уже создана! Дождитесь окончания.")
        return
    
    # Добавляем чат в базу для рассылки
    add_chat(chat_id, message.chat.title or "Беседа")
    
    game_info = GAMES[game_type]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{game_info['emoji']} Присоединиться ({game_info['name']})", callback_data=f"join_game_{game_type}")]
    ])
    
    sent_msg = await message.reply(
        f"{game_info['emoji']} *{message.from_user.first_name}* создал игру *{game_info['name']}*!\n"
        f"⏱️ У вас *5 минут*, чтобы присоединиться!\n\n"
        f"🎮 Нажми на кнопку ниже:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    
    games[chat_id] = {
        'player1_id': message.from_user.id,
        'player1_name': message.from_user.first_name,
        'game_type': game_type,
        'message_id': sent_msg.message_id,
        'start_time': datetime.now()
    }
    
    # Автоотмена через 5 минут
    await asyncio.sleep(300)
    if chat_id in games:
        await cancel_game(chat_id)

async def cancel_game(chat_id: int):
    if chat_id not in games:
        return
    
    game = games[chat_id]
    try:
        await bot.edit_message_reply_markup(chat_id, game['message_id'], reply_markup=None)
        await bot.send_message(
            chat_id,
            f"⏰ Прошло 5 минут! Игра отменена. Никто не присоединился.",
            parse_mode="Markdown"
        )
    except:
        pass
    del games[chat_id]

@dp.message(Command("kube"))
async def cmd_dice(message: types.Message):
    await start_game(message, 'dice')

@dp.message(Command("basketball"))
async def cmd_basketball(message: types.Message):
    await start_game(message, 'basketball')

@dp.message(Command("darts"))
async def cmd_darts(message: types.Message):
    await start_game(message, 'darts')

@dp.message(Command("football"))
async def cmd_football(message: types.Message):
    await start_game(message, 'football')

@dp.callback_query(F.data.startswith("join_game_"))
async def process_join_game(callback_query: types.CallbackQuery):
    game_type = callback_query.data.replace("join_game_", "")
    chat_id = callback_query.message.chat.id
    joiner_id = callback_query.from_user.id
    joiner_name = callback_query.from_user.first_name
    
    if chat_id not in games:
        await callback_query.answer("❌ Игра уже завершена или время вышло!", show_alert=True)
        return
    
    game = games[chat_id]
    player1_id = game['player1_id']
    player1_name = game['player1_name']
    game_type_stored = game['game_type']
    
    if game_type != game_type_stored:
        await callback_query.answer("❌ Неправильная игра!", show_alert=True)
        return
    
    if joiner_id == player1_id:
        await callback_query.answer("❌ Нельзя играть с самим собой!", show_alert=True)
        return
    
    await callback_query.answer(f"✅ Ты присоединился к игре против {player1_name}!")
    
    # Удаляем кнопку
    await bot.edit_message_reply_markup(chat_id, game['message_id'], reply_markup=None)
    
    game_info = GAMES[game_type_stored]
    
    # Отправляем первый кубик (ждём 5 секунд)
    msg = await bot.send_message(chat_id, f"{game_info['emoji']} *{player1_name}* кидает...", parse_mode="Markdown")
    await asyncio.sleep(2)
    dice1 = await bot.send_dice(chat_id, emoji=game_info['emoji'])
    await asyncio.sleep(3)
    
    # Отправляем второй кубик (ждём 5 секунд)
    await bot.edit_message_text(f"{game_info['emoji']} *{joiner_name}* кидает...", chat_id, msg.message_id, parse_mode="Markdown")
    await asyncio.sleep(2)
    dice2 = await bot.send_dice(chat_id, emoji=game_info['emoji'])
    await asyncio.sleep(1)
    
    score1 = dice1.dice.value
    score2 = dice2.dice.value
    
    # Определяем победителя
    if score1 > score2:
        winner_id = player1_id
        winner_name = player1_name
        result = f"🏆 *Победитель: {player1_name}!* 🏆"
        add_win(winner_id, winner_name)
        add_loss(joiner_id, joiner_name)
    elif score2 > score1:
        winner_id = joiner_id
        winner_name = joiner_name
        result = f"🏆 *Победитель: {joiner_name}!* 🏆"
        add_win(winner_id, winner_name)
        add_loss(player1_id, player1_name)
    else:
        result = "🤝 *Ничья!* 🤝"
        add_loss(player1_id, player1_name)
        add_loss(joiner_id, joiner_name)
    
    await bot.delete_message(chat_id, msg.message_id)
    
    await bot.send_message(
        chat_id,
        f"{game_info['emoji']} *Результат {game_info['name']}:*\n\n"
        f"👤 {player1_name}: *{score1}*\n"
        f"👤 {joiner_name}: *{score2}*\n\n"
        f"{result}",
        parse_mode="Markdown"
    )
    
    del games[chat_id]

@dp.message(Command("top"))
async def cmd_top(message: types.Message):
    top_players = get_top(10)
    if not top_players:
        await message.reply("📊 Пока нет ни одной победы! Сыграйте в игры командой /kube, /basketball, /darts или /football")
        return
    
    top_text = "🏆 *Топ победителей UralchikGame:* 🏆\n\n"
    for i, player in enumerate(top_players, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        winrate = (player['wins'] / player['games_played'] * 100) if player['games_played'] > 0 else 0
        top_text += f"{medal} {player['name']} — {player['wins']} побед (📊 {winrate:.1f}%)\n"
    
    await message.reply(top_text, parse_mode="Markdown")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    stats = get_player_stats(message.from_user.id)
    name = message.from_user.first_name
    
    if not stats or stats['games_played'] == 0:
        await message.reply(f"📊 {name}, у тебя пока нет игр! Сыграй в любую игру командой /kube, /basketball, /darts или /football")
        return
    
    winrate = (stats['wins'] / stats['games_played'] * 100) if stats['games_played'] > 0 else 0
    
    await message.reply(
        f"📊 *Статистика {name}:*\n\n"
        f"🏆 Побед: *{stats['wins']}*\n"
        f"🎮 Сыграно игр: *{stats['games_played']}*\n"
        f"📈 Процент побед: *{winrate:.1f}%*\n\n"
        f"Продолжай в том же духе! 🎮",
        parse_mode="Markdown"
    )

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.reply(
        "🎮 *UralchikGame - помощь:*\n\n"
        "📋 *Команды:*\n"
        "/kube - игра в кости 🎲 (1-6)\n"
        "/basketball - баскетбол 🏀 (1-5)\n"
        "/darts - дартс 🎯 (1-6)\n"
        "/football - футбол ⚽ (1-5)\n"
        "/top - топ победителей 🏆\n"
        "/stats - моя статистика 📊\n\n"
        "⏱️ *Как играть:*\n"
        "1. Участник создаёт игру\n"
        "2. Второй участник нажимает кнопку (5 минут!)\n"
        "3. Каждый игрок кидает по 5 секунд\n"
        "4. У кого больше очков - тот победил!\n"
        "5. Победы сохраняются в топ!",
        parse_mode="Markdown"
    )

# ========== ЗАПУСК ==========
async def main():
    init_db()
    print("🤖 Бот UralchikGame запущен!")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print("🎮 Доступные игры: Кости 🎲, Баскетбол 🏀, Дартс 🎯, Футбол ⚽")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
