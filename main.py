import telebot
import requests

TOKEN = "8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y"
bot = telebot.TeleBot(TOKEN)

CHANNELS = ["@russiakrmp", "@UralPwn"]

def check_sub(user_id):
    for ch in CHANNELS:
        try:
            status = bot.get_chat_member(ch, user_id).status
            if status in ["left", "kicked"]:
                return False, ch
        except:
            return False, ch
    return True, None

@bot.message_handler(commands=['start'])
def start(message):
    ok, need = check_sub(message.from_user.id)
    if not ok:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{need[1:]}"))
        markup.add(telebot.types.InlineKeyboardButton("✅ Проверить", callback_data="check"))
        bot.reply_to(message, f"⚠️ Подпишись: {need}", reply_markup=markup)
        return
    bot.reply_to(message, "✅ Отправь .pwn файл")

@bot.callback_query_handler(func=lambda c: c.data == "check")
def callback(c):
    ok, _ = check_sub(c.from_user.id)
    if ok:
        bot.edit_message_text("✅ Доступ открыт", c.message.chat.id, c.message.message_id)
    else:
        bot.answer_callback_query(c.id, "Подпишись", True)

@bot.message_handler(content_types=['document'])
def compile(message):
    ok, _ = check_sub(message.from_user.id)
    if not ok:
        bot.reply_to(message, "❌ Подпишись на каналы")
        return
    
    if not message.document.file_name.endswith('.pwn'):
        bot.reply_to(message, "❌ Отправь .pwn файл")
        return
    
    msg = bot.reply_to(message, "⚙️ Компиляция...")
    
    file = bot.get_file(message.document.file_id)
    pwn = bot.download_file(file.file_path)
    
    try:
        r = requests.post("https://pawn-compiler-api.herokuapp.com/compile", files={"file": pwn}, timeout=15)
        if r.status_code == 200:
            data = r.json()
            if data.get("success"):
                amx = bytes.fromhex(data["amx_hex"])
                bot.send_document(message.chat.id, (message.document.file_name.replace(".pwn", ".amx"), amx))
                bot.delete_message(message.chat.id, msg.message_id)
            else:
                bot.edit_message_text(f"❌ {data.get('error', 'Ошибка')}", message.chat.id, msg.message_id)
        else:
            bot.edit_message_text("❌ Сервер недоступен", message.chat.id, msg.message_id)
    except:
        bot.edit_message_text("❌ Ошибка связи", message.chat.id, msg.message_id)

print("✅ Бот запущен")
bot.infinity_polling()