#!/usr/bin/env python3
"""
БЕСПЛАТНЫЙ Telegram бот — AI помощник (текст + изображения)
- Работает через Google Gemini API (бесплатно)
- Исправленная версия с правильными эндпоинтами
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
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyBBrbYgSv3bItNRs01g2UGpps3JRJZV9hg")

if TELEGRAM_TOKEN == "YOUR_BOT_TOKEN_HERE":
    raise ValueError("❌ Укажите TELEGRAM_TOKEN в переменных окружения!")
if GEMINI_API_KEY == "YOUR_GEMINI_API_KEY_HERE":
    raise ValueError("❌ Укажите GEMINI_API_KEY! Получить: https://aistudio.google.com/apikey")

# НАСТРОЙКА МОДЕЛИ — используем актуальное название
# Популярные бесплатные модели: gemini-2.0-flash-exp, gemini-1.5-flash, gemini-1.5-pro
GEMINI_MODEL = "gemini-2.5-pro"  # или "gemini-1.5-flash"

# Правильный URL для API (без /v1beta, используем /v1)
GEMINI_URL = f"https://generativelanguage.googleapis.com/v1/models/{GEMINI_MODEL}:generateContent"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

user_roles: Dict[int, str] = {}

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


def list_available_models():
    """(Опционально) Показывает доступные модели для отладки"""
    url = f"https://generativelanguage.googleapis.com/v1/models?key={GEMINI_API_KEY}"
    try:
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            models = resp.json().get("models", [])
            return [m["name"] for m in models if "generateContent" in m.get("supportedGenerationMethods", [])]
    except:
        pass
    return []


def gemini_request(prompt: str, system_prompt: str, image_base64: Optional[str] = None) -> str:
    """
    Запрос к Google Gemini API с правильным форматом.
    """
    url = f"{GEMINI_URL}?key={GEMINI_API_KEY}"
    
    # Формируем содержимое запроса
    if image_base64:
        # Мультимодальный запрос (текст + изображение)
        contents = [
            {
                "role": "user",
                "parts": [
                    {"text": f"{system_prompt}\n\nВопрос пользователя: {prompt}"},
                    {"inline_data": {"mime_type": "image/jpeg", "data": image_base64}}
                ]
            }
        ]
    else:
        # Текстовый запрос (системный промпт через обычный текст)
        contents = [
            {
                "role": "user",
                "parts": [{"text": f"{system_prompt}\n\nВопрос пользователя: {prompt}"}]
            }
        ]
    
    payload = {
        "contents": contents,
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 800,
            "topP": 0.95,
        }
    }
    
    try:
        response = requests.post(url, json=payload, timeout=60)
        
        if response.status_code == 200:
            data = response.json()
            # Извлекаем текст ответа
            if "candidates" in data and len(data["candidates"]) > 0:
                candidate = data["candidates"][0]
                if "content" in candidate and "parts" in candidate["content"]:
                    return candidate["content"]["parts"][0]["text"]
            return "❌ Не удалось извлечь ответ из API"
        else:
            error_text = response.text[:500]
            logger.error(f"Gemini API error {response.status_code}: {error_text}")
            
            # Если модель не найдена, предлагаем список доступных
            if response.status_code == 404:
                models = list_available_models()
                if models:
                    return f"❌ Модель {GEMINI_MODEL} не найдена.\nДоступные модели:\n" + "\n".join(models[:5]) + "\n\nИзмените GEMINI_MODEL в коде."
                else:
                    return f"❌ Модель {GEMINI_MODEL} не найдена. Проверьте API ключ или укажите другую модель (например, gemini-1.5-flash)"
            
            return f"❌ Ошибка Gemini API: {response.status_code}\n{error_text[:200]}"
    except Exception as e:
        logger.error(f"Gemini request error: {e}")
        return f"⚠️ Ошибка соединения: {str(e)[:100]}"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start — приветствие и выбор роли."""
    user_id = update.effective_user.id
    user_roles[user_id] = "sage"

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
    role_key = query.data.split("_")[1]

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

    await update.message.chat.send_action(action="typing")
    response = gemini_request(user_text, system_prompt)
    await update.message.reply_text(response[:4096])


async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка фотографий — нейросеть видит детали."""
    user_id = update.effective_user.id
    role_key = user_roles.get(user_id, "sage")
    system_prompt = ROLES[role_key]["prompt"]

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
    user_question = update.message.caption or "Что ты видишь на этом изображении? Опиши подробно в своём стиле."

    await update.message.chat.send_action(action="upload_photo")

    response = gemini_request(user_question, system_prompt, base64_image)
    await update.message.reply_text(response[:4096])


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Глобальный обработчик ошибок."""
    logger.error(f"Ошибка при обработке update: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "⚠️ Произошла внутренняя ошибка. Попробуйте ещё раз или напишите /start"
        )


def main():
    """Запуск бота."""
    print("🤖 Бот DeepSeek (без голоса) запускается...")
    print(f"Используемая модель: {GEMINI_MODEL}")
    
    # Проверка доступности модели
    print("Проверка API ключа и модели...")
    test_response = gemini_request("Привет! Ответь просто 'OK'", "Ты помощник для теста")
    if test_response.startswith("❌"):
        print(f"⚠️ Внимание: {test_response[:200]}")
        print("Возможные решения:")
        print("1. Проверьте правильность GEMINI_API_KEY")
        print("2. Убедитесь, что API активирован: https://aistudio.google.com/apikey")
        print("3. Попробуйте другую модель, изменив GEMINI_MODEL на:")
        print("   - gemini-1.5-flash")
        print("   - gemini-1.5-pro")
        print("   - gemini-2.0-flash-exp")
    else:
        print("✅ API ключ работает!")
    
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(change_role, pattern="^role_"))
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    app.add_error_handler(error_handler)

    print(f"✅ Бот запущен! Telegram токен: {TELEGRAM_TOKEN[:10]}...")
    print("Доступные роли: Хам, Мудрец, Бывшая")
    print("Поддерживается текст и фото\n")
    
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()