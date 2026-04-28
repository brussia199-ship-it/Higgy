import telebot
import requests
import json
import os

# ========== НАСТРОЙКИ ==========
BOT_TOKEN = "8781058326:AAEyJEbz9V6YvXIQy9JF90uRyI2nskDXw0Y"  # ВСТАВЬТЕ ТОКЕН

# Каналы для подписки
REQUIRED_CHANNELS = [
    "@russiakrmp",
    "@UralPwn"
]
# ================================

bot = telebot.TeleBot(BOT_TOKEN)

def check_subscription(user_id):
    """Проверяет подписку"""
    for channel in REQUIRED_CHANNELS:
        try:
            status = bot.get_chat_member(channel, user_id).status
            if status in ["left", "kicked"]:
                return False, channel
        except:
            return False, channel
    return True, None

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    subscribed, channel = check_subscription(user_id)
    
    if not subscribed:
        markup = telebot.types.InlineKeyboardMarkup()
        markup.add(telebot.types.InlineKeyboardButton(
            text="📢 Подписаться", 
            url=f"https://t.me/{channel[1:]}"
        ))
        markup.add(telebot.types.InlineKeyboardButton(
            text="✅ Проверить", 
            callback_data="check"
        ))
        bot.reply_to(message, 
            "⚠️ Подпишитесь на канал: " + channel,
            reply_markup=markup)
        return
    
    bot.reply_to(message, 
        "✅ Бот готов!\n\n"
        "Просто отправьте мне файл .pwn\n"
        "Я отправлю готовый .amx")

@bot.callback_query_handler(func=lambda call: call.data == "check")
def check(call):
    subscribed, channel = check_subscription(call.from_user.id)
    if subscribed:
        bot.edit_message_text("✅ Доступ открыт! Отправляйте .pwn", 
                            call.message.chat.id, call.message.message_id)
    else:
        bot.answer_callback_query(call.id, "Подпишитесь сначала!")

@bot.message_handler(content_types=['document'])
def compile_pwn(message):
    # Проверка подписки
    subscribed, _ = check_subscription(message.from_user.id)
    if not subscribed:
        bot.reply_to(message, "❌ Подпишитесь на каналы!")
        return
    
    # Проверка расширения
    if not message.document.file_name.endswith('.pwn'):
        bot.reply_to(message, "❌ Отправьте файл .pwn")
        return
    
    bot.reply_to(message, "⚙️ Компилирую...")
    
    try:
        # Скачиваем файл
        file_info = bot.get_file(message.document.file_id)
        pwn_content = bot.download_file(file_info.file_path)
        
        # Отправляем на бесплатный онлайн компилятор
        files = {'file': (message.document.file_name, pwn_content)}
        response = requests.post(
            'https://pawn-compiler-api.herokuapp.com/compile',
            files=files,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            if result.get('success'):
                # Отправляем скомпилированный файл
                amx_content = bytes.fromhex(result['amx_hex'])
                bot.send_document(
                    message.chat.id,
                    (message.document.file_name.replace('.pwn', '.amx'), amx_content),
                    caption="✅ Компиляция успешна!"
                )
            else:
                error_msg = result.get('error', 'Ошибка компиляции')[:1000]
                bot.reply_to(message, f"❌ Ошибка:\n{error_msg}")
        else:
            bot.reply_to(message, "❌ Сервер компиляции временно недоступен")
            
    except Exception as e:
        bot.reply_to(message, f"❌ Ошибка: {str(e)[:200]}")

# Запуск
if __name__ == "__main__":
    print("Бот запущен!")
    bot.infinity_polling()