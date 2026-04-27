import os
import subprocess
import tempfile
import time
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()
TOKEN = os.getenv("8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y")

if not TOKEN:
    print("❌ Ошибка: BOT_TOKEN не найден!")
    exit(1)

PAWNCC_PATH = "pawncc"

# Словарь для отслеживания последних сообщений пользователей (анти-флуд)
user_last_message = {}

async def anti_flood(update: Update, context: ContextTypes.DEFAULT_TYPE, cooldown=3):
    """Простая защита от флуда"""
    user_id = update.effective_user.id
    current_time = time.time()
    
    if user_id in user_last_message:
        if current_time - user_last_message[user_id] < cooldown:
            await update.message.reply_text(f"🚫 {update.effective_user.first_name}, не флуди! Подожди {cooldown} секунд.")
            return True  # True = флудит
    
    user_last_message[user_id] = current_time
    return False  # False = не флудит

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 **Pawn Compiler Bot**\n\n"
        "Отправьте мне `.pwn` файл, и я скомпилирую его в `.amx`\n\n"
        "**Команды:**\n"
        "/start - Запуск бота\n"
        "/help - Помощь\n"
        "/info - Информация",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📚 **Как использовать:**\n\n"
        "1️⃣ Отправьте файл с расширением `.pwn`\n"
        "2️⃣ Бот скомпилирует его\n"
        "3️⃣ Получите готовый `.amx` файл\n\n"
        "⚠️ **Важно:**\n"
        "• Максимальный размер файла: 20 MB\n"
        "• Все include файлы должны быть на сервере",
        parse_mode="Markdown"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /info"""
    # Проверяем наличие компилятора
    import shutil
    compiler_exists = shutil.which(PAWNCC_PATH) is not None
    
    info_text = (
        "ℹ️ **Информация:**\n\n"
        f"**Компилятор Pawn:** {'✅ Доступен' if compiler_exists else '❌ Не найден'}\n"
        f"**Путь:** `{PAWNCC_PATH}`\n"
        "**Форматы:** .pwn → .amx\n"
        f"**Активных пользователей:** {len(user_last_message)}\n\n"
        "**Автор:** @bot_compiler"
    )
    
    await update.message.reply_text(info_text, parse_mode="Markdown")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик файлов"""
    # Проверка на флуд
    if await anti_flood(update, context):
        return
    
    document = update.message.document
    
    # Проверка расширения
    if not document.file_name or not document.file_name.lower().endswith('.pwn'):
        await update.message.reply_text(
            "❌ **Ошибка:** Отправьте файл с расширением `.pwn`\n\n"
            "Пример: `script.pwn`",
            parse_mode="Markdown"
        )
        return
    
    # Проверка размера (20 MB)
    if document.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(
            f"❌ **Файл слишком большой!**\n\n"
            f"Размер: {document.file_size // (1024*1024)} MB\n"
            f"Максимум: 20 MB",
            parse_mode="Markdown"
        )
        return
    
    # Отправляем статус
    status_msg = await update.message.reply_text(
        f"🔄 **Компиляция...**\n\n"
        f"Файл: `{document.file_name}`\n"
        f"Размер: {document.file_size:,} байт\n\n"
        f"⏳ Пожалуйста, подождите...",
        parse_mode="Markdown"
    )
    
    # Временная директория
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        
        try:
            # Скачиваем файл
            file = await context.bot.get_file(document.file_id)
            pwn_path = work_dir / document.file_name
            await file.download_to_drive(pwn_path)
            
            # Компилируем
            result = subprocess.run(
                [PAWNCC_PATH, str(pwn_path), '-;+', '-\\+', '-(+', '-r'],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Ищем .amx файл
            amx_path = pwn_path.with_suffix('.amx')
            
            # Успешная компиляция
            if result.returncode == 0 and amx_path.exists() and amx_path.stat().st_size > 0:
                await status_msg.delete()
                
                with open(amx_path, 'rb') as amx_file:
                    output_name = pwn_path.stem + '.amx'
                    await update.message.reply_document(
                        document=amx_file,
                        filename=output_name,
                        caption=f"✅ **Компиляция успешна!**\n\n"
                               f"Исходник: `{document.file_name}`\n"
                               f"Размер AMX: {amx_path.stat().st_size:,} байт",
                        parse_mode="Markdown"
                    )
            else:
                # Ошибка компиляции
                error_msg = result.stderr if result.stderr else result.stdout
                if not error_msg or error_msg.strip() == "":
                    error_msg = "Неизвестная ошибка компиляции"
                
                # Обрезаем длинные ошибки
                if len(error_msg) > 1500:
                    error_msg = error_msg[:1500] + "\n\n... (сообщение обрезано)"
                
                await status_msg.edit_text(
                    f"❌ **Ошибка компиляции:**\n\n"
                    f"```\n{error_msg}\n```",
                    parse_mode="Markdown"
                )
                
        except subprocess.TimeoutExpired:
            await status_msg.edit_text(
                "⏰ **Ошибка:** Превышено время компиляции (30 секунд)\n\n"
                "Возможно, скрипт слишком сложный или зацикленный.",
                parse_mode="Markdown"
            )
        except FileNotFoundError:
            await status_msg.edit_text(
                f"❌ **Ошибка:** Компилятор не найден!\n\n"
                f"Путь: `{PAWNCC_PATH}`\n\n"
                f"Обратитесь к администратору хостинга для установки Pawn компилятора.",
                parse_mode="Markdown"
            )
        except Exception as e:
            await status_msg.edit_text(
                f"❌ **Непредвиденная ошибка:**\n\n"
                f"```\n{str(e)}\n```",
                parse_mode="Markdown"
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    print(f"Ошибка: {context.error}")
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ **Произошла ошибка**\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode="Markdown"
        )

def main():
    """Запуск бота"""
    print("🚀 Запуск Pawn Compiler Bot...")
    
    # Проверка компилятора
    import shutil
    if shutil.which(PAWNCC_PATH):
        print(f"✅ Компилятор найден: {shutil.which(PAWNCC_PATH)}")
    else:
        print(f"⚠️ Компилятор не найден: {PAWNCC_PATH}")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_error_handler(error_handler)
    
    print("✅ Бот успешно запущен!")
    print("💬 Напишите боту в Telegram: /start")
    
    # Запуск (используем drop_pending_updates для решения конфликта)
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()