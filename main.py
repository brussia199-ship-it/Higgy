import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command

# Токен бота (замени на свой)
TOKEN = "8524888141:AAFNuxrcYSeGqiWUAcWBCUp6abFHshVYBgY"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Словарь для хранения ожидающих игроков
pending_games = {}

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply(
        "🎲 Привет! Я бот UralchikGame\n"
        "Используй команду /kube чтобы сыграть в кости с другим игроком."
    )

@dp.message(Command("kube"))
async def cmd_kube(message: types.Message):
    chat_id = message.chat.id
    
    if chat_id in pending_games:
        await message.reply("⚠️ Игра уже создана! Дождитесь, пока кто-то присоединится.")
        return
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎲 Присоединиться к игре", callback_data="join_game")]
    ])
    
    sent_msg = await message.reply(
        f"🎲 {message.from_user.first_name} создал игру в кости!\n"
        f"Нажми на кнопку, чтобы присоединиться.",
        reply_markup=keyboard
    )
    
    pending_games[chat_id] = {
        'player1_id': message.from_user.id,
        'player1_name': message.from_user.first_name,
        'message_id': sent_msg.message_id
    }

@dp.callback_query(F.data == "join_game")
async def process_join_game(callback_query: types.CallbackQuery):
    chat_id = callback_query.message.chat.id
    joiner_id = callback_query.from_user.id
    joiner_name = callback_query.from_user.first_name
    
    if chat_id not in pending_games:
        await callback_query.answer("❌ Игра уже завершена!", show_alert=True)
        await callback_query.message.delete()
        return
    
    game = pending_games[chat_id]
    player1_id = game['player1_id']
    player1_name = game['player1_name']
    
    if joiner_id == player1_id:
        await callback_query.answer("❌ Нельзя играть с самим собой!", show_alert=True)
        return
    
    await callback_query.answer(f"✅ Ты присоединился к игре против {player1_name}!")
    
    # Удаляем кнопку
    await bot.edit_message_reply_markup(chat_id, game['message_id'], reply_markup=None)
    
    # Отправляем сообщение о начале игры
    game_msg = await bot.send_message(
        chat_id,
        f"🎲 *{player1_name} vs {joiner_name}*\nКидаем кубики...",
        parse_mode="Markdown"
    )
    
    # Отправляем встроенные кубики Telegram
    dice_msg1 = await bot.send_dice(chat_id, emoji="🎲")
    dice_msg2 = await bot.send_dice(chat_id, emoji="🎲")
    
    # Получаем значения кубиков (1-6)
    player1_roll = dice_msg1.dice.value
    player2_roll = dice_msg2.dice.value
    
    # Эмодзи для красивого отображения
    dice_emojis = {1: "⚀", 2: "⚁", 3: "⚂", 4: "⚃", 5: "⚄", 6: "⚅"}
    
    # Формируем результат
    result_text = (
        f"🎲 *Результат:*\n\n"
        f"👤 {player1_name}: {dice_emojis[player1_roll]} {player1_roll}\n"
        f"👤 {joiner_name}: {dice_emojis[player2_roll]} {player2_roll}\n\n"
    )
    
    if player1_roll > player2_roll:
        result_text += f"🏆 *Победитель: {player1_name}!* 🏆"
    elif player2_roll > player1_roll:
        result_text += f"🏆 *Победитель: {joiner_name}!* 🏆"
    else:
        result_text += "🤝 *Ничья!* 🤝"
    
    await bot.send_message(chat_id, result_text, parse_mode="Markdown")
    
    # Удаляем временное сообщение
    await bot.delete_message(chat_id, game_msg.message_id)
    
    del pending_games[chat_id]

@dp.message(Command("help"))
async def cmd_help(message: types.Message):
    await message.reply(
        "🎮 *UralchikGame - команды:*\n\n"
        "/kube — создать игру в кости\n"
        "/help — справка\n"
        "/start — приветствие\n\n"
        "🎲 Игроки кидают встроенные Telegram-кубики, у кого больше — тот победил!",
        parse_mode="Markdown"
    )

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
