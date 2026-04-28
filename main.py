import telebot
import subprocess
import os
import tempfile

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
    ok, need = check_sub(m.from_user.id)
    if not ok:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton("📢 Подписаться", url=f"https://t.me/{need[1:]}" ))
        markup.add(telebot.types.InlineKeyboardButton("✅ Проверить", callback_data="check"))
        bot.reply_to(m, f"⚠️ Подпишись на {need}", reply_markup=markup)
        return
    bot.reply_to(m, "✅ Отправь .pwn файл")

@bot.callback_query_handler(func=lambda c: c.data == "check")
def chk(c):
    ok, _ = check_sub(c.from_user.id)
    if ok:
        bot.edit_message_text("✅ Доступ открыт!", c.message.chat.id, c.message.message_id)
    else:
        bot.answer_callback_query(c.id, "Подпишись сначала!", True)

@bot.message_handler(content_types=['document'])
def comp(m):
    ok, _ = check_sub(m.from_user.id)
    if not ok:
        bot.reply_to(m, "❌ Подпишись на каналы")
        return
    
    if not m.document.file_name.endswith('.pwn'):
        bot.reply_to(m, "❌ Отправь .pwn файл")
        return
    
    msg = bot.reply_to(m, "⚙️ Компиляция...")
    
    with tempfile.TemporaryDirectory() as tmp:
        file = bot.get_file(m.document.file_id)
        pwn = bot.download_file(file.file_path)
        
        pwn_path = os.path.join(tmp, "script.pwn")
        amx_path = os.path.join(tmp, "script.amx")
        
        with open(pwn_path, "wb") as f:
            f.write(pwn)
        
        # Пытаемся найти компилятор
        compilers = ["pawncc", "pawncc.exe", "/usr/bin/pawncc", "/usr/local/bin/pawncc"]
        compiler = None
        
        for c in compilers:
            if os.path.exists(c) or subprocess.run(f"which {c}", shell=True, capture_output=True).returncode == 0:
                compiler = c
                break
        
        if not compiler:
            bot.edit_message_text("❌ Компилятор не найден. Установите pawncc", m.chat.id, msg.message_id)
            return
        
        try:
            subprocess.run(f'"{compiler}" "{pwn_path}" -o"{amx_path}" -; -(', shell=True, timeout=30, capture_output=True)
            
            if os.path.exists(amx_path) and os.path.getsize(amx_path) > 0:
                with open(amx_path, "rb") as f:
                    bot.send_document(m.chat.id, f, caption="✅ Готово!")
                bot.delete_message(m.chat.id, msg.message_id)
            else:
                bot.edit_message_text("❌ Ошибка компиляции", m.chat.id, msg.message_id)
        except subprocess.TimeoutExpired:
            bot.edit_message_text("❌ Таймаут компиляции", m.chat.id, msg.message_id)
        except Exception as e:
            bot.edit_message_text(f"❌ Ошибка: {str(e)[:200]}", m.chat.id, msg.message_id)

print("✅ Бот запущен!")
bot.infinity_polling()