import telebot
import requests
import json

TOKEN = "8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y"

CHANNELS = ["@russiakrmp", "@UralPwn"]

bot = telebot.TeleBot(TOKEN)

def check_sub(user_id):
    for ch in CHANNELS:
        try:
            if bot.get_chat_member(ch, user_id).status in ["left", "kicked"]:
                return False, ch
        except:
            return False, ch
    return True, None

@bot.message_handler(commands=['start'])
def start(m):
    ok, ch = check_sub(m.from_user.id)
    if not ok:
        btn = telebot.types.InlineKeyboardMarkup()
        btn.add(telebot.types.InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{ch[1:]}"))
        btn.add(telebot.types.InlineKeyboardButton("✅ Проверить", callback_data="check"))
        bot.reply_to(m, f"⚠️ Подпишись на {ch}", reply_markup=btn)
        return
    bot.reply_to(m, "✅ Отправь .pwn файл")

@bot.callback_query_handler(func=lambda c: c.data == "check")
def check(c):
    ok, _ = check_sub(c.from_user.id)
    if ok:
        bot.edit_message_text("✅ Доступ открыт!", c.message.chat.id, c.message.message_id)
    else:
        bot.answer_callback_query(c.id, "Подпишись!", True)

@bot.message_handler(content_types=['document'])
def compile(m):
    ok, _ = check_sub(m.from_user.id)
    if not ok:
        bot.reply_to(m, "❌ Подпишись на каналы")
        return
    
    if not m.document.file_name.endswith('.pwn'):
        bot.reply_to(m, "❌ Отправь .pwn файл")
        return
    
    msg = bot.reply_to(m, "⚙️ Компиляция...")
    
    # Скачиваем файл
    file = bot.get_file(m.document.file_id)
    pwn = bot.download_file(file.file_path)
    
    # Отправляем на онлайн компилятор
    try:
        response = requests.post(
            "https://pawn-compiler.kuriwa.workers.dev/compile",
            files={"file": (m.document.file_name, pwn)},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get("success"):
                amx = bytes.fromhex(data["amx"])
                bot.send_document(m.chat.id, (m.document.file_name.replace(".pwn", ".amx"), amx))
                bot.delete_message(m.chat.id, msg.message_id)
            else:
                bot.edit_message_text(f"❌ Ошибка:\n{data.get('error', 'Неизвестно')}", m.chat.id, msg.message_id)
        else:
            bot.edit_message_text("❌ Сервер компиляции недоступен", m.chat.id, msg.message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ Ошибка: {e}", m.chat.id, msg.message_id)

bot.infinity_polling()