import os
import subprocess
import tempfile
import shutil
import logging
import asyncio
from pathlib import Path
from dotenv import load_dotenv
from telegram import Update, Document
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# Загружаем токен
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise ValueError("BOT_TOKEN not found! Please check .env file")

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Настройки компилятора Pawn
# Укажите полный путь к pawncc, если он не в PATH
PAWNCC_PATH = "pawncc"  # или r"C:\Program Files\pawno\pawncc.exe" для Windows

# Дополнительные флаги компиляции
COMPILE_FLAGS = ['-;+', '-\\+', '-(+', '-d0', '-r']

# Максимальный размер файла (20 MB - лимит Telegram)
MAX_FILE_SIZE = 20 * 1024 * 1024

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🤖 **Pawn Compiler Bot**\n\n"
        "Отправьте мне `.pwn` файл, и я скомпилирую его в `.amx`\n\n"
        "**Как использовать:**\n"
        "1. Отправьте файл с расширением `.pwn`\n"
        "2. Дождитесь компиляции\n"
        "3. Получите готовый `.amx` файл\n\n"
        "📖 **Доступные команды:**\n"
        "/start - Показать это сообщение\n"
        "/help - Получить справку\n"
        "/info - Информация о боте",
        parse_mode="Markdown"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    await update.message.reply_text(
        "📚 **Справка по использованию:**\n\n"
        "**1. Отправка файла:**\n"
        "Просто отправьте файл с расширением `.pwn` в чат\n\n"
        "**2. Процесс компиляции:**\n"
        "Бот автоматически обнаружит файл и запустит компиляцию\n\n"
        "**3. Результат:**\n"
        "• При успехе - получите `.amx` файл\n"
        "• При ошибке - получите сообщение об ошибке\n\n"
        "**4. Ограничения:**\n"
        f"• Максимальный размер файла: {MAX_FILE_SIZE // (1024*1024)} MB\n"
        "• Время компиляции: до 30 секунд\n\n"
        "**5. Важно:**\n"
        "Все необходимые `.inc` файлы должны быть установлены на сервере!",
        parse_mode="Markdown"
    )

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /info"""
    # Проверяем наличие компилятора
    compiler_exists = shutil.which(PAWNCC_PATH) is not None
    
    info_text = (
        "ℹ️ **Информация о боте:**\n\n"
        f"**Версия:** 1.0.0\n"
        f"**Компилятор Pawn:** {'✅ Доступен' if compiler_exists else '❌ Не найден'}\n"
        f"**Путь к компилятору:** `{PAWNCC_PATH}`\n\n"
        "**Поддерживаемые форматы:**\n"
        "• Вход: `.pwn`\n"
        "• Выход: `.amx`\n\n"
        "**Автор:** @your_username"
    )
    
    await update.message.reply_text(info_text, parse_mode="Markdown")
    
    if not compiler_exists:
        await update.message.reply_text(
            "⚠️ **Внимание:** Компилятор Pawn не найден!\n\n"
            "Убедитесь, что:\n"
            "1. Pawn компилятор установлен\n"
            "2. Путь к нему указан корректно в переменной `PAWNCC_PATH`\n"
            "3. Компилятор есть в PATH системы",
            parse_mode="Markdown"
        )

async def compile_pawn(pwn_path: Path, work_dir: Path) -> tuple[bool, str, Path | None]:
    """
    Компилирует .pwn файл в .amx
    
    Returns:
        tuple: (success, output_message, amx_path_or_none)
    """
    try:
        # Подготовка команды
        cmd = [PAWNCC_PATH, str(pwn_path)] + COMPILE_FLAGS
        
        logger.info(f"Running: {' '.join(cmd)}")
        
        # Запускаем компиляцию
        result = subprocess.run(
            cmd,
            cwd=str(work_dir),
            capture_output=True,
            text=True,
            timeout=30,
            shell=True if os.name == 'nt' else False
        )
        
        # Ищем скомпилированный файл
        amx_path = pwn_path.with_suffix('.amx')
        
        # Успешная компиляция
        if result.returncode == 0 and amx_path.exists() and amx_path.stat().st_size > 0:
            return True, "✅ Компиляция успешно завершена!", amx_path
        
        # Ошибка компиляции
        error_msg = result.stderr if result.stderr else result.stdout
        if not error_msg or error_msg.strip() == "":
            error_msg = "Неизвестная ошибка компиляции"
        
        # Обрезаем слишком длинные сообщения
        if len(error_msg) > 4000:
            error_msg = error_msg[:4000] + "\n\n... (сообщение обрезано)"
        
        return False, f"❌ **Ошибка компиляции:**\n```\n{error_msg}\n```", None
        
    except subprocess.TimeoutExpired:
        return False, "⏰ **Ошибка:** Превышено время компиляции (30 секунд)", None
    except FileNotFoundError:
        return False, f"❌ **Ошибка:** Компилятор не найден по пути `{PAWNCC_PATH}`\n\nПроверьте установку Pawn компилятора", None
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return False, f"❌ **Непредвиденная ошибка:** `{str(e)}`", None

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик входящих документов"""
    document = update.message.document
    
    # Проверяем, что это файл .pwn
    if not document.file_name or not document.file_name.lower().endswith('.pwn'):
        await update.message.reply_text(
            "❌ **Пожалуйста, отправьте файл с расширением `.pwn`**\n\n"
            "Отправьте файл исходного кода Pawn для компиляции.",
            parse_mode="Markdown"
        )
        return
    
    # Проверяем размер файла
    if document.file_size > MAX_FILE_SIZE:
        await update.message.reply_text(
            f"❌ **Файл слишком большой!**\n\n"
            f"Максимальный размер: {MAX_FILE_SIZE // (1024*1024)} MB\n"
            f"Ваш файл: {document.file_size // (1024*1024)} MB",
            parse_mode="Markdown"
        )
        return
    
    # Отправляем статус
    status_msg = await update.message.reply_text(
        "🔄 **Компиляция началась...**\n\n"
        f"Файл: `{document.file_name}`\n"
        "Пожалуйста, подождите...",
        parse_mode="Markdown"
    )
    
    # Создаем временную директорию
    with tempfile.TemporaryDirectory() as tmpdir:
        work_dir = Path(tmpdir)
        
        try:
            # Скачиваем файл
            file = await context.bot.get_file(document.file_id)
            pwn_path = work_dir / document.file_name
            await file.download_to_drive(pwn_path)
            
            logger.info(f"Downloaded file: {pwn_path}, size: {pwn_path.stat().st_size} bytes")
            
            # Компилируем
            success, message, amx_path = await compile_pawn(pwn_path, work_dir)
            
            if success and amx_path and amx_path.exists():
                # Отправляем успешный результат
                await status_msg.delete()
                
                with open(amx_path, 'rb') as amx_file:
                    output_filename = pwn_path.stem + '.amx'
                    await update.message.reply_document(
                        document=amx_file,
                        filename=output_filename,
                        caption=f"✅ **Компиляция успешна!**\n\nИсходный файл: `{document.file_name}`\nРазмер: {amx_path.stat().st_size:,} байт",
                        parse_mode="Markdown"
                    )
            else:
                # Отправляем ошибку
                await status_msg.edit_text(message, parse_mode="Markdown")
                
        except Exception as e:
            logger.error(f"Error processing document: {e}", exc_info=True)
            await status_msg.edit_text(
                f"❌ **Произошла ошибка при обработке файла:**\n\n```\n{str(e)}\n```",
                parse_mode="Markdown"
            )

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}", exc_info=context.error)
    
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ **Внутренняя ошибка бота**\n\n"
            "Пожалуйста, попробуйте позже или сообщите администратору.",
            parse_mode="Markdown"
        )

def main():
    """Запуск бота"""
    # Проверяем наличие компилятора при старте
    compiler_path = shutil.which(PAWNCC_PATH)
    if compiler_path:
        logger.info(f"Pawn compiler found at: {compiler_path}")
    else:
        logger.warning(f"Pawn compiler not found at: {PAWNCC_PATH}")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Регистрируем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info_command))
    
    # Регистрируем обработчик документов
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Регистрируем обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запускаем бота
    logger.info("Bot started! Waiting for .pwn files...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()