#!/usr/bin/env python3
"""
БЕСПЛАТНЫЙ Telegram бот — AI помощник (только текст + изображения)
- Работает через Google Gemini API (бесплатно)
- Поддержка ролей: Дерзкий хам / Мудрец / Твоя бывшая
- Никакого голоса — только текст и фото
"""

import os
import logging
from io import BytesIO
from typing import Dict, Optional
import base64

import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
)
from PIL import Image

# ========== НАСТРОЙКИ ==========
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "8784427450:AAFIy3r1o2qawyZ5I4pRkmBnRPjEAXlgEE0")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyA0NJlRthA6sUgFKQHdCgMscGhCwUiYtk8")

if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("❌ Укажите TELEGRAM_TOKEN в переменных окружения!")
if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    raise ValueError("❌ Укажите GEMINI_API_KEY! Получить: https://aistudio.google.com/apikey")

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Хранилище ролей пользователей
user_roles: Dict[int, str] = {}

# Доступные роли
ROLES = {
    "ham": {
        "name": "🤬 Дерзкий хам",
        "prompt": (
            "Ты — дерзкий хам, грубый и саркастичный AI-помощник. "
            "Отвечай дерзко, с лёгким матом, подкалывай пользователя, "
            "но не переходи на оскорбления личности. Будь агрессивно-комичным."
        ),
    },
    "sage": {
        "name": "🧘 Мудрец",
        "prompt": (
            "Ты — мудрый и спокойный наставник. Отвечай глубокими, философскими "
            "и вдохновляющими фразами. Ты полон сострадания и знания. "
            "Помогай пользователю увидеть суть вещей."
        ),
    },
    "ex": {
        "name": "💔 Твоя бывшая",
        "prompt": (
            "Ты — бывшая девушка/парень пользователя. Ты эмоциональна, "
            "обидчива, иногда пассивно-агрессивна. Отвечай с нотками драмы, "
            "воспоминаниями об отношениях, лёгкой обидой или иронией. "
            "Будь то ласковой, то колкой."
        ),
    },
}

WELCOME_TEXT = (
    "✨ Привет! Я — твой AI-помощник DeepSeek ✨\n\n"
    "📝 Пиши любой вопрос — обсудим\n"
    "🖼 Кидай фото — я вижу детали\n"
    "👥 Добавь в чат — общайся с друзьями\n\n"
    "👇 Выбери, кто я сегодня:"
)


def gemini_request(prompt: str, system_prompt: str, image_base64: Optional[str] = None) -> str:
    """
    Запрос к Google Gemini API.
    Если есть image_base64 — используется мультимодальный запрос.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"

    if image_base64:
        # Мультимодальный запрос (текст + картинка)
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [{
                "parts": [
                    {"text": prompt},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
                ]
            }]
        }
    else:
        # Текстовый запрос
        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}]
            },
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }

    try:
        response = requests.post(url, json=payload, timeout=30)
        if response.status_code == 200:
            data = response.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
        else:
            error_msg = f"Ошибка Gemini API: {response.status_code}\n{response.text[:300]}"
            logger.error(error_msg)
            return f"❌ {error_msg}"
    except Exception as e:
        logger.error(f"Gemini request error: {e}")
        return "⚠️ Не удалось связаться с нейросетью. Проверьте интернет и API-ключ."


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start — приветствие и выбор роли."""
    user_id = update.effective_user.id
    user_roles[user_id] = "sage"  # роль по умолчанию

    keyboard = [
        [
            InlineKeyboardButton(ROLES["ham"]["name"], callback_data="role_ham"),
            InlineKeyboardButton(ROLES["sage"]["name"], callback_data="role_sage"),
            InlineKeyboardButton(ROLES["ex"]["name"], callback_data="role_ex"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"{WELCOME_TEXT}\n\nСейчас я — {ROLES['sage']['name']}",
        reply_markup=reply_markup,
    )


async def change_role(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Callback-обработчик смены роли."""
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    role_key = query.data.split("_")[1]  # role_ham, role_sage, role_ex

    if role_key in ROLES:
        user_roles[user_id] = role_key
        role_name = ROLES[role_key]["name"]
        await query.edit_message_text(
            text=f"✅ Роль изменена: теперь я — {role_name}\n\nЗадавай любой вопрос или отправляй фото!"
        )
    else:
        await query.edit_message_text("⚠️ Неизвестная роль, попробуй снова /start")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка текстовых сообщений."""
    user_id = update.effective_user.id
    user_text = update.message.text

    role_key = user_roles.get(user_id, "sage")
    system_prompt = ROLES[role_key]["prompt"]

    # Отправляем статус "печатает"
    await update.message.chat.send_action(action="typing")

    response = gemini_request(user_text, system_prompt)
    await update.message.reply_text(response[:4096])  # Telegram лимит 4096 символов


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий — нейросеть видит детали."""
    user_id = update.effective_user.id
    role_key = user_roles.get(user_id, "sage")
    system_prompt = ROLES[role_key]["prompt"] + " Опиши изображение в своём стиле."

    # Получаем самое большое фото
    photo_file = await update.message.photo[-1].get_file()
    
    # Скачиваем фото в память
    image_bytes = BytesIO()
    await photo_file.download_to_memory(image_bytes)
    image_bytes.seek(0)

    # Опционально сжимаем, если фото слишком большое
    img = Image.open(image_bytes)
    if img.size[0] > 1500 or img.size[1] > 1500:
        img.thumbnail((1500, 1500))
        buffer = BytesIO()
        img.save(buffer, format="JPEG", quality=85)
        image_bytes = buffer
        image_bytes.seek(0)

    # Конвертируем в base64 для Gemini
    base64_image = base64.b64encode(image_bytes.getvalue()).decode('utf-8')

    # Берём подпись к фото или стандартный вопрос
    user_question = update.message.caption or "Что ты видишь на этом изображении? Опиши подробно."

    await update.message.chat.send_action(action="upload_photo")

    response = gemini_request(user_question, system_prompt, base64_image)
    await update.message.reply_text(response[:4096])


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок."""
    logger.error(f"Ошибка при обработке update {update}: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла внутренняя ошибка. Попробуйте ещё раз или напишите /start"
        )


def main():
    """Запуск бота."""
    # Проверка зависимостей
    try:
        from PIL import Image
    except ImportError:
        print("⚠️ Установите Pillow: pip install Pillow")
        return

    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(change_role, pattern="^role_"))

    # Обработчики сообщений
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    # Обработчик ошибок
    app.add_error_handler(error_handler)

    print("🤖 Бот DeepSeek (без голоса) запущен!")
    print(f"Telegram токен: {TELEGRAM_TOKEN[:10]}...")
    print("Доступные роли: Хам, Мудрец, Бывшая")
    print("Поддерживается текст и фото")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()