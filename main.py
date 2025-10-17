import os
import sys
import asyncio
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask
from threading import Thread

# Logging
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] - %(message)s')
logger = logging.getLogger("TeraboxBot")

# Env variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH")
PORT = int(os.environ.get("PORT", 8080))

if not all([BOT_TOKEN, API_ID, API_HASH]):
    logger.critical("BOT_TOKEN, API_ID, API_HASH must be set!")
    sys.exit(1)

# Flask setup
app = Flask(__name__)

@app.route('/')
def home():
    return "✅ Terabox Watch Bot is Running Successfully!"

# Pyrogram client
bot = Client("terabox", bot_token=BOT_TOKEN, api_id=API_ID, api_hash=API_HASH)

# Terabox API function
async def get_terabox_link(link: str):
    try:
        api = f"https://terabox-api.vercel.app/api?url={link}"
        res = requests.get(api, timeout=15).json()
        if res.get("success") and res.get("downloadLink"):
            return res["downloadLink"]
    except Exception as e:
        logger.error(f"API Error: {e}")
    return None

# Handlers
@bot.on_message(filters.command("start"))
async def start(_, msg):
    await msg.reply_text(
        "👋 হ্যালো!\n\nআমি **Terabox Watch Bot** 🎬\n\n"
        "আমাকে শুধু একটা **Terabox লিংক** পাঠাও, আমি তোমাকে সরাসরি ভিডিও দেখার লিংক দিয়ে দেব 🔥"
    )

@bot.on_message(filters.text & ~filters.command("start"))
async def process_link(_, msg):
    link = msg.text.strip()
    if "terabox" not in link:
        return await msg.reply_text("❌ দয়া করে একটি বৈধ Terabox লিংক পাঠাও।")

    wait = await msg.reply_text("⏳ আপনার লিংক প্রসেস হচ্ছে...")

    video_url = await get_terabox_link(link)
    if not video_url:
        return await wait.edit_text("⚠️ ভিডিও লিংক বের করা যায়নি। আবার চেষ্টা করো।")

    await wait.edit_text(
        "✅ **ভিডিও রেডি!** এখনই দেখতে পারো 👇",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Watch Now", url=video_url)]]
        )
    )

# Asyncio-based main runner
async def main():
    # Flask কে আলাদা থ্রেডে চালানো হচ্ছে
    Thread(target=lambda: app.run(host="0.0.0.0", port=PORT)).start()

    await bot.start()
    logger.info("✅ Terabox Bot started successfully and listening for updates.")
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
