import os
import sys
import threading
import asyncio
import logging
import requests
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from flask import Flask

# --- ১. লগিং সেটআপ ---
logging.basicConfig(level=logging.INFO, 
                    format='[%(asctime)s] - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('TeraboxBot')


# --- ২. কনফিগারেশন লোড করা ---
# Note: Log Channel সম্পর্কিত কোনো ভেরিয়েবল আর ব্যবহার করা হচ্ছে না
BOT_TOKEN = os.environ.get("BOT_TOKEN")
API_ID = os.environ.get("API_ID")
API_HASH = os.environ.get("API_HASH")
SESSION_STRING = os.environ.get("SESSION_STRING")
PORT = int(os.environ.get("PORT", 8080))

TERABOX_API_URL = "https://terabox-api.vercel.app/api?url="
CLIENT_NAME = "terabox_bot_session" 


# --- ৩. কনফিগারেশন বৈধতা যাচাই ---
if not all([BOT_TOKEN, API_ID, API_HASH]):
    logger.critical("FATAL: BOT_TOKEN, API_ID, and API_HASH must be set.")
    sys.exit(1)

try:
    API_ID_INT = int(API_ID)
except ValueError:
    logger.critical("FATAL: API_ID must be a valid integer.")
    sys.exit(1)


# --- ৪. ক্লায়েন্ট ইনিশিয়ালাইজেশন ---
app = Flask(__name__)

try:
    if SESSION_STRING:
        bot = Client(
            CLIENT_NAME, 
            api_id=API_ID_INT,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN,
            session_string=SESSION_STRING
        )
    else:
        bot = Client(
            CLIENT_NAME, 
            api_id=API_ID_INT,
            api_hash=API_HASH,
            bot_token=BOT_TOKEN
        )
    logger.info("Pyrogram Client initialized.")

except Exception as e:
    logger.critical(f"Client initialization failed: {e}")
    sys.exit(1)


# --- ৫. ফ্লাস্ক রুট ---
@app.route('/')
def home():
    return "✅ Terabox Watch Bot is Running Successfully!"


# --- ৬. API লজিক ফাংশন ---

async def get_terabox_link(link: str):
    """Terabox API কল করে সরাসরি ডাউনলোড লিংক বের করে।"""
    api_url = f"{TERABOX_API_URL}{link}"
    
    try:
        res = requests.get(api_url, timeout=15).json()
        if res.get("success") and res.get("downloadLink"):
            return res["downloadLink"]
        else:
            return None
    except requests.exceptions.RequestException:
        return "NETWORK_ERROR"
    except Exception as e:
        logger.error(f"Unknown error during API call: {e}")
        return "UNKNOWN_ERROR"


# --- ৭. Pyrogram হ্যান্ডলার্স ---

@bot.on_message(filters.command("start"))
async def start_handler(_, msg):
    """/start কমান্ডের উত্তর দেয়"""
    logger.info(f"Received /start from user {msg.from_user.id}")
    
    await msg.reply_text(
        "👋 **স্বাগতম! আমি Terabox Watch Bot!**\n\n"
        "আমাকে শুধু একটা **বৈধ Terabox লিংক** পাঠান।\n"
        "আমি সাথে সাথে আপনাকে সরাসরি ভিডিও দেখার লিংক তৈরি করে দেব 🔥\n\n"
        "এখনই চেষ্টা করুন!",
        disable_web_page_preview=True
    )

@bot.on_message(filters.text & ~filters.command("start"))
async def get_video_handler(_, msg):
    link = msg.text.strip()
    
    if "terabox" not in link.lower():
        return await msg.reply_text("❌ দয়া করে একটি বৈধ Terabox লিংক দিন।")

    logger.info(f"Processing link from user {msg.from_user.id}: {link}")
    waiting_msg = await msg.reply_text("⏳ আপনার লিংক প্রসেস করা হচ্ছে... দয়া করে অপেক্ষা করুন।")
    
    video_url = await get_terabox_link(link)
    reply_markup = None
    
    if video_url == "NETWORK_ERROR":
        text = "⚠️ API এর সাথে যোগাযোগ করা যাচ্ছে না বা এটি সময়মত সাড়া দিচ্ছে না। কিছুক্ষণ পর আবার চেষ্টা করুন।"
    elif video_url == "UNKNOWN_ERROR":
        text = "❌ একটি অপ্রত্যাশিত ভুল হয়েছে। সার্ভার লগ চেক করুন।"
    elif video_url:
        text = "✅ **সফল!** ভিডিও রেডি! এখনই দেখতে পারো 👇"
        reply_markup = InlineKeyboardMarkup(
            [[InlineKeyboardButton("▶️ Watch Now", url=video_url)]]
        )
    else:
        text = "⚠️ ভিডিও বের করা যায়নি। সার্ভারের সমস্যা হতে পারে বা লিংকটি অবৈধ/ডিলিট করা হয়েছে।"
    
    await waiting_msg.edit_text(text, reply_markup=reply_markup)


# --- ৮. মাল্টিথ্রেডিং এবং স্টার্টআপ লজিক ---

if __name__ == "__main__":
    
    def start_pyrogram_thread():
        """Pyrogram কে একটি আলাদা থ্রেডে, ম্যানুয়াল asyncio লুপে চালানো।"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def run_pyrogram():
            try:
                await bot.start()
                logger.info("✅ [STATUS] Pyrogram bot online and ready to handle updates.")
                
                # শুধুমাত্র অপেক্ষার জন্য
                await asyncio.Future() 
                
            except Exception as e:
                logger.error(f"❌ [PYROGRAM THREAD ERROR] Failure: {e}")
            finally:
                logger.info("🛑 [STATUS] Pyrogram thread terminated.")
                
        loop.run_until_complete(run_pyrogram())
        
    # বটকে একটি আলাদা থ্রেডে চালানো
    threading.Thread(target=start_pyrogram_thread, name='PyrogramThread').start()
    
    # ফ্লাস্ক অ্যাপকে মূল থ্রেডে শুরু করা
    logger.info("🚀 [STATUS] Flask web server starting...")
    app.run(host="0.0.0.0", port=PORT)
