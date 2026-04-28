import telebot
import subprocess
import os
import tempfile

TOKEN = "8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y"

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(content_types=['document'])
def compile_pwn(message):
    if not message.document.file_name.endswith('.pwn'):
        bot.reply_to(message, 'Кидай .pwn файл')
        return

    msg = bot.reply_to(message, 'Компиляция...')
    
    with tempfile.TemporaryDirectory() as tmp:
        file_info = bot.get_file(message.document.file_id)
        pwn_content = bot.download_file(file_info.file_path)
        
        pwn_path = os.path.join(tmp, 'script.pwn')
        amx_path = os.path.join(tmp, 'script.amx')
        
        with open(pwn_path, 'wb') as f:
            f.write(pwn_content)
        
        # Путь к компилятору (положи pawncc.exe рядом с bot.py)
        compiler = os.path.join(os.path.dirname(__file__), 'pawncc.exe')
        
        if not os.path.exists(compiler):
            bot.edit_message_text('Скачайте pawncc.exe и положите рядом с ботом', message.chat.id, msg.message_id)
            return
        
        cmd = f'"{compiler}" "{pwn_path}" -o"{amx_path}" -; -('
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if os.path.exists(amx_path) and os.path.getsize(amx_path) > 0:
            with open(amx_path, 'rb') as amx_file:
                bot.send_document(message.chat.id, amx_file)
            bot.delete_message(message.chat.id, msg.message_id)
        else:
            error = process.stderr or process.stdout or 'Ошибка компиляции'
            bot.edit_message_text(f'Ошибка:\n{error[:500]}', message.chat.id, msg.message_id)

print('Бот запущен')
bot.infinity_polling()
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
