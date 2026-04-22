import logging
import asyncio
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# ЗАМЕНИ НА НОВЫЙ ТОКЕН!
TOKEN = "8524888141:AAFNuxrcYSeGqiWUAcWBCUp6abFHshVYBgY"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# База данных для топа (в реальном проекте используй SQLite/PostgreSQL)
stats = {}  # {user_id: {'wins': int, 'name': str}}
games = {}  # {chat_id: {'player1_id': int, 'player1_name': str, 'emoji': str, 'message_id': int, 'start_time': datetime}}

# Доступные игры
GAMES = {
    'dice': {'name': '🎲 Кости', 'emoji': '🎲', 'min': 1, 'max': 6},
    'basketball': {'name': '🏀 Баскетбол', 'emoji': '🏀', 'min': 1, 'max': 5},
    'darts': {'name': '🎯 Дартс', 'emoji': '🎯', 'min': 1, 'max': 6},
    'football': {'name': '⚽ Футбол', 'emoji': '⚽', 'min': 1, 'max': 5}
}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply(
        "🎮 *UralchikGame - игровой бот для бесед*\n\n"
        "📋 *Команды:*\n"
        "/kube - игра в кости 🎲\n"
        "/basketball - баскетбол 🏀\n"
        "/darts - дартс 🎯\n"
        "/football - футбол ⚽\n"
        "/top - топ победителей 🏆\n"
        "/stats - моя статистика 📊\n"
        "/help - справка\n\n"
        "⏱️ На присоединение даётся 10 секунд!",
        parse_mode="Markdown"
    )

def create_game_keyboard(game_emoji: str, game_name: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{game_emoji} Присоединиться к {game_name}", callback_data=f"join_game_{game_emoji}")]
    ])

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

async def start_game(message: types.Message, game_type: str):
    if message.chat.type not in ["group", "supergroup"]:
        await message.reply("❌ Игра работает только в групповых чатах!")
        return
    
    chat_id = message.chat.id
    
    if chat_id in games:
        await message.reply("⚠️ Игра уже создана! Дождитесь окончания.")
        return
    
    game_info = GAMES[game_type]
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"{game_info['emoji']} Присоединиться ({game_info['name']})", callback_data=f"join_game_{game_type}")]
    ])
    
    sent_msg = await message.reply(
        f"{game_info['emoji']} *{message.from_user.first_name}* создал игру *{game_info['name']}*!\n"
        f"⏱️ У вас 10 секунд, чтобы присоединиться!\n\n"
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
    
    # Автоотмена через 10 секунд
    await asyncio.sleep(10)
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
            f"⏰ Время вышло! Игра отменена. Никто не присоединился.",
            parse_mode="Markdown"
        )
    except:
        pass
    del games[chat_id]

@dp.callback_query(F.data.startswith("join_game_"))
async def process_join_game(callback_query: types.CallbackQuery):
    game_type = callback_query.data.replace("join_game_", "")
    chat_id = callback_query.message.chat.id
    joiner_id = callback_query.from_user.id
    joiner_name = callback_query.from_user.first_name
    
    if chat_id not in games:
        await callback_query.answer("❌ Игра уже завершена или время вышло!", show_alert=True)
        await callback_query.message.delete()
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
    
    await bot.send_message(
        chat_id,
        f"{game_info['emoji']} *{player1_name}* vs *{joiner_name}*\n🎮 Игра: {game_info['name']}\nКидаем...",
        parse_mode="Markdown"
    )
    
    # Отправляем игровые кубики
    msg1 = await bot.send_dice(chat_id, emoji=game_info['emoji'])
    msg2 = await bot.send_dice(chat_id, emoji=game_info['emoji'])
    
    score1 = msg1.dice.value
    score2 = msg2.dice.value
    
    # Определяем победителя
    if score1 > score2:
        winner_id = player1_id
        winner_name = player1_name
        result = f"🏆 *Победитель: {player1_name}!* 🏆"
    elif score2 > score1:
        winner_id = joiner_id
        winner_name = joiner_name
        result = f"🏆 *Победитель: {joiner_name}!* 🏆"
    else:
        winner_id = None
        result = "🤝 *Ничья!* 🤝"
    
    # Обновляем статистику
    if winner_id:
        if winner_id not in stats:
            stats[winner_id] = {'wins': 0, 'name': winner_name}
        stats[winner_id]['wins'] += 1
        stats[winner_id]['name'] = winner_name
    
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
    if not stats:
        await message.reply("📊 Пока нет ни одной победы! Сыграйте в игры командой /kube, /basketball, /darts или /football")
        return
    
    sorted_stats = sorted(stats.items(), key=lambda x: x[1]['wins'], reverse=True)[:10]
    
    top_text = "🏆 *Топ победителей UralchikGame:* 🏆\n\n"
    for i, (user_id, data) in enumerate(sorted_stats, 1):
        medal = {1: "🥇", 2: "🥈", 3: "🥉"}.get(i, f"{i}.")
        top_text += f"{medal} {data['name']} — {data['wins']} побед\n"
    
    await message.reply(top_text, parse_mode="Markdown")

@dp.message(Command("stats"))
async def cmd_stats(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.first_name
    
    if user_id not in stats:
        await message.reply(f"📊 {name}, у тебя пока нет побед! Сыграй в любую игру командой /kube, /basketball, /darts или /football")
        return
    
    wins = stats[user_id]['wins']
    await message.reply(f"📊 *Статистика {name}:*\n\n🏆 Побед: *{wins}*\n\nПродолжай в том же духе! 🎮", parse_mode="Markdown")

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
        "2. Второй участник нажимает кнопку (10 секунд!)\n"
        "3. Telegram кидает анимированные мячи/кубики\n"
        "4. У кого больше очков - тот победил!\n"
        "5. Победы сохраняются в топ!",
        parse_mode="Markdown"
    )

async def main():
    print("🤖 Бот UralchikGame запущен!")
    print("🎮 Доступные игры: Кости 🎲, Баскетбол 🏀, Дартс 🎯, Футбол ⚽")
    print("🏆 Включён топ победителей")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
