import os
import subprocess
import tempfile
import time
from pathlib import Path
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Токен прямо в коде (ВРЕМЕННОЕ РЕШЕНИЕ)
TOKEN = "8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y"

PAWNCC_PATH = "/pawncc.exe"
user_last_message = {}

async def anti_flood(update: Update, context: ContextTypes.DEFAULT_TYPE, cooldown=3):
    user_id = update.effective_user.id
    current_time = time.time()
    
    if user_id in user_last_message:
        if current_time - user_last_message[user_id] < cooldown:
            await update.message.reply_text(f"🚫 {update.effective_user.first_name}, не флуди! Подожди {cooldown} секунд.")
            return True
    
    user_last_message[user_id] = current_time
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    import shutil
    compiler_exists = shutil.which(PAWNCC_PATH) is not None
    
    info_text = (
        "ℹ️ **Информация:**\n\n"
        f"**Компилятор Pawn:** {'✅ Доступен' if compiler_exists else '❌ Не найден'}\n"
        f"**Путь:** `{PAWNCC_PATH}`\n"
        "**Форматы:** .pwn → .amx\n"
        f"**Активных пользователей:** {len(user_last_message)}"
    )
    
    await update.message.reply_text(info_text, parse_mode="Markdown")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if await anti_flood(update, context):
        return
    
    document = update.message.document
    
    if not document.file_name or not document.file_name.lower().endswith('.pwn'):
        await update.message.reply_text(
            "❌ **Ошибка:** Отправьте файл с расширением `.pwn`",
            parse_mode="Markdown"
        )
        return
    
    if document.file_size > 20 * 1024 * 1024:
        await update.message.reply_text(
            f"❌ **Файл слишком большой!**\nМаксимум: 20 MB",
            parse_mode="Markdown"
        )
        return
    
    status_msg = await update.message.reply_text(
        f"🔄 **Компиляция...**\nФайл: `{document.file_name}`",
        parse_mode="Markdown"
    )
    
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        
        try:
            file = await context.bot.get_file(document.file_id)
            pwn_path = work_dir / document.file_name
            await file.download_to_drive(pwn_path)
            
            result = subprocess.run(
                [PAWNCC_PATH, str(pwn_path), '-;+', '-\\+', '-(+', '-r'],
                cwd=str(work_dir),
                capture_output=True,
                text=True,
                timeout=30
            )
            
            amx_path = pwn_path.with_suffix('.amx')
            
            if result.returncode == 0 and amx_path.exists() and amx_path.stat().st_size > 0:
                await status_msg.delete()
                
                with open(amx_path, 'rb') as amx_file:
                    output_name = pwn_path.stem + '.amx'
                    await update.message.reply_document(
                        document=amx_file,
                        filename=output_name,
                        caption=f"✅ **Компиляция успешна!**",
                        parse_mode="Markdown"
                    )
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                if not error_msg or error_msg.strip() == "":
                    error_msg = "Неизвестная ошибка компиляции"
                
                if len(error_msg) > 1500:
                    error_msg = error_msg[:1500] + "\n\n... (обрезано)"
                
                await status_msg.edit_text(
                    f"❌ **Ошибка компиляции:**\n\n```\n{error_msg}\n```",
                    parse_mode="Markdown"
                )
                
        except subprocess.TimeoutExpired:
            await status_msg.edit_text("⏰ **Ошибка:** Превышено время компиляции (30 секунд)", parse_mode="Markdown")
        except FileNotFoundError:
            await status_msg.edit_text(
                f"❌ **Ошибка:** Компилятор не найден!\nПуть: `{PAWNCC_PATH}`",
                parse_mode="Markdown"
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ **Ошибка:** `{str(e)}`", parse_mode="Markdown")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Ошибка: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text("⚠️ Произошла ошибка. Попробуйте позже.")

def main():
    print("🚀 Запуск Pawn Compiler Bot...")
    
    import shutil
    if shutil.which(PAWNCC_PATH):
        print(f"✅ Компилятор найден: {shutil.which(PAWNCC_PATH)}")
    else:
        print(f"⚠️ Компилятор не найден: {PAWNCC_PATH}")
    
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_error_handler(error_handler)
    
    print("✅ Бот успешно запущен!")
    print(f"🤖 Имя бота: @uralpwn_bot")
    
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
