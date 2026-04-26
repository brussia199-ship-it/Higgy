import asyncio
from datetime import datetime
from telegram import Update, ChatPermissions
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ⚙️ КОНФИГУРАЦИЯ (только токен)
BOT_TOKEN = "8605102614:AAFf8aTK7e0ei9yxc2lky2bUUIAfdTK8_HY"

# 🔧 НАСТРОЙКИ МОДЕРАЦИИ (можно менять)
ANTI_FLOOD = True          # Защита от флуда
FLOOD_TIME = 3             # секунд между сообщениями
MAX_WARNS = 3              # предупреждений до мута
MUTE_TIME = 5              # минут мута
DELETE_BAD_WORDS = True    # удалять сообщения с запрещёнными словами
FORBIDDEN_WORDS = ["хуй", "пизда", "бля", "сука", "редиска"]  # пример

# 📊 Временное хранилище (при перезапуске сбрасывается)
user_warns = {}      # {chat_id: {user_id: warns_count}}
user_last_msg = {}   # {chat_id: {user_id: timestamp}}

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_warns(chat_id, user_id):
    return user_warns.get(chat_id, {}).get(user_id, 0)

def add_warn(chat_id, user_id):
    if chat_id not in user_warns:
        user_warns[chat_id] = {}
    user_warns[chat_id][user_id] = user_warns[chat_id].get(user_id, 0) + 1
    return user_warns[chat_id][user_id]

def reset_warns(chat_id, user_id):
    if chat_id in user_warns and user_id in user_warns[chat_id]:
        user_warns[chat_id][user_id] = 0

async def is_chat_admin(update: Update, user_id: int) -> bool:
    """Проверяет, является ли пользователь админом в этом чате"""
    try:
        chat_member = await update.effective_chat.get_member(user_id)
        return chat_member.status in ['administrator', 'creator']
    except:
        return False

async def mute_user(chat, user_id, minutes, reason=""):
    """Замутить пользователя на N минут"""
    until_date = asyncio.get_event_loop().time() + minutes * 60
    await chat.restrict_member(
        user_id=user_id,
        permissions=ChatPermissions(can_send_messages=False),
        until_date=until_date
    )
    if reason:
        await chat.send_message(f"🔇 Пользователь замучен на {minutes} мин. Причина: {reason}")

async def unmute_user(chat, user_id):
    """Размутить пользователя"""
    await chat.restrict_member(
        user_id=user_id,
        permissions=ChatPermissions(
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True
        )
    )

# ==================== КОМАНДЫ ДЛЯ АДМИНОВ ====================
async def mute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/mute @username [минут] - замутить пользователя"""
    if not await is_chat_admin(update, update.effective_user.id):
        await update.message.reply_text("⛔ Только администраторы чата")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: /mute @username [минут]")
        return
    
    duration = 5
    if len(context.args) > 1 and context.args[1].isdigit():
        duration = int(context.args[1])
    
    try:
        username = context.args[0].replace('@', '')
        users = await update.effective_chat.get_members(filter=username)
        if not users:
            await update.message.reply_text("❌ Пользователь не найден")
            return
        target = users[0].user
    except:
        await update.message.reply_text("❌ Не удалось найти пользователя")
        return
    
    await mute_user(update.effective_chat, target.id, duration, f"команда /mute от {update.effective_user.first_name}")
    await update.message.reply_text(f"🔇 {target.first_name} замучен на {duration} минут")

async def unmute(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/unmute @username - размутить"""
    if not await is_chat_admin(update, update.effective_user.id):
        await update.message.reply_text("⛔ Только администраторы")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: /unmute @username")
        return
    
    try:
        username = context.args[0].replace('@', '')
        users = await update.effective_chat.get_members(filter=username)
        target = users[0].user
    except:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    await unmute_user(update.effective_chat, target.id)
    await update.message.reply_text(f"✅ {target.first_name} размучен")

async def warn(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/warn @username - выдать предупреждение"""
    if not await is_chat_admin(update, update.effective_user.id):
        await update.message.reply_text("⛔ Только администраторы")
        return
    
    if not context.args:
        await update.message.reply_text("❌ Использование: /warn @username")
        return
    
    try:
        username = context.args[0].replace('@', '')
        users = await update.effective_chat.get_members(filter=username)
        target = users[0].user
    except:
        await update.message.reply_text("❌ Пользователь не найден")
        return
    
    chat_id = update.effective_chat.id
    warns = add_warn(chat_id, target.id)
    
    if warns >= MAX_WARNS:
        await mute_user(update.effective_chat, target.id, MUTE_TIME, f"{MAX_WARNS} предупреждений")
        await update.message.reply_text(f"⚠️ {target.first_name} получил {warns}/{MAX_WARNS} предупреждений и замучен на {MUTE_TIME} минут")
        reset_warns(chat_id, target.id)
    else:
        await update.message.reply_text(f"⚠️ {target.first_name} | Предупреждение {warns}/{MAX_WARNS}")

async def warns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/warns [@username] - показать предупреждения"""
    target_id = update.effective_user.id
    target_name = "вас"
    
    if context.args and await is_chat_admin(update, update.effective_user.id):
        try:
            username = context.args[0].replace('@', '')
            users = await update.effective_chat.get_members(filter=username)
            target_id = users[0].user.id
            target_name = users[0].user.first_name
        except:
            pass
    
    warns_count = get_warns(update.effective_chat.id, target_id)
    await update.message.reply_text(f"📊 У {target_name} {warns_count}/{MAX_WARNS} предупреждений")

# ==================== ОБРАБОТЧИКИ СООБЩЕНИЙ ====================
async def anti_flood(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка на флуд"""
    if not ANTI_FLOOD:
        return True
    
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    now = datetime.now().timestamp()
    
    if chat_id not in user_last_msg:
        user_last_msg[chat_id] = {}
    
    last_time = user_last_msg[chat_id].get(user_id, 0)
    
    if now - last_time < FLOOD_TIME:
        await update.message.delete()
        await update.effective_chat.send_message(f"🚫 {update.effective_user.first_name}, не флуди!", delete_in_secs=5)
        return False
    
    user_last_msg[chat_id][user_id] = now
    return True

async def bad_words_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фильтр запрещённых слов"""
    if not DELETE_BAD_WORDS:
        return True
    
    text = update.message.text.lower()
    for word in FORBIDDEN_WORDS:
        if word in text:
            await update.message.delete()
            await update.effective_chat.send_message(
                f"🤬 {update.effective_user.first_name}, ваше сообщение удалено (запрещённое слово)",
                delete_in_secs=5
            )
            return False
    return True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Основной обработчик сообщений"""
    # Не проверяем сообщения от ботов
    if update.effective_user.is_bot:
        return
    
    # Админы чата могут писать что угодно
    if await is_chat_admin(update, update.effective_user.id):
        return
    
    # Проверка на флуд
    if not await anti_flood(update, context):
        return
    
    # Фильтр мата
    if not await bad_words_filter(update, context):
        return

# ==================== ЗАПУСК БОТА ====================
async def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Команды
    app.add_handler(CommandHandler("mute", mute))
    app.add_handler(CommandHandler("unmute", unmute))
    app.add_handler(CommandHandler("warn", warn))
    app.add_handler(CommandHandler("warns", warns))
    
    # Обработка сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Инфо при старте
    print("✅ Бот запущен! Добавьте его в любую группу и сделайте администратором.")
    print("📌 Доступные команды: /mute, /unmute, /warn, /warns")
    
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())