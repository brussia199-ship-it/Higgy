import telebot
import subprocess
import os
import uuid
import shutil
import urllib.request
import zipfile
import sys

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y"  # ← ВСТАВЬТЕ ТОКЕН

# Обязательные каналы
REQUIRED_CHANNELS = [
    {"username": "@russiakrmp", "url": "https://t.me/russiakrmp"},
    {"username": "@UralPwn", "url": "https://t.me/UralPwn"}
]
# ================================

bot = telebot.TeleBot(BOT_TOKEN)
TEMP_DIR = "temp_compile"
os.makedirs(TEMP_DIR, exist_ok=True)

# Пытаемся найти компилятор в разных местах
POSSIBLE_PATHS = [
    "pawncc",
    "pawncc.exe",
    "./pawncc",
    "/usr/local/bin/pawncc",
    "/usr/bin/pawncc"
]

PAWNCC_PATH = None
for path in POSSIBLE_PATHS:
    if os.path.exists(path):
        PAWNCC_PATH = path
        break

def download_compiler_linux():
    """Скачивает компилятор для Linux (рабочая ссылка)"""
    print("📥 Скачивание компилятора Pawn для Linux...")
    
    # Альтернативные рабочие ссылки
    urls = [
        "https://github.com/pawn-lang/compiler/releases/download/v3.10.10/pawnc-linux-x86_64.tar.gz",
        "https://www.compuphase.com/pawn/pawnc-linux-x86_64.tar.gz",
        "https://raw.githubusercontent.com/pawn-lang/compiler/master/bin/pawncc"
    ]
    
    for url in urls:
        try:
            print(f"Пробуем: {url}")
            if url.endswith(".tar.gz"):
                urllib.request.urlretrieve(url, "pawnc.tar.gz")
                os.system("tar -xzf pawnc.tar.gz")
                os.system("chmod +x pawncc")
                os.remove("pawnc.tar.gz")
            else:
                urllib.request.urlretrieve(url, "pawncc")
                os.system("chmod +x pawncc")
            
            if os.path.exists("pawncc"):
                print("✅ Компилятор успешно установлен!")
                return True
        except Exception as e:
            print(f"❌ Не удалось: {e}")
            continue
    
    return False

def download_compiler_windows():
    """Скачивает компилятор для Windows"""
    print("📥 Скачивание компилятора Pawn для Windows...")
    url = "https://github.com/pawn-lang/compiler/releases/download/v3.10.10/pawnc-win32.zip"
    
    try:
        urllib.request.urlretrieve(url, "pawnc.zip")
        with zipfile.ZipFile("pawnc.zip", 'r') as zip_ref:
            zip_ref.extractall(".")
        os.remove("pawnc.zip")
        print("✅ Компилятор успешно установлен!")
        return True
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

def setup_compiler():
    """Автоматически настраивает компилятор"""
    global PAWNCC_PATH
    
    # Проверяем есть ли уже
    if PAWNCC_PATH and os.path.exists(PAWNCC_PATH):
        print(f"✅ Компилятор найден: {PAWNCC_PATH}")
        return True
    
    # Определяем ОС и скачиваем
    if sys.platform == "win32":
        if download_compiler_windows():
            PAWNCC_PATH = "pawncc.exe"
            return True
    else:  # Linux/Mac
        if download_compiler_linux():
            PAWNCC_PATH = "./pawncc"
            return True
    
    print("❌ Не удалось установить компилятор")
    return False

def check_subscription(user_id):
    """Проверяет подписку на каналы"""
    for channel in REQUIRED_CHANNELS:
        try:
            chat_member = bot.get_chat_member(channel["username"], user_id)
            if chat_member.status in ["left", "kicked"]:
                return False, channel["url"]
        except Exception as e:
            print(f"Ошибка проверки {channel['username']}: {e}")
            return False, channel["url"]
    return True, None

@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    subscribed, missing_url = check_subscription(user_id)
    
    if not subscribed:
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
            "⚠️ *Для использования бота подпишитесь на каналы:*\n\n" +
            "\n".join([f"• {ch['username']}" for ch in REQUIRED_CHANNELS]),
            parse_mode="Markdown", reply_markup=markup)
        return
    
    bot.reply_to(message, 
        "🤖 *Pawn Compiler Bot*\n\n"
        "📁 Отправьте мне файл `.pwn`\n"
        "🔧 Я скомпилирую его в `.amx`\n\n"
        "⚡ Бот работает!",
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
        bot.reply_to(message, f"❌ Подпишитесь на {missing_url}")
        return
    
    if not message.document.file_name.endswith('.pwn'):
        bot.reply_to(message, "❌ Отправьте файл .pwn")
        return
    
    if not PAWNCC_PATH or not os.path.exists(PAWNCC_PATH):
        bot.reply_to(message, "❌ Компилятор не найден. Обратитесь к администратору.")
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
        cmd = f'"{PAWNCC_PATH}" "{pwn_path}" -o"{amx_path}" -; -('
        process = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        
        if os.path.exists(amx_path) and os.path.getsize(amx_path) > 0:
            with open(amx_path, 'rb') as amx_file:
                bot.send_document(message.chat.id, amx_file,
                    caption=f"✅ Готово!\n{file_name.replace('.pwn', '.amx')}",
                    reply_to_message_id=message.message_id)
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            output = process.stdout if process.stdout else process.stderr
            error_text = (output if output else "Ошибка компиляции")[:3500]
            bot.edit_message_text(f"❌ Ошибка:\n```\n{error_text}\n```",
                message.chat.id, status_msg.message_id, parse_mode="Markdown")
            
    except subprocess.TimeoutExpired:
        bot.edit_message_text("⏱ Превышено время компиляции (30 сек)",
            message.chat.id, status_msg.message_id)
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
    print("=" * 50)
    print("🤖 Pawn Compiler Bot v2.0")
    print("=" * 50)
    
    # Проверка токена
    if BOT_TOKEN == "ВАШ_ТОКЕН_СЮДА":
        print("❌ ОШИБКА: Вставьте токен бота!")
        print("Получите токен у @BotFather")
        sys.exit(1)
    
    # Настройка компилятора
    print("🔧 Проверка компилятора...")
    if not setup_compiler():
        print("❌ КРИТИЧЕСКАЯ ОШИБКА: Не удалось установить компилятор")
        print("Обратитесь к администратору хостинга для установки pawncc")
        sys.exit(1)
    
    print(f"✅ Компилятор: {PAWNCC_PATH}")
    print(f"✅ Бот запущен: @{bot.get_me().username}")
    print("📢 Требуется подписка на каналы")
    print("=" * 50)
    print("Бот работает! Нажмите Ctrl+C для остановки")
    
    # Запуск бота
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print("\n👋 Бот остановлен")
    except Exception as e:
        print(f"❌ Ошибка: {e}")