import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CRYPTOBOT_API_KEY = os.getenv("CRYPTOBOT_API_KEY")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "7673683792").split(",") if x]
CRYPTOBOT_API_URL = "https://pay.crypt.bot/api"