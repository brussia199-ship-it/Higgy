import telebot
import subprocess
import os
import uuid
import shutil
import time

# ===== НАСТРОЙКИ =====
BOT_TOKEN = "8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y"  # Вставьте токен от @BotFather

# На BotHost сервер Linux, поэтому используем Linux-компилятор
# Путь к компилятору (стандартный путь на многих хостингах)
PAWNCC_PATH = "./pawncc"  # или "/usr/local/bin/pawncc"

# Если компилятора нет, скачаем автоматически при первом запуске
AUTO_DOWNLOAD_COMPILER = True

TEMP_DIR = "app/temp_compile/"
os.makedirs(TEMP_DIR, exist_ok=True)

bot = telebot.TeleBot(BOT_TOKEN)

def download_compiler():
    """Автоматически скачивает компилятор Pawn для Linux"""
    print("📥 Скачивание компилятора Pawn...")
    os.system("wget -O pawn.zip https://github.com/compuphase/pawn-sdk/raw/master/bin/pawncc-linux.zip")
    os.system("unzip -o pawn.zip")
    os.system("chmod +x pawncc")
    os.system("rm pawn.zip")
    print("✅ Компилятор установлен")

def compile_pawn(pwn_path, amx_path):
    """Запускает компиляцию и возвращает (успех, вывод/ошибки)"""
    try:
        # Команда для Linux компилятора
        cmd = f'"{PAWNCC_PATH}" "{pwn_path}" -o"{amx_path}" -; -('
        
        process = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        # Компилятор Pawn выводит результат в stdout
        output = process.stdout if process.stdout else process.stderr
        
        # Проверяем наличие успешного AMX файла
        if os.path.exists(amx_path) and os.path.getsize(amx_path) > 0:
            # Ищем предупреждения (warning) в выводе
            warnings = [line for line in output.split('\n') if 'warning' in line.lower()]
            if warnings:
                output = f"⚠️ Есть предупреждения, но файл создан:\n{output}"
            return True, output
        else:
            return False, output if output else "Неизвестная ошибка компиляции"
            
    except subprocess.TimeoutExpired:
        return False, "Превышено время компиляции (30 сек)"
    except Exception as e:
        return False, str(e)

@bot.message_handler(commands=['start'])
def start_command(message):
    bot.reply_to(message, 
        "🤖 *Pawn Compiler Bot*\n\n"
        "Просто отправьте мне файл `.pwn`\n"
        "Я скомпилирую его и пришлю `.amx`\n\n"
        "⚡ Работает на BotHost",
        parse_mode="Markdown"
    )

@bot.message_handler(content_types=['document'])
def handle_document(message):
    # Проверяем расширение
    if not message.document.file_name.endswith('.pwn'):
        bot.reply_to(message, "❌ Отправьте файл с расширением `.pwn`")
        return
    
    # Статус: компилируем
    status_msg = bot.reply_to(message, "⚙️ Компиляция...")
    
    unique_id = str(uuid.uuid4())[:8]
    work_dir = os.path.join(TEMP_DIR, unique_id)
    os.makedirs(work_dir, exist_ok=True)
    
    try:
        # Скачиваем файл
        file_info = bot.get_file(message.document.file_id)
        file_name = message.document.file_name
        pwn_path = os.path.join(work_dir, file_name)
        amx_path = os.path.join(work_dir, file_name.replace('.pwn', '.amx'))
        
        downloaded = bot.download_file(file_info.file_path)
        with open(pwn_path, 'wb') as f:
            f.write(downloaded)
        
        # Компилируем
        success, output = compile_pawn(pwn_path, amx_path)
        
        if success and os.path.exists(amx_path):
            # Отправляем AMX файл
            with open(amx_path, 'rb') as amx_file:
                bot.send_document(
                    message.chat.id, 
                    amx_file,
                    caption=f"✅ Компиляция успешна!\nФайл: {file_name.replace('.pwn', '.amx')}",
                    reply_to_message_id=message.message_id
                )
            # Удаляем статусное сообщение
            bot.delete_message(message.chat.id, status_msg.message_id)
        else:
            # Отправляем ошибки
            error_text = output[:3500]  # Telegram лимит
            bot.edit_message_text(
                f"❌ Ошибка компиляции:\n```\n{error_text}\n```",
                message.chat.id,
                status_msg.message_id,
                parse_mode="Markdown"
            )
            
    except Exception as e:
        bot.edit_message_text(
            f"⚠️ Ошибка: {str(e)[:200]}",
            message.chat.id,
            status_msg.message_id
        )
    finally:
        # Очищаем временные файлы
        if os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)

@bot.message_handler(func=lambda m: True)
def unknown_message(message):
    bot.reply_to(message, "📤 Отправьте мне файл .pwn")

# Запуск
if __name__ == "__main__":
    # Проверяем наличие компилятора
    if AUTO_DOWNLOAD_COMPILER and not os.path.exists(PAWNCC_PATH):
        download_compiler()
    
    if not os.path.exists(PAWNCC_PATH):
        print(f"❌ Компилятор не найден по пути: {PAWNCC_PATH}")
        print("Установите компилятор вручную или исправьте путь")
        exit(1)
    
    print("✅ Бот запущен на BotHost!")
    print(f"Компилятор: {PAWNCC_PATH}")
    bot.infinity_polling()