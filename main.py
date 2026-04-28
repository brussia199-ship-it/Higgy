import telebot
import subprocess
import os
import uuid
import shutil
import sys
import zipfile
import urllib.request

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y"  # ← ВСТАВЬТЕ ТОКЕН ОТ @BotFather

# Обязательные каналы (проверка подписки)
REQUIRED_CHANNELS = [
    {"username": "@russiakrmp", "url": "https://t.me/russiakrmp"},
    {"username": "@UralPwn", "url": "https://t.me/UralPwn"}
]
# ================================

bot = telebot.TeleBot(BOT_TOKEN)

# Путь к компилятору (встроенный в скрипт)
PAWNCC_EXE = "pawncc.exe"
TEMP_DIR = "temp_compile"
os.makedirs(TEMP_DIR, exist_ok=True)

def download_pawn_compiler():
    """Скачивает компилятор Pawn для Windows (без лишних движений)"""
    print("📥 Скачивание компилятора Pawn...")
    url = "https://github.com/pawn-lang/compiler/releases/download/v3.10.10/pawnc-win32.zip"
    zip_path = "pawnc.zip"
    
    try:
        urllib.request.urlretrieve(url, zip_path)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(".")
        os.chmod(PAWNCC_EXE, 0o755)
        os.remove(zip_path)
        print("✅ Компилятор готов!")
        return True
    except Exception as e:
        print(f"❌ Ошибка скачивания: {e}")
        print("Скачайте компилятор вручную с https://github.com/pawn-lang/compiler/releases")
        return False

def check_subscription(user_id):
    """Проверяет, подписан ли пользователь на все каналы"""
    for channel in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(channel["username"], user_id).status
            if status in ["left", "kicked"]:
                return False, channel["url"]
        except:
            return False, channel["url"]
    return True, None

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    subscribed, missing_url = check_subscription(user_id)
    
    if not subscribed:
        # Формируем кнопки для подписки
        markup = telebot.types.InlineKeyboardMarkup()
        for channel in REQUIRED_CHANNELS:
            markup.add(telebot.types.InlineKeyboardButton(
                text=f"📢 Подписаться на {channel['username']}", 
                url=channel['url']
            ))
        markup.add(telebot.types.InlineKeyboardButton(
            text="✅ Проверить подписку", 
            callback_data="check_sub"
        ))
        
        bot.reply_to(message, 
            "⚠️ *Для использования бота необходимо подписаться на наши каналы:*\n\n"
            + "\n".join([f"• {ch['username']}" for ch in REQUIRED_CHANNELS]),
            parse_mode="Markdown", reply_markup=markup)
        return
    
    bot.reply_to(message, 
        "🤖 *Pawn Compiler Bot*\n\n"
        "📁 Просто отправьте мне файл `.pwn`\n"
        "🔧 Я скомпилирую его в `.amx`\n\n"
        "⚡ Бот работает локально на вашем ПК",
        parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def check_sub_callback(call):
    subscribed, missing_url = check_subscription(call.from_user.id)
    if subscribed:
        bot.edit_message_text(
            "✅ Подписка подтверждена! Теперь отправляйте .pwn файлы",
            call.message.chat.id, call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, f"Подпишитесь на {missing_url}", show_alert=True)

@bot.message_handler(content_types=['document'])
def handle_document(message):
    # Проверка подписки
    subscribed, missing_url = check_subscription(message.from_user.id)
    if not subscribed:
        bot.reply_to(message, f"❌ Подпишитесь на {missing_url} чтобы использовать бота")
        return
    
    if not message.document.file_name.endswith('.pwn'):
        bot.reply_to(message, "❌ Отправьте файл с расширением `.pwn`")
        return
    
    status_msg = bot.reply_to(message, "⚙️ Компиляция...")
    unique_id = str(uuid.uuid4())[:8]
    work_dir = os.path.join(TEMP_DIR, unique_id)
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        pwn_path = os.path.join(work_dir, file_name)
        amx_path = os.path.join(work_dir, file_name.replace('.pwn', '.amx'))
        
        downloaded = bot.download_file(file_info.file_path)
        with open(pwn_path, 'wb') as f:
            f.write(downloaded)
        
        # Компиляция
        cmd = f'"{PAWNCC_EXE}" "{pwn_path}" -o"{amx_path}" -; -('
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        output = process.stdout if process.stdout else process.stderr
        
        if os.path.exists(amx_path) and os.path.getsize(amx_path) > 0:
            with open(amx_path, 'rb') as amx_file:
                bot.send_document(message.chat.id, amx_file, 
                    caption=f"✅ Готово!\n{file_name.replace('.pwn', '.amx')}",
                    reply_to_message_id=message.message_id)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            error_text = (output if output else "Неизвестная ошибка")[:3500]
            bot.edit_message_text(f"❌ Ошибка:\n```\n{error_text}\n```",
                message.chat.id, status_msg.message_id, parse_mode="Markdown")
    except Exception as e:
        bot.edit_message_text(f"⚠️ Ошибка: {str(e)[:200]}", 
            message.chat.id, status_msg.message_id)
    finally:
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

@bot.message_handler(func=lambda m: True)
def unknown(message):
    bot.reply_to(message, "📤 Отправьте мне файл .pwn")

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("=" * 40)
    print("🤖 Pawn Compiler Bot")
    print("=" * 40)
    
    # Скачиваем компилятор если нет
    if not os.path.exists(PAWNCC_EXE):
        if not download_pawn_compiler():
            input("Нажмите Enter для выхода...")
            sys.exit(1)
    
    # Проверка токена
    if BOT_TOKEN == "ВАШ_ТОКЕН_СЮДА":
        print("❌ ОШИБКА: Вставьте токен бота в переменную BOT_TOKEN")
        input("Нажмите Enter для выхода...")
        sys.exit(1)
    
    print(f"✅ Бот запущен! ID: {bot.get_me().username}")
    print("📢 Требуется подписка на:")
    for ch in REQUIRED_CHANNELS:
        print(f"   - {ch['username']}")
    print("=" * 40)
    print("Бот работает! Не закрывайте это окно")
    
    bot.infinity_polling()